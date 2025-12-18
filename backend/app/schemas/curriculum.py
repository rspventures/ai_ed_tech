"""
AI Tutor Platform - Curriculum Schemas
Pydantic schemas for subjects, topics, and subtopics
"""
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.curriculum import DifficultyLevel


# ============================================================================
# Subject Schemas
# ============================================================================

class SubjectBase(BaseModel):
    """Base subject schema."""
    name: Annotated[str, Field(min_length=1, max_length=100)]
    slug: Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")]
    description: str | None = None
    icon: str | None = None
    color: str = "#6366f1"


class SubjectCreate(SubjectBase):
    """Schema for creating a subject."""
    pass


class SubjectResponse(SubjectBase):
    """Schema for subject response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    is_active: bool
    display_order: int
    created_at: datetime


class SubjectWithTopics(SubjectResponse):
    """Subject with nested topics."""
    topics: list["TopicResponse"] = []


# ============================================================================
# Topic Schemas
# ============================================================================

class TopicBase(BaseModel):
    """Base topic schema."""
    name: Annotated[str, Field(min_length=1, max_length=200)]
    slug: Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[a-z0-9-]+$")]
    description: str | None = None
    grade_level: Annotated[int, Field(ge=1, le=12)]
    learning_objectives: list[str] | None = None
    estimated_duration_minutes: int = 15


class TopicCreate(TopicBase):
    """Schema for creating a topic."""
    subject_id: uuid.UUID


class TopicResponse(TopicBase):
    """Schema for topic response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    subject_id: uuid.UUID
    is_active: bool
    display_order: int
    created_at: datetime


class TopicWithSubtopics(TopicResponse):
    """Topic with nested subtopics."""
    subtopics: list["SubtopicResponse"] = []


# ============================================================================
# Subtopic Schemas
# ============================================================================

class SubtopicBase(BaseModel):
    """Base subtopic schema."""
    name: Annotated[str, Field(min_length=1, max_length=200)]
    slug: Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[a-z0-9-]+$")]
    description: str | None = None
    difficulty: DifficultyLevel = DifficultyLevel.EASY
    question_prompt_template: str | None = None
    example_questions: list[dict] | None = None


class SubtopicCreate(SubtopicBase):
    """Schema for creating a subtopic."""
    topic_id: uuid.UUID


class SubtopicResponse(SubtopicBase):
    """Schema for subtopic response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    topic_id: uuid.UUID
    is_active: bool
    display_order: int
    created_at: datetime


# ============================================================================
# Progress Schemas
# ============================================================================

class ProgressResponse(BaseModel):
    """Schema for progress response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    student_id: uuid.UUID
    subtopic_id: uuid.UUID
    questions_attempted: int
    questions_correct: int
    current_streak: int
    best_streak: int
    mastery_level: float
    total_time_seconds: int
    last_practiced_at: datetime | None


class ProgressSummary(BaseModel):
    """Summarized progress for a student."""
    total_questions_attempted: int
    total_questions_correct: int
    overall_accuracy: float
    subjects_practiced: int
    current_streak_days: int
    total_practice_time_minutes: int


class EnrichedProgressResponse(ProgressResponse):
    """Progress response with curriculum context."""
    subject_name: str
    topic_name: str
    subtopic_name: str


# Resolve forward references
SubjectWithTopics.model_rebuild()
TopicWithSubtopics.model_rebuild()
