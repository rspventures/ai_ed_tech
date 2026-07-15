"""triggers and fulltext indexes

Revision ID: 44aa224653c9
Revises: fc4860b64979
Create Date: 2026-07-15 19:13:11.076538

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44aa224653c9'
down_revision: Union[str, None] = 'fc4860b64979'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # GIN full-text index on document chunk contexts (from 07_contextual_retrieval.sql).
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_chunks_context "
        "ON document_chunks USING gin(to_tsvector('english', context)) "
        "WHERE context IS NOT NULL"
    )

    # Touch chat_sessions.updated_at when a message is inserted (from 08_chat_memory.sql).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_chat_session_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE chat_sessions SET updated_at = NOW() WHERE id = NEW.session_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trigger_update_chat_session_timestamp ON chat_messages")
    op.execute(
        """
        CREATE TRIGGER trigger_update_chat_session_timestamp
        AFTER INSERT ON chat_messages
        FOR EACH ROW EXECUTE FUNCTION update_chat_session_timestamp();
        """
    )

    # Maintain flashcard_decks.updated_at on update (from 11_flashcards.sql).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_flashcard_decks_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trigger_flashcard_decks_updated_at ON flashcard_decks")
    op.execute(
        """
        CREATE TRIGGER trigger_flashcard_decks_updated_at
        BEFORE UPDATE ON flashcard_decks
        FOR EACH ROW EXECUTE FUNCTION update_flashcard_decks_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trigger_flashcard_decks_updated_at ON flashcard_decks")
    op.execute("DROP FUNCTION IF EXISTS update_flashcard_decks_updated_at()")
    op.execute("DROP TRIGGER IF EXISTS trigger_update_chat_session_timestamp ON chat_messages")
    op.execute("DROP FUNCTION IF EXISTS update_chat_session_timestamp()")
    op.execute("DROP INDEX IF EXISTS idx_document_chunks_context")
