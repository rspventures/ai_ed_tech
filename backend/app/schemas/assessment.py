"""
AI Tutor Platform - Assessment Schemas
Pydantic schemas for assessment requests and responses
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class AssessmentQuestion(BaseModel):
    """A single question in an assessment."""
    question_id: str
    question: str
    options: list[str]
    question_type: str = "multiple_choice"  # "multiple_choice" or "multi_select"
    # We generally don't send the answer to the frontend for assessments until submission,
    # but for simplicity/security trade-offs in this MVP, we might keep it server-side.
    # For now, let's NOT send the answer.

class AssessmentStartResponse(BaseModel):
    """Response when starting an assessment."""
    assessment_id: str # Temporary ID for the session (or we can just use stateless submission)
    topic_name: str
    questions: list[AssessmentQuestion]

class AssessmentSubmissionItem(BaseModel):
    """Single answer submission with question context."""
    question_id: str
    question: str  # The question text
    options: list[str]  # The options shown
    answer: str | list[str]  # Student's selected answer (string or list of strings)
    correct_answer: str | list[str]  # The correct answer (first option or list)


class AssessmentSubmitRequest(BaseModel):
    """Request to submit an assessment."""
    topic_id: uuid.UUID
    answers: list[AssessmentSubmissionItem]
    assessment_session_id: str
    subject_name: str | None = None  # For feedback generation
    topic_name: str | None = None  # For feedback generation

class QuestionResultDetail(BaseModel):
    """Detail for a single question result."""
    question: str
    student_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str


class AssessmentFeedbackResponse(BaseModel):
    """AI-generated detailed feedback for an assessment."""
    overall_score_interpretation: str
    strengths: list[str]
    areas_of_improvement: list[str]
    ways_to_improve: list[str]
    practical_assignments: list[str]
    encouraging_words: str
    pattern_analysis: str


class AssessmentResultResponse(BaseModel):
    """Response after submitting assessment."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    score: float
    total_questions: int
    correct_questions: int
    completed_at: datetime
    details: list[QuestionResultDetail] | None = None
    topic_name: str | None = None  # Enriched
    feedback: AssessmentFeedbackResponse | None = None  # AI feedback

