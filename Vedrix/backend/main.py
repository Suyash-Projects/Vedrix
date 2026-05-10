from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1 import api_router
from app.core.config import settings
from app.db.session import init_db, get_session
from app.services.cache_service import init_cache, close_cache
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.rate_limit import limiter
from app.core.logging_config import setup_logging, get_logger
from app.core.metrics import router as metrics_router
import uuid
import time
from sqlalchemy import text

# Setup logging (JSON in production, plain in dev)
setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()
    await init_cache()
    logger.info("Vedrix backend started — DB and cache initialized")
    yield
    # Shutdown logic
    await close_cache()
    logger.info("Vedrix backend shutting down")

app = FastAPI(
    title="Vedrix AI Interview System",
    description="Modern AI-powered interview platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(metrics_router)  # Prometheus metrics at /metrics

# ── Request ID Middleware for Tracing ───────────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    request.state.start_time = time.time()

    response = await call_next(request)

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    # Log request details
    duration = time.time() - request.state.start_time
    logger.info(
        f"request_id={request_id} method={request.method} path={request.url.path} "
        f"status={response.status_code} duration={duration:.3f}s"
    )

    return response

# ── Health Check Endpoints ───────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Basic health check - service is running"""
    return {
        "status": "healthy",
        "service": "vedrix-backend",
        "version": "1.0.0",
    }

@app.get("/health/ready")
async def readiness_check():
    """Detailed health check - includes database connectivity"""
    checks = {
        "database": "unhealthy",
        "service": "healthy",
    }

    # Check database connection
    try:
        async for session in get_session():
            await session.execute(text("SELECT 1"))
            checks["database"] = "healthy"
            break
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = "unhealthy"

    overall = "healthy" if checks["database"] == "healthy" else "degraded"

    return JSONResponse(
        status_code=200 if overall == "healthy" else 503,
        content={
            "status": overall,
            "checks": checks,
            "service": "vedrix-backend",
            "version": "1.0.0",
        }
    )

@app.get("/")
async def root():
    return {"message": "Welcome to Vedrix API", "status": "online"}
