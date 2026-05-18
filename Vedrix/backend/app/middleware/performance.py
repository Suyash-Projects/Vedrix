"""
Performance monitoring middleware for tracking request latency,
AI response times, and database query performance.
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.metrics import (
    http_requests_total,
    http_request_duration,
    RequestTimer,
)
from app.core.alerting import alert_manager

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware that tracks request performance metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip health checks and metrics endpoints
        if request.url.path in ("/health", "/health/ready", "/metrics", "/"):
            return await call_next(request)

        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Record metrics
            try:
                http_request_duration.labels(
                    method=request.method,
                    endpoint=request.url.path,
                ).observe(duration)

                http_requests_total.labels(
                    method=request.method,
                    endpoint=request.url.path,
                    status=response.status_code,
                ).inc()
            except Exception:
                # Don't let metrics failures break the request
                pass

            # Record for alerting
            alert_manager.record_response_time(duration)
            if response.status_code >= 400:
                alert_manager.record_error(request.url.path, response.status_code)

            # Log slow requests
            if duration > 2.0:
                logger.warning(
                    f"Slow request: {request.method} {request.url.path} "
                    f"took {duration:.2f}s"
                )

            return response

        except Exception as e:
            duration = time.time() - start_time

            # Record error metrics
            try:
                http_request_duration.labels(
                    method=request.method,
                    endpoint=request.url.path,
                ).observe(duration)

                http_requests_total.labels(
                    method=request.method,
                    endpoint=request.url.path,
                    status=500,
                ).inc()
            except Exception:
                pass

            # Record for alerting
            alert_manager.record_error(request.url.path, 500)

            logger.error(
                f"Request error: {request.method} {request.url.path} "
                f"after {duration:.2f}s: {str(e)}"
            )
            raise
