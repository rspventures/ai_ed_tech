"""
AI Tutor Platform - Analytics Service
Service for generating parent/guardian insights and reports
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import Student
from app.models.curriculum import Subject, Topic, Progress
from app.models.assessment import AssessmentResult
from app.models.lesson import GeneratedLesson, StudentLessonProgress
from app.schemas.parent import (
    ChildSummary,
    ChildListItem,
    SubjectMastery,
    ActivityItem,
    WeeklyProgress,
    ChildDetailResponse
)


class AnalyticsService:
    """
    Service for aggregating student analytics for parent view.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_children_list(self, parent_id: uuid.UUID) -> List[ChildListItem]:
        """Get list of children for a parent."""
        query = select(Student).where(Student.parent_id == parent_id)
        result = await self.db.execute(query)
        students = result.scalars().all()
        
        return [
            ChildListItem(
                student_id=s.id,
                student_name=f"{s.first_name} {s.last_name}",
                avatar_url=s.avatar_url,
                grade_level=s.grade_level
            )
            for s in students
        ]

    async def get_child_summary(self, student_id: uuid.UUID) -> ChildSummary:
        """Get a summary of a child's learning progress."""
        # Get student
        student_query = select(Student).where(Student.id == student_id)
        result = await self.db.execute(student_query)
        student = result.scalar_one_or_none()
        
        if not student:
            raise ValueError("Student not found")
        
        # Count lessons completed
        lessons_query = select(func.count(StudentLessonProgress.id)).where(
            StudentLessonProgress.student_id == student_id,
            StudentLessonProgress.completed_at.isnot(None)
        )
        lessons_result = await self.db.execute(lessons_query)
        total_lessons = lessons_result.scalar() or 0
        
        # Count assessments and average score
        assessments_query = select(
            func.count(AssessmentResult.id),
            func.avg(AssessmentResult.score)
        ).where(AssessmentResult.student_id == student_id)
        assessments_result = await self.db.execute(assessments_query)
        assessments_data = assessments_result.first()
        total_assessments = assessments_data[0] or 0
        average_score = float(assessments_data[1] or 0)
        
        # Calculate total time (from lessons)
        time_query = select(func.sum(StudentLessonProgress.time_spent_seconds)).where(
            StudentLessonProgress.student_id == student_id
        )
        time_result = await self.db.execute(time_query)
        total_seconds = time_result.scalar() or 0
        total_time_minutes = total_seconds // 60
        
        # Get subject mastery
        subject_mastery = await self._get_subject_mastery(student_id)
        
        # Determine top subjects and needs attention
        top_subjects = [
            sm.subject_name for sm in subject_mastery 
            if sm.mastery_level in ["proficient", "mastered"]
        ][:3]
        
        needs_attention = [
            sm.subject_name for sm in subject_mastery 
            if sm.mastery_level in ["struggling"]
        ][:3]
        
        return ChildSummary(
            student_id=student.id,
            student_name=f"{student.first_name} {student.last_name}",
            avatar_url=student.avatar_url,
            grade_level=student.grade_level,
            total_lessons_completed=total_lessons,
            total_assessments_taken=total_assessments,
            total_time_minutes=total_time_minutes,
            average_score=round(average_score, 1),
            current_streak=0,  # TODO: Implement streak tracking
            subject_mastery=subject_mastery,
            top_subjects=top_subjects,
            needs_attention=needs_attention
        )

    async def _get_subject_mastery(self, student_id: uuid.UUID) -> List[SubjectMastery]:
        """Get mastery level for each subject."""
        from app.models.curriculum import Subtopic
        
        # Get all subjects with their topics
        subjects_query = select(Subject).options(selectinload(Subject.topics))
        subjects_result = await self.db.execute(subjects_query)
        subjects = subjects_result.scalars().all()
        
        mastery_list = []
        
        for subject in subjects:
            topic_ids = [t.id for t in subject.topics]
            if not topic_ids:
                continue
            
            # Get subtopic IDs for this subject's topics
            subtopic_query = select(Subtopic.id).where(Subtopic.topic_id.in_(topic_ids))
            subtopic_result = await self.db.execute(subtopic_query)
            subtopic_ids = [row[0] for row in subtopic_result.fetchall()]
            
            if not subtopic_ids:
                mastery_list.append(SubjectMastery(
                    subject_id=subject.id,
                    subject_name=subject.name,
                    average_score=0.0,
                    topics_completed=0,
                    total_topics=len(subject.topics),
                    mastery_level="learning"
                ))
                continue
            
            # Get progress for subtopics in this subject
            progress_query = select(
                func.count(Progress.id),
                func.avg(Progress.mastery_level)
            ).where(Progress.subtopic_id.in_(subtopic_ids), Progress.student_id == student_id)
            progress_result = await self.db.execute(progress_query)
            progress_data = progress_result.first()
            
            subtopics_with_progress = progress_data[0] or 0
            avg_mastery = float(progress_data[1] or 0)
            
            # Determine mastery level label
            if avg_mastery >= 0.8:
                level = "mastered"
            elif avg_mastery >= 0.6:
                level = "proficient"
            elif avg_mastery >= 0.4:
                level = "learning"
            else:
                level = "struggling"
            
            # Get assessment scores for this subject
            score_query = select(func.avg(AssessmentResult.score)).where(
                and_(
                    AssessmentResult.student_id == student_id,
                    AssessmentResult.topic_id.in_(topic_ids)
                )
            )
            score_result = await self.db.execute(score_query)
            avg_score = float(score_result.scalar() or 0)
            
            mastery_list.append(SubjectMastery(
                subject_id=subject.id,
                subject_name=subject.name,
                average_score=round(avg_score, 1),
                topics_completed=subtopics_with_progress,
                total_topics=len(subtopic_ids),
                mastery_level=level
            ))
        
        return mastery_list

    async def get_weekly_progress(self, student_id: uuid.UUID) -> List[WeeklyProgress]:
        """Get progress data for the last 7 days."""
        today = datetime.utcnow().date()
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        weekly = []
        
        for i in range(7):
            day_date = today - timedelta(days=6-i)
            day_name = days[day_date.weekday()]
            
            # Count lessons on this day
            lessons_query = select(func.count(StudentLessonProgress.id)).where(
                and_(
                    StudentLessonProgress.student_id == student_id,
                    func.date(StudentLessonProgress.completed_at) == day_date
                )
            )
            lessons_result = await self.db.execute(lessons_query)
            lessons_count = lessons_result.scalar() or 0
            
            # Sum time on this day
            time_query = select(func.sum(StudentLessonProgress.time_spent_seconds)).where(
                and_(
                    StudentLessonProgress.student_id == student_id,
                    func.date(StudentLessonProgress.completed_at) == day_date
                )
            )
            time_result = await self.db.execute(time_query)
            practice_time = (time_result.scalar() or 0) // 60
            
            weekly.append(WeeklyProgress(
                day=day_name,
                lessons=lessons_count,
                practice_time=practice_time
            ))
        
        return weekly

    async def get_recent_activity(
        self, 
        student_id: uuid.UUID, 
        limit: int = 10
    ) -> List[ActivityItem]:
        """Get recent activity feed for a student."""
        activities = []
        
        # Get recent lesson completions
        lessons_query = select(StudentLessonProgress).options(
            selectinload(StudentLessonProgress.lesson)
        ).where(
            StudentLessonProgress.student_id == student_id,
            StudentLessonProgress.completed_at.isnot(None)
        ).order_by(StudentLessonProgress.completed_at.desc()).limit(limit)
        
        lessons_result = await self.db.execute(lessons_query)
        for lp in lessons_result.scalars():
            activities.append(ActivityItem(
                timestamp=lp.completed_at,
                action_type="lesson_completed",
                description=f"Completed lesson: {lp.lesson.title}",
                emoji="📖"
            ))
        
        # Get recent assessments
        assessments_query = select(AssessmentResult).options(
            selectinload(AssessmentResult.topic)
        ).where(
            AssessmentResult.student_id == student_id
        ).order_by(AssessmentResult.completed_at.desc()).limit(limit)
        
        assessments_result = await self.db.execute(assessments_query)
        for ar in assessments_result.scalars():
            topic_name = ar.topic.name if ar.topic else "Unknown"
            emoji = "🏆" if ar.score >= 80 else "📝"
            activities.append(ActivityItem(
                timestamp=ar.completed_at,
                action_type="assessment_taken",
                description=f"Scored {ar.score}% on {topic_name}",
                score=ar.score,
                emoji=emoji
            ))
        
        # Sort by timestamp and limit
        activities.sort(key=lambda x: x.timestamp, reverse=True)
        return activities[:limit]

    async def get_child_detail(self, student_id: uuid.UUID) -> ChildDetailResponse:
        """Get full detail for a child including all analytics."""
        summary = await self.get_child_summary(student_id)
        weekly = await self.get_weekly_progress(student_id)
        activity = await self.get_recent_activity(student_id)
        
        # Generate AI insights (placeholder for now)
        ai_insights = None
        if summary.needs_attention:
            topics = ", ".join(summary.needs_attention)
            ai_insights = f"📊 Focus areas: {summary.student_name} could use more practice in {topics}. Consider setting aside 15-20 minutes daily for these subjects."
        elif summary.top_subjects:
            topics = ", ".join(summary.top_subjects)
            ai_insights = f"🌟 Great progress! {summary.student_name} is excelling in {topics}. They're ready for more challenging content!"
        
        return ChildDetailResponse(
            summary=summary,
            weekly_progress=weekly,
            recent_activity=activity,
            ai_insights=ai_insights
        )
