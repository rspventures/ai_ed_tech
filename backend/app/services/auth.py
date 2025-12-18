"""
AI Tutor Platform - Authentication Service
Business logic for user registration, login, and token management
"""
import uuid
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.user import RefreshToken, User, UserRole
from app.schemas.user import TokenResponse, UserCreate


class AuthenticationError(Exception):
    """Base authentication error."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Invalid email or password."""
    pass


class AccountLockedError(AuthenticationError):
    """Account is locked due to failed attempts."""
    pass


class AccountNotVerifiedError(AuthenticationError):
    """Account email not verified."""
    pass


class TokenError(AuthenticationError):
    """Token validation error."""
    pass


class AuthService:
    """Service for authentication operations."""
    
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def register_user(self, user_data: UserCreate) -> User:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
        
        Returns:
            Created user instance
        
        Raises:
            ValueError: If email already exists
        """
        # Check if email exists
        existing = await self.db.execute(
            select(User).where(User.email == user_data.email)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Email already registered")
        
        # Create user
        user = User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=UserRole.PARENT,
            is_verified=False,  # Require email verification
        )
        
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        
        return user
    
    async def authenticate(self, email: str, password: str) -> User:
        """
        Authenticate user with email and password.
        
        Args:
            email: User email
            password: User password
        
        Returns:
            Authenticated user
        
        Raises:
            InvalidCredentialsError: If credentials are invalid
            AccountLockedError: If account is locked
        """
        # Find user
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise InvalidCredentialsError("Invalid email or password")
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            remaining = (user.locked_until - datetime.now(timezone.utc)).seconds // 60
            raise AccountLockedError(
                f"Account locked. Try again in {remaining} minutes."
            )
        
        # Verify password
        if not verify_password(password, user.hashed_password):
            # Increment failed attempts
            user.failed_login_attempts += 1
            
            if user.failed_login_attempts >= self.MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=self.LOCKOUT_DURATION_MINUTES
                )
            
            await self.db.flush()
            raise InvalidCredentialsError("Invalid email or password")
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(timezone.utc)
        await self.db.flush()
        
        return user
    
    async def create_tokens(self, user: User) -> TokenResponse:
        """
        Create access and refresh tokens for a user.
        
        Args:
            user: User to create tokens for
        
        Returns:
            Token response with access and refresh tokens
        """
        # Create tokens
        # Handle both enum and string role values
        role_value = user.role.value if hasattr(user.role, 'value') else user.role
        access_token = create_access_token(
            subject=str(user.id),
            additional_claims={"role": role_value}
        )
        refresh_token = create_refresh_token(subject=str(user.id))
        
        # Store refresh token hash
        token_hash = sha256(refresh_token.encode()).hexdigest()
        refresh_token_record = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        )
        self.db.add(refresh_token_record)
        await self.db.flush()
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
        
        Returns:
            New token response
        
        Raises:
            TokenError: If refresh token is invalid or expired
        """
        # Verify token
        user_id = verify_token(refresh_token, token_type="refresh")
        if not user_id:
            raise TokenError("Invalid refresh token")
        
        # Check token in database
        token_hash = sha256(refresh_token.encode()).hexdigest()
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None)
            )
        )
        token_record = result.scalar_one_or_none()
        
        if not token_record or token_record.is_expired:
            raise TokenError("Refresh token expired or revoked")
        
        # Get user
        result = await self.db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise TokenError("User not found or inactive")
        
        # Revoke old token
        token_record.revoked_at = datetime.now(timezone.utc)
        
        # Create new tokens
        return await self.create_tokens(user)
    
    async def logout(self, refresh_token: str) -> None:
        """
        Logout user by revoking refresh token.
        
        Args:
            refresh_token: Refresh token to revoke
        """
        token_hash = sha256(refresh_token.encode()).hexdigest()
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        token_record = result.scalar_one_or_none()
        
        if token_record:
            token_record.revoked_at = datetime.now(timezone.utc)
            await self.db.flush()
    
    async def get_user_by_id(self, user_id: str | uuid.UUID) -> User | None:
        """Get user by ID."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
