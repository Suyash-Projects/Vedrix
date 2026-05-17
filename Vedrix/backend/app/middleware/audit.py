"""
Audit Logging Middleware for Vedrix AI Interview System.

Logs all state-changing actions (POST, PUT, DELETE, PATCH) with:
- User ID (if authenticated)
- Action type
- Target resource
- IP address
- Request details
- Timestamp
"""
import logging
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_session
from app.models.user import User
from app.core import security

logger = logging.getLogger(__name__)

# HTTP methods that should be audited
AUDIT_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

# Paths to exclude from audit logging
EXCLUDED_PATHS = {
    "/health",
    "/health/ready",
    "/metrics",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
}


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Middleware that logs all state-changing actions."""

    async def dispatch(self, request: Request, call_next):
        # Skip audit for safe methods or excluded paths
        if request.method not in AUDIT_METHODS:
            return await call_next(request)

        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        # Extract user ID from token (cookie or header)
        user_id = await self._get_user_id(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        # Log the action
        logger.info(
            json.dumps({
                "audit": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "action": f"{request.method} {request.url.path}",
                "target": request.url.path,
                "ip_address": client_ip,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params) if request.query_params else None,
            })
        )

        # Continue with request
        response = await call_next(request)

        # Log response status
        logger.info(
            json.dumps({
                "audit_response": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "action": f"{request.method} {request.url.path}",
                "status_code": response.status_code,
                "ip_address": client_ip,
            })
        )

        return response

    async def _get_user_id(self, request: Request) -> Optional[int]:
        """Extract user ID from request cookies or authorization header."""
        # Try cookie first
        token = request.cookies.get("access_token")

        # Fall back to Authorization header
        if not token:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]

        if not token:
            return None

        try:
            from app.core.config import settings
            from app.core.security import ALGORITHM
            from jose import jwt

            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            return int(payload.get("sub"))
        except Exception:
            return None
