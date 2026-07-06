"""
AI Tutor Platform - Question Instance model (Phase 0, D1).

Persists every generated assessment/test/exam question together with its
server-side answer key so grading never trusts the client. The client receives
only the shuffled options; the correct value lives here and is looked up by
``question_id`` at submit time.

Created automatically by ``Base.metadata.create_all`` at startup (an Alembic
revision replaces that mechanism in Phase 1).
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QuestionInstance(Base):
    """A single generated question with its server-held answer key."""

    __tablename__ = "question_instances"

    # Client-facing id (returned in the question payload, echoed back on submit).
    question_id: Mapped[str] = mapped_column(String(64), primary_key=True)

    # Groups all questions belonging to one assessment/test/exam attempt.
    session_id: Mapped[str] = mapped_column(String(128), index=True)

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True,
    )

    # Which flow generated it: "assessment" | "test" | "exam" | "practice" | "doc_quiz".
    origin: Mapped[str] = mapped_column(String(32), index=True)

    # Curriculum context (nullable; stored without FK constraints to stay flexible).
    subtopic_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    topic_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    question: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSONB)              # shuffled, as shown to the client
    correct_answer: Mapped[str] = mapped_column(Text)         # the answer key (server secret)
    correct_answers: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # multi-select keys
    question_type: Mapped[str] = mapped_column(String(32), default="multiple_choice")
    difficulty: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Reserved for Phase 1 misconception tracking (P1.5).
    misconception_tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<QuestionInstance {self.question_id} origin={self.origin}>"
