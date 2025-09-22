from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Iterable, Iterator, List, Optional, Sequence, Set

import idna
import orjson

_HOST_REGEX = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Z0-9-]{1,63}(?<!-)(\.(?!-)[A-Z0-9-]{1,63}(?<!-))*\.?$",
    re.IGNORECASE,
)


def normalize_hostname(value: str) -> Optional[str]:
    if not value:
        return None
    trimmed = value.strip().lower()
    if not trimmed:
        return None
    trimmed = trimmed.replace("*.", "")
    trimmed = trimmed.strip(".")
    trimmed = trimmed.replace("\x00", "")
    if " " in trimmed:
        return None
    if not trimmed:
        return None
    try:
        ascii_name = idna.encode(trimmed, uts46=True).decode("ascii")
    except idna.IDNAError:
        return None
    if not _HOST_REGEX.fullmatch(ascii_name):
        return None
    return ascii_name.rstrip(".")


def sanitize_domain(value: str) -> Optional[str]:
    normalized = normalize_hostname(value)
    if not normalized:
        return None
    if "." not in normalized:
        return None
    return normalized


def is_subdomain(candidate: str, root: str) -> bool:
    candidate = candidate.rstrip(".").lower()
    root = root.rstrip(".").lower()
    return candidate == root or candidate.endswith(f".{root}")


def iter_crtsh_names(value: str) -> Iterator[str]:
    for token in value.splitlines():
        cleaned = token.strip()
        if not cleaned:
            continue
        if cleaned.startswith("*."):
            cleaned = cleaned[2:]
        yield cleaned


def unique_everseen(items: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    output: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def chunked(sequence: Sequence[str], size: int) -> Iterator[List[str]]:
    if size <= 0:
        size = 1
    for idx in range(0, len(sequence), size):
        yield list(sequence[idx : idx + size])


def format_sse(data: dict, event: Optional[str] = None) -> bytes:
    payload = orjson.dumps(data).decode("utf-8")
    if event:
        return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")
    return f"data: {payload}\n\n".encode("utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
