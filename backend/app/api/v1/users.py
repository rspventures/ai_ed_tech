"""
AI Tutor Platform - User API Routes
Endpoints for user profile and student management
"""
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.user import Student, User
from app.schemas.user import (
    StudentCreate,
    StudentResponse,
    StudentUpdate,
    UserProfile,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get user profile",
    description="Get the current user's full profile including their students.",
)
async def get_profile(
    current_user: CurrentUser,
    db: DbSession,
) -> UserProfile:
    """Get current user's profile with students."""
    # Reload user with students relationship
    result = await db.execute(
        select(User)
        .options(selectinload(User.students))
        .where(User.id == current_user.id)
    )
    user = result.scalar_one()
    return UserProfile.model_validate(user)


@router.patch(
    "/me",
    response_model=UserProfile,
    summary="Update user profile",
    description="Update the current user's profile information.",
)
async def update_profile(
    user_update: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> UserProfile:
    """Update current user's profile."""
    # Update fields
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    await db.flush()
    await db.refresh(current_user)
    
    # Reload with students
    result = await db.execute(
        select(User)
        .options(selectinload(User.students))
        .where(User.id == current_user.id)
    )
    user = result.scalar_one()
    return UserProfile.model_validate(user)


# ============================================================================
# Student Management
# ============================================================================

@router.get(
    "/me/students",
    response_model=list[StudentResponse],
    summary="List students",
    description="Get all students linked to the current user.",
)
async def list_students(
    current_user: CurrentUser,
    db: DbSession,
) -> list[StudentResponse]:
    """List all students for current user."""
    result = await db.execute(
        select(Student).where(Student.parent_id == current_user.id)
    )
    students = result.scalars().all()
    return [StudentResponse.model_validate(s) for s in students]


@router.post(
    "/me/students",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create student",
    description="Create a new student profile linked to the current user.",
)
async def create_student(
    student_data: StudentCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> StudentResponse:
    """Create a new student profile."""
    student = Student(
        parent_id=current_user.id,
        **student_data.model_dump(),
    )
    db.add(student)
    await db.flush()
    await db.refresh(student)
    
    return StudentResponse.model_validate(student)


@router.get(
    "/me/students/{student_id}",
    response_model=StudentResponse,
    summary="Get student",
    description="Get a specific student profile.",
)
async def get_student(
    student_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> StudentResponse:
    """Get a specific student."""
    result = await db.execute(
        select(Student).where(
            Student.id == student_id,
            Student.parent_id == current_user.id,
        )
    )
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    
    return StudentResponse.model_validate(student)


@router.patch(
    "/me/students/{student_id}",
    response_model=StudentResponse,
    summary="Update student",
    description="Update a student profile.",
)
async def update_student(
    student_id: uuid.UUID,
    student_update: StudentUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> StudentResponse:
    """Update a student profile."""
    result = await db.execute(
        select(Student).where(
            Student.id == student_id,
            Student.parent_id == current_user.id,
        )
    )
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    
    update_data = student_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)
    
    await db.flush()
    await db.refresh(student)
    
    return StudentResponse.model_validate(student)


@router.delete(
    "/me/students/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete student",
    description="Delete a student profile.",
)
async def delete_student(
    student_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete a student profile."""
    result = await db.execute(
        select(Student).where(
            Student.id == student_id,
            Student.parent_id == current_user.id,
        )
    )
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    
    await db.delete(student)


# ============================================================================
# Convenience Endpoint for Settings Page
# ============================================================================

@router.patch(
    "/students/me",
    response_model=StudentResponse,
    summary="Update or create current student",
    description="Update the first student profile for the current user, or create one if none exists. Convenience endpoint for Settings page.",
)
async def update_current_student(
    student_update: StudentUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> StudentResponse:
    """Update the first student for the current user, or create one if none exists."""
    # Get the first student for this user
    result = await db.execute(
        select(Student).where(Student.parent_id == current_user.id).limit(1)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        # Create a new student profile if one doesn't exist
        # Use the user's name as default, and require grade_level from the update
        update_data = student_update.model_dump(exclude_unset=True)
        
        if "grade_level" not in update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="grade_level is required when creating a new student profile",
            )
        
        student = Student(
            parent_id=current_user.id,
            first_name=update_data.get("first_name", current_user.first_name),
            last_name=update_data.get("last_name", current_user.last_name),
            grade_level=update_data["grade_level"],
            display_name=update_data.get("display_name"),
            theme_color=update_data.get("theme_color", "#6366f1"),
        )
        db.add(student)
        await db.flush()
        await db.refresh(student)
        
        return StudentResponse.model_validate(student)
    
    # Update existing student
    update_data = student_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)
    
    await db.flush()
    await db.refresh(student)
    
    return StudentResponse.model_validate(student)
