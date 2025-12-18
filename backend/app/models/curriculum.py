"""
AI Tutor Platform - Curriculum Models
SQLAlchemy models for subjects, topics, and content management
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import Student


class DifficultyLevel(str, Enum):
    """Question difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Subject(Base):
    """Academic subjects (Math, English, etc.)."""
    
    __tablename__ = "subjects"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Icon name or emoji
    color: Mapped[str] = mapped_column(String(7), default="#6366f1")  # Hex color
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    
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
    topics: Mapped[list["Topic"]] = relationship(
        "Topic", 
        back_populates="subject",
        cascade="all, delete-orphan"
    )


class Topic(Base):
    """Topics within a subject (e.g., Addition, Subtraction for Math)."""
    
    __tablename__ = "topics"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("subjects.id", ondelete="CASCADE"),
        index=True
    )
    
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    grade_level: Mapped[int] = mapped_column(Integer)  # 1, 2, 3
    
    # Content metadata
    learning_objectives: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    prerequisites: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # List of topic IDs
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, default=15)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    
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
    subject: Mapped["Subject"] = relationship("Subject", back_populates="topics")
    subtopics: Mapped[list["Subtopic"]] = relationship(
        "Subtopic", 
        back_populates="topic",
        cascade="all, delete-orphan"
    )


class Subtopic(Base):
    """Subtopics for granular content (e.g., Adding single digits)."""
    
    __tablename__ = "subtopics"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("topics.id", ondelete="CASCADE"),
        index=True
    )
    
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        String(20), 
        default=DifficultyLevel.EASY
    )
    
    # AI generation hints
    question_prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    example_questions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    
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
    topic: Mapped["Topic"] = relationship("Topic", back_populates="subtopics")


class Progress(Base):
    """Student progress tracking per subtopic."""
    
    __tablename__ = "progress"
    
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
    subtopic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("subtopics.id", ondelete="CASCADE"),
        index=True
    )
    
    # Progress metrics
    questions_attempted: Mapped[int] = mapped_column(Integer, default=0)
    questions_correct: Mapped[int] = mapped_column(Integer, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    mastery_level: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 to 1.0
    
    # Time tracking
    total_time_seconds: Mapped[int] = mapped_column(Integer, default=0)
    last_practiced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    # Spaced Repetition System (SRS) - when to review this topic next
    next_review_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    review_interval_days: Mapped[int] = mapped_column(Integer, default=1)  # 1, 3, 7, 14, 30
    
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
    student: Mapped["Student"] = relationship("Student", back_populates="progress")
    subtopic: Mapped["Subtopic"] = relationship("Subtopic")
    
    @property
    def accuracy(self) -> float:
        if self.questions_attempted == 0:
            return 0.0
        return self.questions_correct / self.questions_attempted
