import os
import asyncio
import io
import base64
import logging
import time
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

    def _prepare_audio(self, audio_bytes: bytes) -> tuple[io.BytesIO, str]:
        """
        Attempt to normalize audio using pydub.
        If pydub/ffmpeg fails, returns the raw bytes with a webm extension.
        Returns a tuple of (buffer, filename).
        """
        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            if len(audio) < 100:  # Less than 100ms
                return None, "audio.mp3"
            buffer = io.BytesIO()
            audio.export(buffer, format="mp3", bitrate="64k")
            buffer.seek(0)
            return buffer, "audio.mp3"
        except Exception as e:
            logger.warning(
                f"Audio normalization failed (likely missing ffmpeg): {e}. "
                f"Falling back to raw audio transmission."
            )
            # Return the raw audio bytes as a BytesIO stream
            return io.BytesIO(audio_bytes), "audio.webm"

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio bytes → text via Groq Whisper Large V3.
        Uses pydub to ensure compatible format and normalize audio.
        Falls back to OpenAI Whisper if Groq fails or is unavailable.
        """
        start_time = time.monotonic()

        if not self._groq:
            logger.warning("Groq not configured for STT. Trying OpenAI Whisper fallback directly.")
            return await self._transcribe_openai_fallback(audio_bytes, Exception("Groq not configured"))

        loop = asyncio.get_running_loop()
        buffer, filename = await loop.run_in_executor(None, self._prepare_audio, audio_bytes)
        if not buffer:
            return ""

        def _run_groq():
            result = self._groq.audio.transcriptions.create(
                file=(filename, buffer),
                model="whisper-large-v3",
                response_format="json",
                language="en",
                temperature=0.0,
            )
            return result.text or ""

        try:
            # Groq API call is synchronous, run in executor
            text = await loop.run_in_executor(None, _run_groq)
            return text
        except Exception as e:
            logger.error(f"Primary Groq STT failed: {e}. Attempting OpenAI fallback.")
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await self._log_stt_failure_trace("groq_whisper_failed", e, duration_ms)
            return await self._transcribe_openai_fallback(audio_bytes, e)

    async def _transcribe_openai_fallback(self, audio_bytes: bytes, original_error: Exception) -> str:
        if not self._openai:
            logger.warning("OpenAI fallback STT not configured")
            return ""

        start_time = time.monotonic()
        try:
            loop = asyncio.get_running_loop()
            buffer, filename = await loop.run_in_executor(None, self._prepare_audio, audio_bytes)
            if not buffer:
                return ""

            # OpenAI audio transcription is async under AsyncOpenAI
            response = await self._openai.audio.transcriptions.create(
                model="whisper-1",
                file=(filename, buffer),
                response_format="json",
                language="en",
                temperature=0.0,
            )
            return response.text or ""
        except Exception as oe:
            logger.error(f"OpenAI fallback STT failed: {oe}")
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await self._log_stt_failure_trace("openai_whisper_fallback_failed", oe, duration_ms)
            return ""

    async def _log_stt_failure_trace(self, action_type: str, error: Exception, duration_ms: int):
        try:
            from app.db.session import async_session
            from app.services.observability_service import ObservabilityService
            from app.models.trace_entry import TraceEntryCreate
            async with async_session() as db:
                obs = ObservabilityService(db)
                await obs.record(TraceEntryCreate(
                    agent_name="voice_service",
                    action_type=action_type,
                    input_summary="audio_bytes",
                    reasoning_summary=f"STT call failed: {str(error)[:300]}",
                    output_summary="Failed transcription, attempting fallback/exiting",
                    confidence_score=0.0,
                    duration_ms=duration_ms,
                ))
        except Exception as trace_err:
            logger.error(f"Failed to record TraceEntry for STT failure: {trace_err}")

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
