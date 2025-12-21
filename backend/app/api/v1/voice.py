"""
AI Tutor Platform - Voice API Router
WebSocket endpoint for real-time voice conversations with Professor Sage
using OpenAI's Realtime API (gpt-4o-realtime-preview)

SAFETY: Voice transcripts are validated through the safety pipeline
OBSERVABILITY: All voice sessions are traced via Langfuse
"""
import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
import websockets

from app.core.config import settings
from app.api.deps import get_current_user_ws
from app.ai.core.safety_pipeline import get_safety_pipeline, SafetyAction
from app.ai.core.observability import get_observer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice"])

# OpenAI Realtime API configuration
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"
OPENAI_MODEL = "gpt-4o-realtime-preview"

# Professor Sage voice system prompt
VOICE_SYSTEM_PROMPT = """You are Professor Sage 🦉, a warm and encouraging AI tutor for school students (grades 1-7).

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
- Never be condescending
- If you don't know something, say "That's a great question! Let me think..."
- Gently redirect off-topic questions back to learning
"""


async def create_openai_connection() -> websockets.WebSocketClientProtocol:
    """Create authenticated connection to OpenAI Realtime API."""
    url = f"{OPENAI_REALTIME_URL}?model={OPENAI_MODEL}"
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1",
    }
    
    # Use additional_headers for websockets v10+ (was extra_headers in older versions)
    connection = await websockets.connect(url, additional_headers=headers)
    logger.info("Connected to OpenAI Realtime API")
    return connection


async def configure_session(openai_ws: websockets.WebSocketClientProtocol):
    """Configure the OpenAI Realtime session with tutor settings."""
    session_config = {
        "type": "session.update",
        "session": {
            "modalities": ["audio", "text"],
            "instructions": VOICE_SYSTEM_PROMPT,
            "voice": "alloy",  # Friendly voice
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": "whisper-1"
            },
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500
            },
            "temperature": 0.7,
            "max_response_output_tokens": 500,
        }
    }
    
    await openai_ws.send(json.dumps(session_config))
    logger.info("Configured OpenAI Realtime session")


