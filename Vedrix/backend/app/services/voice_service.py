import os
import asyncio
import tempfile
import base64
import logging
from groq import Groq
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class VoiceService:
    """
    Speech-to-Text : Groq Whisper Large V3   (~300ms, fastest available)
    Text-to-Speech : OpenAI TTS or Fallback  (PlayAI is decommissioned)

    STT is run in a thread executor because the Groq SDK call is synchronous.
    TTS uses AsyncOpenAI if available for better async performance.
    """

    def __init__(self):
        self._groq = None
        self._openai = None

        if settings.GROQ_API_KEY:
            self._groq = Groq(api_key=settings.GROQ_API_KEY)
        else:
            logger.warning("VoiceService: GROQ_API_KEY not set — STT disabled")

        if settings.OPENAI_API_KEY:
            self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            logger.warning("VoiceService: OPENAI_API_KEY not set — OpenAI TTS disabled")

    # ── STT ──────────────────────────────────────────────────────────────────

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes → text via Groq Whisper Large V3."""
        if not self._groq:
            return ""

        def _run():
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
                    f.write(audio_bytes)
                    tmp_path = f.name
                with open(tmp_path, "rb") as f:
                    result = self._groq.audio.transcriptions.create(
                        file=(os.path.basename(tmp_path), f.read()),
                        model="whisper-large-v3",
                        response_format="json",
                        language="en",
                        temperature=0.0,
                    )
                return result.text or ""
            except Exception as e:
                logger.error(f"STT error: {e}")
                return ""
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except:
                        pass

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _run)

    # ── TTS ──────────────────────────────────────────────────────────────────

    async def speak_text(self, text: str) -> str:
        """
        Convert text -> base64-encoded MP3 audio.
        Uses Browser Web Speech API (via frontend). Backend sends the text,
        frontend handles synthesis for zero-cost TTS.
        Returns empty string — frontend uses Web Speech API.
        """
        # TTS is handled by the frontend using the free Browser Web Speech API.
        # This method is kept as a placeholder for potential future server-side
        # TTS (e.g. Coqui TTS, XTTS, or Bark). For now, returns empty to signal
        # the frontend to use its built-in speech synthesis.
        return ""


voice_service = VoiceService()
