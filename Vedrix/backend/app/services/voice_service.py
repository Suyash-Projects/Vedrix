import os
import tempfile
from groq import Groq
from app.core.config import settings

class VoiceService:
    """Service for Speech-to-Text and Text-to-Speech operations."""
    
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Transcribes audio bytes to text using Groq's Whisper Large V3.
        """
        # 1. Create a temporary file to store the audio
        # Groq's transcription API expects a file object
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_path = temp_audio.name

        try:
            # 2. Open and transcribe
            with open(temp_path, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                    file=(temp_path, file.read()),
                    model="whisper-large-v3",
                    response_format="json",
                    language="en",
                    temperature=0.0
                )
            return transcription.text
        except Exception as e:
            print(f"STT Error: {e}")
            return ""
        finally:
            # 3. Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def speak_text(self, text: str):
        """
        Placeholder for Text-to-Speech (Coqui or OpenAI TTS).
        Will return audio bytes or a URL to the audio file.
        """
        # This will be Goal 2 of Phase 4
        pass

voice_service = VoiceService()
