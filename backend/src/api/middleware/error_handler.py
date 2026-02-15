"""Error handling middleware."""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.exceptions import DocJarvisError
from src.config.monitoring import telemetry

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for handling errors and recording metrics"""

    async def dispatch(self, request: Request, call_next: Callable):
        try:
            response = await call_next(request)

            if response.status_code < 400:
                telemetry.increment_counter(
                    "http_requests_total",
                    attributes={
                        "method": request.method,
                        "path": request.url.path,
                        "status": str(response.status_code)
                    }
                )
            
            return response
        except DocJarvisError as e:
            logger.warning("Application error: %s", e)
            telemetry.increment_counter(
                "http_errors_total",
                attributes={"type": e.__class__.__name__}
            )
            raise
        except Exception as e:
            logger.exception("Unexpected error in request: %s", e)
            telemetry.increment_counter(
                "http_errors_total",
                attributes={"type": "UnexpectedError"}
            )
            raise


async def error_handler_middleware(request: Request, call_next: Callable) -> Response:
    """Functional middleware for error handling"""

    try:
        return await call_next(request)
    except Exception as e:
        logger.exception("Request error: %s", e)
        raise
