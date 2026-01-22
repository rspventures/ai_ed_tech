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
    import re
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
        "10_lesson_v2.sql",
        "11_flashcards.sql",
        "12_favorites.sql",
    ]
    
    def split_sql_statements(sql_content: str) -> list:
        """
        Split SQL into statements, respecting $$ and $tag$ quoted blocks.
        This avoids splitting on semicolons inside function definitions.
        """
        statements = []
        current = []
        in_dollar_quote = False
        dollar_tag = None
        
        # Split by lines to process
        lines = sql_content.split('\n')
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines and comments when not in a statement
            if not current and (not stripped or stripped.startswith('--')):
                continue
            
            current.append(line)
            
            # Check for dollar quote start/end
            dollar_matches = re.findall(r'\$(\w*)\$', line)
            for tag in dollar_matches:
                full_tag = f'${tag}$'
                if not in_dollar_quote:
                    in_dollar_quote = True
                    dollar_tag = full_tag
                elif full_tag == dollar_tag:
                    in_dollar_quote = False
                    dollar_tag = None
            
            # If not in dollar quote and line ends with semicolon, end statement
            if not in_dollar_quote and stripped.endswith(';'):
                stmt = '\n'.join(current).strip()
                if stmt and not stmt.startswith('--'):
                    statements.append(stmt)
                current = []
        
        # Add any remaining statement
        if current:
            stmt = '\n'.join(current).strip()
            if stmt and not stmt.startswith('--'):
                statements.append(stmt)
        
        return statements
    
    async with engine.begin() as conn:
        for filename in migration_files:
            filepath = migrations_dir / filename
            if filepath.exists():
                try:
                    sql_content = filepath.read_text()
                    # Execute each statement separately (respecting $$ blocks)
                    for statement in split_sql_statements(sql_content):
                        if statement:
                            await conn.execute(text(statement))
                    print(f"[Migration] ✓ Executed {filename}")
                except Exception as e:
                    print(f"[Migration] ⚠ Error in {filename}: {e}")
            else:
                print(f"[Migration] ⚠ File not found: {filename}")

