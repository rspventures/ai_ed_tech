"""
AI Tutor Platform - User Models
SQLAlchemy models for user management and authentication
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.curriculum import Progress
    from app.models.assessment import AssessmentResult
    from app.models.exam import ExamResult
    from app.models.test import TestResult


class UserRole(str, Enum):
    """User roles for RBAC."""
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(Base):
    """Base user model for authentication."""
    
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(String(50), default=UserRole.PARENT)
    
    # Profile info
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    students: Mapped[list["Student"]] = relationship(
        "Student", 
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Student(Base):
    """Student profile linked to a parent user."""
    
    __tablename__ = "students"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    
    # Profile
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    theme_color: Mapped[str] = mapped_column(String(7), default="#6366f1")  # Hex color
    
    # Academic info
    grade_level: Mapped[int] = mapped_column(Integer)  # 1, 2, 3
    birth_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Settings
    preferences: Mapped[dict | None] = mapped_column(JSONB, default={}, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Gamification - XP & Levels
    xp_total: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    
    # Gamification - Streaks
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_activity_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    parent: Mapped["User"] = relationship("User", back_populates="students")
    progress: Mapped[list["Progress"]] = relationship(
        "Progress",
        back_populates="student",
        cascade="all, delete-orphan"
    )
    assessment_results: Mapped[list["AssessmentResult"]] = relationship(
        "AssessmentResult",
        back_populates="student",
        cascade="all, delete-orphan"
    )
    exam_results: Mapped[list["ExamResult"]] = relationship(
        "ExamResult",
        back_populates="student",
        cascade="all, delete-orphan"
    )
    test_results: Mapped[list["TestResult"]] = relationship(
        "TestResult",
        back_populates="student",
        cascade="all, delete-orphan"
    )
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class RefreshToken(Base):
    """Stored refresh tokens for session management."""
    
    __tablename__ = "refresh_tokens"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None
