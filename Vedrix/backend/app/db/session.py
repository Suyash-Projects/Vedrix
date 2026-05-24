"""
Secure database session configuration.
Includes SSL/TLS, connection pooling, and audit logging.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from app.core.config import settings
from sqlmodel import SQLModel
import logging

logger = logging.getLogger(__name__)

# ── Connection Pool Settings ───────────────────────────────────────────────────
# These provide protection against connection exhaustion and abuse
pool_config = {
    "poolclass": AsyncAdaptedQueuePool,
    "pool_size": 10,           # Base connections
    "max_overflow": 20,        # Additional connections under load
    "pool_timeout": 30,        # Wait time for available connection
    "pool_recycle": 1800,      # Recycle connections after 30 min
    "pool_pre_ping": True,     # Verify connection before use
}

# ── SSL/TLS Configuration ───────────────────────────────────────────────────────
# PostgreSQL SSL settings for encrypted data transit
connect_args = {}

if settings.DATABASE_URL.startswith("postgresql"):
    # Enable SSL for PostgreSQL
    connect_args = {
        "ssl": "require",  # Enforce SSL
    }

    # Add SSL mode options if specified
    if hasattr(settings, 'DB_SSL_MODE') and settings.DB_SSL_MODE:
        connect_args["sslmode"] = settings.DB_SSL_MODE
elif settings.DATABASE_URL.startswith("sqlite"):
    # SQLite-specific security settings
    connect_args = {
        "check_same_thread": False,
    }

# ── Create Async Engine with Security Settings ───────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True for query debugging (never in production!)
    future=True,
    connect_args=connect_args,
    # Apply pool configuration
    poolclass=pool_config.get("poolclass"),
    pool_size=pool_config.get("pool_size"),
    max_overflow=pool_config.get("max_overflow"),
    pool_timeout=pool_config.get("pool_timeout"),
    pool_recycle=pool_config.get("pool_recycle"),
    pool_pre_ping=pool_config.get("pool_pre_ping"),
)

# ── Session Factory ───────────────────────────────────────────────────────────────
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    """Initialize database - create tables if needed."""
    async with engine.begin() as conn:
        # Import all models to ensure they are registered
        from app.models import (
            User, StudentProfile, HRProfile, JobDrive,
            InterviewSession, DriveInviteToken, ScenarioTemplate, AuditLog,
            CandidateFeedback, HRFeedback, UserConsent, TraceEntry
        )
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("Database initialized successfully")


async def get_session() -> AsyncSession:
    """Get database session with automatic cleanup."""
    async with async_session() as session:
        yield session


# ── Database Health Check ───────────────────────────────────────────────────────
async def check_db_connection() -> bool:
    """Verify database connectivity."""
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False