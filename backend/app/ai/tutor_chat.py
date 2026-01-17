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
        user_id: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> dict:
        """
        Send a message to the tutor and get a response.
        Uses RAGAgent for answer generation and ChatService for persistence.
        """
        from app.core.database import async_session_maker
        from app.services.chat import ChatService
        from app.models.chat import MessageRole

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
                    "injection_threat": str(safety_result.injection_threat)
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
            
            # === PERSISTENCE: Save User Message ===
            session_uuid = None
            async with async_session_maker() as db:
                chat_service = ChatService(db)
                
                # Ensure session exists (if ID provided) or create new
                if session_id:
                     try:
                         session_uuid = uuid.UUID(session_id)
                     except ValueError:
                         session_uuid = None
                         session_id = None
                
                if not session_uuid and user_id:
                    # Create new session if none provided
                    try:
                        new_session = await chat_service.create_session(uuid.UUID(user_id), title=safe_message[:50])
                        session_uuid = new_session.id
                        session_id = str(session_uuid)
                    except Exception as e:
                        logger.error(f"Failed to create session: {e}")

                if session_uuid:
                    await chat_service.add_message(session_uuid, MessageRole.USER, safe_message)

            
            # === GENERATION: Direct LLM Call (NOT RAG) ===
            # Tutor chat uses direct LLM conversation, NOT document retrieval
            # Add to in-memory session for context building
            if session_id:
                self._add_to_session(session_id, "user", safe_message)
            
            # Build messages with context and history
            messages = self._build_messages(
                session_id or str(uuid.uuid4()),
                context,
                grade_level
            )
            
            # Add current user message
            messages.append(HumanMessage(content=safe_message))
            
            # Call LLM directly
            llm_span = observer.create_span(trace, "llm_generation")
            try:
                llm_response = await self.llm.ainvoke(messages)
                response_text = llm_response.content
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                response_text = "I'm having trouble thinking right now. Could you try asking again? 🤔"
            
            if llm_span:
                llm_span.end(output={"response_length": len(response_text)})
            
            # Parse out suggestions
            clean_response, suggestions = self._parse_suggestions(response_text)
            
            # Add assistant response to in-memory session
            if session_id:
                self._add_to_session(session_id, "assistant", clean_response)
            
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

            # === PERSISTENCE: Save AI Message ===
            if session_uuid:
                async with async_session_maker() as db:
                    chat_service = ChatService(db)
                    await chat_service.add_message(session_uuid, MessageRole.ASSISTANT, clean_response)

            if trace:
                trace.update(output={"success": True, "suggestions_count": len(suggestions)})
            
            return {
                "response": clean_response,
                "session_id": session_id,
                "suggestions": suggestions,
                "grounded": False  # Not from documents
            }
            
        except Exception as e:
            logger.error(f"TutorChat error: {e}")
            if trace:
                trace.update(output={"error": str(e)})
            raise

    async def get_session_history(self, session_id: str) -> List[dict]:
         """
         Get the chat history for a session from DB.
         """
         from app.core.database import async_session_maker
         from app.services.chat import ChatService
         import uuid
         
         async with async_session_maker() as db:
             chat_service = ChatService(db)
             msgs = await chat_service.get_history(uuid.UUID(session_id), limit=50)
             return [
                 {"role": m.role, "content": m.content, "timestamp": m.created_at}
                 for m in msgs
             ]

    async def clear_session(self, session_id: str):
        """Clear a chat session."""
        from app.core.database import async_session_maker
        from app.models.chat import ChatSession
        from sqlalchemy import delete
        import uuid
        
        try:
            async with async_session_maker() as db:
                await db.execute(delete(ChatSession).where(ChatSession.id == uuid.UUID(session_id)))
                await db.commit()
                logger.info(f"Cleared session {session_id}")
        except Exception as e:
            logger.error(f"Failed to clear session {session_id}: {e}")

# Singleton instance
tutor_chat = TutorChatAgent()


# Singleton instance
tutor_chat = TutorChatAgent()
