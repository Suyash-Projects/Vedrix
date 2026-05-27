"""
Health check endpoint for load balancers, container orchestration, and
monitoring systems.

Returns structured JSON with per-component status. No auth required.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.health_service import health_service

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint — no authentication required.

    Returns HTTP 200 when all components are healthy,
    HTTP 503 when any component is degraded.
    """
    health = await health_service.check_all()

    status_code = 200 if health.status == "healthy" else 503

    return JSONResponse(
        status_code=status_code,
        content=health.model_dump(),
    )
