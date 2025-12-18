"""
AI Tutor Platform - Exam Schemas
Pydantic schemas for subject-level exam requests and responses
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ExamTopicSelection(BaseModel):
    """A topic selected for the exam."""
    topic_id: uuid.UUID
    topic_name: str


class ExamStartRequest(BaseModel):
    """Request to start an exam."""
    subject_id: uuid.UUID
    topic_ids: list[uuid.UUID] = Field(..., min_length=1, description="List of topic IDs to include")
    num_questions: int = Field(default=10, ge=5, le=50, description="Number of questions (5-50)")
    time_limit_minutes: int | None = Field(default=None, ge=5, le=120, description="Optional time limit in minutes")


class ExamQuestion(BaseModel):
    """A single question in an exam."""
    question_id: str
    question: str
    options: list[str]
    topic_id: str  # Track which topic this question belongs to
    topic_name: str


class ExamStartResponse(BaseModel):
    """Response when starting an exam."""
    exam_id: str
    subject_name: str
    topics: list[ExamTopicSelection]
    questions: list[ExamQuestion]
    time_limit_seconds: int | None = None
    total_questions: int


class ExamSubmissionItem(BaseModel):
    """Single answer submission with question context."""
    question_id: str
    question: str
    options: list[str]
    answer: str
    correct_answer: str
    topic_id: str


class ExamSubmitRequest(BaseModel):
    """Request to submit an exam."""
    exam_id: str
    subject_id: uuid.UUID
    subject_name: str
    topic_ids: list[uuid.UUID]
    answers: list[ExamSubmissionItem]
    duration_seconds: int | None = None  # Time taken by student


class TopicBreakdown(BaseModel):
    """Score breakdown for a single topic."""
    topic_id: str
    topic_name: str
    correct: int
    total: int
    percentage: float


class ExamFeedbackResponse(BaseModel):
    """AI-generated detailed feedback for an exam."""
    overall_interpretation: str
    topic_analysis: list[str]  # Per-topic insights
    strengths: list[str]
    areas_to_focus: list[str]
    study_recommendations: list[str]
    encouraging_message: str


class ExamResultResponse(BaseModel):
    """Response after submitting an exam."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    score: float
    total_questions: int
    correct_questions: int
    duration_seconds: int | None = None
    completed_at: datetime
    subject_name: str
    topic_breakdown: list[TopicBreakdown]
    feedback: ExamFeedbackResponse | None = None


class ExamHistoryItem(BaseModel):
    """Summary of a past exam for history listing."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    score: float
    total_questions: int
    correct_questions: int
    subject_name: str
    topics_count: int
    completed_at: datetime
