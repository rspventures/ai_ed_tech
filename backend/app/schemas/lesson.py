"""
AI Tutor Platform - Lesson Schemas
Pydantic schemas for AI-generated lessons and study flow
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Enums
# ============================================================================

class StudyActionType(str, Enum):
    """Types of study actions the system can recommend."""
    LESSON = "lesson"
    PRACTICE = "practice"
    ASSESSMENT = "assessment"
    COMPLETE = "complete"  # Topic mastered


# ============================================================================
# Lesson Content Structure
# ============================================================================

class LessonSection(BaseModel):
    """A section within a lesson."""
    title: str
    content: str  # Markdown content
    example: Optional[str] = None  # Optional worked example


class LessonContent(BaseModel):
    """The full content structure of a generated lesson."""
    hook: str = Field(description="Attention-grabbing opener")
    introduction: str = Field(description="What we'll learn today")
    sections: List[LessonSection] = Field(description="Main teaching content")
    summary: str = Field(description="Key takeaways")
    fun_fact: Optional[str] = Field(default=None, description="Fun related fact")


# ============================================================================
# API Response Schemas
# ============================================================================

class LessonResponse(BaseModel):
    """Response schema for a generated lesson."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    subtopic_id: uuid.UUID
    grade_level: int
    title: str
    content: LessonContent
    generated_by: str
    created_at: datetime
    
    # Progress info (if user is logged in)
    is_completed: Optional[bool] = None
    completed_at: Optional[datetime] = None


class LessonProgressResponse(BaseModel):
    """Response for lesson progress update."""
    model_config = ConfigDict(from_attributes=True)
    
    lesson_id: uuid.UUID
    student_id: uuid.UUID
    completed_at: datetime
    time_spent_seconds: int


# ============================================================================
# Study Path Schemas
# ============================================================================

class StudyActionResponse(BaseModel):
    """The recommended next study action for a student."""
    action_type: StudyActionType
    resource_id: uuid.UUID  # lesson_id, subtopic_id, or topic_id
    resource_name: str  # Human-readable name
    reason: str  # Why this is recommended
    mastery_level: float  # Current mastery (0-1)
    
    # Additional context
    estimated_time_minutes: Optional[int] = None
    difficulty: Optional[str] = None


class LearningPathResponse(BaseModel):
    """Full learning path for a topic."""
    topic_id: uuid.UUID
    topic_name: str
    current_mastery: float
    next_action: StudyActionResponse
    completed_lessons: int
    total_lessons: int
    completed_practice: int
    recommended_path: List[StudyActionResponse] = Field(
        default_factory=list,
        description="Ordered list of recommended actions"
    )


# ============================================================================
# Request Schemas
# ============================================================================

class GenerateLessonRequest(BaseModel):
    """Request to generate a new lesson."""
    subtopic_id: uuid.UUID
    grade_level: int = Field(ge=1, le=12, default=1)
    style: Optional[str] = Field(
        default="story", 
        description="Lesson style: 'story', 'facts', 'visual'"
    )


class CompleteLessonRequest(BaseModel):
    """Request to mark a lesson as complete."""
    time_spent_seconds: int = Field(ge=0)
