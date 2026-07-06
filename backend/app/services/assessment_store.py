"""
Persistence + grading for server-authoritative questions (Phase 0, D1).

Bridges the pure grading core (``assessment_grading``) and the durable
``QuestionInstance`` store. Endpoints call:

  * ``persist_prepared`` at generation time (stores the answer key), and
  * ``grade_submissions`` at submit time (grades against the stored key,
    ignoring any client-supplied correctness).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question_instance import QuestionInstance
from app.services.assessment_grading import PreparedQuestion, is_answer_correct


def _as_uuid(value) -> uuid.UUID | None:
    """Coerce a str/UUID/None into a UUID (or None on failure)."""
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


@dataclass
class GradedAnswer:
    """Outcome of grading one submitted answer against the stored key."""

    question_id: str
    question: str
    student_answer: str | list[str]
    correct_answer: str | list[str]
    is_correct: bool
    found: bool  # False if the question_id was not a real server-issued question
    topic_id: str | None = None       # authoritative curriculum context (from the stored question)
    subtopic_id: str | None = None


async def persist_prepared(
    db: AsyncSession,
    *,
    session_id: str,
    student_id: uuid.UUID,
    origin: str,
    prepared: list[PreparedQuestion],
    subtopic_id: uuid.UUID | None = None,
    topic_id: uuid.UUID | None = None,
) -> None:
    """Store the answer keys for a freshly generated set of questions.

    Per-question ``subtopic_id``/``topic_id`` on the PreparedQuestion take
    precedence over the batch-level defaults (tests span multiple subtopics).
    """
    for p in prepared:
        db.add(
            QuestionInstance(
                question_id=p.question_id,
                session_id=session_id,
                student_id=student_id,
                origin=origin,
                subtopic_id=_as_uuid(p.subtopic_id) or subtopic_id,
                topic_id=_as_uuid(p.topic_id) or topic_id,
                question=p.question,
                options=p.options,
                correct_answer=p.correct_answer,
                correct_answers=p.correct_answers,
                question_type=p.question_type,
                difficulty=p.difficulty,
            )
        )
    await db.flush()


async def grade_submissions(
    db: AsyncSession,
    *,
    student_id: uuid.UUID,
    submissions: list[dict],
) -> list[GradedAnswer]:
    """
    Grade each ``{"question_id", "answer"}`` against its stored key.

    Questions are looked up by their (unguessable, unique) ``question_id`` scoped
    to ``student_id`` — a client cannot submit a fabricated question_id or another
    student's question. No session match is required (the random question_id is
    sufficient), so grading does not depend on the client echoing a session token.
    Unknown question_ids are graded incorrect and flagged ``found=False``.
    """
    question_ids = [s.get("question_id") for s in submissions if s.get("question_id")]
    stored: dict[str, QuestionInstance] = {}
    if question_ids:
        result = await db.execute(
            select(QuestionInstance).where(
                QuestionInstance.question_id.in_(question_ids),
                QuestionInstance.student_id == student_id,
            )
        )
        stored = {qi.question_id: qi for qi in result.scalars().all()}

    graded: list[GradedAnswer] = []
    for sub in submissions:
        qid = sub.get("question_id")
        student_answer = sub.get("answer", "")
        qi = stored.get(qid)
        if qi is None:
            graded.append(
                GradedAnswer(
                    question_id=qid or "",
                    question=sub.get("question", ""),
                    student_answer=student_answer,
                    correct_answer="",
                    is_correct=False,
                    found=False,
                )
            )
            continue

        correct = is_answer_correct(
            student_answer=student_answer,
            correct_answer=qi.correct_answer,
            correct_answers=qi.correct_answers,
        )
        # Reveal the correct value only now, after grading (safe post-submit).
        correct_value: str | list[str]
        if qi.question_type == "multi_select" and qi.correct_answers:
            correct_value = list(qi.correct_answers)
        else:
            correct_value = qi.correct_answer

        graded.append(
            GradedAnswer(
                question_id=qi.question_id,
                question=qi.question,
                student_answer=student_answer,
                correct_answer=correct_value,
                is_correct=correct,
                found=True,
                topic_id=str(qi.topic_id) if qi.topic_id else None,
                subtopic_id=str(qi.subtopic_id) if qi.subtopic_id else None,
            )
        )

    return graded
