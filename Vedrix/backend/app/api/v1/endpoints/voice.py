from fastapi import APIRouter
from app.services.interview_engine.model_router import is_provider_configured

router = APIRouter()


@router.get("/capabilities")
async def voice_capabilities():
    """Return whether voice capabilities (STT & TTS) are configured."""
    groq_stt_available = is_provider_configured("groq")
    openai_available = is_provider_configured("openai")
    stt_available = groq_stt_available or openai_available
    tts_available = openai_available
    stt_provider = (
        "Groq (Whisper V3)"
        if groq_stt_available
        else "OpenAI (Whisper fallback)" if openai_available else None
    )
    
    return {
        "voice_available": stt_available or tts_available,
        "stt": stt_available,
        "tts": tts_available,
        "providers": {
            "stt": stt_provider,
            "tts": "OpenAI" if tts_available else "Browser Fallback"
        }
    }
