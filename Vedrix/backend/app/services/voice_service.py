import os
import asyncio
import tempfile
import base64
import logging
from groq import Groq
from app.core.config import settings

logger = logging.getLogger(__name__)


class VoiceService:
    """
    Speech-to-Text : Groq Whisper Large V3   (~300ms, fastest available)
    Text-to-Speech : Groq PlayAI TTS         (uses same GROQ_API_KEY)

    Both SDK calls are synchronous — run in a thread executor so they
    never block the async event loop.
    """

    def __init__(self):
        if settings.GROQ_API_KEY:
            self._groq = Groq(api_key=settings.GROQ_API_KEY)
        else:
            self._groq = None
            logger.warning("VoiceService: GROQ_API_KEY not set — STT and TTS disabled")

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
                    os.remove(tmp_path)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _run)

    # ── TTS ──────────────────────────────────────────────────────────────────

    async def speak_text(self, text: str) -> str:
        """
        Convert text → base64-encoded WAV audio via Groq PlayAI TTS.
        Returns empty string if Groq key is not set (silent fallback).
        """
        if not self._groq or not text.strip():
            return ""

        def _run():
            try:
                response = self._groq.audio.speech.create(
                    model="playai-tts",
                    voice="Celeste-PlayAI",   # clear, professional female voice
                    input=text[:4096],
                    response_format="wav",
                )
                # response.content is raw bytes
                return base64.b64encode(response.content).decode("utf-8")
            except Exception as e:
                logger.error(f"TTS error: {e}")
                return ""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _run)


voice_service = VoiceService()
