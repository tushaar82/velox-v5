"""Error handling middleware."""
import time
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logging import get_logger
from src.utils.monitoring import record_http_request

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for handling errors and logging requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Dispatch the request and handle errors."""
        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Record metrics
            record_http_request(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code,
                duration=duration,
            )

            # Log request
            logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
            )

            return response

        except Exception as e:
            duration = time.time() - start_time

            # Log error
            logger.error(
                "http_request_error",
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                duration=duration,
            )

            # Record metrics
            record_http_request(
                method=request.method,
                endpoint=request.url.path,
                status=500,
                duration=duration,
            )

            # Return error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "detail": str(e) if logger.level == "DEBUG" else "An error occurred",
                },
            )
