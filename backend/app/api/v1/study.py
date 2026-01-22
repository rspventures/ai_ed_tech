"""
AI Tutor Platform - Study API Router
Endpoints for adaptive learning and AI-generated lessons
"""
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, Student
from app.models.curriculum import Topic, Subtopic
from app.models.lesson import GeneratedLesson, StudentLessonProgress
from app.models.flashcard import FlashcardDeck, StudentFlashcardProgress
from app.schemas.lesson import (
    LessonResponse,
    LessonContent,
    LessonProgressResponse,
    StudyActionResponse,
    LearningPathResponse,
    GenerateLessonRequest,
    CompleteLessonRequest
)
from app.schemas.flashcard import (
    FlashcardDeckResponse,
    FlashcardDeckListItem,
    FlashcardItem,
)
from app.services.learning_path import LearningPathService
from app.ai.agents.lesson import lesson_agent, lesson_agent_v2  # V1 + V2
from app.ai.agents.flashcard import flashcard_agent
from app.schemas.lesson_modules import Lesson2Content, Lesson2Response
from app.models.favorite import StudentFavorite
from app.models.curriculum import Subject
from app.schemas.favorite import (
    FavoriteCreate,
    FavoriteResponse,
    FavoriteListResponse,
)


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
    
    # Check for existing V1 lesson first (generated_by="LessonAgent")
    lesson_query = select(GeneratedLesson).where(
        GeneratedLesson.subtopic_id == subtopic_id,
        GeneratedLesson.grade_level == grade_level,
        GeneratedLesson.generated_by == "LessonAgent"
    )
    lesson_result = await db.execute(lesson_query)
    lesson = lesson_result.scalars().first()
    
    # If no V1 lesson found, check for ANY lesson (fallback)
    if not lesson:
        fallback_query = select(GeneratedLesson).where(
            GeneratedLesson.subtopic_id == subtopic_id,
            GeneratedLesson.grade_level == grade_level
        )
        fallback_result = await db.execute(fallback_query)
        lesson = fallback_result.scalars().first()
    
    if not lesson:
        # Generate new lesson
        # V1 GENERATION DISABLED - Force V2 Integration
        # content = await lesson_agent.generate(
        #     subject=subtopic.topic.subject.name,
        #     topic=subtopic.topic.name,
        #     subtopic=subtopic.name,
        #     grade=grade_level,
        #     style="story"  # Default style
        # )
        raise HTTPException(
            status_code=status.HTTP_426_UPGRADE_REQUIRED,
            detail="Lesson V1 is deprecated. Please use V2."
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


# ============================================================================
# LESSON 2.0 - Interactive Module Playlist
# ============================================================================

@router.get("/lesson/v2/{subtopic_id}", response_model=Lesson2Response)
async def get_lesson_v2(
    subtopic_id: uuid.UUID,
    student: Student = Depends(get_student_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Get an Interactive Lesson Playlist (Lesson 2.0).
    
    Returns a lesson with multiple module types:
    - Hook, Text, Flashcard, Fun Fact, Quiz, Activity
    
    This is the new format optimized for engagement and micro-learning.
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
    
    # Check for existing V2 lesson
    lesson_query = select(GeneratedLesson).where(
        GeneratedLesson.subtopic_id == subtopic_id,
        GeneratedLesson.grade_level == grade_level,
        GeneratedLesson.generated_by == "LessonAgentV2"
    )
    lesson_result = await db.execute(lesson_query)
    lesson = lesson_result.scalars().first()
    
    if not lesson:
        # Generate new V2 lesson using LessonAgentV2
        content = await lesson_agent_v2.generate(
            subject=subtopic.topic.subject.name,
            topic=subtopic.topic.name,
            subtopic=subtopic.name,
            grade=grade_level,
        )
        
        lesson = GeneratedLesson(
            subtopic_id=subtopic_id,
            grade_level=grade_level,
            title=content.get("title", f"Learning {subtopic.name}"),
            content=content,
            generated_by="LessonAgentV2"
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
    progress = progress_result.scalars().first()
    
    # Validate content against Lesson2Content schema
    try:
        validated_content = Lesson2Content(**lesson.content)
    except Exception:
        # Fallback: wrap raw content if validation fails
        validated_content = Lesson2Content(
            title=lesson.title,
            modules=[{"type": "text", "content": str(lesson.content)}],
            estimated_duration_minutes=5
        )
    
    return Lesson2Response(
        id=str(lesson.id),
        subtopic_id=str(lesson.subtopic_id),
        grade_level=lesson.grade_level,
        content=validated_content,
        generated_by=lesson.generated_by,
        content_version=2,
        is_completed=progress.is_completed if progress else False
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


# ============================================================================
# FLASHCARD ENDPOINTS
# ============================================================================

@router.get(
    "/flashcards/{subtopic_id}",
    response_model=FlashcardDeckResponse,
    summary="Get or Generate Flashcard Deck"
)
async def get_flashcard_deck(
    subtopic_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get or generate a flashcard deck for a subtopic.
    
    If a deck already exists for this subtopic/grade combination,
    returns the existing deck. Otherwise, generates a new deck
    using the FlashcardAgent (10-15 cards).
    """
    # Get student profile
    student_query = select(Student).where(Student.parent_id == user.id)
    student_result = await db.execute(student_query)
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )
    
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
    
    # Check for existing deck
    deck_query = select(FlashcardDeck).where(
        FlashcardDeck.subtopic_id == subtopic_id,
        FlashcardDeck.grade_level == grade_level,
        FlashcardDeck.generated_by == "FlashcardAgent"
    )
    deck_result = await db.execute(deck_query)
    deck = deck_result.scalars().first()
    
    if not deck:
        # Generate new flashcard deck
        content = await flashcard_agent.generate(
            subject=subtopic.topic.subject.name,
            topic=subtopic.topic.name,
            subtopic=subtopic.name,
            grade=grade_level,
        )
        
        cards = content.get("cards", [])
        
        deck = FlashcardDeck(
            subtopic_id=subtopic_id,
            grade_level=grade_level,
            title=content.get("title", f"Flashcards: {subtopic.name}"),
            description=content.get("description"),
            cards=cards,
            card_count=len(cards),
            generated_by="FlashcardAgent"
        )
        db.add(deck)
        await db.commit()
        await db.refresh(deck)
    
    # Get student's progress for this deck
    progress_query = select(StudentFlashcardProgress).where(
        StudentFlashcardProgress.student_id == student.id,
        StudentFlashcardProgress.deck_id == deck.id
    )
    progress_result = await db.execute(progress_query)
    progress = progress_result.scalars().first()
    
    # Convert cards to FlashcardItem format
    flashcard_items = [
        FlashcardItem(
            front=card.get("front", ""),
            back=card.get("back", ""),
            difficulty=card.get("difficulty")
        )
        for card in deck.cards
    ]
    
    return FlashcardDeckResponse(
        id=str(deck.id),
        subtopic_id=str(deck.subtopic_id),
        grade_level=deck.grade_level,
        title=deck.title,
        description=deck.description,
        cards=flashcard_items,
        card_count=deck.card_count,
        generated_by=deck.generated_by,
        cards_reviewed=progress.cards_reviewed if progress else 0,
        cards_mastered=progress.cards_mastered if progress else 0,
        mastery_percentage=progress.mastery_percentage if progress else 0.0
    )


@router.get(
    "/flashcards/topic/{topic_id}",
    response_model=List[FlashcardDeckListItem],
    summary="List Flashcard Decks for Topic"
)
async def list_flashcard_decks(
    topic_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    List all flashcard decks for subtopics under a given topic.
    Returns compact deck info with mastery progress.
    """
    # Get student profile
    student_query = select(Student).where(Student.parent_id == user.id)
    student_result = await db.execute(student_query)
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )
    
    # Get all subtopics for this topic
    subtopics_query = select(Subtopic).where(
        Subtopic.topic_id == topic_id,
        Subtopic.is_active == True
    ).order_by(Subtopic.display_order)
    subtopics_result = await db.execute(subtopics_query)
    subtopics = subtopics_result.scalars().all()
    
    grade_level = student.grade_level or 5
    
    result = []
    for subtopic in subtopics:
        # Check if deck exists
        deck_query = select(FlashcardDeck).where(
            FlashcardDeck.subtopic_id == subtopic.id,
            FlashcardDeck.grade_level == grade_level
        )
        deck_result = await db.execute(deck_query)
        deck = deck_result.scalars().first()
        
        if deck:
            # Get progress
            progress_query = select(StudentFlashcardProgress).where(
                StudentFlashcardProgress.student_id == student.id,
                StudentFlashcardProgress.deck_id == deck.id
            )
            progress_result = await db.execute(progress_query)
            progress = progress_result.scalars().first()
            
            result.append(FlashcardDeckListItem(
                id=str(deck.id),
                subtopic_id=str(subtopic.id),
                subtopic_name=subtopic.name,
                title=deck.title,
                card_count=deck.card_count,
                mastery_percentage=progress.mastery_percentage if progress else 0.0
            ))
        else:
            # Deck not yet generated - show placeholder
            result.append(FlashcardDeckListItem(
                id="",  # Empty = not generated
                subtopic_id=str(subtopic.id),
                subtopic_name=subtopic.name,
                title=f"Flashcards: {subtopic.name}",
                card_count=0,
                mastery_percentage=None
            ))
    
    return result


# ============================================================================
# FAVORITES ENDPOINTS
# ============================================================================

@router.post(
    "/favorites",
    response_model=FavoriteResponse,
    summary="Add Module to Favorites"
)
async def add_favorite(
    request: FavoriteCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Add a lesson module to favorites (star it).
    
    The module is identified by lesson_id and module_index.
    """
    # Get student profile
    student_query = select(Student).where(Student.parent_id == user.id)
    student_result = await db.execute(student_query)
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )
    
    # Get the lesson
    lesson_query = select(GeneratedLesson).options(
        selectinload(GeneratedLesson.subtopic).selectinload(Subtopic.topic).selectinload(Topic.subject)
    ).where(GeneratedLesson.id == uuid.UUID(request.lesson_id))
    lesson_result = await db.execute(lesson_query)
    lesson = lesson_result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Validate module_index
    modules = lesson.content.get("modules", [])
    if request.module_index < 0 or request.module_index >= len(modules):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid module_index. Lesson has {len(modules)} modules."
        )
    
    module = modules[request.module_index]
    
    # Check if already favorited
    existing_query = select(StudentFavorite).where(
        StudentFavorite.student_id == student.id,
        StudentFavorite.lesson_id == lesson.id,
        StudentFavorite.module_index == request.module_index
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Module already in favorites"
        )
    
    # Create favorite
    favorite = StudentFavorite(
        student_id=student.id,
        lesson_id=lesson.id,
        module_index=request.module_index,
        module_type=module.get("type", "unknown"),
        module_content=module,
        subtopic_id=lesson.subtopic_id,
        topic_id=lesson.subtopic.topic_id,
        subject_id=lesson.subtopic.topic.subject_id,
    )
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)
    
    return FavoriteResponse(
        id=str(favorite.id),
        lesson_id=str(favorite.lesson_id),
        module_index=favorite.module_index,
        module_type=favorite.module_type,
        module_content=favorite.module_content,
        subtopic_id=str(favorite.subtopic_id),
        subtopic_name=lesson.subtopic.name,
        topic_id=str(favorite.topic_id),
        topic_name=lesson.subtopic.topic.name,
        subject_id=str(favorite.subject_id),
        subject_name=lesson.subtopic.topic.subject.name,
        created_at=favorite.created_at,
    )


@router.delete(
    "/favorites/{favorite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove from Favorites"
)
async def remove_favorite(
    favorite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Remove a module from favorites (unstar it)."""
    # Get student profile
    student_query = select(Student).where(Student.parent_id == user.id)
    student_result = await db.execute(student_query)
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )
    
    # Get and delete favorite
    fav_query = select(StudentFavorite).where(
        StudentFavorite.id == favorite_id,
        StudentFavorite.student_id == student.id
    )
    fav_result = await db.execute(fav_query)
    favorite = fav_result.scalar_one_or_none()
    
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found"
        )
    
    await db.delete(favorite)
    await db.commit()


@router.get(
    "/favorites",
    response_model=FavoriteListResponse,
    summary="Get All Favorites"
)
async def get_all_favorites(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get all favorites for the current student."""
    # Get student profile
    student_query = select(Student).where(Student.parent_id == user.id)
    student_result = await db.execute(student_query)
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )
    
    # Get all favorites with related data
    fav_query = select(StudentFavorite).where(
        StudentFavorite.student_id == student.id
    ).order_by(StudentFavorite.created_at.desc())
    fav_result = await db.execute(fav_query)
    favorites = fav_result.scalars().all()
    
    response_items = []
    for fav in favorites:
        response_items.append(FavoriteResponse(
            id=str(fav.id),
            lesson_id=str(fav.lesson_id),
            module_index=fav.module_index,
            module_type=fav.module_type,
            module_content=fav.module_content,
            subtopic_id=str(fav.subtopic_id),
            topic_id=str(fav.topic_id),
            subject_id=str(fav.subject_id),
            created_at=fav.created_at,
        ))
    
    return FavoriteListResponse(
        favorites=response_items,
        total_count=len(response_items)
    )


@router.get(
    "/favorites/subtopic/{subtopic_id}",
    response_model=FavoriteListResponse,
    summary="Get Favorites by Subtopic"
)
async def get_favorites_by_subtopic(
    subtopic_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get all favorites for a specific subtopic (Quick Review)."""
    student_query = select(Student).where(Student.parent_id == user.id)
    student_result = await db.execute(student_query)
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    fav_query = select(StudentFavorite).where(
        StudentFavorite.student_id == student.id,
        StudentFavorite.subtopic_id == subtopic_id
    ).order_by(StudentFavorite.created_at.desc())
    fav_result = await db.execute(fav_query)
    favorites = fav_result.scalars().all()
    
    response_items = [
        FavoriteResponse(
            id=str(f.id),
            lesson_id=str(f.lesson_id),
            module_index=f.module_index,
            module_type=f.module_type,
            module_content=f.module_content,
            subtopic_id=str(f.subtopic_id),
            topic_id=str(f.topic_id),
            subject_id=str(f.subject_id),
            created_at=f.created_at,
        ) for f in favorites
    ]
    
    return FavoriteListResponse(favorites=response_items, total_count=len(response_items))


@router.get(
    "/favorites/topic/{topic_id}",
    response_model=FavoriteListResponse,
    summary="Get Favorites by Topic"
)
async def get_favorites_by_topic(
    topic_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get all favorites for a specific topic (Quick Review)."""
    student_query = select(Student).where(Student.parent_id == user.id)
    student_result = await db.execute(student_query)
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    fav_query = select(StudentFavorite).where(
        StudentFavorite.student_id == student.id,
        StudentFavorite.topic_id == topic_id
    ).order_by(StudentFavorite.created_at.desc())
    fav_result = await db.execute(fav_query)
    favorites = fav_result.scalars().all()
    
    response_items = [
        FavoriteResponse(
            id=str(f.id),
            lesson_id=str(f.lesson_id),
            module_index=f.module_index,
            module_type=f.module_type,
            module_content=f.module_content,
            subtopic_id=str(f.subtopic_id),
            topic_id=str(f.topic_id),
            subject_id=str(f.subject_id),
            created_at=f.created_at,
        ) for f in favorites
    ]
    
    return FavoriteListResponse(favorites=response_items, total_count=len(response_items))


@router.get(
    "/favorites/subject/{subject_id}",
    response_model=FavoriteListResponse,
    summary="Get Favorites by Subject"
)
async def get_favorites_by_subject(
    subject_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get all favorites for a subject (Quick Review)."""
    student_query = select(Student).where(Student.parent_id == user.id)
    student_result = await db.execute(student_query)
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    fav_query = select(StudentFavorite).where(
        StudentFavorite.student_id == student.id,
        StudentFavorite.subject_id == subject_id
    ).order_by(StudentFavorite.created_at.desc())
    fav_result = await db.execute(fav_query)
    favorites = fav_result.scalars().all()
    
    response_items = [
        FavoriteResponse(
            id=str(f.id),
            lesson_id=str(f.lesson_id),
            module_index=f.module_index,
            module_type=f.module_type,
            module_content=f.module_content,
            subtopic_id=str(f.subtopic_id),
            topic_id=str(f.topic_id),
            subject_id=str(f.subject_id),
            created_at=f.created_at,
        ) for f in favorites
    ]
    
    return FavoriteListResponse(favorites=response_items, total_count=len(response_items))


