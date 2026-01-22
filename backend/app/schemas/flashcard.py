"""
AI Tutor Platform - Flashcard Schemas
Pydantic models for flashcard API requests and responses
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class FlashcardDifficulty(str, Enum):
    """Difficulty levels for flashcards."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class FlashcardItem(BaseModel):
    """Single flashcard with front and back content."""
    front: str = Field(..., min_length=2, max_length=500, description="Question/term side")
    back: str = Field(..., min_length=2, max_length=1000, description="Answer/definition side")
    difficulty: Optional[FlashcardDifficulty] = Field(None, description="Card difficulty level")


class FlashcardDeckCreate(BaseModel):
    """Request model for creating a flashcard deck."""
    subtopic_id: str
    grade_level: int = Field(default=5, ge=1, le=12)


class FlashcardDeckContent(BaseModel):
    """Content structure for a flashcard deck."""
    title: str = Field(..., min_length=5, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    cards: List[FlashcardItem] = Field(..., min_items=1, max_items=50)


class FlashcardDeckResponse(BaseModel):
    """API response for a flashcard deck."""
    id: str
    subtopic_id: str
    grade_level: int
    title: str
    description: Optional[str]
    cards: List[FlashcardItem]
    card_count: int
    generated_by: str
    
    # Progress (optional, included when student context available)
    cards_reviewed: Optional[int] = None
    cards_mastered: Optional[int] = None
    mastery_percentage: Optional[float] = None
    
    class Config:
        from_attributes = True


class FlashcardDeckListItem(BaseModel):
    """Compact deck info for listing."""
    id: str
    subtopic_id: str
    subtopic_name: str
    title: str
    card_count: int
    mastery_percentage: Optional[float] = None
    
    class Config:
        from_attributes = True
