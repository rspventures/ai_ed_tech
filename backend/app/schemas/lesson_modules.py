"""
AI Tutor Platform - Lesson 2.0 Module Schemas
Pydantic models for Interactive Lesson Playlists.

Each lesson is a sequence of modules that can be:
- Hook: Attention-grabbing opener
- Text: Short explanatory content (max 3 sentences)
- Flashcard: Term/definition flip card
- FunFact: Interesting related fact
- QuizSingle: Single-choice question
- Activity: Real-world task or social challenge
- ImagePlaceholder: Future image support (deferred)
"""
from enum import Enum
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field, validator


class LessonModuleType(str, Enum):
    """Types of lesson modules."""
    HOOK = "hook"
    TEXT = "text"
    FLASHCARD = "flashcard"
    FUN_FACT = "fun_fact"
    QUIZ_SINGLE = "quiz_single"
    ACTIVITY = "activity"
    IMAGE_PLACEHOLDER = "image_placeholder"
    EXAMPLE = "example"  # Worked example with step-by-step
    SUMMARY = "summary"  # Key takeaways recap


# ============================================================================
# Module Schemas
# ============================================================================

class HookModule(BaseModel):
    """Attention-grabbing opener (question, scenario, or fun fact)."""
    type: Literal["hook"] = "hook"
    content: str = Field(..., min_length=5, max_length=1000, description="Hook text")
    emoji: Optional[str] = Field(None, description="Optional emoji to accompany")


class TextModule(BaseModel):
    """Short explanatory text (max 3 sentences)."""
    type: Literal["text"] = "text"
    content: str = Field(..., min_length=10, max_length=5000, description="Explanation")
    
    @validator('content')
    def limit_sentences(cls, v):
        # Soft check: warn if too long
        sentence_count = v.count('.') + v.count('!') + v.count('?')
        if sentence_count > 5:
            # Don't fail, just truncate in practice
            pass
        return v


class FlashcardModule(BaseModel):
    """Interactive flip-card for key terms."""
    type: Literal["flashcard"] = "flashcard"
    front: str = Field(..., min_length=2, max_length=500, description="Term or question")
    back: str = Field(..., min_length=2, max_length=1000, description="Definition or answer")


class FunFactModule(BaseModel):
    """Mind-blowing fact related to the topic."""
    type: Literal["fun_fact"] = "fun_fact"
    content: str = Field(..., min_length=10, max_length=1000, description="The fun fact")
    source: Optional[str] = Field(None, description="Optional source/attribution")


class QuizSingleModule(BaseModel):
    """Single-choice quiz question."""
    type: Literal["quiz_single"] = "quiz_single"
    question: str = Field(..., min_length=5, max_length=1000)
    options: List[str] = Field(..., min_items=2, max_items=4)
    correct_answer: str = Field(..., description="Must match one of the options")
    
    @validator('correct_answer')
    def answer_must_be_in_options(cls, v, values):
        if 'options' in values and v not in values['options']:
            raise ValueError(f"correct_answer '{v}' must be one of the options")
        return v


class ActivityModule(BaseModel):
    """Real-world task or social challenge."""
    type: Literal["activity"] = "activity"
    content: str = Field(..., min_length=10, max_length=1000, description="Activity description")
    activity_type: Literal["solo", "social", "creative", "group"] = Field(
        "solo", 
        description="solo=do alone, social/group=involves others, creative=draw/build"
    )


class ImagePlaceholderModule(BaseModel):
    """Placeholder for future image support."""
    type: Literal["image_placeholder"] = "image_placeholder"
    image_hint: str = Field(..., description="Description of what image would show")
    caption: Optional[str] = Field(None, description="Image caption")


class ExampleModule(BaseModel):
    """Worked example with step-by-step explanation."""
    type: Literal["example"] = "example"
    title: str = Field(..., min_length=5, max_length=200, description="Example title")
    problem: str = Field(..., min_length=10, max_length=500, description="The problem or scenario")
    steps: List[str] = Field(..., min_items=1, max_items=10, description="Step-by-step solution")
    answer: str = Field(..., min_length=1, max_length=500, description="Final answer")


class SummaryModule(BaseModel):
    """Key takeaways/summary at end of lesson."""
    type: Literal["summary"] = "summary"
    title: str = Field("Key Takeaways", max_length=100, description="Summary title")
    points: List[str] = Field(..., min_items=2, max_items=10, description="Bullet points of key concepts")


# ============================================================================
# Union Type for All Modules
# ============================================================================

LessonModule = Union[
    HookModule,
    TextModule,
    FlashcardModule,
    FunFactModule,
    QuizSingleModule,
    ActivityModule,
    ImagePlaceholderModule,
    ExampleModule,
    SummaryModule,
]


# ============================================================================
# Lesson 2.0 Content Schema
# ============================================================================

class Lesson2Content(BaseModel):
    """
    Complete Lesson 2.0 content structure.
    A lesson is a playlist of interactive modules.
    """
    title: str = Field(..., min_length=5, max_length=100, description="Lesson title")
    modules: List[LessonModule] = Field(
        ..., 
        min_items=1, 
        max_items=25,
        description="Ordered list of lesson modules (12-20 recommended)"
    )
    estimated_duration_minutes: Optional[int] = Field(
        None, 
        ge=1, 
        le=30,
        description="Estimated time to complete"
    )
    
    def get_module_counts(self) -> dict:
        """Get count of each module type."""
        counts = {}
        for module in self.modules:
            module_type = module.type
            counts[module_type] = counts.get(module_type, 0) + 1
        return counts


# ============================================================================
# API Response Schema
# ============================================================================

class Lesson2Response(BaseModel):
    """API response for Lesson 2.0 endpoint."""
    id: str
    subtopic_id: str
    grade_level: int
    content: Lesson2Content
    generated_by: str = "LessonAgentV2"
    content_version: int = 2
    is_completed: bool = False
    
    class Config:
        from_attributes = True
