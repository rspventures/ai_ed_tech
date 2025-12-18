"""
AI Tutor Platform - Authentication API Routes
Endpoints for registration, login, token refresh, and logout
"""
from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import (
    TokenRefresh,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth import (
    AccountLockedError,
    AuthService,
    InvalidCredentialsError,
    TokenError,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new parent account. Email verification is required before full access.",
)
async def register(
    user_data: UserCreate,
    db: DbSession,
) -> UserResponse:
    """Register a new user account."""
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.register_user(user_data)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user",
    description="Login with email and password to receive access and refresh tokens.",
)
async def login(
    credentials: UserLogin,
    db: DbSession,
) -> TokenResponse:
    """Authenticate user and return tokens."""
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.authenticate(
            email=credentials.email,
            password=credentials.password,
        )
        return await auth_service.create_tokens(user)
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AccountLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(e),
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Use a valid refresh token to obtain new access and refresh tokens.",
)
async def refresh_token(
    token_data: TokenRefresh,
    db: DbSession,
) -> TokenResponse:
    """Refresh access token using refresh token."""
    auth_service = AuthService(db)
    
    try:
        return await auth_service.refresh_tokens(token_data.refresh_token)
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
    description="Revoke the refresh token to end the session.",
)
async def logout(
    token_data: TokenRefresh,
    db: DbSession,
) -> None:
    """Logout by revoking refresh token."""
    auth_service = AuthService(db)
    await auth_service.logout(token_data.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get the currently authenticated user's profile.",
)
async def get_current_user_profile(
    current_user: CurrentUser,
) -> UserResponse:
    """Get current user profile."""
    return UserResponse.model_validate(current_user)
