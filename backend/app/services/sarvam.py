"""
Sarvam AI Service - Multilingual Voice Processing

Provides Speech-to-Text (Saaras), Translation, and Text-to-Speech (Bulbul)
for 22 Indian languages.

SAFETY: This service is used within our safety pipeline workflow
OBSERVABILITY: All API calls are traced
"""
import base64
import logging
from typing import Optional

import io
import wave
import httpx

from app.core.config import settings
from app.ai.core.observability import get_observer

logger = logging.getLogger(__name__)


class SarvamAPIError(Exception):
    """Exception raised for Sarvam API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class SarvamService:
    """
    Unified Sarvam AI client for multilingual voice processing.
    
    Supports:
    - Speech-to-English (Saaras): Any Indian language audio → English text
    - Translation (Sarvam-Translate): English ↔ 22 Indian languages
    - Text-to-Speech (Bulbul): Text → Audio in any supported language
    
    Supported Languages:
    hi-IN, bn-IN, ta-IN, te-IN, gu-IN, kn-IN, ml-IN, mr-IN, pa-IN, od-IN, en-IN
    + 11 more via Sarvam-Translate
    """
    
    BASE_URL = "https://api.sarvam.ai"
    TIMEOUT = 30.0  # seconds

    LANGUAGES = {
        "hi-IN": "Hindi",
        "bn-IN": "Bengali",
        "ta-IN": "Tamil",
        "te-IN": "Telugu",
        "gu-IN": "Gujarati",
        "kn-IN": "Kannada",
        "ml-IN": "Malayalam",
        "mr-IN": "Marathi",
        "pa-IN": "Punjabi",
        "od-IN": "Odia",
        "en-IN": "English"
    }
    
    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        if not self.api_key:
            logger.warning("SARVAM_API_KEY not configured - multilingual voice disabled")
        
        self.observer = get_observer()

    def get_language_name(self, code: str) -> str:
        """Get full language name from code."""
        return self.LANGUAGES.get(code, "English")
    
    @property
    def _headers(self) -> dict:
        """Common headers for all API requests."""
        return {
            "api-subscription-key": self.api_key,
        }

    def _add_wav_header(self, pcm_data: bytes, sample_rate: int = 16000) -> bytes:
        """Add WAV header to raw PCM data."""
        # specific to Sarvam: 16kHz, 16-bit, mono
        with io.BytesIO() as wav_buffer:
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_data)
            return wav_buffer.getvalue()
    
    async def speech_to_english(
        self, 
        audio_bytes: bytes,
        model: Optional[str] = None
    ) -> dict:
        """
        Convert speech in any Indian language to English text.
        
        Uses Saaras model which automatically:
        1. Detects the spoken language
        2. Transcribes the speech
        3. Translates to English
        
        Args:
            audio_bytes: Raw audio data (WAV format preferred)
            model: STT model to use (default: saaras:v2.5)
        
        Returns:
            {
                "transcript": "English text",
                "language_code": "hi-IN",  # Detected language
            }
        
        Raises:
            SarvamAPIError: If API call fails
        """
        if not self.api_key:
            raise SarvamAPIError("Sarvam API key not configured")
        
        model = model or settings.SARVAM_STT_MODEL
        
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                # Ensure audio has WAV header if it looks like raw PCM (no RIFF header)
                if not audio_bytes.startswith(b'RIFF'):
                    final_audio = self._add_wav_header(audio_bytes)
                else:
                    final_audio = audio_bytes

                # Saaras expects multipart form data with audio file
                files = {
                    "file": ("audio.wav", final_audio, "audio/wav")
                }
                data = {
                    "model": model,
                }
                
                response = await client.post(
                    f"{self.BASE_URL}/speech-to-text-translate",
                    headers=self._headers,
                    files=files,
                    data=data
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"Sarvam STT failed: {response.status_code} - {error_detail}")
                    raise SarvamAPIError(
                        f"Speech-to-text failed: {error_detail}",
                        status_code=response.status_code
                    )
                
                result = response.json()
                logger.info(f"Sarvam STT: detected={result.get('language_code', 'unknown')}")
                print(f"🦉 [Sarvam AI] STT Success | Language: {result.get('language_code')} | Transcript: {result.get('transcript')[:30]}...")
                
                return {
                    "transcript": result.get("transcript", ""),
                    "language_code": result.get("language_code", "en-IN"),
                }
                
        except httpx.TimeoutException:
            logger.error("Sarvam STT timed out")
            raise SarvamAPIError("Speech-to-text request timed out")
        except httpx.RequestError as e:
            logger.error(f"Sarvam STT request error: {e}")
            raise SarvamAPIError(f"Speech-to-text request failed: {str(e)}")
    
    async def translate(
        self,
        text: str,
        source_language: str = "en-IN",
        target_language: str = "hi-IN",
        model: Optional[str] = None
    ) -> str:
        """
        Translate text between English and Indian languages.
        
        Args:
            text: Text to translate
            source_language: Source language code (e.g., "en-IN")
            target_language: Target language code (e.g., "hi-IN")
            model: Translation model (default: sarvam-translate:v1)
        
        Returns:
            Translated text
        
        Raises:
            SarvamAPIError: If API call fails
        """
        # Skip translation if same language
        if source_language == target_language:
            return text
        
        if not self.api_key:
            raise SarvamAPIError("Sarvam API key not configured")
        
        model = model or settings.SARVAM_TRANSLATE_MODEL
        
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(
                    f"{self.BASE_URL}/translate",
                    headers={**self._headers, "Content-Type": "application/json"},
                    json={
                        "input": text,
                        "source_language_code": source_language,
                        "target_language_code": target_language,
                        "model": model
                    }
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"Sarvam translate failed: {response.status_code} - {error_detail}")
                    raise SarvamAPIError(
                        f"Translation failed: {error_detail}",
                        status_code=response.status_code
                    )
                
                result = response.json()
                translated = result.get("translated_text", text)
                logger.info(f"Sarvam translate: {source_language} → {target_language}")
                print(f"🦉 [Sarvam AI] Translation Success | {source_language} -> {target_language}")
                
                return translated
                
        except httpx.TimeoutException:
            logger.error("Sarvam translate timed out")
            raise SarvamAPIError("Translation request timed out")
        except httpx.RequestError as e:
            logger.error(f"Sarvam translate request error: {e}")
            raise SarvamAPIError(f"Translation request failed: {str(e)}")
    
    async def text_to_speech(
        self,
        text: str,
        language_code: str = "en-IN",
        speaker: Optional[str] = None,
        pace: Optional[float] = None,
        model: Optional[str] = None
    ) -> bytes:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to speak
            language_code: Language code for speech (e.g., "hi-IN")
            speaker: Voice to use (default: vidya)
            pace: Speaking pace 0.5-2.0 (default: 0.9 for teaching)
            model: TTS model (default: bulbul:v2)
        
        Returns:
            Audio bytes (WAV format, 16kHz)
        
        Raises:
            SarvamAPIError: If API call fails
        """
        if not self.api_key:
            raise SarvamAPIError("Sarvam API key not configured")
        
        model = model or settings.SARVAM_TTS_MODEL
        speaker = speaker or settings.SARVAM_TTS_SPEAKER
        pace = pace or settings.SARVAM_TTS_PACE
        
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(
                    f"{self.BASE_URL}/text-to-speech",
                    headers={**self._headers, "Content-Type": "application/json"},
                    json={
                        "inputs": [text],
                        "target_language_code": language_code,
                        "model": model,
                        "speaker": speaker,
                        "pace": pace,
                        "speech_sample_rate": settings.SARVAM_TTS_SAMPLE_RATE
                    }
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"Sarvam TTS failed: {response.status_code} - {error_detail}")
                    raise SarvamAPIError(
                        f"Text-to-speech failed: {error_detail}",
                        status_code=response.status_code
                    )
                
                result = response.json()
                
                # Response contains base64-encoded audio
                audios = result.get("audios", [])
                if not audios:
                    raise SarvamAPIError("No audio returned from TTS")
                
                audio_base64 = audios[0]
                audio_bytes = base64.b64decode(audio_base64)
                
                logger.info(f"Sarvam TTS: {len(audio_bytes)} bytes, lang={language_code}")
                print(f"🦉 [Sarvam AI] TTS Success | Language: {language_code} | Audio Size: {len(audio_bytes)} bytes")
                return audio_bytes
                
        except httpx.TimeoutException:
            logger.error("Sarvam TTS timed out")
            raise SarvamAPIError("Text-to-speech request timed out")
        except httpx.RequestError as e:
            logger.error(f"Sarvam TTS request error: {e}")
            raise SarvamAPIError(f"Text-to-speech request failed: {str(e)}")
    
    async def process_voice_turn(
        self,
        audio_bytes: bytes,
        llm_response: str,
    ) -> tuple[str, str, bytes]:
        """
        Complete voice turn: STT → (external LLM) → Translate → TTS
        
        This is a convenience method that handles the full pipeline
        except for LLM processing (which happens externally with safety).
        
        Args:
            audio_bytes: Input audio from user
            llm_response: Response from LLM (in English)
        
        Returns:
            Tuple of (user_transcript, detected_language, response_audio)
        """
        # Step 1: Speech to English
        stt_result = await self.speech_to_english(audio_bytes)
        user_transcript = stt_result["transcript"]
        detected_lang = stt_result["language_code"]
        
        # Step 2: Translate LLM response if not English
        if detected_lang != "en-IN":
            translated_response = await self.translate(
                text=llm_response,
                source_language="en-IN",
                target_language=detected_lang
            )
        else:
            translated_response = llm_response
        
        # Step 3: Text to Speech
        response_audio = await self.text_to_speech(
            text=translated_response,
            language_code=detected_lang
        )
        
        return user_transcript, detected_lang, response_audio


# Singleton instance
_sarvam_service: Optional[SarvamService] = None


def get_sarvam_service() -> SarvamService:
    """Get or create singleton SarvamService instance."""
    global _sarvam_service
    if _sarvam_service is None:
        _sarvam_service = SarvamService()
    return _sarvam_service