@router.websocket("/ws")
async def voice_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for voice conversations.
    
    Relay audio between frontend and OpenAI Realtime API.
    
    Protocol:
    - Client sends: {"type": "audio", "data": "<base64 PCM16>"} or {"type": "text", "text": "..."}
    - Server sends: {"type": "audio", "data": "<base64 PCM16>"} or {"type": "transcript", "text": "..."}
    
    SAFETY: Text inputs and transcripts are validated through safety pipeline
    OBSERVABILITY: Session is traced via Langfuse
    """
    # Authenticate user
    user = await get_current_user_ws(websocket, token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    await websocket.accept()
    logger.info(f"Voice WebSocket connected for user {user.id}")
    
    # === OBSERVABILITY: Create trace for voice session ===
    observer = get_observer()
    trace = observer.create_trace(
        name="voice_session",
        user_id=str(user.id),
        metadata={"session_type": "realtime_voice"}
    )
    
    # === SAFETY: Initialize safety pipeline ===
    safety_pipeline = get_safety_pipeline()
    
    openai_ws = None
    
    try:
        # Connect to OpenAI Realtime API
        conn_span = observer.create_span(trace, "openai_connection")
        openai_ws = await create_openai_connection()
        await configure_session(openai_ws)
        if conn_span:
            conn_span.end(output={"connected": True})
        
        # Send initial greeting
        await websocket.send_json({
            "type": "status",
            "message": "Connected to Professor Sage! Start speaking..."
        })
        
        async def forward_to_openai():
            """Forward client audio/text to OpenAI."""
            try:
                async for message in websocket.iter_json():
                    msg_type = message.get("type")
                    
                    if msg_type == "audio":
                        # Forward audio chunk to OpenAI (no safety check on raw audio)
                        audio_event = {
                            "type": "input_audio_buffer.append",
                            "audio": message.get("data")
                        }
                        await openai_ws.send(json.dumps(audio_event))
                        
                    elif msg_type == "commit":
                        # Signal end of speech
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.commit"
                        }))
                        
                    elif msg_type == "text":
                        # === SAFETY: Validate text input ===
                        text_input = message.get("text", "")
                        
                        safety_span = observer.create_span(trace, "safety_text_input")
                        safety_result = await safety_pipeline.validate_input(
                            text=text_input,
                            grade=5,  # Default grade for voice
                            student_id=str(user.id)
                        )
                        if safety_span:
                            safety_span.end(output={
                                "action": safety_result.action.value,
                                "pii_detected": safety_result.pii_detected
                            })
                        
                        if safety_result.action == SafetyAction.BLOCK:
                            logger.warning(f"Voice text blocked for user {user.id}")
                            await websocket.send_json({
                                "type": "error",
                                "message": "I can't help with that request. Let's focus on learning!"
                            })
                            continue
                        
                        # Use sanitized text
                        safe_text = safety_result.processed_text
                        
                        # Send text message instead of audio
                        text_event = {
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "role": "user",
                                "content": [{
                                    "type": "input_text",
                                    "text": safe_text
                                }]
                            }
                        }
                        await openai_ws.send(json.dumps(text_event))
                        await openai_ws.send(json.dumps({
                            "type": "response.create"
                        }))
                        
            except WebSocketDisconnect:
                logger.info("Client disconnected")
            except Exception as e:
                logger.error(f"Error forwarding to OpenAI: {e}")
        
        async def forward_to_client():
            """Forward OpenAI responses to client."""
            # Buffer for accumulating response transcript for validation
            response_transcript_buffer = []
            
            try:
                async for message in openai_ws:
                    event = json.loads(message)
                    event_type = event.get("type")
                    
                    if event_type == "response.audio.delta":
                        # Forward audio chunk to client immediately
                        # (can't validate raw audio bytes)
                        await websocket.send_json({
                            "type": "audio",
                            "data": event.get("delta")
                        })
                        
                    elif event_type == "response.audio_transcript.delta":
                        # Accumulate transcript deltas for validation
                        delta = event.get("delta", "")
                        response_transcript_buffer.append(delta)
                        # Note: We don't send partial transcripts anymore
                        # Full validated transcript sent on response.done
                        
                    elif event_type == "conversation.item.input_audio_transcription.completed":
                        # User's speech transcription - validate input
                        transcript = event.get("transcript", "")
                        
                        # Create observability span
                        user_span = observer.create_span(trace, "user_transcript")
                        
                        # === SAFETY: Validate user transcript ===
                        safety_result = await safety_pipeline.validate_input(
                            text=transcript,
                            grade=5,
                            student_id=str(user.id)
                        )
                        
                        if user_span:
                            user_span.end(output={
                                "text": transcript[:100],
                                "action": safety_result.action.value
                            })
                        
                        if safety_result.action == SafetyAction.BLOCK:
                            logger.warning(f"User voice transcript blocked: {user.id}")
                            await websocket.send_json({
                                "type": "transcript",
                                "text": "[Message filtered]",
                                "role": "user"
                            })
                        else:
                            await websocket.send_json({
                                "type": "transcript",
                                "text": safety_result.processed_text,
                                "role": "user"
                            })
                        
                    elif event_type == "response.done":
                        # === SAFETY: Validate complete AI response transcript ===
                        full_transcript = "".join(response_transcript_buffer)
                        
                        if full_transcript:
                            output_span = observer.create_span(trace, "safety_output_validation")
                            
                            output_result = await safety_pipeline.validate_output(
                                output=full_transcript,
                                original_question="voice conversation",
                                grade=5
                            )
                            
                            if output_span:
                                output_span.end(output={
                                    "is_safe": output_result.is_safe,
                                    "original_length": len(full_transcript),
                                    "validated_length": len(output_result.validated_output)
                                })
                            
                            # Send validated transcript to client
                            await websocket.send_json({
                                "type": "transcript",
                                "text": output_result.validated_output,
                                "role": "assistant"
                            })
                        
                        # Clear buffer for next response
                        response_transcript_buffer.clear()
                        
                        # Signal response complete
                        await websocket.send_json({
                            "type": "response_complete"
                        })
                        
                    elif event_type == "error":
                        logger.error(f"OpenAI error: {event}")
                        error_span = observer.create_span(trace, "openai_error")
                        if error_span:
                            error_span.end(output={"error": str(event)})
                        await websocket.send_json({
                            "type": "error",
                            "message": event.get("error", {}).get("message", "Unknown error")
                        })
                        
            except websockets.exceptions.ConnectionClosed:
                logger.info("OpenAI connection closed")
            except Exception as e:
                logger.error(f"Error forwarding to client: {e}")
        
        # Run both forwarding tasks concurrently
        await asyncio.gather(
            forward_to_openai(),
            forward_to_client()
        )
        
        if trace:
            trace.update(output={"success": True})

        
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}")
        trace.update(output={"error": str(e)})
        await websocket.send_json({
            "type": "error",
            "message": "Failed to connect to voice service"
        })
    finally:
        if openai_ws:
            await openai_ws.close()
        logger.info(f"Voice WebSocket closed for user {user.id}")


@router.get("/health")
async def voice_health():
    """Check if voice service is available."""
    if not settings.OPENAI_API_KEY:
        return {"status": "unavailable", "reason": "OpenAI API key not configured"}
    
    return {
        "status": "available",
        "model": OPENAI_MODEL,
        "features": ["speech-to-speech", "transcription", "interruption"]
    }
