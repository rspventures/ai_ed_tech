"""
AI Tutor Platform - Parent Dashboard Schemas
Pydantic schemas for parent/guardian analytics and reporting
"""
import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ============================================================================
# Child Summary & Analytics
# ============================================================================

class SubjectMastery(BaseModel):
    """Mastery level for a subject."""
    subject_id: uuid.UUID
    subject_name: str
    average_score: float
    topics_completed: int
    total_topics: int
    mastery_level: str  # "struggling", "learning", "proficient", "mastered"


class ActivityItem(BaseModel):
    """A single activity in the student's timeline."""
    timestamp: datetime
    action_type: str  # "lesson_completed", "assessment_taken", "practice_done"
    description: str
    subject: Optional[str] = None
    score: Optional[float] = None
    emoji: str = "📚"


class ChildSummary(BaseModel):
    """Summary of a child's learning progress."""
    student_id: uuid.UUID
    student_name: str
    avatar_url: Optional[str] = None
    grade_level: int
    
    # Stats
    total_lessons_completed: int
    total_assessments_taken: int
    total_time_minutes: int
    average_score: float
    current_streak: int = 0
    
    # Performance breakdown
    subject_mastery: List[SubjectMastery] = Field(default_factory=list)
    
    # Insights
    top_subjects: List[str] = Field(default_factory=list)
    needs_attention: List[str] = Field(default_factory=list)


class ChildListItem(BaseModel):
    """Brief child info for listing."""
    student_id: uuid.UUID
    student_name: str
    avatar_url: Optional[str] = None
    grade_level: int


class WeeklyProgress(BaseModel):
    """Weekly progress data for charts."""
    day: str  # "Mon", "Tue", etc.
    lessons: int
    practice_time: int  # minutes
    score: Optional[float] = None


class ChildDetailResponse(BaseModel):
    """Full detail response for a child."""
    summary: ChildSummary
    weekly_progress: List[WeeklyProgress]
    recent_activity: List[ActivityItem]
    ai_insights: Optional[str] = None  # AI-generated summary
