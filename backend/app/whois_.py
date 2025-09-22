from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from dateutil import parser as date_parser
import whois
from whois.parser import PywhoisError

logger = logging.getLogger(__name__)


def _serialize_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, list):
        for item in value:
            serialized = _serialize_date(item)
            if serialized:
                return serialized
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, str):
        try:
            parsed = date_parser.parse(value)
        except (ValueError, TypeError, OverflowError):
            return None
        return parsed.date().isoformat()
    return None


def _normalize_status(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item]
    return [str(value)]


def _safe_dict(record: Any) -> Dict[str, Any]:
    if isinstance(record, dict):
        return record
    data = getattr(record, "__dict__", {})
    if "_WhoisEntry__data" in data:
        return data["_WhoisEntry__data"]
    return data


async def lookup_whois(domain: str, force: bool = False) -> Optional[dict]:
    _ = force  # kept for compatibility with previous signature
    loop = asyncio.get_running_loop()
    try:
        record = await loop.run_in_executor(None, whois.whois, domain)
    except PywhoisError as exc:
        logger.warning("WHOIS lookup failed for %s: %s", domain, exc)
        return None
    except Exception as exc:
        logger.exception("Unexpected WHOIS error for %s: %s", domain, exc)
        return None

    record_dict = _safe_dict(record)
    result = {
        "domain": domain,
        "registrar": record_dict.get("registrar"),
        "created": _serialize_date(record_dict.get("creation_date")),
        "expires": _serialize_date(record_dict.get("expiration_date")),
        "status": _normalize_status(record_dict.get("status")),
        "raw": getattr(record, "text", "") or record_dict.get("raw", ""),
    }

    return result
