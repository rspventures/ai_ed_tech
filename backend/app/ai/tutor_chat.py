"""
AI Tutor Platform - Tutor Chat Agent
LangChain-based conversational agent for real-time student support
"""
import uuid
import logging
from typing import Optional, Dict, List
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.core.config import settings
from app.ai.core.safety_pipeline import get_safety_pipeline, SafetyAction
from app.ai.core.observability import get_observer

logger = logging.getLogger(__name__)


class TutorChatAgent:
    """
    The Support Agent 💬
    
    A context-aware conversational AI that helps students
    understand lesson content and answer their questions.
    """

    SYSTEM_PROMPT = """You are Professor Sage 🦉, a warm and encouraging AI tutor for school students (grades 1-7).

YOUR PERSONALITY:
- Kind, patient, and enthusiastic about learning
- Use simple words a {grade_level}-grader would understand  
- Celebrate effort and curiosity ("Great question!" "You're thinking like a scientist!")
- Use emojis sparingly to add warmth 🌟

YOUR JOB:
1. Answer questions about the current lesson clearly and simply
2. Use relatable examples (toys, animals, snacks, playground)
3. If a student is confused, try explaining differently (not just repeating)
4. Give HINTS for assessment questions, never the direct answer
5. Encourage them to think ("What do you think happens if...?")

CURRENT CONTEXT:
{context}

RULES:
- Keep responses SHORT (2-4 sentences max for young learners)
- If you don't know something, say "That's a great question! Let's think about it together..."
- Never be condescending or make the student feel bad for not understanding
- If the question is off-topic, gently redirect: "That's interesting! But right now, let's focus on..."

SUGGESTIONS:
After your response, think of 2 follow-up questions the student might ask.
Format them as a JSON array at the very end of your response like this:
[SUGGESTIONS: ["question 1", "question 2"]]"""

    def __init__(self):
        self._llm = None
        # In-memory session storage (use Redis in production)
        self._sessions: Dict[str, List[dict]] = {}

    @property
    def llm(self):
        """Lazy load the LLM based on configuration."""
        if self._llm is None:
            if settings.LLM_PROVIDER == "openai":
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL,
                    api_key=settings.OPENAI_API_KEY,
                    temperature=0.7,
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
            else:
                from langchain_anthropic import ChatAnthropic
                self._llm = ChatAnthropic(
                    model=settings.ANTHROPIC_MODEL,
                    api_key=settings.ANTHROPIC_API_KEY,
                    temperature=0.7,
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
        return self._llm

    def _get_session(self, session_id: str) -> List[dict]:
        """Get or create a chat session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        return self._sessions[session_id]

    def _add_to_session(self, session_id: str, role: str, content: str):
        """Add a message to the session history."""
        session = self._get_session(session_id)
        session.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        # Keep only last 10 messages to manage context window
        if len(session) > 10:
            self._sessions[session_id] = session[-10:]

    def _build_messages(self, session_id: str, context: str, grade_level: int):
        """Build the message list for the LLM."""
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT.format(
                context=context,
                grade_level=grade_level
            ))
        ]
        
        session = self._get_session(session_id)
        for msg in session:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                # Strip suggestions from previous AI responses
                content = msg["content"]
                if "[SUGGESTIONS:" in content:
                    content = content.split("[SUGGESTIONS:")[0].strip()
                messages.append(AIMessage(content=content))
        
        return messages

    def _parse_suggestions(self, response: str) -> tuple[str, List[str]]:
        """Extract suggestions from the response."""
        suggestions = []
        clean_response = response
        
        if "[SUGGESTIONS:" in response:
            parts = response.split("[SUGGESTIONS:")
            clean_response = parts[0].strip()
            try:
                # Extract the JSON array
                suggestion_part = parts[1].strip()
                if suggestion_part.endswith("]"):
                    import json
                    suggestions = json.loads(suggestion_part)
                elif "]" in suggestion_part:
                    suggestion_part = suggestion_part[:suggestion_part.index("]")+1]
                    import json
                    suggestions = json.loads(suggestion_part)
            except (json.JSONDecodeError, IndexError):
                pass
        
        return clean_response, suggestions

    async def chat(
        self,
        message: str,
        context: str = "General tutoring session",
        grade_level: int = 1,
        session_id: Optional[str] = None,
        image_attachment: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> dict:
        """
        Send a message to the tutor and get a response.
        
        Args:
            message: The student's question
            context: Description of what the student is currently viewing
            grade_level: The student's grade (1, 2, or 3)
            session_id: Optional session ID for conversation continuity
            image_attachment: Optional base64-encoded image or URL for Vision mode
            user_id: Optional user ID for observability tracing
            
        Returns:
            Dictionary with response, session_id, and suggestions
        """
        # Create or use existing session
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # === OBSERVABILITY: Create trace ===
        observer = get_observer()
        trace = observer.create_trace(
            name="tutor_chat",
            user_id=user_id,
            metadata={
                "session_id": session_id,
                "grade_level": grade_level,
                "has_image": image_attachment is not None,
                "context": context[:100] if context else None
            }
        )
        
        try:
            # === SAFETY: Validate input ===
            safety_pipeline = get_safety_pipeline()
            
            # Create span for input validation
            safety_span = observer.create_span(trace, "safety_input_validation")
            safety_result = await safety_pipeline.validate_input(
                text=message,
                grade=grade_level,
                student_id=user_id
            )
            if safety_span:
                safety_span.end(output={
                    "action": safety_result.action.value,
                    "pii_detected": safety_result.pii_detected,
                    "injection_threat": safety_result.injection_threat.value if hasattr(safety_result.injection_threat, 'value') else str(safety_result.injection_threat)
                })
            
            # Check if input is blocked
            if safety_result.action == SafetyAction.BLOCK:
                logger.warning(f"Input blocked for user {user_id}: {safety_result.block_reason}")
                if trace:
                    trace.update(output={"blocked": True, "reason": safety_result.block_reason})
                return {
                    "response": "I can't help with that request. Let's focus on learning together! 📚 What would you like to study?",
                    "session_id": session_id,
                    "suggestions": ["Help me with math", "Explain a science concept"],
                    "blocked": True
                }
            
            # Use sanitized message
            safe_message = safety_result.processed_text
            
            # Add user message to session
            self._add_to_session(session_id, "user", safe_message)
            
            # Build system prompt with optional vision instructions
            system_content = self.SYSTEM_PROMPT.format(
                context=context,
                grade_level=grade_level
            )
            
            if image_attachment:
                system_content += """

VISION MODE:
The student has shared an image. First, carefully analyze the image.
- If it's a math problem: Solve it step-by-step, showing your work.
- If it's a diagram or chart: Explain what you see.
- If it's handwritten text: Transcribe and respond to it.
- If it's unclear: Ask the student to clarify or take a clearer photo."""
            
            messages = [SystemMessage(content=system_content)]
            
            # Add history
            session = self._get_session(session_id)
            for msg in session[:-1]:  # Exclude the message we just added
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    content = msg["content"]
                    if "[SUGGESTIONS:" in content:
                        content = content.split("[SUGGESTIONS:")[0].strip()
                    messages.append(AIMessage(content=content))
            
            # Add current message - with image if attached
            if image_attachment:
                # GPT-4o Vision format: content as list of parts
                message_content = [
                    {"type": "text", "text": safe_message or "Please analyze this image."},
                ]
                
                # Determine if base64 or URL
                if image_attachment.startswith("data:") or image_attachment.startswith("http"):
                    image_url = image_attachment
                else:
                    # Assume base64, add data URI prefix
                    image_url = f"data:image/jpeg;base64,{image_attachment}"
                
                message_content.append({
                    "type": "image_url",
                    "image_url": {"url": image_url, "detail": "high"}
                })
                
                messages.append(HumanMessage(content=message_content))
            else:
                messages.append(HumanMessage(content=safe_message))
            
            # === LLM CALL with tracing ===
            llm_span = observer.create_span(trace, "llm_invoke")
            response = await self.llm.ainvoke(messages)
            response_text = response.content
            if llm_span:
                llm_span.end(output={"response_length": len(response_text)})
            
            # Parse out suggestions
            clean_response, suggestions = self._parse_suggestions(response_text)
            
            # === SAFETY: Validate output ===
            output_span = observer.create_span(trace, "safety_output_validation")
            output_result = await safety_pipeline.validate_output(
                output=clean_response,
                original_question=safe_message,
                grade=grade_level
            )
            clean_response = output_result.validated_output
            if output_span:
                output_span.end(output={
                    "is_safe": output_result.is_safe,
                    "iterations": output_result.iterations
                })
            
            # Add AI response to session (store clean version)
            self._add_to_session(session_id, "assistant", clean_response)
            
            if trace:
                trace.update(output={"success": True, "suggestions_count": len(suggestions)})
            
            return {
                "response": clean_response,
                "session_id": session_id,
                "suggestions": suggestions
            }
            
        except Exception as e:
            logger.error(f"TutorChat error: {e}")
            if trace:
                trace.update(output={"error": str(e)})
            raise

    def get_session_history(self, session_id: str) -> List[dict]:
        """Get the chat history for a session."""
        return self._get_session(session_id)

    def clear_session(self, session_id: str):
        """Clear a chat session."""
        if session_id in self._sessions:
            del self._sessions[session_id]


# Singleton instance
tutor_chat = TutorChatAgent()
