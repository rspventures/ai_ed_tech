"""
AI Tutor Platform - Flashcard Models
SQLAlchemy models for AI-generated flashcard decks and student progress tracking
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import Student
    from app.models.curriculum import Subtopic


class FlashcardDeck(Base):
    """AI-generated flashcard deck for a subtopic."""
    
    __tablename__ = "flashcard_decks"
    
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
    
    # Deck metadata
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Flashcards content (JSONB array)
    # Structure: [{"front": "Term", "back": "Definition", "difficulty": "easy|medium|hard"}]
    cards: Mapped[list] = mapped_column(JSONB, default=list)
    card_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    generated_by: Mapped[str] = mapped_column(String(100))  # Agent name
    
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
    student_progress: Mapped[list["StudentFlashcardProgress"]] = relationship(
        "StudentFlashcardProgress",
        back_populates="deck",
        cascade="all, delete-orphan"
    )


class StudentFlashcardProgress(Base):
    """Tracks student progress on flashcard decks."""
    
    __tablename__ = "student_flashcard_progress"
    
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
    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("flashcard_decks.id", ondelete="CASCADE"),
        index=True
    )
    
    # Progress tracking
    cards_reviewed: Mapped[int] = mapped_column(Integer, default=0)
    cards_mastered: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Relationships
    student: Mapped["Student"] = relationship("Student")
    deck: Mapped["FlashcardDeck"] = relationship(
        "FlashcardDeck", 
        back_populates="student_progress"
    )
    
    @property
    def mastery_percentage(self) -> float:
        if self.deck.card_count == 0:
            return 0.0
        return (self.cards_mastered / self.deck.card_count) * 100
