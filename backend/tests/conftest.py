"""
AI Tutor Platform - Test Configuration (Phase 1).

Fixtures run against a REAL Postgres (pgvector image) via testcontainers —
the previous SQLite fixtures could not even create the schema (JSONB/UUID/
Vector are Postgres-only, audit D11), so the suite never ran.

Requires a running Docker daemon (locally: Docker Desktop; CI: the runner's
Docker service).
"""
import os

# Test-environment knobs — MUST be set before importing the app, because the
# rate limiter and config singletons are constructed at import time.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("LANGFUSE_ENABLED", "false")
os.environ.setdefault("DEBUG", "false")

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from app.core.database import Base, get_db
from app.main import app

POSTGRES_IMAGE = "pgvector/pgvector:pg16"


@pytest.fixture(scope="session")
def pg_container():
    """One Postgres container for the whole test session."""
    with PostgresContainer(POSTGRES_IMAGE) as pg:
        yield pg


@pytest_asyncio.fixture
async def db_engine(pg_container):
    """Fresh schema per test: create_all before, drop_all after."""
    url = pg_container.get_connection_url().replace("psycopg2", "asyncpg")
    engine = create_async_engine(url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """A session bound to the per-test schema."""
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with the app's DB dependency overridden."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
        # Mirror the app's get_db post-yield commit so write endpoints persist.
        await db_session.commit()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    """Sample user registration data."""
    return {
        "email": "test@example.com",
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.fixture
def sample_student_data() -> dict[str, Any]:
    """Sample student data."""
    return {
        "first_name": "Sarah",
        "last_name": "Student",
        "grade_level": 2,
        "display_name": "Super Sarah",
        "theme_color": "#6366f1",
    }
