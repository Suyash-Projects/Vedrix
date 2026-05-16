"""
CSRF Protection Middleware — Double-Submit Cookie Pattern.

How it works:
1. On login, backend sets both an httpOnly access token cookie AND a CSRF token cookie.
2. The CSRF cookie is readable by JavaScript (not httpOnly).
3. For every state-changing request (POST, PUT, DELETE, PATCH), the frontend
   must send the CSRF token in a custom header (X-CSRF-Token).
4. The middleware verifies that the cookie value matches the header value.

This prevents CSRF attacks because:
- An attacker cannot read the CSRF cookie (same-origin policy).
- An attacker cannot forge the custom header (CORS blocks custom headers).
"""
import secrets
import logging
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings

logger = logging.getLogger(__name__)

# HTTP methods that require CSRF validation
CSRF_UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

# Paths that are exempt from CSRF validation (e.g., login, health checks)
CSRF_EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/health",
    "/health/ready",
    "/metrics",
    "/",
}


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware that implements double-submit CSRF protection."""

    async def dispatch(self, request: Request, call_next):
        # Skip CSRF check for safe methods or exempt paths
        if request.method not in CSRF_UNSAFE_METHODS:
            return await call_next(request)

        if request.url.path in CSRF_EXEMPT_PATHS:
            return await call_next(request)

        # Skip CSRF check for WebSocket upgrade requests
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        # Skip CSRF check for API clients that use Bearer tokens (not browser cookies)
        # If the request has an Authorization header, it's likely an API client or test
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)

        # Get CSRF token from cookie and header
        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("x-csrf-token")

        if not csrf_cookie or not csrf_header:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "CSRF token missing. Include X-CSRF-Token header with the value from the csrf_token cookie."
                },
            )

        if not secrets.compare_digest(csrf_cookie, csrf_header):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token mismatch."},
            )

        # CSRF validation passed
        return await call_next(request)
