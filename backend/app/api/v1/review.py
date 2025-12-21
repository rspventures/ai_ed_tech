"""
AI Tutor Platform - Review API Router
Endpoints for Spaced Repetition System (Smart Review)

This router implements the Agentic Architecture pattern:
- Uses the ReviewAgent for intelligent review scheduling
- LLM-powered insights for personalized learning guidance
"""
import uuid
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_student
from app.ai.agents.reviewer import review_agent, ReviewItem  # BaseAgent-compliant alias
from app.models.user import User, Student
from app.models.curriculum import Progress
from app.schemas.review import (
    ReviewItemResponse,
    DailyReviewResponse,
    ReviewSessionComplete,
    ReviewScheduleUpdate
)

router = APIRouter(prefix="/review", tags=["Review (SRS)"])


@router.get("/daily", response_model=DailyReviewResponse)
async def get_daily_review(
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_student),
    limit: int = 10
):
    """
    Get today's review topics using the Agentic Review System.
    
    The ReviewAgent uses:
    1. SRS intervals (1, 3, 7, 14, 30 days) based on mastery
    2. LLM reasoning to generate personalized insights
    3. Priority scoring for optimal learning order
    """
    # Use the Review Agent to get due reviews
    review_items: List[ReviewItem] = await review_agent.get_due_reviews(
        db=db,
        student_id=current_student.id,
        limit=limit
    )
    
    # Generate AI insight about the review session
    ai_insight = await review_agent.generate_review_insight(
        student_name=current_student.first_name,
        review_items=review_items
    )
    
    # Convert to response schema
    items = [
        ReviewItemResponse(
            subtopic_id=item.subtopic_id,
            subtopic_name=item.subtopic_name,
            topic_name=item.topic_name,
            subject_name=item.subject_name,
            mastery_level=item.mastery_level,
            last_practiced=item.last_practiced,
            days_since_review=item.days_since_review,
            priority=item.priority,
            review_reason=item.review_reason
        )
        for item in review_items
    ]
    
    high_priority = sum(1 for item in items if item.priority == "high")
    
    return DailyReviewResponse(
        items=items,
        total_due=len(items),
        ai_insight=ai_insight,
        high_priority_count=high_priority
    )


@router.post("/complete", response_model=ReviewScheduleUpdate)
async def complete_review_session(
    data: ReviewSessionComplete,
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    """
    Mark a review session as complete and update the SRS schedule.
    
    The ReviewAgent adjusts the next review interval based on performance:
    - Good (>0.7): Increase interval (move to longer SRS cycle)
    - Medium (0.4-0.7): Keep interval
    - Poor (<0.4): Reset to short interval (1 day)
    """
    # Use the Review Agent to update the schedule
    await review_agent.update_review_schedule(
        db=db,
        student_id=current_student.id,
        subtopic_id=data.subtopic_id,
        performance_score=data.performance_score
    )
    
    # Fetch updated progress to return
    query = select(Progress).where(
        and_(
            Progress.student_id == current_student.id,
            Progress.subtopic_id == data.subtopic_id
        )
    )
    result = await db.execute(query)
    progress = result.scalar_one_or_none()
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Progress record not found"
        )
    
    # Generate encouraging message based on performance
    if data.performance_score >= 0.8:
        message = "🌟 Excellent! You've mastered this topic!"
    elif data.performance_score >= 0.6:
        message = "👍 Good job! Keep practicing to get even better!"
    elif data.performance_score >= 0.4:
        message = "📚 You're making progress! Review this topic again soon."
    else:
        message = "💪 Don't give up! We'll review this again tomorrow."
    
    return ReviewScheduleUpdate(
        subtopic_id=data.subtopic_id,
        new_mastery_level=progress.mastery_level,
        next_review_at=progress.next_review_at or datetime.utcnow() + timedelta(days=1),
        interval_days=progress.review_interval_days,
        message=message
    )


@router.get("/stats")
async def get_review_stats(
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    """
    Get review statistics for the student.
    
    Returns metrics about their SRS progress.
    """
    # Count topics by mastery level
    query = select(Progress).where(Progress.student_id == current_student.id)
    result = await db.execute(query)
    all_progress = result.scalars().all()
    
    now = datetime.utcnow()
    
    stats = {
        "total_topics_practiced": len(all_progress),
        "mastered": sum(1 for p in all_progress if p.mastery_level >= 0.8),
        "proficient": sum(1 for p in all_progress if 0.6 <= p.mastery_level < 0.8),
        "learning": sum(1 for p in all_progress if 0.4 <= p.mastery_level < 0.6),
        "struggling": sum(1 for p in all_progress if p.mastery_level < 0.4),
        "due_today": sum(1 for p in all_progress if p.next_review_at and p.next_review_at <= now),
        "upcoming_week": sum(
            1 for p in all_progress 
            if p.next_review_at and now < p.next_review_at <= now + timedelta(days=7)
        )
    }
    
    return stats
