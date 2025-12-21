"""
AI Tutor Platform - Feedback API
Endpoint for collecting user feedback (thumbs up/down) on AI responses.
"""
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Depends

from app.api.deps import get_current_student
from app.ai.core.observability import record_user_feedback, get_observer

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    """Request body for feedback submission."""
    trace_id: str
    is_positive: bool
    message_id: Optional[str] = None
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Response for feedback submission."""
    success: bool
    message: str


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
    current_student = Depends(get_current_student)
):
    """
    Submit user feedback for an AI response.
    
    Args:
        feedback: Feedback data including trace_id and rating
        current_student: Authenticated student
        
    Returns:
        Success status
    """
    observer = get_observer()
    
    if not observer.is_enabled:
        # Still accept feedback even if Langfuse isn't available
        return FeedbackResponse(
            success=True,
            message="Feedback received (observability not configured)"
        )
    
    try:
        # Record feedback in Langfuse
        comment = feedback.comment
        if current_student:
            comment = f"[Student: {current_student.id}] {comment or ''}"
        
        record_user_feedback(
            trace_id=feedback.trace_id,
            is_positive=feedback.is_positive,
            comment=comment
        )
        
        return FeedbackResponse(
            success=True,
            message="Thank you for your feedback!"
        )
        
    except Exception as e:
        # Don't fail the request if feedback recording fails
        return FeedbackResponse(
            success=True,
            message="Feedback received"
        )


@router.get("/health")
async def feedback_health():
    """Check if observability is configured."""
    observer = get_observer()
    return {
        "observability_enabled": observer.is_enabled,
        "langfuse_available": observer._initialized if hasattr(observer, '_initialized') else False
    }
