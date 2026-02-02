"""
ElevenLabs Text-to-Speech Service

Provides high-quality, natural-sounding TTS using ElevenLabs' AI voices.
Uses Turbo v2.5 model for low latency in real-time conversations.
"""
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ElevenLabsTTSError(Exception):
    """Exception raised for ElevenLabs TTS errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ElevenLabsTTSService:
    """
    ElevenLabs Text-to-Speech service.
    
    Uses ElevenLabs' Turbo v2.5 model for low-latency, high-quality speech.
    Perfect for real-time conversational AI like tutoring.
    
    Recommended Voices for Teaching:
    - Rachel: Warm, friendly female (great for younger kids)
    - Adam: Encouraging, clear male voice
    - Charlie: Enthusiastic, youthful
    - Elli: Young female, energetic
    """
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    # Voice IDs for popular teaching-friendly voices
    VOICE_IDS = {
        "rachel": "21m00Tcm4TlvDq8ikWAM",      # Warm, friendly female
        "adam": "pNInz6obpgDQGcFmaJgB",        # Clear, encouraging male
        "charlie": "IKne3meq5aSn9XLyUdCD",     # Enthusiastic, youthful
        "elli": "MF3mGyEYCl7XYWbV9V6O",        # Young female, energetic
        "josh": "TxGEqnHWrfWFTfGW9XjX",        # Deep, warm male
        "bella": "EXAVITQu4vr4xnSDxMaL",       # Soft, storytelling female
    }
    
    # Models available
    MODELS = {
        "turbo": "eleven_turbo_v2_5",         # Fastest, ~250ms latency
        "multilingual": "eleven_multilingual_v2",  # Best quality, higher latency
        "english": "eleven_monolingual_v1",   # English only, balanced
    }
    
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        if not self.api_key:
            logger.warning("ELEVENLABS_API_KEY not configured - ElevenLabs TTS disabled")
        
        # Get settings with defaults
        self.default_voice = getattr(settings, 'ELEVENLABS_VOICE', 'rachel')
        self.default_model = getattr(settings, 'ELEVENLABS_MODEL', 'turbo')
        self.default_stability = getattr(settings, 'ELEVENLABS_STABILITY', 0.5)
        self.default_similarity = getattr(settings, 'ELEVENLABS_SIMILARITY', 0.75)
    
    @property
    def _headers(self) -> dict:
        """Common headers for API requests."""
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
    
    def _get_voice_id(self, voice: str) -> str:
        """Get voice ID from voice name or return as-is if already an ID."""
        return self.VOICE_IDS.get(voice.lower(), voice)
    
    def _get_model_id(self, model: str) -> str:
        """Get model ID from model name or return as-is if already an ID."""
        return self.MODELS.get(model.lower(), model)
    
    async def text_to_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[str] = None,
        stability: Optional[float] = None,
        similarity_boost: Optional[float] = None,
        output_format: str = "pcm_24000"
    ) -> bytes:
        """
        Convert text to speech using ElevenLabs.
        
        Args:
            text: Text to convert to speech
            voice: Voice name (rachel, adam, charlie, etc.) or voice ID
            model: Model name (turbo, multilingual) or model ID
            stability: Voice stability 0.0-1.0 (lower = more expressive)
            similarity_boost: Voice similarity 0.0-1.0 (higher = more consistent)
            output_format: Audio format (pcm_24000, mp3_44100_128, etc.)
        
        Returns:
            Audio bytes in requested format
        
        Raises:
            ElevenLabsTTSError: If TTS fails
        """
        if not self.api_key:
            raise ElevenLabsTTSError("ElevenLabs API key not configured")
        
        voice = voice or self.default_voice
        model = model or self.default_model
        stability = stability if stability is not None else self.default_stability
        similarity_boost = similarity_boost if similarity_boost is not None else self.default_similarity
        
        voice_id = self._get_voice_id(voice)
        model_id = self._get_model_id(model)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/text-to-speech/{voice_id}",
                    headers=self._headers,
                    json={
                        "text": text,
                        "model_id": model_id,
                        "voice_settings": {
                            "stability": stability,
                            "similarity_boost": similarity_boost,
                            "style": 0.5,  # Expressiveness
                            "use_speaker_boost": True
                        }
                    },
                    params={
                        "output_format": output_format
                    }
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"ElevenLabs TTS failed: {response.status_code} - {error_detail}")
                    raise ElevenLabsTTSError(
                        f"Text-to-speech failed: {error_detail}",
                        status_code=response.status_code
                    )
                
                audio_bytes = response.content
                
                logger.info(f"ElevenLabs TTS: {len(audio_bytes)} bytes, voice={voice}, model={model}")
                print(f"🎙️ [ElevenLabs] Success | Voice: {voice} | Model: {model} | Size: {len(audio_bytes)} bytes")
                
                return audio_bytes
                
        except httpx.TimeoutException:
            logger.error("ElevenLabs TTS timed out")
            raise ElevenLabsTTSError("Text-to-speech request timed out")
        except httpx.RequestError as e:
            logger.error(f"ElevenLabs TTS request error: {e}")
            raise ElevenLabsTTSError(f"Text-to-speech request failed: {str(e)}")
    
    async def text_to_speech_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Stream text-to-speech for lower time-to-first-byte.
        
        Yields audio chunks as they become available.
        """
        if not self.api_key:
            raise ElevenLabsTTSError("ElevenLabs API key not configured")
        
        voice = voice or self.default_voice
        model = model or self.default_model
        
        voice_id = self._get_voice_id(voice)
        model_id = self._get_model_id(model)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/text-to-speech/{voice_id}/stream",
                headers=self._headers,
                json={
                    "text": text,
                    "model_id": model_id,
                    "voice_settings": {
                        "stability": self.default_stability,
                        "similarity_boost": self.default_similarity,
                    }
                },
                params={
                    "output_format": "pcm_24000"
                }
            ) as response:
                if response.status_code != 200:
                    raise ElevenLabsTTSError(
                        f"Streaming failed: {response.status_code}",
                        status_code=response.status_code
                    )
                
                async for chunk in response.aiter_bytes():
                    yield chunk

    async def speech_to_text(
        self,
        audio_bytes: bytes,
        language_code: Optional[str] = None
    ) -> dict:
        """
        Convert speech to text using ElevenLabs Scribe.
        
        Supports 90+ languages including 12 Indian languages:
        Hindi, Tamil, Telugu, Bengali, Kannada, Malayalam, 
        Marathi, Gujarati, Punjabi, Assamese, Nepali, Urdu
        
        Args:
            audio_bytes: Raw audio data (WAV format preferred)
            language_code: Optional ISO-639-1 code (auto-detected if not provided)
        
        Returns:
            {
                "text": "Transcribed text",
                "language_code": "hi",  # Detected/specified language
            }
        
        Raises:
            ElevenLabsTTSError: If STT fails
        """
        if not self.api_key:
            raise ElevenLabsTTSError("ElevenLabs API key not configured")
        
        try:
            # Add WAV header if needed
            if not audio_bytes.startswith(b'RIFF'):
                audio_bytes = self._add_wav_header(audio_bytes)
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Prepare multipart form data
                files = {
                    "file": ("audio.wav", audio_bytes, "audio/wav")
                }
                data = {
                    "model_id": "scribe_v1"  # ElevenLabs Scribe model
                }
                
                # Add language hint if provided
                if language_code:
                    data["language_code"] = language_code
                
                response = await client.post(
                    f"{self.BASE_URL}/speech-to-text",
                    headers={"xi-api-key": self.api_key},
                    files=files,
                    data=data
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"ElevenLabs STT failed: {response.status_code} - {error_detail}")
                    raise ElevenLabsTTSError(
                        f"Speech-to-text failed: {error_detail}",
                        status_code=response.status_code
                    )
                
                result = response.json()
                transcript = result.get("text", "")
                detected_lang = result.get("language_code", "en")
                
                logger.info(f"ElevenLabs STT: detected={detected_lang}")
                print(f"🎧 [ElevenLabs Scribe] STT Success | Language: {detected_lang} | Transcript: {transcript[:30]}...")
                
                return {
                    "text": transcript,
                    "language_code": detected_lang,
                }
                
        except httpx.TimeoutException:
            logger.error("ElevenLabs STT timed out")
            raise ElevenLabsTTSError("Speech-to-text request timed out")
        except httpx.RequestError as e:
            logger.error(f"ElevenLabs STT request error: {e}")
            raise ElevenLabsTTSError(f"Speech-to-text request failed: {str(e)}")

    def _add_wav_header(self, pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
        """Add WAV header to raw PCM data."""
        import struct
        
        data_size = len(pcm_data)
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        
        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            36 + data_size,
            b'WAVE',
            b'fmt ',
            16,  # Subchunk1Size
            1,   # AudioFormat (PCM)
            channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
            b'data',
            data_size
        )
        
        return header + pcm_data


# Singleton instance
_elevenlabs_service: Optional[ElevenLabsTTSService] = None


def get_elevenlabs_service() -> ElevenLabsTTSService:
    """Get or create singleton ElevenLabsTTSService instance."""
    global _elevenlabs_service
    if _elevenlabs_service is None:
        _elevenlabs_service = ElevenLabsTTSService()
    return _elevenlabs_service

