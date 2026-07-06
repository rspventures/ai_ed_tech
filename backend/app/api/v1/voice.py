"""
AI Tutor Platform - Multilingual Voice API Router
WebSocket endpoint for real-time voice conversations with Professor Sage
supporting 12 Indian languages via ElevenLabs

SAFETY: Voice transcripts are validated through the safety pipeline
OBSERVABILITY: All voice sessions are traced via Langfuse
"""
import asyncio
import base64
import json
import logging
import io
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.config import settings
from app.api.deps import get_current_user_ws
from app.ai.core.safety_pipeline import get_safety_pipeline, SafetyAction
from app.ai.core.observability import get_observer
from app.ai.core.llm import get_llm_client
from app.services.elevenlabs_tts import get_elevenlabs_service, ElevenLabsTTSError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice"])

# Professor Sage voice system prompt (English responses only)
VOICE_SYSTEM_PROMPT = """You are Professor Sage 🦉, a warm and encouraging AI tutor for school students (grades 1-7).

IMPORTANT: Always respond in ENGLISH only, even if the student speaks in Hindi, Tamil, or other languages.

YOUR VOICE PERSONALITY:
- Speak in a friendly, patient, and enthusiastic tone
- Use simple words appropriate for young learners
- Celebrate effort and curiosity!
- Keep responses SHORT and conversational (2-4 sentences)

YOUR JOB:
1. Answer questions clearly and simply
2. Use relatable examples (toys, animals, snacks, playground)
3. If a student is confused, try explaining differently
4. Give HINTS, never direct answers for homework
5. Encourage thinking ("What do you think happens if...?")

RULES:
- ALWAYS respond in English only
- Never be condescending
- If you don't know something, say "That's a great question! Let me think..."
- Gently redirect off-topic questions back to learning
"""


