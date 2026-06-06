import os
import asyncio
import io
import base64
import logging
import time
from groq import Groq
from pydub import AudioSegment
from app.core.config import settings

logger = logging.getLogger(__name__)


class VoiceService:
    """
    Speech-to-Text : Groq Whisper Large V3   (~300ms, fastest available)
    Text-to-Speech : Groq PlayAI TTS         (free, no OpenAI key required)

    STT uses pydub to normalize audio and runs in a thread executor
    because the Groq SDK call is synchronous.
    TTS uses Groq's PlayAI TTS endpoint (Orion / Arista voices).
    """

    def __init__(self):
        self._groq = None

        if settings.GROQ_API_KEY:
            self._groq = Groq(api_key=settings.GROQ_API_KEY)
        else:
            logger.warning("VoiceService: GROQ_API_KEY not set — STT and TTS disabled")

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
            return io.BytesIO(audio_bytes), "audio.webm"

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio bytes → text via Groq Whisper Large V3.
        Uses pydub to ensure compatible format and normalize audio.
        Returns empty string if Groq is not configured.
        """
        start_time = time.monotonic()

        if not self._groq:
            logger.warning("Groq not configured for STT — transcription unavailable")
            return ""

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
            text = await loop.run_in_executor(None, _run_groq)
            return text
        except Exception as e:
            logger.error(f"Groq STT failed: {e}")
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await self._log_stt_failure_trace("groq_whisper_failed", e, duration_ms)
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
                    output_summary="Failed transcription, returning empty string",
                    confidence_score=0.0,
                    duration_ms=duration_ms,
                ))
        except Exception as trace_err:
            logger.error(f"Failed to record TraceEntry for STT failure: {trace_err}")

    # ── TTS (Groq PlayAI) ────────────────────────────────────────────────────

    async def speak_text(self, text: str, voice: str = "Arista-PlayAI") -> str:
        """
        Convert text -> base64-encoded WAV audio via Groq PlayAI TTS.

        Groq's PlayAI TTS supports voices: Arista-PlayAI, Atlas-PlayAI,
        Basil-PlayAI, Briggs-PlayAI, Calum-PlayAI, Celeste-PlayAI,
        Cheyenne-PlayAI, Chip-PlayAI, Cillian-PlayAI, Deedee-PlayAI,
        Eleanor-PlayAI, Fritz-PlayAI, Gail-PlayAI, Indigo-PlayAI,
        Jennifer-PlayAI, Jupiter-PlayAI, Kara-PlayAI, Liam-PlayAI,
        Linda-PlayAI, Madison-PlayAI, Maya-PlayAI, Mei-PlayAI,
        Mikael-PlayAI, Miles-PlayAI, Mia-PlayAI, Orion-PlayAI,
        Quinn-PlayAI, Royce-PlayAI, Samson-PlayAI, Seth-PlayAI,
        Stella-PlayAI, Thor-PlayAI, Titus-PlayAI, Valkyrie-PlayAI.

        Returns empty string if Groq is not configured or TTS fails —
        frontend should fall back to browser SpeechSynthesis API.
        """
        if not self._groq:
            logger.warning("Groq not configured for TTS — frontend will use browser fallback")
            return ""

        if not text or not text.strip():
            return ""

        try:
            loop = asyncio.get_running_loop()

            def _run_playai():
                response = self._groq.audio.speech.create(
                    model="playai-tts",
                    voice=voice,
                    input=text,
                    response_format="wav",
                )
                # Groq returns binary content synchronously
                buffer = io.BytesIO()
                for chunk in response.iter_bytes(chunk_size=4096):
                    buffer.write(chunk)
                return buffer.getvalue()

            audio_bytes = await loop.run_in_executor(None, _run_playai)
            if not audio_bytes:
                return ""
            return base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"Groq PlayAI TTS error: {e}")
            return ""


voice_service = VoiceService()
