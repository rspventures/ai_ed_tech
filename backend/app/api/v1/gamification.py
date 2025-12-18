"""
AI Tutor Platform - Gamification API Router
Endpoints for XP, levels, and streaks
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_student
from app.models.user import Student
from app.services.gamification import GamificationService, LEVEL_THRESHOLDS, XP_REWARDS


router = APIRouter(prefix="/gamification", tags=["Gamification"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


# ============================================================================
# Response Schemas
# ============================================================================

class GamificationStats(BaseModel):
    """Full gamification stats for a student."""
    xp_total: int
    level: int
    level_progress: float  # 0.0 to 1.0
    xp_to_next_level: int
    current_streak: int
    longest_streak: int
    last_activity: str | None = None


class XPAwardResponse(BaseModel):
    """Response after awarding XP."""
    xp_earned: int
    new_xp_total: int
    level_up: bool
    new_level: int
    xp_to_next_level: int
    current_streak: int


class StreakResponse(BaseModel):
    """Response after streak update."""
    current_streak: int
    longest_streak: int
    bonus_xp: int
    message: str
    xp_total: int
    level: int


class XPAwardRequest(BaseModel):
    """Request to award XP."""
    activity: str
    multiplier: float = 1.0


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/stats", response_model=GamificationStats)
async def get_gamification_stats(
    current_student: Student = Depends(get_current_student),
    db: DbSession = None
):
    """
    Get the student's gamification stats.
    
    Returns XP, level, streak information.
    """
    service = GamificationService(db)
    stats = await service.get_stats(current_student.id)
    
    if "error" in stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=stats["error"]
        )
    
    return GamificationStats(**stats)


@router.post("/xp", response_model=XPAwardResponse)
async def award_xp(
    request: XPAwardRequest,
    current_student: Student = Depends(get_current_student),
    db: DbSession = None
):
    """
    Award XP to the current student.
    
    Valid activities:
    - lesson_complete: +50 XP
    - question_correct: +10 XP
    - question_incorrect: +2 XP
    - assessment_complete: +25 XP
    - assessment_perfect: +100 XP
    """
    if request.activity not in XP_REWARDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid activity. Valid activities: {list(XP_REWARDS.keys())}"
        )
    
    service = GamificationService(db)
    result = await service.award_xp(
        student_id=current_student.id,
        activity=request.activity,
        multiplier=request.multiplier
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    
    return XPAwardResponse(**result)


@router.post("/streak", response_model=StreakResponse)
async def update_streak(
    current_student: Student = Depends(get_current_student),
    db: DbSession = None
):
    """
    Update the student's daily streak.
    
    Should be called when student completes any activity.
    Returns streak info and any bonus XP earned.
    """
    service = GamificationService(db)
    result = await service.update_streak(current_student.id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    
    return StreakResponse(**result)


@router.get("/levels")
async def get_level_info():
    """
    Get level progression information.
    
    Returns the XP thresholds for each level.
    """
    return {
        "thresholds": LEVEL_THRESHOLDS,
        "rewards": XP_REWARDS
    }