@router.websocket("/ws")
async def voice_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    Multilingual WebSocket endpoint for voice conversations.
    
    Pipeline:
    1. Sarvam Saaras: Speech → English (auto-detect language)
    2. Safety Pipeline: Validate input
    3. LLM (GPT-4o): Generate response in English
    4. Safety Pipeline: Validate output
    5. OpenAI TTS: English Text → Speech
    """
    user = await get_current_user_ws(websocket, token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    await websocket.accept()
    logger.info(f"Voice WebSocket connected for user {user.id}")
    
    observer = get_observer()
    trace = observer.create_trace(
        name="voice_session_elevenlabs",
        user_id=str(user.id),
        metadata={"session_type": "elevenlabs_voice", "languages": "12_indian"}
    )
    
    safety_pipeline = get_safety_pipeline()
    
    detected_language = "en"  # Default to English
    audio_chunks: list[bytes] = []
    
    try:
        await websocket.send_json({
            "type": "status",
            "message": "Connected to Professor Sage! 🦉 Speak in any Indian language..."
        })
        
        async for message_text in websocket.iter_text():
            try:
                message = json.loads(message_text)
            except json.JSONDecodeError:
                continue
            
            msg_type = message.get("type")
            
            if msg_type == "audio":
                audio_data = message.get("data", "")
                if audio_data:
                    try:
                        chunk = base64.b64decode(audio_data)
                        audio_chunks.append(chunk)
                    except Exception as e:
                        logger.error(f"Failed to decode audio chunk: {e}")
                        
            elif msg_type == "commit" or msg_type == "end_audio":
                if not audio_chunks:
                    continue
                
                # Immediately tell frontend to stop recording
                await websocket.send_json({
                    "type": "processing",
                    "message": "Processing your message..."
                })
                
                combined_audio = b''.join(audio_chunks)
                audio_chunks.clear()
                
                process_span = observer.create_span(trace, "process_voice_turn")
                
                try:
                    # === STEP 1: ElevenLabs STT (Speech → Text) ===
                    stt_span = observer.create_span(trace, "elevenlabs_stt")
                    elevenlabs = get_elevenlabs_service()
                    
                    try:
                        stt_result = await elevenlabs.speech_to_text(combined_audio)
                        user_transcript = stt_result["text"]
                        detected_language = stt_result["language_code"]
                        
                        if stt_span:
                            stt_span.end(output={
                                "language": detected_language,
                                "transcript_length": len(user_transcript)
                            })
                        
                    except ElevenLabsTTSError as e:
                        logger.error(f"ElevenLabs STT failed: {e}")
                        print(f"❌ [ElevenLabs] STT Failed: {e}")
                        if stt_span:
                            stt_span.end(output={"error": str(e)})
                        await websocket.send_json({
                            "type": "error",
                            "message": "Couldn't understand the audio. Please try again."
                        })
                        continue
                    
                    await websocket.send_json({
                        "type": "transcript",
                        "text": user_transcript,
                        "role": "user",
                        "language": detected_language
                    })
                    
                    # === STEP 2: Safety Input Validation ===
                    safety_span = observer.create_span(trace, "safety_input")
                    safety_result = await safety_pipeline.validate_input(
                        text=user_transcript,
                        grade=5,
                        student_id=str(user.id)
                    )
                    
                    if safety_result.action == SafetyAction.BLOCK:
                        await websocket.send_json({
                            "type": "error",
                            "message": "I can't help with that request. Let's focus on learning!"
                        })
                        continue
                        
                    if safety_span:
                        safety_span.end(output={"safe": True})
                    
                    safe_input = safety_result.processed_text
                    
                    # === STEP 3: LLM Response (in English) ===
                    llm_span = observer.create_span(trace, "llm_response")
                    try:
                        llm_client = get_llm_client()
                        llm_result = await llm_client.generate(
                            prompt=safe_input,
                            system_prompt=VOICE_SYSTEM_PROMPT,
                            agent_name="voice_tutor"
                        )
                        llm_response = llm_result.content
                        
                        if llm_span:
                            llm_span.end(output={
                                "response_length": len(llm_response),
                                "tokens": llm_result.tokens_total
                            })
                            
                    except Exception as e:
                        logger.error(f"LLM response failed: {e}")
                        await websocket.send_json({"type": "error", "message": "Thinking failed."})
                        continue
                    
                    # === STEP 4: Safety Output Validation ===
                    output_result = await safety_pipeline.validate_output(
                        output=llm_response,
                        original_question=safe_input,
                        grade=5
                    )
                    safe_output = output_result.validated_output
                    
                    # Send English transcript to client
                    await websocket.send_json({
                        "type": "transcript",
                        "text": safe_output,
                        "role": "assistant",
                        "language": "en-IN"  # Always English now
                    })
                    
                    # === STEP 5: ElevenLabs TTS (English Text → Speech) ===
                    tts_span = observer.create_span(trace, "elevenlabs_tts")
                    elevenlabs_tts = get_elevenlabs_service()
                    try:
                        response_audio = await elevenlabs_tts.text_to_speech(
                            text=safe_output,
                            output_format="pcm_24000"  # PCM at 24kHz
                        )
                        
                        if tts_span:
                            tts_span.end(output={
                                "audio_bytes": len(response_audio),
                                "voice": settings.ELEVENLABS_VOICE
                            })
                        
                        # Send audio to client
                        audio_base64 = base64.b64encode(response_audio).decode('utf-8')
                        await websocket.send_json({
                            "type": "audio",
                            "data": audio_base64,
                            "format": "pcm",
                            "sample_rate": 24000  # ElevenLabs PCM at 24kHz
                        })
                        
                    except ElevenLabsTTSError as e:
                        logger.error(f"ElevenLabs TTS failed: {e}")
                        if tts_span:
                            tts_span.end(output={"error": str(e)})
                        # Still send transcript even if TTS fails
                        await websocket.send_json({
                            "type": "error",
                            "message": "Audio unavailable, see transcript above."
                        })
                    
                    # Signal response complete
                    await websocket.send_json({
                        "type": "response_complete"
                    })
                    
                    if process_span:
                        process_span.end(output={
                            "detected_language": detected_language,
                            "success": True
                        })
                        
                except Exception as e:
                    logger.error(f"Voice turn processing error: {e}")
                    if process_span:
                        process_span.end(output={"error": str(e)})
                    await websocket.send_json({
                        "type": "error",
                        "message": "Something went wrong. Please try again."
                    })
                    
            elif msg_type == "text":
                # Handle text input (typed message)
                text_input = message.get("text", "").strip()
                if not text_input:
                    continue
                
                # Create processing span
                text_span = observer.create_span(trace, "process_text_input")
                
                try:
                    # === STEP 2: Safety Input Validation ===
                    safety_result = await safety_pipeline.validate_input(
                        text=text_input,
                        grade=5,
                        student_id=str(user.id)
                    )
                    
                    if safety_result.action == SafetyAction.BLOCK:
                        await websocket.send_json({
                            "type": "error",
                            "message": "I can't help with that request. Let's focus on learning!"
                        })
                        continue
                    
                    safe_input = safety_result.processed_text
                    
                    # Send user transcript
                    await websocket.send_json({
                        "type": "transcript",
                        "text": safe_input,
                        "role": "user",
                        "language": "en-IN"  # Text input assumed English
                    })
                    
                    # === STEP 3: LLM Response ===
                    llm_client = get_llm_client()
                    llm_result = await llm_client.generate(
                        prompt=safe_input,
                        system_prompt=VOICE_SYSTEM_PROMPT,
                        agent_name="voice_tutor"
                    )
                    llm_response = llm_result.content
                    
                    # === STEP 4: Safety Output Validation ===
                    output_result = await safety_pipeline.validate_output(
                        output=llm_response,
                        original_question=safe_input,
                        grade=5
                    )
                    
                    safe_output = output_result.validated_output
                    
                    # Send assistant transcript
                    await websocket.send_json({
                        "type": "transcript",
                        "text": safe_output,
                        "role": "assistant",
                        "language": "en-IN"
                    })
                    
                    # === STEP 6: TTS for text response (ElevenLabs) ===
                    # D4: this branch previously called the removed `sarvam` module
                    # (NameError on every text turn). Use the same ElevenLabs
                    # service as the audio branch.
                    try:
                        elevenlabs_tts = get_elevenlabs_service()
                        response_audio = await elevenlabs_tts.text_to_speech(
                            text=safe_output,
                            output_format="pcm_24000"
                        )

                        audio_base64 = base64.b64encode(response_audio).decode('utf-8')
                        await websocket.send_json({
                            "type": "audio",
                            "data": audio_base64,
                            "format": "pcm",
                            "sample_rate": 24000
                        })

                    except ElevenLabsTTSError as e:
                        logger.error(f"ElevenLabs TTS failed (text mode): {e}")
                        # TTS failure for text mode is non-fatal; transcript already sent.
                    
                    await websocket.send_json({
                        "type": "response_complete"
                    })
                    
                    if text_span:
                        text_span.end(output={"success": True})
                        
                except Exception as e:
                    logger.error(f"Text input processing error: {e}")
                    if text_span:
                        text_span.end(output={"error": str(e)})
                    await websocket.send_json({
                        "type": "error",
                        "message": "Something went wrong. Please try again."
                    })
        
        if trace:
            trace.update(output={"success": True, "final_language": detected_language})
            
    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected for user {user.id}")
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}")
        if trace:
            trace.update(output={"error": str(e)})
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Connection error. Please reconnect."
            })
        except:
            pass
    finally:
        logger.info(f"Voice WebSocket closed for user {user.id}")


@router.get("/health")
async def voice_health():
    """Check if voice service is available."""
    elevenlabs_configured = bool(settings.ELEVENLABS_API_KEY)
    
    if not elevenlabs_configured:
        return {
            "status": "unavailable",
            "reason": "ElevenLabs API key not configured"
        }
    
    return {
        "status": "available",
        "provider": "elevenlabs",
        "models": {
            "stt": "scribe_v1",
            "tts": f"eleven_{settings.ELEVENLABS_MODEL}_v2_5"
        },
        "voice": settings.ELEVENLABS_VOICE,
        "input_languages": [
            "hi", "bn", "ta", "te", "gu", "kn",
            "ml", "mr", "pa", "as", "ne", "ur", "en"
        ],
        "output_language": "en",
        "features": [
            "speech-to-text",
            "auto-language-detection", 
            "high-quality-tts",
            "12-indian-languages"
        ]
    }



