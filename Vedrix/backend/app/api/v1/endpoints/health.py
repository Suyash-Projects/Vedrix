from fastapi import APIRouter
from datetime import datetime, timezone
import time

router = APIRouter()

# Set at module import time (close enough to app start)
_start_time = time.time()


@router.get("/health")
async def health_check():
    """Health check endpoint for load balancers and container orchestration."""
    uptime = int(time.time() - _start_time)

    # Check database connectivity
    db_status = "healthy"
    try:
        from app.db.session import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)[:100]}"

    # Check Redis (optional — may not be configured)
    redis_status = "healthy"
    try:
        from app.services.cache_service import redis_client
        if redis_client:
            await redis_client.ping()
        else:
            redis_status = "not_configured"
    except Exception:
        redis_status = "unavailable"

    all_healthy = db_status == "healthy"
    status_code = 200 if all_healthy else 503

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "degraded",
            "version": "1.0.0",
            "uptime_seconds": uptime,
            "components": {
                "database": db_status,
                "redis": redis_status,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
