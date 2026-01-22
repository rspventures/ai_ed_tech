"""
AI Tutor Platform - Learning Path Service
The "Brain" that determines adaptive learning recommendations
"""
import uuid
from typing import Optional, List
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.curriculum import Topic, Subtopic, Progress
from app.models.lesson import GeneratedLesson, StudentLessonProgress
from app.models.assessment import AssessmentResult
from app.schemas.lesson import StudyActionType, StudyActionResponse, LearningPathResponse


class LearningPathService:
    """
    The Curriculum Agent (The Brain) 🧠
    
    Analyzes student progress and determines the optimal next study action.
    Uses mastery levels and completion status to guide the learning journey.
    """
    
    # Mastery thresholds
    LESSON_THRESHOLD = 0.4   # Below this -> needs concept introduction
    PRACTICE_THRESHOLD = 0.7  # Between LESSON and this -> needs practice
    # Above PRACTICE_THRESHOLD -> ready for assessment or next topic
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_topic_mastery(
        self, 
        student_id: uuid.UUID, 
        topic_id: uuid.UUID
    ) -> float:
        """
        Calculate overall mastery for a topic based on subtopic progress.
        
        Returns:
            Float between 0.0 and 1.0
        """
        # Get all subtopics for this topic
        subtopics_query = select(Subtopic.id).where(Subtopic.topic_id == topic_id)
        subtopic_result = await self.db.execute(subtopics_query)
        subtopic_ids = [row[0] for row in subtopic_result.fetchall()]
        
        if not subtopic_ids:
            return 0.0
        
        # Get progress for each subtopic
        progress_query = select(Progress).where(
            Progress.student_id == student_id,
            Progress.subtopic_id.in_(subtopic_ids)
        )
        progress_result = await self.db.execute(progress_query)
        progress_records = progress_result.scalars().all()
        
        if not progress_records:
            return 0.0
        
        # Calculate average mastery
        total_mastery = sum(p.mastery_level for p in progress_records)
        return total_mastery / len(subtopic_ids)  # Use total subtopics, not just practiced ones
    
    async def get_subtopic_mastery(
        self,
        student_id: uuid.UUID,
        subtopic_id: uuid.UUID
    ) -> float:
        """Get mastery level for a specific subtopic."""
        query = select(Progress).where(
            Progress.student_id == student_id,
            Progress.subtopic_id == subtopic_id
        )
        result = await self.db.execute(query)
        progress = result.scalar_one_or_none()
        
        return progress.mastery_level if progress else 0.0
    
    async def has_completed_lesson(
        self,
        student_id: uuid.UUID,
        subtopic_id: uuid.UUID
    ) -> bool:
        """Check if student has completed ANY lesson for a subtopic (V1 or V2)."""
        # Find all lessons for this subtopic (could be V1 and V2)
        lesson_query = select(GeneratedLesson.id).where(
            GeneratedLesson.subtopic_id == subtopic_id
        )
        lesson_result = await self.db.execute(lesson_query)
        lesson_ids = lesson_result.scalars().all()
        
        if not lesson_ids:
            return False
        
        # Check if student completed any of them
        progress_query = select(StudentLessonProgress).where(
            StudentLessonProgress.student_id == student_id,
            StudentLessonProgress.lesson_id.in_(lesson_ids),
            StudentLessonProgress.completed_at.isnot(None)
        )
        progress_result = await self.db.execute(progress_query)
        return progress_result.first() is not None
    
    async def get_next_action(
        self,
        student_id: uuid.UUID,
        topic_id: uuid.UUID
    ) -> StudyActionResponse:
        """
        Determine the next best study action for a student on a topic.
        
        The logic:
        1. Find the "weakest" subtopic (lowest mastery)
        2. If mastery < 40% and no lesson completed -> LESSON
        3. If mastery < 70% -> PRACTICE
        4. If mastery >= 70% -> ASSESSMENT or move to next subtopic
        """
        # Get topic details
        topic_query = select(Topic).options(
            selectinload(Topic.subtopics)
        ).where(Topic.id == topic_id)
        topic_result = await self.db.execute(topic_query)
        topic = topic_result.scalar_one_or_none()
        
        if not topic or not topic.subtopics:
            return StudyActionResponse(
                action_type=StudyActionType.COMPLETE,
                resource_id=topic_id,
                resource_name=topic.name if topic else "Unknown",
                reason="No content available for this topic.",
                mastery_level=0.0
            )
        
        # Find the subtopic with lowest mastery
        weakest_subtopic = None
        lowest_mastery = 1.0
        
        for subtopic in sorted(topic.subtopics, key=lambda s: s.display_order):
            mastery = await self.get_subtopic_mastery(student_id, subtopic.id)
            if mastery < lowest_mastery:
                lowest_mastery = mastery
                weakest_subtopic = subtopic
        
        if not weakest_subtopic:
            weakest_subtopic = topic.subtopics[0]
            lowest_mastery = 0.0
        
        # Determine action based on mastery
        if lowest_mastery < self.LESSON_THRESHOLD:
            # Check if lesson exists and was completed
            lesson_completed = await self.has_completed_lesson(student_id, weakest_subtopic.id)
            
            if not lesson_completed:
                return StudyActionResponse(
                    action_type=StudyActionType.LESSON,
                    resource_id=weakest_subtopic.id,
                    resource_name=weakest_subtopic.name,
                    reason="Let's learn the basics first! 📚",
                    mastery_level=lowest_mastery,
                    estimated_time_minutes=5,
                    difficulty="easy"
                )
        
        if lowest_mastery < self.PRACTICE_THRESHOLD:
            return StudyActionResponse(
                action_type=StudyActionType.PRACTICE,
                resource_id=weakest_subtopic.id,
                resource_name=weakest_subtopic.name,
                reason="Time to practice what you've learned! 💪",
                mastery_level=lowest_mastery,
                estimated_time_minutes=10,
                difficulty="medium" if lowest_mastery > 0.5 else "easy"
            )
        
        # High mastery - check if ready for assessment
        topic_mastery = await self.get_topic_mastery(student_id, topic_id)
        
        if topic_mastery >= self.PRACTICE_THRESHOLD:
            return StudyActionResponse(
                action_type=StudyActionType.ASSESSMENT,
                resource_id=topic_id,
                resource_name=topic.name,
                reason="You're doing great! Ready for a challenge? 🌟",
                mastery_level=topic_mastery,
                estimated_time_minutes=15,
                difficulty="medium"
            )
        
        # Find next subtopic to work on
        for subtopic in sorted(topic.subtopics, key=lambda s: s.display_order):
            sub_mastery = await self.get_subtopic_mastery(student_id, subtopic.id)
            if sub_mastery < self.PRACTICE_THRESHOLD:
                return StudyActionResponse(
                    action_type=StudyActionType.PRACTICE,
                    resource_id=subtopic.id,
                    resource_name=subtopic.name,
                    reason="Let's strengthen your skills here! 🎯",
                    mastery_level=sub_mastery,
                    estimated_time_minutes=10,
                    difficulty="medium"
                )
        
        # All subtopics mastered!
        return StudyActionResponse(
            action_type=StudyActionType.COMPLETE,
            resource_id=topic_id,
            resource_name=topic.name,
            reason="Amazing! You've mastered this topic! 🏆",
            mastery_level=topic_mastery
        )
    
    async def get_learning_path(
        self,
        student_id: uuid.UUID,
        topic_id: uuid.UUID
    ) -> LearningPathResponse:
        """
        Get the full learning path for a topic, including progress stats.
        """
        # Get topic
        topic_query = select(Topic).options(
            selectinload(Topic.subtopics)
        ).where(Topic.id == topic_id)
        topic_result = await self.db.execute(topic_query)
        topic = topic_result.scalar_one_or_none()
        
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")
        
        # Calculate stats
        topic_mastery = await self.get_topic_mastery(student_id, topic_id)
        next_action = await self.get_next_action(student_id, topic_id)
        
        # Count completed lessons
        completed_lessons = 0
        total_lessons = 0
        completed_practice = 0
        
        for subtopic in topic.subtopics:
            total_lessons += 1
            if await self.has_completed_lesson(student_id, subtopic.id):
                completed_lessons += 1
            
            mastery = await self.get_subtopic_mastery(student_id, subtopic.id)
            if mastery >= self.LESSON_THRESHOLD:
                completed_practice += 1
        
        return LearningPathResponse(
            topic_id=topic_id,
            topic_name=topic.name,
            current_mastery=topic_mastery,
            next_action=next_action,
            completed_lessons=completed_lessons,
            total_lessons=total_lessons,
            completed_practice=completed_practice,
            recommended_path=[]  # Could be expanded to show full path
        )
