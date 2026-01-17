"""
AI Tutor Platform - Database Configuration
Async SQLAlchemy engine and session management
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def run_sql_migrations() -> None:
    """
    Run SQL migration scripts after SQLAlchemy creates base tables.
    
    This function executes SQL files that depend on tables created by init_db().
    Scripts use IF NOT EXISTS patterns, making them safe to run multiple times.
    """
    import os
    from pathlib import Path
    from sqlalchemy import text
    
    # Path to migrations directory (mounted as volume in Docker)
    migrations_dir = Path("/app/migrations")
    
    # List of additive migrations to run (in order)
    # These are scripts that ALTER existing tables or CREATE tables with FKs
    migration_files = [
        "07_contextual_retrieval.sql",
        "08_chat_memory.sql",
        "09_document_quiz_history.sql",
    ]
    
    async with engine.begin() as conn:
        for filename in migration_files:
            filepath = migrations_dir / filename
            if filepath.exists():
                try:
                    sql_content = filepath.read_text()
                    # Execute each statement separately (split by semicolon)
                    for statement in sql_content.split(";"):
                        statement = statement.strip()
                        if statement and not statement.startswith("--"):
                            await conn.execute(text(statement))
                    print(f"[Migration] ✓ Executed {filename}")
                except Exception as e:
                    print(f"[Migration] ⚠ Error in {filename}: {e}")
            else:
                print(f"[Migration] ⚠ File not found: {filename}")
