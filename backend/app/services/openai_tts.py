"""
OpenAI Text-to-Speech Service

Provides high-quality TTS using OpenAI's neural voices.
Works with multiple languages including English and all Indic languages
that Sarvam STT supports.
"""
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAITTSError(Exception):
    """Exception raised for OpenAI TTS errors."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class OpenAITTSService:
    """
    OpenAI Text-to-Speech service.
    
    Uses OpenAI's TTS-1 or TTS-1-HD models with neural voices.
    Supports multiple languages automatically based on input text.
    
    Voices:
    - alloy: Warm, rounded
    - echo: Bright, clear  
    - fable: Expressive, dramatic
    - onyx: Deep, authoritative
    - nova: Soft, comforting (great for teaching)
    - shimmer: Clear, gentle (great for teaching)
    """
    
    # Recommended voices for education
    VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    MODELS = ["tts-1", "tts-1-hd"]
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        # Voice settings from config
        self.default_voice = getattr(settings, 'OPENAI_TTS_VOICE', 'alloy')
        self.default_model = getattr(settings, 'OPENAI_TTS_MODEL', 'tts-1')
        self.default_speed = getattr(settings, 'OPENAI_TTS_SPEED', 1.15)
        
    async def text_to_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[str] = None,
        response_format: str = "pcm",
        speed: Optional[float] = None
    ) -> bytes:
        """
        Convert text to speech using OpenAI TTS.
        
        Args:
            text: Text to convert to speech (any language)
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: TTS model (tts-1 for speed, tts-1-hd for quality)
            response_format: Audio format (mp3, opus, aac, flac, wav, pcm)
            speed: Speaking speed 0.25-4.0 (default from config)
        
        Returns:
            Audio bytes in requested format
        
        Raises:
            OpenAITTSError: If TTS fails
        """
        voice = voice or self.default_voice
        model = model or self.default_model
        speed = speed or self.default_speed
        
        # Validate voice
        if voice not in self.VOICES:
            logger.warning(f"Unknown voice '{voice}', using '{self.default_voice}'")
            voice = self.default_voice
        
        try:
            response = await self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                response_format=response_format,
                speed=speed
            )
            
            # Get audio bytes
            audio_bytes = response.content
            
            logger.info(f"OpenAI TTS: {len(audio_bytes)} bytes, voice={voice}, model={model}")
            print(f"🔊 [OpenAI TTS] Success | Voice: {voice} | Size: {len(audio_bytes)} bytes")
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"OpenAI TTS failed: {e}")
            raise OpenAITTSError(f"Text-to-speech failed: {str(e)}")


# Singleton instance
_openai_tts_service: Optional[OpenAITTSService] = None


def get_openai_tts_service() -> OpenAITTSService:
    """Get or create singleton OpenAITTSService instance."""
    global _openai_tts_service
    if _openai_tts_service is None:
        _openai_tts_service = OpenAITTSService()
    return _openai_tts_service
