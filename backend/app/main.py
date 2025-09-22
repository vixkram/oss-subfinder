from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

import orjson
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .config import get_settings
from .db import (
    close_db_pool,
    fetch_recent_scans,
    fetch_runs_for_domain,
    init_db_pool,
    load_domain_snapshot,
)
from .search_pipeline import SearchPipeline
from .status_probe import probe_host
from .utils import format_sse, now_iso, sanitize_domain
from .whois_ import lookup_whois
from .rate_limiter import RateLimitQuota, RateLimiter, enforce_rate_limit


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return orjson.dumps(payload).decode("utf-8")


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
root_logger = logging.getLogger()
root_logger.handlers = [handler]
root_logger.setLevel(logging.INFO)

app = FastAPI(title="oss-subfinder", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    settings = get_settings()
    db_pool = None
    if settings.postgres_dsn:
        try:
            db_pool = await init_db_pool(settings.postgres_dsn)
        except Exception as exc:
            logging.getLogger(__name__).exception("Failed to initialize Postgres pool: %s", exc)
            db_pool = None
    elif settings.enable_history:
        logging.getLogger(__name__).warning("Postgres DSN not configured; history storage disabled")
    app.state.db_pool = db_pool
    rate_limiter: Optional[RateLimiter] = None
    if settings.rate_limit_requests > 0:
        rate_limiter = RateLimiter(
            requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window,
            trust_x_forwarded_for=settings.trust_x_forwarded_for,
        )
    app.state.rate_limiter = rate_limiter
    app.state.pipeline = SearchPipeline(db_pool)
    logging.getLogger(__name__).info("startup complete", extra={"component": "startup"})


@app.on_event("shutdown")
async def on_shutdown() -> None:
    db_pool = getattr(app.state, "db_pool", None)
    await close_db_pool(db_pool)


def get_pipeline() -> SearchPipeline:
    return app.state.pipeline


def get_db_pool():
    return getattr(app.state, "db_pool", None)


@app.get("/healthz")
async def healthcheck() -> dict:
    return {"status": "ok", "timestamp": now_iso()}


def _merge_rate_headers(headers: dict[str, str], quota: Optional[RateLimitQuota]) -> dict[str, str]:
    if quota is None:
        return headers
    headers = dict(headers)
    headers.update(RateLimiter.headers_from_quota(quota))
    return headers


@app.get("/api/search")
async def api_search(
    domain: str = Query(..., description="Domain to enumerate"),
    refresh: bool = Query(False, description="Force refresh even if cached"),
    rate_quota: Optional[RateLimitQuota] = Depends(enforce_rate_limit),
) -> StreamingResponse:
    normalized = sanitize_domain(domain)
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid domain")
    pipeline = get_pipeline()

    async def event_stream() -> AsyncIterator[bytes]:
        try:
            async for event in pipeline.search(normalized, refresh=refresh):
                yield format_sse(event)
        except Exception as exc:
            logging.getLogger(__name__).exception("Search failed for %s", normalized)
            yield format_sse({"stage": "error", "domain": normalized, "error": str(exc)}, event="error")

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    headers = _merge_rate_headers(headers, rate_quota)
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)


@app.get("/api/whois")
async def api_whois(
    domain: str = Query(..., description="Domain to look up"),
    rate_quota: Optional[RateLimitQuota] = Depends(enforce_rate_limit),
) -> JSONResponse:
    normalized = sanitize_domain(domain)
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid domain")
    result = await lookup_whois(normalized)
    if result is None:
        raise HTTPException(status_code=404, detail="WHOIS data not found")
    response = JSONResponse(result)
    response.headers.update(RateLimiter.headers_from_quota(rate_quota))
    return response


@app.get("/api/status")
async def api_status(
    domain: str = Query(..., description="Hostname to probe"),
    rate_quota: Optional[RateLimitQuota] = Depends(enforce_rate_limit),
) -> JSONResponse:
    normalized = sanitize_domain(domain)
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid domain")
    result = await probe_host(normalized)
    response = JSONResponse(result)
    response.headers.update(RateLimiter.headers_from_quota(rate_quota))
    return response


@app.get("/api/history")
async def api_history(
    domain: str = Query(..., description="Domain to inspect history for"),
    rate_quota: Optional[RateLimitQuota] = Depends(enforce_rate_limit),
) -> JSONResponse:
    normalized = sanitize_domain(domain)
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid domain")
    pool = get_db_pool()
    entries, meta = await load_domain_snapshot(pool, normalized)
    settings = get_settings()
    runs = await fetch_runs_for_domain(pool, normalized, settings.per_domain_history_limit)
    payload = {
        "domain": normalized,
        "cached": meta.get("cached_at") if meta else None,
        "total": meta.get("total_unique") if meta else len(entries),
        "results": entries,
        "runs": runs,
    }
    response = JSONResponse(payload)
    response.headers.update(RateLimiter.headers_from_quota(rate_quota))
    return response


@app.get("/api/recent")
async def api_recent(
    limit: int = Query(10, ge=1, le=100),
    rate_quota: Optional[RateLimitQuota] = Depends(enforce_rate_limit),
) -> JSONResponse:
    settings = get_settings()
    effective_limit = min(limit, settings.recent_scans_limit)
    pool = get_db_pool()
    recent = await fetch_recent_scans(pool, effective_limit)
    response = JSONResponse({"recent": recent})
    response.headers.update(RateLimiter.headers_from_quota(rate_quota))
    return response


@app.get("/")
async def root(request: Request) -> JSONResponse:
    settings = get_settings()
    docs_link = request.url_for("swagger_ui_html") if app.docs_url else None
    redoc_link = request.url_for("redoc_html") if app.redoc_url else None
    payload = {
        "name": app.title,
        "version": app.version,
        "status": "ok",
        "links": {
            "docs": docs_link,
            "redoc": redoc_link,
            "api_reference": "https://github.com/vixkram/oss-subfinder/tree/main/docs/api.md",
            "source": "https://github.com/vixkram/oss-subfinder",
            "demo": "https://oss-subfinder.vikk.dev/",
        },
        "features": {
            "history_enabled": settings.enable_history and bool(get_db_pool()),
            "massdns_available": bool(settings.massdns_path()),
        },
        "rate_limit": {
            "requests": settings.rate_limit_requests,
            "window_seconds": settings.rate_limit_window,
        },
    }
    return JSONResponse(payload)
