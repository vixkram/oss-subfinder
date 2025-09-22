from __future__ import annotations

import asyncio
import logging
from asyncio.subprocess import PIPE
import time
from typing import AsyncIterator, Dict, List, Optional, Tuple

import aiohttp
import aiodns
from asyncpg.pool import Pool

from .config import get_settings
from .db import (
    complete_scan_run,
    load_domain_snapshot,
    start_scan_run,
    upsert_subdomains,
)
from .status_probe import probe_host
from .utils import (
    chunked,
    is_subdomain,
    iter_crtsh_names,
    normalize_hostname,
    now_iso,
    sanitize_domain,
    unique_everseen,
)

logger = logging.getLogger(__name__)


class SearchPipeline:
    def __init__(self, db_pool: Optional[Pool]):
        self.db_pool = db_pool
        self.settings = get_settings()

    async def search(self, domain: str, refresh: bool = False) -> AsyncIterator[dict]:
        normalized = sanitize_domain(domain)
        if not normalized:
            raise ValueError("invalid domain")

        cached_results: Dict[str, dict] = {}
        cached_meta = None
        if self.db_pool is not None:
            cached_list, cached_meta = await load_domain_snapshot(self.db_pool, normalized)
            if cached_list:
                for entry in cached_list:
                    cached_results[entry["name"]] = entry
                yield {"stage": "cache_hit", "domain": normalized, "count": len(cached_results)}
                for entry in cached_results.values():
                    yield {"type": "entry", **entry}
                if not refresh:
                    payload = {"stage": "done", "domain": normalized, "total_unique": len(cached_results)}
                    if cached_meta:
                        payload.update(cached_meta)
                    yield payload
                    return

        yield {"stage": "started", "domain": normalized}
        run_id = await start_scan_run(self.db_pool, normalized)
        started_at = time.monotonic()

        candidates = await self._collect_candidates(normalized)
        yield {"stage": "crt_sh_found", "domain": normalized, "count": len(candidates)}

        resolver_name = "massdns" if self.settings.massdns_path() else "aiodns"
        yield {"stage": "resolving", "domain": normalized, "resolver": resolver_name, "count": len(candidates)}

        for seen_name in list(cached_results.keys()):
            if seen_name not in candidates:
                candidates.append(seen_name)

        entries: Dict[str, dict] = dict(cached_results)
        persisted = False
        session_timeout = aiohttp.ClientTimeout(total=self.settings.http_timeout)
        try:
            async with aiohttp.ClientSession(timeout=session_timeout) as session:
                async for entry in self._resolve_and_probe(candidates, session=session):
                    if not entry:
                        continue
                    entries[entry["name"]] = entry
                    yield {"type": "entry", **entry}

            all_entries, duration_ms = await self._persist_results(
                normalized,
                run_id,
                entries,
                started_at,
            )

            payload = {
                "stage": "done",
                "domain": normalized,
                "total_unique": len(all_entries),
                "cached_at": now_iso(),
                "duration_ms": duration_ms,
            }
            yield payload
            persisted = True
        finally:
            if not persisted:
                try:
                    await self._persist_results(normalized, run_id, entries, started_at)
                except Exception as exc:  # pragma: no cover - defensive guard
                    logger.warning("Failed to persist incomplete scan for %s: %s", normalized, exc)

    async def _collect_candidates(self, domain: str) -> List[str]:
        candidates: List[str] = []
        crt_names = await self._fetch_crtsh(domain)
        candidates.extend(crt_names)
        candidates.append(domain)
        brute = self._build_bruteforce(domain)
        candidates.extend(brute)
        filtered = [name for name in candidates if is_subdomain(name, domain)]
        return unique_everseen(filtered)

    async def _fetch_crtsh(self, domain: str) -> List[str]:
        settings = self.settings
        url = f"https://crt.sh/?q=%25.{domain}&output=json"
        session_timeout = aiohttp.ClientTimeout(total=settings.crtsh_timeout)
        headers = {"User-Agent": settings.crtsh_user_agent}
        names: List[str] = []
        try:
            async with aiohttp.ClientSession(timeout=session_timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning("crt.sh returned status %s for %s", response.status, domain)
                        return []
                    data = await response.json(content_type=None)
        except asyncio.TimeoutError:
            logger.warning("crt.sh timed out for %s", domain)
            return []
        except (aiohttp.ClientError, ValueError) as exc:
            logger.warning("crt.sh fetch failed for %s: %s", domain, exc)
            return []
        for row in data:
            name_value = row.get("name_value")
            if not name_value:
                continue
            for raw in iter_crtsh_names(name_value):
                normalized = normalize_hostname(raw)
                if not normalized:
                    continue
                if is_subdomain(normalized, domain):
                    names.append(normalized)
        return unique_everseen(names)

    def _build_bruteforce(self, domain: str) -> List[str]:
        base_words = [word.strip().lower() for word in self.settings.bruteforce_words if word.strip()]
        extra_words = [word.strip().lower() for word in self.settings.extra_bruteforce_words() if word.strip()]
        combined = unique_everseen(base_words + extra_words)
        return [f"{word}.{domain}" for word in combined]

    async def _resolve_and_probe(self, candidates: List[str], session: aiohttp.ClientSession) -> AsyncIterator[Optional[dict]]:
        massdns_bin = self.settings.massdns_path()
        resolved: List[Tuple[str, dict]] = []
        if massdns_bin:
            async for name, record in self._resolve_with_massdns(candidates, massdns_bin):
                resolved.append((name, record))
        else:
            async for name, record in self._resolve_with_aiodns(candidates):
                resolved.append((name, record))

        async for entry in self._probe_concurrently(resolved, session):
            yield entry

    async def _probe_concurrently(
        self,
        items: List[Tuple[str, dict]],
        session: aiohttp.ClientSession,
    ) -> AsyncIterator[Optional[dict]]:
        if not items:
            return
        semaphore = asyncio.Semaphore(max(1, self.settings.probe_concurrency))

        async def worker(name: str, record: dict) -> Optional[dict]:
            async with semaphore:
                try:
                    return await self._finalize_entry(name, record, session)
                except Exception as exc:  # pragma: no cover - defensive guard
                    logger.debug("Probe worker failed for %s: %s", name, exc)
                    return None

        tasks = [asyncio.create_task(worker(name, record)) for name, record in items]
        for task in asyncio.as_completed(tasks):
            result = await task
            if result:
                yield result

    async def _finalize_entry(self, name: str, record: dict, session: aiohttp.ClientSession) -> Optional[dict]:
        ips = record.get("ips", [])
        cname = record.get("cname")
        if not ips and not cname:
            return None
        try:
            status = await probe_host(
                name,
                session=session,
                ips=ips,
                cname=cname,
                skip_rate_limit=True,
            )
        except Exception as exc:
            logger.debug("Status probe failed for %s: %s", name, exc)
            status = {
                "domain": name,
                "ips": ips,
                "cname": cname or "",
                "http_status": None,
                "tls": False,
                "server": "",
            }
        return {
            "name": status.get("domain", name),
            "ips": status.get("ips", ips) or [],
            "cname": status.get("cname", cname or "") or "",
            "http_status": status.get("http_status"),
            "tls": bool(status.get("tls")),
            "server": status.get("server", "") or "",
        }

    async def _persist_results(
        self,
        domain: str,
        run_id: Optional[int],
        entries: Dict[str, dict],
        started_at: float,
    ) -> Tuple[List[dict], int]:
        all_entries = sorted(entries.values(), key=lambda item: item["name"])
        duration_ms = int((time.monotonic() - started_at) * 1000)
        if self.db_pool is not None and run_id is not None:
            await upsert_subdomains(self.db_pool, domain, all_entries, run_id=run_id)
            await complete_scan_run(
                self.db_pool,
                run_id,
                total=len(all_entries),
                duration_ms=duration_ms,
            )
        return all_entries, duration_ms

    async def _resolve_with_massdns(self, candidates: List[str], massdns_bin: str) -> AsyncIterator[Tuple[str, dict]]:
        resolvers_file = self.settings.resolvers_path()
        batch_size = self.settings.massdns_batch_size
        for chunk in chunked(candidates, batch_size):
            if not chunk:
                continue
            try:
                process = await asyncio.create_subprocess_exec(
                    massdns_bin,
                    "-r",
                    resolvers_file,
                    "-o",
                    "S",
                    "-w",
                    "-",
                    stdin=PIPE,
                    stdout=PIPE,
                    stderr=PIPE,
                )
            except FileNotFoundError:
                logger.warning("massdns binary missing, falling back to aiodns")
                async for item in self._resolve_with_aiodns(chunk):
                    yield item
                return
            input_payload = "\n".join(f"{name}." for name in chunk).encode("utf-8") + b"\n"
            stdout, stderr = await process.communicate(input_payload)
            if process.returncode != 0:
                logger.warning("massdns exited with %s: %s", process.returncode, stderr.decode("utf-8", errors="ignore"))
                continue
            results = self._parse_massdns_output(stdout.decode("utf-8", errors="ignore"))
            for name, record in results.items():
                yield name, record

    async def _resolve_with_aiodns(self, candidates: List[str]) -> AsyncIterator[Tuple[str, dict]]:
        semaphore = asyncio.Semaphore(self.settings.resolver_concurrency)
        resolver = aiodns.DNSResolver()

        async def worker(hostname: str) -> Optional[Tuple[str, dict]]:
            normalized = normalize_hostname(hostname)
            if not normalized:
                return None
            async with semaphore:
                ips: List[str] = []
                for record_type in ("A", "AAAA"):
                    try:
                        answers = await resolver.query(normalized, record_type)
                        ips.extend(answer.host for answer in answers)
                    except aiodns.error.DNSError:
                        continue
                cname = None
                try:
                    cname_answers = await resolver.query(normalized, "CNAME")
                    if cname_answers:
                        if isinstance(cname_answers, (list, tuple)):
                            candidates_iter = cname_answers
                        else:
                            candidates_iter = [cname_answers]
                        for candidate_obj in candidates_iter:
                            cname_value = getattr(candidate_obj, "host", None) or getattr(candidate_obj, "cname", None)
                            if cname_value:
                                cname = cname_value.rstrip(".").lower()
                                break
                except aiodns.error.DNSError:
                    cname = None
                if not ips and not cname:
                    return None
                return normalized, {"ips": list(dict.fromkeys(ips)), "cname": cname}

        tasks = [asyncio.create_task(worker(candidate)) for candidate in candidates]
        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result:
                yield result

    def _parse_massdns_output(self, output: str) -> Dict[str, dict]:
        entries: Dict[str, dict] = {}
        for line in output.splitlines():
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            name = parts[0].rstrip(".").lower()
            record_type = parts[1].upper()
            value = parts[2].rstrip(".")
            entry = entries.setdefault(name, {"ips": set(), "cname": None})
            if record_type in {"A", "AAAA"}:
                entry["ips"].add(value)
            elif record_type == "CNAME":
                entry["cname"] = value.lower()
        normalized_entries = {
            name: {"ips": list(sorted(values["ips"])), "cname": values["cname"]}
            for name, values in entries.items()
        }
        return normalized_entries
