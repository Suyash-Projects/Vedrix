from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/capabilities")
async def voice_capabilities():
    """Return whether voice capabilities (STT & TTS) are configured."""
    stt_available = bool(getattr(settings, 'GROQ_API_KEY', ''))
    tts_available = bool(getattr(settings, 'OPENAI_API_KEY', ''))
    
    return {
        "voice_available": stt_available or tts_available,
        "stt": stt_available,
        "tts": tts_available,
        "providers": {
            "stt": "Groq (Whisper V3)" if stt_available else None,
            "tts": "OpenAI" if tts_available else "Browser Fallback"
        }
    }
