"""
AI Tutor Platform - Authentication API Tests
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, sample_user_data):
    """Test user registration."""
    response = await client.post("/api/v1/auth/register", json=sample_user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == sample_user_data["email"]
    assert data["first_name"] == sample_user_data["first_name"]
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, sample_user_data):
    """Test that duplicate email registration fails."""
    # First registration
    await client.post("/api/v1/auth/register", json=sample_user_data)
    
    # Second registration with same email
    response = await client.post("/api/v1/auth/register", json=sample_user_data)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, sample_user_data):
    """Test successful login."""
    # Register user first
    await client.post("/api/v1/auth/register", json=sample_user_data)
    
    # Login
    response = await client.post("/api/v1/auth/login", json={
        "email": sample_user_data["email"],
        "password": sample_user_data["password"],
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, sample_user_data):
    """Test login with invalid credentials."""
    # Register user first
    await client.post("/api/v1/auth/register", json=sample_user_data)
    
    # Login with wrong password
    response = await client.post("/api/v1/auth/login", json={
        "email": sample_user_data["email"],
        "password": "WrongPassword123!",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, sample_user_data):
    """Test getting current user profile."""
    # Register and login
    await client.post("/api/v1/auth/register", json=sample_user_data)
    login_response = await client.post("/api/v1/auth/login", json={
        "email": sample_user_data["email"],
        "password": sample_user_data["password"],
    })
    token = login_response.json()["access_token"]
    
    # Get current user
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == sample_user_data["email"]


@pytest.mark.asyncio  
async def test_refresh_token(client: AsyncClient, sample_user_data):
    """Test token refresh."""
    # Register and login
    await client.post("/api/v1/auth/register", json=sample_user_data)
    login_response = await client.post("/api/v1/auth/login", json={
        "email": sample_user_data["email"],
        "password": sample_user_data["password"],
    })
    refresh_token = login_response.json()["refresh_token"]
    
    # Refresh tokens
    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
