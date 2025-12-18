"""
AI Tutor Platform - Assessment Models
SQLAlchemy models for student assessments and results
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import Student
    from app.models.curriculum import Topic

class AssessmentResult(Base):
    """Result of a topic assessment."""
    
    __tablename__ = "assessment_results"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("topics.id", ondelete="CASCADE"),
        index=True
    )
    
    # Score details
    score: Mapped[float] = mapped_column(Float)  # 0.0 to 100.0 or 0.0 to 1.0
    total_questions: Mapped[int] = mapped_column(Integer)
    correct_questions: Mapped[int] = mapped_column(Integer)
    
    # Detailed results (JSON)
    # Stores list of {question_id, question, student_answer, correct_answer, is_correct, explanation}
    details: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # AI-generated feedback (JSON)
    # Stores {strengths, areas_of_improvement, ways_to_improve, practical_assignments, encouraging_words, pattern_analysis}
    feedback: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="assessment_results")
    topic: Mapped["Topic"] = relationship("Topic")
