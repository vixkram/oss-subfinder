from __future__ import annotations

import asyncio
import logging
import ssl
from typing import List, Optional, Tuple

import aiohttp
import aiodns

from .config import get_settings
from .utils import now_iso, sanitize_domain

logger = logging.getLogger(__name__)

_dns_resolver: Optional[aiodns.DNSResolver] = None


def _get_resolver() -> aiodns.DNSResolver:
    global _dns_resolver
    if _dns_resolver is None:
        _dns_resolver = aiodns.DNSResolver()
    return _dns_resolver


async def _resolve_dns(name: str) -> Tuple[List[str], Optional[str]]:
    resolver = _get_resolver()
    ips: List[str] = []
    cname: Optional[str] = None
    for record_type in ("A", "AAAA"):
        try:
            answers = await resolver.query(name, record_type)
            ips.extend(answer.host for answer in answers)
        except aiodns.error.DNSError:
            continue
    try:
        cname_answers = await resolver.query(name, "CNAME")
        if cname_answers:
            cname = cname_answers[0].host.rstrip(".").lower()
    except aiodns.error.DNSError:
        cname = None
    deduped_ips = list(dict.fromkeys(ips))
    return deduped_ips, cname


async def _attempt_request(session: aiohttp.ClientSession, url: str) -> Tuple[Optional[int], str]:
    for method in ("HEAD", "GET"):
        try:
            async with session.request(method, url, allow_redirects=True) as response:
                await response.read()
                return response.status, response.headers.get("Server", "")
        except aiohttp.ClientResponseError as exc:
            if method == "HEAD" and exc.status in {403, 405}:
                continue
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue
    return None, ""


async def _check_tls(host: str, timeout: float) -> bool:
    ssl_ctx = ssl.create_default_context()
    writer = None
    success = False
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host=host, port=443, ssl=ssl_ctx, server_hostname=host),
            timeout=timeout,
        )
        success = True
    except Exception:
        success = False
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
    return success


async def probe_host(
    domain: str,
    *,
    session: Optional[aiohttp.ClientSession] = None,
    ips: Optional[List[str]] = None,
    cname: Optional[str] = None,
    skip_rate_limit: bool = False,
) -> dict:
    _ = skip_rate_limit  # maintained for backwards compatibility
    normalized = sanitize_domain(domain)
    if not normalized:
        raise ValueError("invalid domain for status probe")

    settings = get_settings()
    if ips is None or cname is None:
        try:
            resolved_ips, resolved_cname = await _resolve_dns(normalized)
        except Exception as exc:
            logger.debug("DNS resolution failed for %s: %s", normalized, exc)
            resolved_ips, resolved_cname = [], None
        if ips is None:
            ips = resolved_ips
        if cname is None:
            cname = resolved_cname

    client_session = session
    owned_session = False
    if client_session is None:
        timeout = aiohttp.ClientTimeout(total=settings.http_timeout)
        client_session = aiohttp.ClientSession(timeout=timeout)
        owned_session = True

    http_status: Optional[int] = None
    server_header = ""
    tls_supported = False

    try:
        status_https, server_https = await _attempt_request(client_session, f"https://{normalized}")
        if status_https:
            http_status = status_https
            server_header = server_https
            tls_supported = True
        else:
            status_http, server_http = await _attempt_request(client_session, f"http://{normalized}")
            if status_http:
                http_status = status_http
                server_header = server_http
        if not tls_supported:
            tls_supported = await _check_tls(normalized, settings.http_timeout)
    finally:
        if owned_session:
            await client_session.close()

    result = {
        "domain": normalized,
        "ips": ips or [],
        "http_status": http_status,
        "tls": bool(tls_supported),
        "server": server_header or "",
        "cname": cname or "",
        "last_probe": now_iso(),
    }

    return result
