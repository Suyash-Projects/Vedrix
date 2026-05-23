import os
import asyncio
import io
import base64
import logging
from groq import Groq
from openai import AsyncOpenAI
from pydub import AudioSegment
from app.core.config import settings

logger = logging.getLogger(__name__)


class VoiceService:
    """
    Speech-to-Text : Groq Whisper Large V3   (~300ms, fastest available)
    Text-to-Speech : OpenAI TTS with Browser Fallback

    STT uses pydub to normalize audio and runs in a thread executor
    because the Groq SDK call is synchronous.
    TTS uses AsyncOpenAI for non-blocking audio generation.
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
        """
        Transcribe audio bytes → text via Groq Whisper Large V3.
        Uses pydub to ensure compatible format and normalize audio.
        """
        if not self._groq:
            return ""

        def _run():
            try:
                # 1. Load audio from bytes (supports webm, ogg, wav, etc.)
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
                
                # 2. Basic validation
                if len(audio) < 100:  # Less than 100ms
                    return ""

                # 3. Standardize format for Groq (MP3 is compact and reliable)
                buffer = io.BytesIO()
                audio.export(buffer, format="mp3", bitrate="64k")
                buffer.seek(0)
                
                # 4. Transcribe via Groq
                result = self._groq.audio.transcriptions.create(
                    file=("audio.mp3", buffer),
                    model="whisper-large-v3",
                    response_format="json",
                    language="en",
                    temperature=0.0,
                )
                return result.text or ""
            except Exception as e:
                logger.error(f"STT error: {e}")
                return ""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _run)

    # ── TTS ──────────────────────────────────────────────────────────────────

    async def speak_text(self, text: str) -> str:
        """
        Convert text -> base64-encoded MP3 audio via OpenAI TTS.
        If OpenAI is not configured, returns empty string to allow frontend fallback.
        """
        if not self._openai:
            return ""

        try:
            response = await self._openai.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
            )
            # OpenAI response content can be read asynchronously
            audio_data = await response.aread()
            return base64.b64encode(audio_data).decode("utf-8")
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return ""


voice_service = VoiceService()
