"""Redis-backed fixed-window rate limiter so limits hold across multiple
FastAPI instances (not process-local memory)."""

import time

from fastapi import Request

from app.core.exceptions import RateLimitedError
from app.core.redis import get_redis


class RateLimiter:
    def __init__(self, times: int, seconds: int, scope: str):
        self.times = times
        self.seconds = seconds
        self.scope = scope

    async def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        window = int(time.time() // self.seconds)
        key = f"ratelimit:{self.scope}:{client_ip}:{window}"
        redis = get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, self.seconds)
        if count > self.times:
            ttl = await redis.ttl(key)
            raise RateLimitedError(retry_after=max(ttl, 1))
