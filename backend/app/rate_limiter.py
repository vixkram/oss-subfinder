from __future__ import annotations

import asyncio
import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

from fastapi import HTTPException, Request


@dataclass
class RateLimitQuota:
    remaining: int
    reset_after: float


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__("rate limit exceeded")


class RateLimiter:
    """Simple in-memory sliding window limiter keyed by client identifier."""

    def __init__(
        self,
        *,
        requests: int,
        window_seconds: float,
        trust_x_forwarded_for: bool = False,
    ) -> None:
        self.requests = max(1, requests)
        self.window = max(1.0, window_seconds)
        self.trust_x_forwarded_for = trust_x_forwarded_for
        self._entries: Dict[str, Deque[float]] = {}
        self._lock = asyncio.Lock()

    def _now(self) -> float:
        return time.monotonic()

    def identify(self, request: Request) -> str:
        if self.trust_x_forwarded_for:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",", 1)[0].strip()
        client = request.client
        return client.host if client else "unknown"

    async def hit(self, key: str) -> RateLimitQuota:
        now = self._now()
        async with self._lock:
            bucket = self._entries.setdefault(key, deque())
            window_start = now - self.window
            while bucket and bucket[0] <= window_start:
                bucket.popleft()
            if len(bucket) >= self.requests:
                retry_after = self.window - (now - bucket[0]) if bucket else self.window
                raise RateLimitExceeded(retry_after)
            bucket.append(now)
            remaining = self.requests - len(bucket)
            reset_after = self.window - (now - bucket[0]) if bucket else self.window
            return RateLimitQuota(remaining=remaining, reset_after=max(0.0, reset_after))

    @staticmethod
    def headers_from_quota(quota: Optional[RateLimitQuota]) -> Dict[str, str]:
        if quota is None:
            return {}
        reset_seconds = max(0, math.ceil(quota.reset_after))
        return {
            "X-RateLimit-Remaining": str(max(0, quota.remaining)),
            "X-RateLimit-Reset": str(reset_seconds),
        }

    @staticmethod
    def retry_headers(exc: RateLimitExceeded) -> Dict[str, str]:
        return {"Retry-After": str(max(0, math.ceil(exc.retry_after)))}


async def enforce_rate_limit(request: Request) -> Optional[RateLimitQuota]:
    limiter: Optional[RateLimiter] = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        return None
    key = limiter.identify(request)
    try:
        return await limiter.hit(key)
    except RateLimitExceeded as exc:
        headers = RateLimiter.retry_headers(exc)
        raise HTTPException(status_code=429, detail="Rate limit exceeded", headers=headers) from exc
