"""
AI Tutor Platform - Tutor Agent
Conversational AI tutor for real-time student support.
Refactored from tutor_chat.py to use Agentic Architecture.
"""
import json
from typing import Dict, Any, List, Optional

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.ai.core.telemetry import get_tracer


class TutorAgent(BaseAgent):
    """
    The Tutor Agent 💬
    
    A context-aware conversational AI that helps students
    understand lesson content and answer their questions.
    
    Features:
    - Conversation memory (multi-turn)
    - Age-appropriate responses
    - Encouragement and hints
    - Follow-up suggestions
    
    Uses the Plan-Execute pattern:
    - Plan: Build conversation context
    - Execute: Generate response via LLM
    """
    
    name = "TutorAgent"
    description = "Personalized conversational tutor for students"
    version = "2.0.0"
    
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override LLM temperature for more conversational responses
        self.llm.temperature = 0.7
    
    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """
        Plan the conversation turn.
        
        Builds the message history and context for the LLM.
        Supports vision: if image_attachment is in metadata, formats message for GPT-4o Vision.
        """
        metadata = context.metadata
        
        # Get conversation context
        lesson_context = metadata.get("context", "General tutoring session")
        grade_level = metadata.get("grade_level", 1)
        image_attachment = metadata.get("image_attachment")  # base64 or URL
        
        # Build message history from memory
        messages = []
        
        # Add system prompt
        system_content = self.SYSTEM_PROMPT.format(
            context=lesson_context,
            grade_level=grade_level,
        )
        
        # If image is attached, add vision instructions
        if image_attachment:
            system_content += """

VISION MODE:
The student has shared an image. First, carefully analyze the image.
- If it's a math problem: Solve it step-by-step, showing your work.
- If it's a diagram or chart: Explain what you see.
- If it's handwritten text: Transcribe and respond to it.
- If it's unclear: Ask the student to clarify or take a clearer photo."""
        
        messages.append(SystemMessage(content=system_content))
        
        # Add conversation history
        for msg in context.history:
            content = msg.get("content", "")
            role = msg.get("role", "user")
            
            # Strip suggestions from previous AI responses
            if "[SUGGESTIONS:" in content:
                content = content.split("[SUGGESTIONS:")[0].strip()
            
            if role == "user":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))
        
        # Add current message - with image if attached
        if image_attachment:
            # GPT-4o Vision format: content as list of parts
            message_content = [
                {"type": "text", "text": context.user_input or "Please analyze this image."},
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
            messages.append(HumanMessage(content=context.user_input))
        
        return {
            "action": "generate_response",
            "messages": messages,
            "has_image": bool(image_attachment),
            "params": {
                "context": lesson_context,
                "grade_level": grade_level,
            }
        }
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """
        Execute the conversation turn.
        """
        tracer = get_tracer()
        
        with tracer.start_as_current_span("tutor_response") as span:
            try:
                messages = plan["messages"]
                params = plan["params"]
                
                span.set_attribute("tutor.context", params["context"][:100])
                span.set_attribute("tutor.grade_level", params["grade_level"])
                span.set_attribute("tutor.message_count", len(messages))
                
                # Generate response via LLM
                response = await self.llm.chat(
                    messages=messages,
                    agent_name=self.name,
                )
                
                # Parse suggestions from response
                clean_response, suggestions = self._parse_suggestions(response.content)
                
                result = {
                    "response": clean_response,
                    "session_id": context.session_id,
                    "suggestions": suggestions,
                }
                
                span.set_attribute("tutor.response_length", len(clean_response))
                span.set_attribute("tutor.suggestions_count", len(suggestions))
                
                return AgentResult(
                    success=True,
                    output=result,
                    state=AgentState.COMPLETED,
                    metadata=params,
                )
                
            except Exception as e:
                span.record_exception(e)
                return AgentResult(
                    success=False,
                    output=None,
                    state=AgentState.ERROR,
                    error=str(e),
                )
    
    def _parse_suggestions(self, response: str) -> tuple[str, List[str]]:
        """Extract suggestions from the response."""
        suggestions = []
        clean_response = response
        
        if "[SUGGESTIONS:" in response:
            parts = response.split("[SUGGESTIONS:")
            clean_response = parts[0].strip()
            try:
                suggestion_part = parts[1].strip()
                if suggestion_part.endswith("]"):
                    suggestions = json.loads(suggestion_part)
                elif "]" in suggestion_part:
                    suggestion_part = suggestion_part[:suggestion_part.index("]")+1]
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
    ) -> dict:
        """
        Convenience method matching the old API.
        
        This provides backward compatibility with existing code.
        """
        result = await self.run(
            user_input=message,
            session_id=session_id,
            metadata={
                "context": context,
                "grade_level": grade_level,
            }
        )
        
        if result.success:
            return result.output
        else:
            raise Exception(result.error or "Failed to generate response")
    
    async def get_session_history_formatted(self, session_id: str) -> List[dict]:
        """
        Get formatted session history matching old API.
        """
        history = await self.memory.get_history(session_id)
        return [
            {
                "role": msg.get("role"),
                "content": msg.get("content"),
                "timestamp": msg.get("timestamp"),
            }
            for msg in history
        ]


# Singleton instance for backward compatibility
tutor_agent = TutorAgent()

# Alias for backward compatibility with old imports
tutor_chat = tutor_agent
