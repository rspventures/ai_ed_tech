"""
AI Tutor Platform - API Dependencies
FastAPI dependencies for authentication and authorization
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User, UserRole
from app.services.auth import AuthService

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    user_id = verify_token(token, token_type="access")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current active user."""
    return current_user


def require_role(*roles: UserRole):
    """
    Dependency factory for role-based access control.
    
    Usage:
        @router.get("/admin")
        async def admin_only(user: User = Depends(require_role(UserRole.ADMIN))):
            ...
    """
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {[r.value for r in roles]}",
            )
        return current_user
    
    return role_checker


async def get_current_student(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get the current student profile.
    
    For parent users, returns their first student.
    This is used by student-facing endpoints like Smart Review.
    
    Raises:
        HTTPException: If no student profile found
    """
    from sqlalchemy import select
    from app.models.user import Student
    
    # Query for the first student associated with this user
    query = select(Student).where(Student.parent_id == current_user.id).limit(1)
    result = await db.execute(query)
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No student profile found for this user",
        )
    
    return student


# Type aliases for common dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
