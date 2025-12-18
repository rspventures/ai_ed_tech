"""
AI Tutor Platform - Exam Models
SQLAlchemy models for subject-level exams
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
    from app.models.curriculum import Subject


class ExamResult(Base):
    """Result of a subject-level exam covering multiple topics."""
    
    __tablename__ = "exam_results"
    
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
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("subjects.id", ondelete="CASCADE"),
        index=True
    )
    
    # Topics covered in this exam (list of UUIDs as strings)
    topic_ids: Mapped[list] = mapped_column(JSONB, default=list)
    
    # Score details
    score: Mapped[float] = mapped_column(Float)  # 0.0 to 100.0
    total_questions: Mapped[int] = mapped_column(Integer)
    correct_questions: Mapped[int] = mapped_column(Integer)
    
    # Time tracking
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_limit_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Per-topic breakdown: { "topic_id": { "correct": 3, "total": 5, "name": "Algebra" } }
    topic_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Detailed question results (JSON array)
    details: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # AI-generated feedback
    feedback: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="exam_results")
    subject: Mapped["Subject"] = relationship("Subject")
