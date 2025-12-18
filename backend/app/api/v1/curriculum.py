"""
AI Tutor Platform - Curriculum API
Endpoints for browsing subjects, topics, and subtopics
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.curriculum import Subject, Topic, Subtopic
from app.models.user import User
from app.schemas.curriculum import (
    SubjectResponse,
    SubjectWithTopics,
    TopicResponse,
    TopicWithSubtopics,
    TopicResponse,
    TopicWithSubtopics,
    SubtopicResponse,
    ProgressResponse,
    EnrichedProgressResponse,
)

router = APIRouter(prefix="/curriculum", tags=["Curriculum"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/subjects", response_model=list[SubjectResponse])
async def list_subjects(db: DbSession):
    """
    List all active subjects.
    """
    result = await db.execute(
        select(Subject)
        .where(Subject.is_active == True)
        .order_by(Subject.display_order)
    )
    subjects = result.scalars().all()
    return subjects


@router.get("/subjects/{slug}", response_model=SubjectWithTopics)
async def get_subject(slug: str, db: DbSession):
    """
    Get a subject by slug with its topics.
    """
    result = await db.execute(
        select(Subject)
        .where(Subject.slug == slug, Subject.is_active == True)
        .options(selectinload(Subject.topics))
    )
    subject = result.scalar_one_or_none()
    
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found"
        )
    
    return subject


@router.get("/topics/{slug}", response_model=TopicWithSubtopics)
async def get_topic(slug: str, db: DbSession):
    """
    Get a topic by slug with its subtopics.
    """
    result = await db.execute(
        select(Topic)
        .where(Topic.slug == slug, Topic.is_active == True)
        .options(selectinload(Topic.subtopics))
    )
    topic = result.scalar_one_or_none()
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    
    return topic


@router.get("/subtopics/{subtopic_id}", response_model=SubtopicResponse)
async def get_subtopic(subtopic_id: UUID, db: DbSession):
    """
    Get a subtopic by ID.
    """
    result = await db.execute(
        select(Subtopic)
        .where(Subtopic.id == subtopic_id, Subtopic.is_active == True)
    )
    subtopic = result.scalar_one_or_none()
    
    if not subtopic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subtopic not found"
        )
    
    return subtopic


@router.get("/grade/{grade_level}/topics", response_model=list[TopicResponse])
async def get_topics_by_grade(grade_level: int, db: DbSession):
    """
    Get all topics for a specific grade level.
    """
    if grade_level < 1 or grade_level > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grade level must be between 1 and 12"
        )
    
    result = await db.execute(
        select(Topic)
        .where(Topic.grade_level == grade_level, Topic.is_active == True)
        .order_by(Topic.display_order)
    )
    topics = result.scalars().all()
    return topics


@router.get("/progress", response_model=list[EnrichedProgressResponse])
async def get_student_progress(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession
):
    """
    Get progress for the current user's student profile.
    """
    from app.models.curriculum import Progress
    from app.models.user import Student, User
    from app.api.deps import get_current_user
    
    # Get student profile
    result = await db.execute(select(Student).where(Student.parent_id == current_user.id))
    student = result.scalars().first()
    
    if not student:
        return []
        
    # Get all progress records with related curriculum info
    result = await db.execute(
        select(Progress)
        .where(Progress.student_id == student.id)
        .options(
            selectinload(Progress.subtopic)
            .selectinload(Subtopic.topic)
            .selectinload(Topic.subject)
        )
    )
    progress_records = result.scalars().all()
    
    # Enrich response
    response_data = []
    for p in progress_records:
        # Create dict from model
        item = {
            "id": p.id,
            "student_id": p.student_id,
            "subtopic_id": p.subtopic_id,
            "questions_attempted": p.questions_attempted,
            "questions_correct": p.questions_correct,
            "current_streak": p.current_streak,
            "best_streak": p.best_streak,
            "mastery_level": p.mastery_level,
            "total_time_seconds": p.total_time_seconds,
            "last_practiced_at": p.last_practiced_at,
            # Enriched fields
            "subject_name": p.subtopic.topic.subject.name,
            "topic_name": p.subtopic.topic.name,
            "subtopic_name": p.subtopic.name,
        }
        response_data.append(item)
    
    return response_data

