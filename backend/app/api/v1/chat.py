"""
AI Tutor Platform - Chat API Router
Endpoints for the interactive AI tutor chat feature
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, Student
from app.models.lesson import GeneratedLesson
from app.models.curriculum import Subtopic, Topic
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ChatMessage,
    ChatContextType,
    ChatRole
)
from app.ai.tutor_chat import tutor_chat


router = APIRouter(prefix="/chat", tags=["Chat"])


async def get_student_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Student:
    """Get the student profile for the current user."""
    query = select(Student).where(Student.parent_id == user.id)
    result = await db.execute(query)
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )
    return student


async def build_context(
    context_type: ChatContextType,
    context_id: Optional[uuid.UUID],
    db: AsyncSession
) -> str:
    """Build context string based on what the student is viewing."""
    
    if context_type == ChatContextType.LESSON and context_id:
        # Get lesson details
        query = select(GeneratedLesson).where(GeneratedLesson.id == context_id)
        result = await db.execute(query)
        lesson = result.scalar_one_or_none()
        
        if lesson:
            # Get subtopic for more context
            subtopic_query = select(Subtopic).options(
                selectinload(Subtopic.topic).selectinload(Topic.subject)
            ).where(Subtopic.id == lesson.subtopic_id)
            subtopic_result = await db.execute(subtopic_query)
            subtopic = subtopic_result.scalar_one_or_none()
            
            subject_name = subtopic.topic.subject.name if subtopic else "Unknown"
            topic_name = subtopic.topic.name if subtopic else "Unknown"
            
            # Extract key content from lesson
            content = lesson.content or {}
            hook = content.get("hook", "")
            intro = content.get("introduction", "")
            
            return f"""The student is reading a lesson about:
- Subject: {subject_name}
- Topic: {topic_name}  
- Lesson Title: "{lesson.title}"
- What they're learning: {intro}
- The lesson starts with: {hook}"""
    
    elif context_type == ChatContextType.QUESTION and context_id:
        # For assessment questions, we just provide general guidance
        return """The student is working on an assessment question.
IMPORTANT: Give HINTS only, never the direct answer. 
Help them THINK through the problem step by step."""
    
    return "General tutoring session - the student may ask about any topic they're learning."


# ============================================================================
# Chat Endpoints
# ============================================================================

@router.post("/ask", response_model=ChatResponse)
async def ask_tutor(
    request: ChatRequest,
    student: Student = Depends(get_student_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a question to the AI tutor and get a response.
    
    The tutor is context-aware and knows what the student is currently viewing.
    Pass a session_id to continue a conversation.
    Optionally include an image_attachment (base64 or URL) for Vision mode.
    """
    # Build context based on what student is viewing
    context = await build_context(request.context_type, request.context_id, db)
    
    # Get grade level for age-appropriate responses
    grade_level = student.grade_level or 1
    
    # Get response from AI tutor
    result = await tutor_chat.chat(
        message=request.message,
        context=context,
        grade_level=grade_level,
        session_id=str(request.session_id) if request.session_id else None,
        image_attachment=request.image_attachment
    )
    
    return ChatResponse(
        response=result["response"],
        session_id=uuid.UUID(result["session_id"]),
        suggestions=result["suggestions"]
    )


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: uuid.UUID,
    student: Student = Depends(get_student_profile)
):
    """
    Get the chat history for a session.
    
    Useful for displaying previous messages when reopening the chat.
    """
    history = tutor_chat.get_session_history(str(session_id))
    
    messages = [
        ChatMessage(
            role=ChatRole(msg["role"]),
            content=msg["content"],
            timestamp=msg["timestamp"]
        )
        for msg in history
    ]
    
    return ChatHistoryResponse(
        session_id=session_id,
        messages=messages,
        context_type=ChatContextType.GENERAL
    )


@router.delete("/session/{session_id}")
async def clear_chat_session(
    session_id: uuid.UUID,
    student: Student = Depends(get_student_profile)
):
    """
    Clear a chat session.
    
    Useful when starting fresh or leaving a lesson.
    """
    tutor_chat.clear_session(str(session_id))
    return {"message": "Session cleared"}
