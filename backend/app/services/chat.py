import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update
from app.models.chat import ChatSession, ChatMessage, MessageRole

class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, user_id: uuid.UUID, title: Optional[str] = None) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            user_id=user_id,
            title=title or "New Conversation"
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: uuid.UUID) -> Optional[ChatSession]:
        """Fetch a specific session."""
        result = await self.db.execute(select(ChatSession).where(ChatSession.id == session_id))
        return result.scalar_one_or_none()

    async def get_user_sessions(self, user_id: uuid.UUID, limit: int = 20) -> List[ChatSession]:
        """Get recent sessions for a user."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(desc(ChatSession.updated_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_message(
        self, 
        session_id: uuid.UUID, 
        role: MessageRole, 
        content: str, 
        token_count: Optional[int] = None
    ) -> ChatMessage:
        """Add a message to the session."""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            token_count=token_count
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_history(self, session_id: uuid.UUID, limit: int = 10) -> List[ChatMessage]:
        """
        Get the most recent N messages for context.
        Returns messages in chronological order (oldest -> newest).
        """
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        messages = list(result.scalars().all())
        # Re-sort to chronological order for the LLM context
        return sorted(messages, key=lambda m: m.created_at)

    async def update_summary(self, session_id: uuid.UUID, summary: str):
        """Update the conversation summary."""
        stmt = (
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(summary=summary)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def update_title(self, session_id: uuid.UUID, title: str):
        """Update the session title."""
        stmt = (
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(title=title)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def get_message_count(self, session_id: uuid.UUID) -> int:
        """Get total number of messages in session."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(ChatMessage).where(ChatMessage.session_id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()
