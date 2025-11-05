"""
Rate limiting middleware using token bucket algorithm
"""
import time
from collections import defaultdict
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Tuple


class TokenBucket:
    """Token bucket rate limiter"""

    def __init__(self, rate_per_minute: int, rate_per_hour: int):
        self.rate_per_minute = rate_per_minute
        self.rate_per_hour = rate_per_hour
        self.buckets: Dict[str, Tuple[float, int, float, int]] = defaultdict(
            lambda: (time.time(), rate_per_minute, time.time(), rate_per_hour)
        )

    def consume(self, key: str) -> Tuple[bool, int, int]:
        """
        Try to consume a token

        Returns:
            (allowed, remaining_minute, remaining_hour)
        """
        now = time.time()
        last_minute, tokens_minute, last_hour, tokens_hour = self.buckets[key]

        # Refill minute bucket
        elapsed_minute = now - last_minute
        if elapsed_minute > 60:
            tokens_minute = self.rate_per_minute
            last_minute = now
        else:
            refill_minute = int((elapsed_minute / 60) * self.rate_per_minute)
            tokens_minute = min(self.rate_per_minute, tokens_minute + refill_minute)

        # Refill hour bucket
        elapsed_hour = now - last_hour
        if elapsed_hour > 3600:
            tokens_hour = self.rate_per_hour
            last_hour = now
        else:
            refill_hour = int((elapsed_hour / 3600) * self.rate_per_hour)
            tokens_hour = min(self.rate_per_hour, tokens_hour + refill_hour)

        # Check if we can consume
        if tokens_minute > 0 and tokens_hour > 0:
            tokens_minute -= 1
            tokens_hour -= 1
            self.buckets[key] = (last_minute, tokens_minute, last_hour, tokens_hour)
            return True, tokens_minute, tokens_hour
        else:
            self.buckets[key] = (last_minute, tokens_minute, last_hour, tokens_hour)
            return False, tokens_minute, tokens_hour


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware

    Limits:
    - 60 requests per minute per IP
    - 1000 requests per hour per IP
    """

    def __init__(self, app, rate_per_minute: int = 60, rate_per_hour: int = 1000):
        super().__init__(app)
        self.limiter = TokenBucket(rate_per_minute, rate_per_hour)

    async def dispatch(self, request: Request, call_next):
        # Get client IP (handle proxy headers)
        client_ip = request.headers.get("X-Forwarded-For", request.client.host).split(",")[0]

        # Skip rate limiting for health check
        if request.url.path in ["/health", "/"]:
            return await call_next(request)

        # Check rate limit
        allowed, remaining_minute, remaining_hour = self.limiter.consume(client_ip)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "type": "https://permia.is/errors/rate-limit-exceeded",
                    "title": "Rate Limit Exceeded",
                    "status": 429,
                    "detail": "Too many requests. Please try again later.",
                },
                headers={
                    "X-RateLimit-Remaining-Minute": str(remaining_minute),
                    "X-RateLimit-Remaining-Hour": str(remaining_hour),
                    "Retry-After": "60",
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining_minute)
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining_hour)

        return response
