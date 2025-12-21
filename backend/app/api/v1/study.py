"""
AI Tutor Platform - Study API Router
Endpoints for adaptive learning and AI-generated lessons
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, Student
from app.models.curriculum import Topic, Subtopic
from app.models.lesson import GeneratedLesson, StudentLessonProgress
from app.schemas.lesson import (
    LessonResponse,
    LessonContent,
    LessonProgressResponse,
    StudyActionResponse,
    LearningPathResponse,
    GenerateLessonRequest,
    CompleteLessonRequest
)
from app.services.learning_path import LearningPathService
from app.ai.agents.lesson import lesson_agent  # Compliant with Safety Pipeline via BaseAgent


def sanitize_lesson_content(content: dict) -> dict:
    """
    Sanitize AI-generated lesson content to match expected schema.
    The AI sometimes returns lists where strings are expected.
    """
    sanitized = content.copy()
    
    # Convert list fields to strings
    for field in ['hook', 'introduction', 'summary', 'fun_fact']:
        if field in sanitized and isinstance(sanitized[field], list):
            sanitized[field] = '\n'.join(str(item) for item in sanitized[field])
    
    # Ensure sections is a list
    if 'sections' in sanitized and not isinstance(sanitized['sections'], list):
        sanitized['sections'] = []
    
    # Sanitize each section
    if 'sections' in sanitized:
        sanitized_sections = []
        for section in sanitized['sections']:
            if isinstance(section, dict):
                sanitized_section = section.copy()
                for field in ['title', 'content', 'example']:
                    if field in sanitized_section and isinstance(sanitized_section[field], list):
                        sanitized_section[field] = '\n'.join(str(item) for item in sanitized_section[field])
                sanitized_sections.append(sanitized_section)
        sanitized['sections'] = sanitized_sections
    
    return sanitized


router = APIRouter(prefix="/study", tags=["Study"])


async def get_student_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Student:
    """Get the student profile for the current user."""
    query = select(Student).where(Student.parent_id == user.id)
    result = await db.execute(query)
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )
    return student


# ============================================================================
# Learning Path Endpoints
# ============================================================================

@router.get("/next-step/{topic_id}", response_model=StudyActionResponse)
async def get_next_step(
    topic_id: uuid.UUID,
    student: Student = Depends(get_student_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the recommended next study action for a topic.
    
    The system analyzes the student's progress and returns:
    - LESSON: If they need to learn concepts first
    - PRACTICE: If they need more practice
    - ASSESSMENT: If they're ready to test their knowledge
    - COMPLETE: If they've mastered the topic
    """
    service = LearningPathService(db)
    return await service.get_next_action(student.id, topic_id)


