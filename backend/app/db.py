from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable, Optional

import asyncpg
import orjson

logger = logging.getLogger(__name__)


async def init_db_pool(dsn: str) -> asyncpg.pool.Pool:
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
    async with pool.acquire() as conn:
        await _apply_schema(conn)
    return pool


async def close_db_pool(pool: Optional[asyncpg.pool.Pool]) -> None:
    if pool is None:
        return
    await pool.close()


async def _apply_schema(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scan_runs (
            id BIGSERIAL PRIMARY KEY,
            domain TEXT NOT NULL,
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at TIMESTAMPTZ,
            total INTEGER DEFAULT 0,
            duration_ms INTEGER,
            source TEXT DEFAULT 'pipeline'
        );
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS subdomains (
            id BIGSERIAL PRIMARY KEY,
            domain TEXT NOT NULL,
            name TEXT NOT NULL,
            ips JSONB,
            cname TEXT,
            http_status INTEGER,
            tls BOOLEAN,
            server TEXT,
            first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (domain, name)
        );
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scan_run_entries (
            run_id BIGINT REFERENCES scan_runs(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            PRIMARY KEY (run_id, name)
        );
        """
    )
    await conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_scan_runs_domain_completed
            ON scan_runs (domain, completed_at DESC NULLS LAST);
        """
    )
    await conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_subdomains_domain
            ON subdomains (domain);
        """
    )


async def fetch_recent_scans(
    pool: Optional[asyncpg.pool.Pool], limit: int
) -> list[dict]:
    if pool is None:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, domain, completed_at, total, duration_ms
            FROM scan_runs
            WHERE completed_at IS NOT NULL
            ORDER BY completed_at DESC
            LIMIT $1
            """,
            limit,
        )
    results: list[dict] = []
    for row in rows:
        completed = row["completed_at"]
        results.append(
            {
                "id": row["id"],
                "domain": row["domain"],
                "timestamp": completed.isoformat() if completed else None,
                "total": row["total"],
                "duration_ms": row["duration_ms"],
            }
        )
    return results


async def fetch_runs_for_domain(
    pool: Optional[asyncpg.pool.Pool], domain: str, limit: int
) -> list[dict]:
    if pool is None:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, started_at, completed_at, total, duration_ms
            FROM scan_runs
            WHERE domain = $1
            ORDER BY completed_at DESC NULLS LAST, started_at DESC
            LIMIT $2
            """,
            domain,
            limit,
        )
    runs: list[dict] = []
    for row in rows:
        completed = row["completed_at"] or row["started_at"]
        runs.append(
            {
                "id": row["id"],
                "domain": domain,
                "timestamp": completed.isoformat() if completed else None,
                "total": row["total"],
                "duration_ms": row["duration_ms"],
            }
        )
    return runs


async def load_domain_snapshot(
    pool: Optional[asyncpg.pool.Pool], domain: str
) -> tuple[list[dict], Optional[dict]]:
    if pool is None:
        return [], None
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT name, ips, cname, http_status, tls, server
            FROM subdomains
            WHERE domain = $1
            ORDER BY name
            """,
            domain,
        )
        latest_run = await conn.fetchrow(
            """
            SELECT completed_at, total, duration_ms
            FROM scan_runs
            WHERE domain = $1 AND completed_at IS NOT NULL
            ORDER BY completed_at DESC
            LIMIT 1
            """,
            domain,
        )
    entries: list[dict] = []
    for row in rows:
        entries.append(
            {
                "name": row["name"],
                "ips": row["ips"] or [],
                "cname": row["cname"] or "",
                "http_status": row["http_status"],
                "tls": bool(row["tls"]),
                "server": row["server"] or "",
            }
        )
    meta = None
    if latest_run:
        completed = latest_run["completed_at"]
        meta = {
            "cached_at": completed.isoformat() if completed else None,
            "total_unique": latest_run["total"],
            "duration_ms": latest_run["duration_ms"],
        }
    return entries, meta


async def start_scan_run(pool: Optional[asyncpg.pool.Pool], domain: str) -> Optional[int]:
    if pool is None:
        return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO scan_runs (domain)
            VALUES ($1)
            RETURNING id
            """,
            domain,
        )
    return row["id"] if row else None


async def complete_scan_run(
    pool: Optional[asyncpg.pool.Pool],
    run_id: Optional[int],
    *,
    total: int,
    duration_ms: int,
) -> None:
    if pool is None or run_id is None:
        return
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE scan_runs
            SET completed_at = $2,
                total = $3,
                duration_ms = $4
            WHERE id = $1
            """,
            run_id,
            datetime.now(timezone.utc),
            total,
            duration_ms,
        )


async def upsert_subdomains(
    pool: Optional[asyncpg.pool.Pool],
    domain: str,
    entries: Iterable[dict],
    run_id: Optional[int] = None,
) -> None:
    if pool is None:
        return
    payload = list(entries)
    if not payload:
        return
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.executemany(
                """
                INSERT INTO subdomains (domain, name, ips, cname, http_status, tls, server, first_seen, last_seen)
                VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7, NOW(), NOW())
                ON CONFLICT (domain, name) DO UPDATE SET
                    ips = EXCLUDED.ips,
                    cname = EXCLUDED.cname,
                    http_status = EXCLUDED.http_status,
                    tls = EXCLUDED.tls,
                    server = EXCLUDED.server,
                    last_seen = NOW()
                """,
                [
                    (
                        domain,
                        entry["name"],
                        orjson.dumps(list(entry.get("ips", []))).decode("utf-8"),
                        entry.get("cname") or None,
                        entry.get("http_status"),
                        bool(entry.get("tls")),
                        entry.get("server") or None,
                    )
                    for entry in payload
                ],
            )
            if run_id is not None:
                await conn.executemany(
                    """
                    INSERT INTO scan_run_entries (run_id, name)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                    """,
                    [(run_id, entry["name"]) for entry in payload],
                )
