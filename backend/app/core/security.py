"""
AI Tutor Platform - Security Module
JWT token handling and password hashing utilities
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: The token subject (usually user ID)
        expires_delta: Optional custom expiration time
        additional_claims: Optional additional JWT claims
    
    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | int) -> str:
    """
    Create a JWT refresh token with longer expiration.
    
    Args:
        subject: The token subject (usually user ID)
    
    Returns:
        Encoded JWT refresh token string
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode
    
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> str | None:
    """
    Verify a token and return the subject if valid.
    
    Args:
        token: The JWT token to verify
        token_type: Expected token type ("access" or "refresh")
    
    Returns:
        User ID (subject) if valid, None otherwise
    """
    payload = decode_token(token)
    if payload is None:
        return None
    
    if payload.get("type") != token_type:
        return None
    
    return payload.get("sub")
