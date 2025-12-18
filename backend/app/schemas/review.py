"""
AI Tutor Platform - Review Schemas
Pydantic schemas for Spaced Repetition System (SRS) / Smart Review
"""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ReviewItemResponse(BaseModel):
    """A single topic due for review."""
    subtopic_id: uuid.UUID
    subtopic_name: str
    topic_name: str
    subject_name: str
    mastery_level: float
    last_practiced: Optional[datetime] = None
    days_since_review: int
    priority: str  # "high", "medium", "low"
    review_reason: str


class DailyReviewResponse(BaseModel):
    """Response for daily review with AI-generated insight."""
    items: List[ReviewItemResponse]
    total_due: int
    ai_insight: str
    high_priority_count: int


class ReviewSessionComplete(BaseModel):
    """Request to mark a review session as complete."""
    subtopic_id: uuid.UUID
    performance_score: float  # 0.0 to 1.0 based on quiz/practice results
    time_spent_seconds: int = 0


class ReviewScheduleUpdate(BaseModel):
    """Response after completing a review session."""
    subtopic_id: uuid.UUID
    new_mastery_level: float
    next_review_at: datetime
    interval_days: int
    message: str
