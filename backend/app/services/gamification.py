"""
AI Tutor Platform - Gamification Service
Handles XP, levels, and streak management
"""
from datetime import datetime, date
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Student


# Level XP thresholds - inspired by game progression curves
LEVEL_THRESHOLDS = {
    1: 0,
    2: 100,
    3: 250,
    4: 500,
    5: 800,
    6: 1200,
    7: 1700,
    8: 2300,
    9: 3000,
    10: 4000,
    11: 5200,
    12: 6600,
    13: 8200,
    14: 10000,
    15: 12000,
}

# XP rewards for different activities
XP_REWARDS = {
    # Lessons & Practice
    "lesson_complete": 50,       # Completing a lesson
    "question_correct": 10,      # Correct answer in practice
    "question_incorrect": 2,     # Attempt even if wrong
    
    # Assessments (Subtopic level)
    "assessment_complete": 25,   # Completing an assessment
    "assessment_perfect": 100,   # Perfect score on assessment
    
    # Exams (Subject level, multi-topic)
    "exam_complete": 50,         # Completing an exam
    "exam_excellent": 75,        # Score 80%+ on exam
    "exam_perfect": 150,         # Score 100% on exam
    
    # Tests (Topic level) - for future use
    "test_complete": 35,         # Completing a topic test
    "test_excellent": 60,        # Score 80%+ on test
    "test_perfect": 120,         # Score 100% on test
    
    # Streaks & Engagement
    "streak_bonus": 20,          # Daily streak bonus
    "first_login_today": 5,      # Just logging in
}


class GamificationService:
    """
    The Gamification Engine 🎮
    
    Manages XP, levels, and streaks to keep students engaged.
    Inspired by Duolingo's proven engagement mechanics.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_student(self, student_id: uuid.UUID) -> Optional[Student]:
        """Get student by ID."""
        result = await self.db.execute(
            select(Student).where(Student.id == student_id)
        )
        return result.scalar_one_or_none()
    
    async def award_xp(
        self, 
        student_id: uuid.UUID, 
        activity: str, 
        multiplier: float = 1.0
    ) -> dict:
        """
        Award XP to a student for an activity.
        
        Returns:
            {
                "xp_earned": int,
                "new_xp_total": int,
                "level_up": bool,
                "new_level": int,
                "xp_to_next_level": int
            }
        """
        student = await self.get_student(student_id)
        if not student:
            return {"error": "Student not found"}
        
        # Calculate XP to award
        base_xp = XP_REWARDS.get(activity, 0)
        xp_earned = int(base_xp * multiplier)
        
        # Add streak bonus if maintaining streak
        if student.current_streak >= 3:
            streak_bonus = min(student.current_streak * 2, 20)  # Cap at 20
            xp_earned += streak_bonus
        
        # Update total XP
        old_level = student.level
        student.xp_total += xp_earned
        
        # Check for level up
        new_level = self._calculate_level(student.xp_total)
        level_up = new_level > old_level
        
        if level_up:
            student.level = new_level
        
        # Calculate XP to next level
        xp_to_next = self._get_xp_to_next_level(student.xp_total, new_level)
        
        await self.db.commit()
        
        return {
            "xp_earned": xp_earned,
            "new_xp_total": student.xp_total,
            "level_up": level_up,
            "new_level": new_level,
            "xp_to_next_level": xp_to_next,
            "current_streak": student.current_streak
        }
    
    def _calculate_level(self, xp: int) -> int:
        """Calculate level based on XP."""
        level = 1
        for lvl, threshold in sorted(LEVEL_THRESHOLDS.items()):
            if xp >= threshold:
                level = lvl
        return level
    
    def _get_xp_to_next_level(self, current_xp: int, current_level: int) -> int:
        """Calculate XP needed for next level."""
        next_level = current_level + 1
        if next_level in LEVEL_THRESHOLDS:
            return LEVEL_THRESHOLDS[next_level] - current_xp
        # Max level
        return 0
    
    async def update_streak(self, student_id: uuid.UUID) -> dict:
        """
        Update the student's daily streak.
        
        Called when student completes any activity.
        Returns streak info and any bonus XP earned.
        """
        student = await self.get_student(student_id)
        if not student:
            return {"error": "Student not found"}
        
        today = date.today()
        last_activity = student.last_activity_date
        
        bonus_xp = 0
        streak_message = ""
        
        if last_activity is None:
            # First ever activity!
            student.current_streak = 1
            student.longest_streak = 1
            streak_message = "🎉 You started your learning journey!"
        
        elif last_activity.date() == today:
            # Already active today, no streak update needed
            streak_message = f"🔥 {student.current_streak} day streak!"
        
        elif last_activity.date() == today - timedelta(days=1):
            # Consecutive day - extend streak!
            student.current_streak += 1
            if student.current_streak > student.longest_streak:
                student.longest_streak = student.current_streak
            
            # Award streak bonus
            bonus_xp = min(student.current_streak * 5, 50)  # Cap at 50
            student.xp_total += bonus_xp
            
            if student.current_streak == 7:
                streak_message = "🌟 Amazing! 1 week streak!"
                bonus_xp += 50  # Week bonus
            elif student.current_streak == 30:
                streak_message = "🏆 Legendary! 1 month streak!"
                bonus_xp += 200  # Month bonus
            else:
                streak_message = f"🔥 {student.current_streak} day streak! +{bonus_xp} XP"
        
        else:
            # Streak broken 😢
            old_streak = student.current_streak
            student.current_streak = 1
            streak_message = f"Starting fresh! Your best was {old_streak} days."
        
        # Update last activity date
        student.last_activity_date = datetime.utcnow()
        
        await self.db.commit()
        
        return {
            "current_streak": student.current_streak,
            "longest_streak": student.longest_streak,
            "bonus_xp": bonus_xp,
            "message": streak_message,
            "xp_total": student.xp_total,
            "level": student.level
        }
    
    async def get_stats(self, student_id: uuid.UUID) -> dict:
        """Get full gamification stats for a student."""
        student = await self.get_student(student_id)
        if not student:
            return {"error": "Student not found"}
        
        # Calculate progress to next level
        current_level_xp = LEVEL_THRESHOLDS.get(student.level, 0)
        next_level_xp = LEVEL_THRESHOLDS.get(student.level + 1, current_level_xp)
        
        if next_level_xp > current_level_xp:
            progress_in_level = student.xp_total - current_level_xp
            xp_for_level = next_level_xp - current_level_xp
            level_progress = progress_in_level / xp_for_level
        else:
            level_progress = 1.0  # Max level
        
        return {
            "xp_total": student.xp_total,
            "level": student.level,
            "level_progress": round(level_progress, 2),
            "xp_to_next_level": max(0, next_level_xp - student.xp_total),
            "current_streak": student.current_streak,
            "longest_streak": student.longest_streak,
            "last_activity": student.last_activity_date.isoformat() if student.last_activity_date else None
        }


# Import timedelta at top
from datetime import timedelta
