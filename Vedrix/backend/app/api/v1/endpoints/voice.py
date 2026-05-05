from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/capabilities")
async def voice_capabilities():
    """Return whether voice capabilities (GROQ-based) are configured."""
    # Simple gate: if GROQ_API_KEY is configured, assume voice capability is available
    available = bool(getattr(settings, 'GROQ_API_KEY', ''))
    return {"voice_available": available}
