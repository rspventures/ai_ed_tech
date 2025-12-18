"""
AI Tutor Platform - Test Schemas
Pydantic schemas for Topic-level test API
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TestQuestion(BaseModel):
    """A question in a test."""
    question_id: str
    question: str
    options: list[str] = []
    subtopic_id: Optional[str] = None
    subtopic_name: Optional[str] = None


class TestStartRequest(BaseModel):
    """Request to start a topic test."""
    topic_id: UUID
    time_limit_minutes: Optional[int] = 10  # Default 10 minutes


class TestStartResponse(BaseModel):
    """Response with test questions."""
    test_id: str
    topic_name: str
    topic_id: UUID
    questions: list[TestQuestion]
    time_limit_seconds: Optional[int] = 600  # 10 min default
    total_questions: int = 10


class TestAnswerItem(BaseModel):
    """A single answer submission."""
    question_id: str
    question: str
    answer: str | list[str]
    correct_answer: str | list[str]
    subtopic_id: Optional[str] = None


class TestSubmitRequest(BaseModel):
    """Request to submit test answers."""
    test_id: str
    topic_id: UUID
    topic_name: str
    answers: list[TestAnswerItem]
    duration_seconds: int


class QuestionExplanation(BaseModel):
    """AI explanation for a wrong answer."""
    question: str
    student_answer: str | list[str]
    correct_answer: str | list[str]
    is_correct: bool
    explanation: str = ""  # AI-generated explanation


class TestFeedbackResponse(BaseModel):
    """AI feedback for the test."""
    summary: str
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []
    encouragement: str = ""


class TestResultResponse(BaseModel):
    """Response after submitting test."""
    id: UUID
    score: float
    total_questions: int
    correct_questions: int
    duration_seconds: Optional[int]
    completed_at: datetime
    topic_name: str
    question_results: list[QuestionExplanation] = []
    feedback: Optional[TestFeedbackResponse] = None

    class Config:
        from_attributes = True


class TestHistoryItem(BaseModel):
    """Summary of a past test for history list."""
    id: UUID
    score: float
    total_questions: int
    correct_questions: int
    topic_name: str
    completed_at: datetime

    class Config:
        from_attributes = True
