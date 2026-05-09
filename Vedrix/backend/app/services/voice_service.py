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
        Convert text -> base64-encoded MP3/WAV audio.
        Returns empty string if no provider is available (silent fallback).
        """
        if not text.strip():
            return ""

        # Priority 1: OpenAI TTS (High quality, reliable)
        if self._openai:
            try:
                response = await self._openai.audio.speech.create(
                    model="tts-1",
                    voice="alloy",  # professional neutral voice
                    input=text[:4096],
                )
                # response.content is raw bytes
                return base64.b64encode(response.content).decode("utf-8")
            except Exception as e:
                logger.error(f"OpenAI TTS error: {e}")

        # Priority 2: Fallback (Silent for now, or add other providers)
        logger.warning("TTS: No active provider or all providers failed. Falling back to silent mode.")
        return ""


voice_service = VoiceService()