@router.get("/path/{topic_id}", response_model=LearningPathResponse)
async def get_learning_path(
    topic_id: uuid.UUID,
    student: Student = Depends(get_student_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the full learning path for a topic, including progress stats.
    """
    service = LearningPathService(db)
    try:
        return await service.get_learning_path(student.id, topic_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/subtopic/{subtopic_id}/progress")
async def get_subtopic_progress(
    subtopic_id: uuid.UUID,
    student: Student = Depends(get_student_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Get progress for a specific subtopic.
    
    Returns:
    - mastery_level: 0.0 to 1.0
    - lesson_completed: boolean
    - practice_count: number of questions attempted (as practice indicator)
    """
    from app.models.curriculum import Progress
    
    service = LearningPathService(db)
    
    # Get mastery level
    mastery = await service.get_subtopic_mastery(student.id, subtopic_id)
    
    # Check if lesson is completed
    lesson_completed = await service.has_completed_lesson(student.id, subtopic_id)
    
    # Get practice count from Progress model (using questions_attempted as practice indicator)
    progress_query = select(Progress).where(
        Progress.student_id == student.id,
        Progress.subtopic_id == subtopic_id
    )
    progress_result = await db.execute(progress_query)
    progress = progress_result.scalar_one_or_none()
    
    # Use questions_attempted as practice count indicator
    practice_count = progress.questions_attempted if progress else 0
    
    return {
        "mastery_level": mastery,
        "lesson_completed": lesson_completed,
        "practice_count": practice_count
    }


# ============================================================================
# Lesson Endpoints
# ============================================================================

@router.get("/lesson/{subtopic_id}", response_model=LessonResponse)
async def get_or_generate_lesson(
    subtopic_id: uuid.UUID,
    student: Student = Depends(get_student_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a lesson for a subtopic. If no lesson exists, generate one.
    
    This endpoint:
    1. Checks if a lesson already exists for this subtopic + grade
    2. If not, generates a new lesson using AI
    3. Returns the lesson with user's completion status
    """
    # Get subtopic with topic and subject info
    subtopic_query = select(Subtopic).options(
        selectinload(Subtopic.topic).selectinload(Topic.subject)
    ).where(Subtopic.id == subtopic_id)
    subtopic_result = await db.execute(subtopic_query)
    subtopic = subtopic_result.scalar_one_or_none()
    
    if not subtopic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subtopic not found"
        )
    
    grade_level = student.grade_level or subtopic.topic.grade_level
    
    # Check for existing lesson
    lesson_query = select(GeneratedLesson).where(
        GeneratedLesson.subtopic_id == subtopic_id,
        GeneratedLesson.grade_level == grade_level
    )
    lesson_result = await db.execute(lesson_query)
    lesson = lesson_result.scalar_one_or_none()
    
    if not lesson:
        # Generate new lesson
        content = await lesson_agent.generate(
            subject=subtopic.topic.subject.name,
            topic=subtopic.topic.name,
            subtopic=subtopic.name,
            grade=grade_level,
            style="story"  # Default style
        )
        
        lesson = GeneratedLesson(
            subtopic_id=subtopic_id,
            grade_level=grade_level,
            title=content.get("title", f"Learning {subtopic.name}"),
            content=content,
            generated_by="LessonAgent"  # BaseAgent-compliant
        )
        db.add(lesson)
        await db.commit()
        await db.refresh(lesson)
    
    # Check student's completion status
    progress_query = select(StudentLessonProgress).where(
        StudentLessonProgress.student_id == student.id,
        StudentLessonProgress.lesson_id == lesson.id
    )
    progress_result = await db.execute(progress_query)
    progress = progress_result.scalar_one_or_none()
    
    # Create or update progress record (start tracking)
    if not progress:
        progress = StudentLessonProgress(
            student_id=student.id,
            lesson_id=lesson.id
        )
        db.add(progress)
        await db.commit()
    
    return LessonResponse(
        id=lesson.id,
        subtopic_id=lesson.subtopic_id,
        grade_level=lesson.grade_level,
        title=lesson.title,
        content=LessonContent(**sanitize_lesson_content(lesson.content)),
        generated_by=lesson.generated_by,
        created_at=lesson.created_at,
        is_completed=progress.is_completed if progress else False,
        completed_at=progress.completed_at if progress else None
    )


@router.post("/lesson/{lesson_id}/complete", response_model=LessonProgressResponse)
async def complete_lesson(
    lesson_id: uuid.UUID,
    request: CompleteLessonRequest,
    student: Student = Depends(get_student_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a lesson as completed.
    
    This updates the student's progress and can trigger mastery updates.
    """
    # Verify lesson exists
    lesson_query = select(GeneratedLesson).where(GeneratedLesson.id == lesson_id)
    lesson_result = await db.execute(lesson_query)
    lesson = lesson_result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Get or create progress record
    progress_query = select(StudentLessonProgress).where(
        StudentLessonProgress.student_id == student.id,
        StudentLessonProgress.lesson_id == lesson_id
    )
    progress_result = await db.execute(progress_query)
    progress = progress_result.scalar_one_or_none()
    
    if not progress:
        progress = StudentLessonProgress(
            student_id=student.id,
            lesson_id=lesson_id
        )
        db.add(progress)
    
    # Mark as completed
    progress.completed_at = datetime.utcnow()
    progress.time_spent_seconds = request.time_spent_seconds
    
    await db.commit()
    await db.refresh(progress)
    
    # Award XP for lesson completion (+50 XP)
    try:
        from app.services.gamification import GamificationService
        gamification = GamificationService(db)
        await gamification.award_xp(student.id, "lesson_complete")
        await gamification.update_streak(student.id)
    except Exception as e:
        print(f"Gamification error (non-critical): {e}")
    
    return LessonProgressResponse(
        lesson_id=lesson_id,
        student_id=student.id,
        completed_at=progress.completed_at,
        time_spent_seconds=progress.time_spent_seconds
    )


@router.post("/lesson/generate", response_model=LessonResponse)
async def generate_new_lesson(
    request: GenerateLessonRequest,
    student: Student = Depends(get_student_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Force generate a new lesson (even if one exists).
    
    Useful for getting a different teaching style or regenerating content.
    """
    # Get subtopic with topic and subject info
    subtopic_query = select(Subtopic).options(
        selectinload(Subtopic.topic).selectinload(Topic.subject)
    ).where(Subtopic.id == request.subtopic_id)
    subtopic_result = await db.execute(subtopic_query)
    subtopic = subtopic_result.scalar_one_or_none()
    
    if not subtopic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subtopic not found"
        )
    
    # Generate new lesson
    content = await lesson_agent.generate(
        subject=subtopic.topic.subject.name,
        topic=subtopic.topic.name,
        subtopic=subtopic.name,
        grade=request.grade_level,
        style=request.style or "story"
    )
    
    # Create new lesson record
    lesson = GeneratedLesson(
        subtopic_id=request.subtopic_id,
        grade_level=request.grade_level,
        title=content.get("title", f"Learning {subtopic.name}"),
        content=content,
        generated_by="LessonAgent"  # BaseAgent-compliant
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    
    return LessonResponse(
        id=lesson.id,
        subtopic_id=lesson.subtopic_id,
        grade_level=lesson.grade_level,
        title=lesson.title,
        content=LessonContent(**sanitize_lesson_content(lesson.content)),
        generated_by=lesson.generated_by,
        created_at=lesson.created_at,
        is_completed=False,
        completed_at=None
    )
