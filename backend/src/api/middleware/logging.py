"""Request logging middleware."""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.monitoring import telemetry

logger = logging.getLogger(__name__)


class RequestLoggingMiddleWare(BaseHTTPMiddleware):
    """Middleware for logging requests and measuring latency"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()

        request.state.request_id = request_id
        logger.info(
            "[%s] %s %s started",
            request_id,
            request.method,
            request.url.path
        )

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "[%s] %s %s completed - %d (%.2fms)",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration_ms
            )

            telemetry.record_histogram(
                "http_request_duration_ms",
                duration_ms,
                attributes={
                    "method": request.method,
                    "path": request.url.path,
                    "status": str(response.status_code)
                }
            )

            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "[%s] %s %s failed after %.2fms: %s",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
                str(e)
            )
            raise
