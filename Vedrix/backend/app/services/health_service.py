"""
Health check service for monitoring system component status.

Checks database connectivity, Redis availability, and AI service
configuration. Each check has a 3-second timeout to prevent health
endpoints from blocking under failure conditions.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Literal

from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# Captured at module import time (≈ app start)
APP_START_TIME = time.time()

# Timeout for individual health checks (seconds)
_CHECK_TIMEOUT = 3.0


class ComponentStatus(BaseModel):
    """Status of a single infrastructure component."""
    status: Literal["healthy", "degraded", "not_configured"]
    detail: str | None = None


class HealthResponse(BaseModel):
    """Aggregated health check response."""
    status: Literal["healthy", "degraded"]
    version: str
    uptime_seconds: int
    components: Dict[str, ComponentStatus]
    timestamp: str


class HealthService:
    """
    Checks the health of all backend infrastructure components.

    Each check method is individually timeout-guarded (3 s) so a single
    slow dependency cannot stall the health endpoint indefinitely.
    """

    async def check_database(self) -> ComponentStatus:
        """Test DB connectivity with a simple SELECT 1 query (3 s timeout)."""
        try:
            async with asyncio.timeout(_CHECK_TIMEOUT):
                from app.db.session import engine
                from sqlalchemy import text

                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))

            return ComponentStatus(status="healthy")
        except asyncio.TimeoutError:
            logger.warning("Health check: database timed out after %.1fs", _CHECK_TIMEOUT)
            return ComponentStatus(status="degraded", detail="timeout")
        except Exception as exc:
            logger.warning("Health check: database error — %s", exc)
            return ComponentStatus(status="degraded", detail=str(exc)[:100])

    async def check_redis(self) -> ComponentStatus:
        """Test Redis ping (3 s timeout). Returns 'not_configured' if Redis isn't set up."""
        try:
            async with asyncio.timeout(_CHECK_TIMEOUT):
                from app.services.cache_service import cache_service

                if not cache_service._connected or cache_service._redis is None:
                    return ComponentStatus(status="not_configured", detail="Redis client not connected")

                await cache_service._redis.ping()

            return ComponentStatus(status="healthy")
        except asyncio.TimeoutError:
            logger.warning("Health check: Redis timed out after %.1fs", _CHECK_TIMEOUT)
            return ComponentStatus(status="degraded", detail="timeout")
        except Exception as exc:
            logger.warning("Health check: Redis error — %s", exc)
            return ComponentStatus(status="degraded", detail="unavailable")

    async def check_ai_services(self) -> ComponentStatus:
        """Check whether AI chat or voice providers are configured (3 s timeout)."""
        try:
            async with asyncio.timeout(_CHECK_TIMEOUT):
                from app.services.interview_engine.model_router import (
                    get_provider_statuses,
                    get_route_statuses,
                )

                provider_statuses = get_provider_statuses()
                configured_names = [
                    name for name, status in provider_statuses.items()
                    if status["configured"]
                ]
                chat_providers = [
                    name for name, status in provider_statuses.items()
                    if status["configured"] and "chat" in status["capabilities"]
                ]
                voice_providers = [
                    name for name, status in provider_statuses.items()
                    if status["configured"]
                    and any(cap in status["capabilities"] for cap in ("stt", "tts"))
                ]
                route_statuses = get_route_statuses()
                available_routes = sum(
                    1 for route in route_statuses.values() if route["available"]
                )

                if not configured_names:
                    return ComponentStatus(
                        status="degraded",
                        detail="No AI API keys configured",
                    )

                if not chat_providers and not voice_providers:
                    return ComponentStatus(
                        status="degraded",
                        detail="AI keys/base URLs incomplete; no usable AI providers configured",
                    )

                return ComponentStatus(
                    status="healthy",
                    detail=(
                        f"Configured providers: {', '.join(configured_names)}; "
                        f"chat_routes_available={available_routes}/{len(route_statuses)}; "
                        f"voice_providers={', '.join(voice_providers) or 'none'}"
                    ),
                )
        except asyncio.TimeoutError:
            return ComponentStatus(status="degraded", detail="timeout")
        except Exception as exc:
            logger.warning("Health check: AI services error — %s", exc)
            return ComponentStatus(status="degraded", detail=str(exc)[:100])

    async def check_all(self) -> HealthResponse:
        """
        Run all component checks concurrently and return an aggregate response.

        Overall status is 'healthy' only when every *configured* component is
        healthy (components with status='not_configured' are ignored).
        """
        db_status, redis_status, ai_status = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_ai_services(),
        )

        components = {
            "database": db_status,
            "redis": redis_status,
            "ai_services": ai_status,
        }

        # 'not_configured' is acceptable — only 'degraded' makes the system degraded
        all_ok = all(
            c.status != "degraded" for c in components.values()
        )

        return HealthResponse(
            status="healthy" if all_ok else "degraded",
            version=settings.APP_VERSION,
            uptime_seconds=int(time.time() - APP_START_TIME),
            components=components,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


# Module-level singleton
health_service = HealthService()
