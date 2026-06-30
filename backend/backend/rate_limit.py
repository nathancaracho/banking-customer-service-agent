from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


@dataclass
class _TokenBucket:
    capacity: float
    refill_rate: float
    tokens: float = field(init=False)
    last_refill: float = field(init=False, default_factory=time.monotonic)

    def __post_init__(self) -> None:
        self.tokens = self.capacity

    def consume(self, now: float | None = None) -> bool:
        now = now or time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        requests_per_second: float = 10.0,
        burst_capacity: float = 20.0,
    ) -> None:
        super().__init__(app)
        self._requests_per_second = requests_per_second
        self._burst_capacity = burst_capacity
        self._buckets: dict[str, _TokenBucket] = defaultdict(
            lambda: _TokenBucket(
                capacity=burst_capacity,
                refill_rate=requests_per_second,
            )
        )

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        bucket = self._buckets[client_ip]

        if not bucket.consume():
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": "1"},
            )

        return await call_next(request)
