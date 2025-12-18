"""
AI Tutor Platform - Parent Dashboard API Router
Endpoints for parent/guardian analytics and progress monitoring
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, Student
from app.schemas.parent import (
    ChildListItem,
    ChildSummary,
    ChildDetailResponse,
    ActivityItem,
    WeeklyProgress
)
from app.services.analytics import AnalyticsService


router = APIRouter(prefix="/parent", tags=["Parent Dashboard"])


async def verify_parent_access(
    student_id: uuid.UUID,
    user: User,
    db: AsyncSession
) -> Student:
    """Verify that the user has access to the student's data."""
    query = select(Student).where(
        Student.id == student_id,
        Student.parent_id == user.id
    )
    result = await db.execute(query)
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this student's data"
        )
    return student


# ============================================================================
# Parent Dashboard Endpoints
# ============================================================================

@router.get("/children", response_model=List[ChildListItem])
async def get_children(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of all children (students) for the current parent.
    """
    service = AnalyticsService(db)
    return await service.get_children_list(user.id)


@router.get("/child/{student_id}", response_model=ChildDetailResponse)
async def get_child_detail(
    student_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get full analytics detail for a specific child.
    
    Includes:
    - Summary stats (lessons, assessments, time spent)
    - Subject mastery breakdown
    - Weekly progress chart data
    - Recent activity feed
    - AI-generated insights
    """
    # Verify access
    await verify_parent_access(student_id, user, db)
    
    service = AnalyticsService(db)
    try:
        return await service.get_child_detail(student_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/child/{student_id}/summary", response_model=ChildSummary)
async def get_child_summary(
    student_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a quick summary of a child's progress.
    
    Lighter than the full detail endpoint, good for dashboard cards.
    """
    await verify_parent_access(student_id, user, db)
    
    service = AnalyticsService(db)
    try:
        return await service.get_child_summary(student_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/child/{student_id}/activity", response_model=List[ActivityItem])
async def get_child_activity(
    student_id: uuid.UUID,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent activity feed for a child.
    
    Shows lessons completed, assessments taken, etc.
    """
    await verify_parent_access(student_id, user, db)
    
    service = AnalyticsService(db)
    return await service.get_recent_activity(student_id, limit=limit)


@router.get("/child/{student_id}/weekly", response_model=List[WeeklyProgress])
async def get_child_weekly_progress(
    student_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get weekly progress data for charts.
    
    Returns data for the last 7 days.
    """
    await verify_parent_access(student_id, user, db)
    
    service = AnalyticsService(db)
    return await service.get_weekly_progress(student_id)
