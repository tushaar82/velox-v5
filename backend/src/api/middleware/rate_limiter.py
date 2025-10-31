"""
Rate limiting middleware.
Protects API from abuse using Redis-based rate limiting.
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time

from ...core.redis_client import redis_client
from ...core.config import get_settings


settings = get_settings()


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ):
        """
        Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response

        Raises:
            HTTPException: If rate limit exceeded
        """
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        # Get client identifier (IP address or user ID)
        client_id = request.client.host if request.client else "unknown"

        # Create rate limit key
        current_minute = int(time.time() / 60)
        rate_limit_key = f"rate_limit:{client_id}:{current_minute}"

        # Check rate limit
        try:
            if redis_client.client:
                current_count = await redis_client.increment(rate_limit_key)

                # Set expiration on first request
                if current_count == 1:
                    await redis_client.expire(rate_limit_key, 60)

                # Check if limit exceeded
                if current_count > settings.RATE_LIMIT_PER_MINUTE:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded. Please try again later."
                    )

        except HTTPException:
            raise
        except Exception as e:
            # Log error but don't block request if Redis is down
            print(f"Rate limiting error: {e}")

        # Process request
        response = await call_next(request)
        return response
