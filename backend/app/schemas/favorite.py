"""
AI Tutor Platform - Favorites Schemas
Pydantic models for favorites/starred module endpoints.
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class FavoriteCreate(BaseModel):
    """Request to add a module to favorites."""
    lesson_id: str = Field(..., description="UUID of the lesson")
    module_index: int = Field(..., ge=0, description="Index of module in lesson.modules array")
    

class FavoriteResponse(BaseModel):
    """Response for a single favorite."""
    id: str
    lesson_id: str
    module_index: int
    module_type: str
    module_content: dict
    subtopic_id: str
    subtopic_name: Optional[str] = None
    topic_id: str
    topic_name: Optional[str] = None
    subject_id: str
    subject_name: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class FavoriteListResponse(BaseModel):
    """Response for list of favorites with context."""
    favorites: List[FavoriteResponse]
    total_count: int
    

class FavoritesByLevel(BaseModel):
    """Favorites grouped by subtopic/topic/subject."""
    level: str  # "subtopic", "topic", or "subject"
    level_id: str
    level_name: str
    count: int
    favorites: List[FavoriteResponse]
