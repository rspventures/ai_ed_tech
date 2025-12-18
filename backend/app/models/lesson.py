"""
AI Tutor Platform - Lesson Models
SQLAlchemy models for AI-generated lessons and student progress tracking
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import Student
    from app.models.curriculum import Subtopic


class GeneratedLesson(Base):
    """AI-generated lesson content for a subtopic."""
    
    __tablename__ = "generated_lessons"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    subtopic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("subtopics.id", ondelete="CASCADE"),
        index=True
    )
    grade_level: Mapped[int] = mapped_column(Integer, default=1)
    
    # Lesson content
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[dict] = mapped_column(JSONB)
    # Content structure:
    # {
    #   "hook": "Did you know...",
    #   "introduction": "Today we'll learn...",
    #   "sections": [
    #     { "title": "What is Addition?", "content": "...", "example": "..." }
    #   ],
    #   "summary": "Key points...",
    #   "fun_fact": "..."
    # }
    
    # Metadata
    generated_by: Mapped[str] = mapped_column(String(100))  # Model name/version
    generation_prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    subtopic: Mapped["Subtopic"] = relationship("Subtopic")
    student_progress: Mapped[list["StudentLessonProgress"]] = relationship(
        "StudentLessonProgress",
        back_populates="lesson",
        cascade="all, delete-orphan"
    )


class StudentLessonProgress(Base):
    """Tracks which lessons a student has completed."""
    
    __tablename__ = "student_lesson_progress"
    
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
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("generated_lessons.id", ondelete="CASCADE"),
        index=True
    )
    
    # Progress tracking
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    student: Mapped["Student"] = relationship("Student")
    lesson: Mapped["GeneratedLesson"] = relationship(
        "GeneratedLesson", 
        back_populates="student_progress"
    )
    
    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None
