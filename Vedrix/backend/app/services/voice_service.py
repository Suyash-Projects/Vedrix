import os
import tempfile
import base64
from groq import Groq
from openai import OpenAI
from app.core.config import settings

class VoiceService:
    """Service for Speech-to-Text and Text-to-Speech operations."""
    
    def __init__(self):
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Transcribes audio bytes to text using Groq's Whisper Large V3.
        """
        # 1. Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_path = temp_audio.name

        try:
            # 2. Open and transcribe
            with open(temp_path, "rb") as file:
                transcription = self.groq_client.audio.transcriptions.create(
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

    async def speak_text(self, text: str) -> str:
        """
        Converts text to speech using OpenAI TTS and returns base64 encoded audio.
        """
        if not settings.OPENAI_API_KEY:
            return ""

        try:
            response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
                response_format="opus"
            )
            
            # Convert binary response to base64 string
            audio_base64 = base64.b64encode(response.content).decode('utf-8')
            return audio_base64
        except Exception as e:
            print(f"TTS Error: {e}")
            return ""

voice_service = VoiceService()
