"""
AI Tutor Platform - User Schemas
Pydantic schemas for user registration, authentication, and profiles
"""
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


# ============================================================================
# Base Schemas
# ============================================================================

class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    first_name: Annotated[str, Field(min_length=1, max_length=100)]
    last_name: Annotated[str, Field(min_length=1, max_length=100)]


class StudentBase(BaseModel):
    """Base student schema."""
    first_name: Annotated[str, Field(min_length=1, max_length=100)]
    last_name: Annotated[str, Field(min_length=1, max_length=100)]
    grade_level: Annotated[int, Field(ge=1, le=12)]
    display_name: str | None = None
    theme_color: str = "#6366f1"
    birth_date: datetime | None = None

    @field_validator("theme_color")
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Invalid hex color format. Use #RRGGBB")
        return v


# ============================================================================
# Registration & Authentication
# ============================================================================

class UserCreate(UserBase):
    """Schema for user registration."""
    password: Annotated[str, Field(min_length=8, max_length=128)]
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes in seconds


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str


class PasswordChange(BaseModel):
    """Schema for password change."""
    current_password: str
    new_password: Annotated[str, Field(min_length=8, max_length=128)]


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str
    new_password: Annotated[str, Field(min_length=8, max_length=128)]


# ============================================================================
# User Response Schemas
# ============================================================================

class UserResponse(UserBase):
    """Schema for user response (public data)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    role: UserRole
    avatar_url: str | None = None
    timezone: str = "UTC"
    is_active: bool
    is_verified: bool
    created_at: datetime


class UserProfile(UserResponse):
    """Extended user profile with additional data."""
    last_login: datetime | None = None
    students: list["StudentResponse"] = []


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    first_name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    last_name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    avatar_url: str | None = None
    timezone: str | None = None


# ============================================================================
# Student Schemas
# ============================================================================

class StudentCreate(StudentBase):
    """Schema for creating a student profile."""
    pass


class StudentResponse(StudentBase):
    """Schema for student response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    parent_id: uuid.UUID
    avatar_url: str | None = None
    is_active: bool
    created_at: datetime
    # Gamification fields
    xp_total: int = 0
    level: int = 1
    current_streak: int = 0
    longest_streak: int = 0
    last_activity_date: datetime | None = None


class StudentUpdate(BaseModel):
    """Schema for updating student profile."""
    first_name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    last_name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    theme_color: str | None = None
    grade_level: Annotated[int, Field(ge=1, le=12)] | None = None
    preferences: dict | None = None  # JSONB storage for flexible settings


# Resolve forward references
UserProfile.model_rebuild()
