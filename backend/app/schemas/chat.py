"""
AI Tutor Platform - Chat Schemas
Pydantic schemas for the interactive AI tutor chat feature
"""
import uuid
from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field


class ChatContextType(str, Enum):
    """Type of context the chat is aware of."""
    LESSON = "lesson"
    QUESTION = "question"
    GENERAL = "general"


class ChatRole(str, Enum):
    """Role in the conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ============================================================================
# Request/Response Schemas
# ============================================================================

class ChatMessage(BaseModel):
    """A single chat message."""
    role: ChatRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Request to send a message to the AI tutor."""
    message: str = Field(min_length=1, max_length=1000)
    context_type: ChatContextType = ChatContextType.GENERAL
    context_id: Optional[uuid.UUID] = None  # lesson_id or subtopic_id
    session_id: Optional[uuid.UUID] = None  # For conversation continuity
    

class ChatResponse(BaseModel):
    """Response from the AI tutor."""
    response: str
    session_id: uuid.UUID
    suggestions: List[str] = Field(
        default_factory=list,
        description="Follow-up question suggestions"
    )


class ChatHistoryResponse(BaseModel):
    """Chat history for a session."""
    session_id: uuid.UUID
    messages: List[ChatMessage]
    context_type: ChatContextType
    context_id: Optional[uuid.UUID] = None
