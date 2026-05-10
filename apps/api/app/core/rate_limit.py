"""Fixed-window rate limiter with Redis or in-memory storage.

Use as a FastAPI dependency:

    UploadRateLimit = Annotated[None, Depends(rate_limit("upload", 10, 60))]

The dependency raises ``HTTPException(429)`` when the bucket overflows.
When ``Settings.rate_limit_enabled`` is False the dependency is a no-op,
which keeps tests deterministic and avoids surprising local devs.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Request, status

from app.auth.cookie import COOKIE_NAME
from app.auth.jwt import decode_token
from app.core.config import Settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Storage for fixed-window counters keyed by an arbitrary string."""

    def __init__(self, redis_client=None) -> None:  # type: ignore[no-untyped-def]
        self._redis = redis_client
        self._memory: dict[str, tuple[int, float]] = {}
        self._lock = asyncio.Lock()

    async def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Record a hit and return True if it is allowed, False if it overflows."""
        if self._redis is not None:
            try:
                return await self._hit_redis(key, limit, window_seconds)
            except Exception:  # pragma: no cover - fall through on Redis failure
                logger.exception("Redis rate-limit hit failed; falling back to memory")
        return await self._hit_memory(key, limit, window_seconds)

    async def _hit_redis(self, key: str, limit: int, window_seconds: int) -> bool:
        full_key = f"ratelimit:{key}:{int(time.time()) // window_seconds}"
        pipe = self._redis.pipeline()
        pipe.incr(full_key)
        pipe.expire(full_key, window_seconds)
        count, _ = await pipe.execute()
        return int(count) <= limit

    async def _hit_memory(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        async with self._lock:
            count, window_start = self._memory.get(key, (0, now))
            if now - window_start >= window_seconds:
                count, window_start = 0, now
            count += 1
            self._memory[key] = (count, window_start)
        return count <= limit


def _ip_from_request(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def _user_or_ip_key(request: Request) -> str:
    settings: Settings = request.app.state.settings
    token = request.cookies.get(COOKIE_NAME)
    if settings.auth_enabled and token:
        user_id = decode_token(token, settings)
        if user_id is not None:
            return f"u:{user_id}"
    return f"ip:{_ip_from_request(request)}"


def rate_limit(
    bucket: str,
    limit: int,
    window_seconds: int,
    *,
    key_fn: Callable[[Request], str] = _user_or_ip_key,
) -> Callable[..., None]:
    """Build a FastAPI dependency that enforces ``limit`` hits per window."""

    async def _dep(request: Request) -> None:
        settings: Settings = request.app.state.settings
        if not settings.rate_limit_enabled:
            return
        limiter: RateLimiter | None = getattr(
            request.app.state, "rate_limiter", None
        )
        if limiter is None:
            return
        key = f"{bucket}:{key_fn(request)}"
        if not await limiter.hit(key, limit, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {bucket}",
                headers={"Retry-After": str(window_seconds)},
            )

    return _dep


AuthRateLimit = Annotated[None, Depends(rate_limit("auth", 30, 60))]
UploadRateLimit = Annotated[None, Depends(rate_limit("upload", 10, 60))]
MutationRateLimit = Annotated[None, Depends(rate_limit("mutation", 240, 60))]
