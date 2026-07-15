"""
DB-backed tests for server-authoritative grading (Phase 0 D1 exit proof).

Complements the pure-function tests in test_assessment_grading.py by proving
the persistence layer end-to-end against real Postgres:

  * answer keys are stored server-side at generation time,
  * grading uses ONLY the stored key (tampered submissions score 0),
  * question lookups are scoped to the owning student,
  * fabricated question_ids never score.
"""
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Student, User
from app.services.assessment_grading import prepare_question
from app.services.assessment_store import grade_submissions, persist_prepared


async def _make_student(db: AsyncSession, email: str = "parent@example.com") -> Student:
    user = User(
        email=email,
        hashed_password="x" * 60,
        first_name="Parent",
        last_name="Test",
    )
    db.add(user)
    await db.flush()
    student = Student(
        parent_id=user.id,
        first_name="Kid",
        last_name="Test",
        grade_level=4,
    )
    db.add(student)
    await db.flush()
    return student


def _prepared_set():
    return [
        prepare_question(
            question="What is 2 + 2?",
            answer="4",
            options=["4", "3", "5", "6"],
        ),
        prepare_question(
            question="Capital of India?",
            answer="New Delhi",
            options=["New Delhi", "Mumbai", "Kolkata", "Chennai"],
        ),
    ]


@pytest.mark.asyncio
async def test_persist_and_grade_correct_answers(db_session: AsyncSession):
    student = await _make_student(db_session)
    prepared = _prepared_set()
    await persist_prepared(
        db_session,
        session_id="assessment_test1",
        student_id=student.id,
        origin="assessment",
        prepared=prepared,
    )

    graded = await grade_submissions(
        db_session,
        student_id=student.id,
        submissions=[
            {"question_id": prepared[0].question_id, "answer": "4"},
            {"question_id": prepared[1].question_id, "answer": "New Delhi"},
        ],
    )
    assert all(g.found for g in graded)
    assert all(g.is_correct for g in graded)
    # The stored key is revealed only in the graded result.
    assert graded[0].correct_answer == "4"


@pytest.mark.asyncio
async def test_tampered_submission_scores_zero(db_session: AsyncSession):
    """The D1 exit criterion: a tampered submit cannot score."""
    student = await _make_student(db_session)
    prepared = _prepared_set()
    await persist_prepared(
        db_session,
        session_id="assessment_tamper",
        student_id=student.id,
        origin="assessment",
        prepared=prepared,
    )

    # Old exploit #1: client claims its own answer is the correct one.
    # There is no channel for that claim anymore — grading reads the stored key.
    graded = await grade_submissions(
        db_session,
        student_id=student.id,
        submissions=[
            {"question_id": prepared[0].question_id, "answer": "5", "correct_answer": "5"},
            {"question_id": prepared[1].question_id, "answer": "Mumbai", "correct_answer": "Mumbai"},
        ],
    )
    assert all(g.found for g in graded)
    assert not any(g.is_correct for g in graded)

    # Old exploit #2: fabricated question with attacker-chosen key.
    graded_fake = await grade_submissions(
        db_session,
        student_id=student.id,
        submissions=[
            {"question_id": uuid.uuid4().hex, "answer": "anything", "correct_answer": "anything"},
        ],
    )
    assert graded_fake[0].found is False
    assert graded_fake[0].is_correct is False


@pytest.mark.asyncio
async def test_cannot_grade_another_students_question(db_session: AsyncSession):
    """Lookups are scoped to the owning student."""
    student_a = await _make_student(db_session, email="a@example.com")
    student_b = await _make_student(db_session, email="b@example.com")

    prepared = _prepared_set()
    await persist_prepared(
        db_session,
        session_id="assessment_scope",
        student_id=student_a.id,
        origin="test",
        prepared=prepared,
    )

    graded = await grade_submissions(
        db_session,
        student_id=student_b.id,  # different student
        submissions=[{"question_id": prepared[0].question_id, "answer": "4"}],
    )
    assert graded[0].found is False
    assert graded[0].is_correct is False


@pytest.mark.asyncio
async def test_options_are_shuffled_but_complete(db_session: AsyncSession):
    """Client-visible options contain everything, in server-chosen order."""
    student = await _make_student(db_session)
    prepared = [
        prepare_question(
            question="q",
            answer="A",
            options=["A", "B", "C", "D"],
        )
        for _ in range(30)
    ]
    await persist_prepared(
        db_session,
        session_id="assessment_shuffle",
        student_id=student.id,
        origin="exam",
        prepared=prepared,
    )
    assert all(set(p.options) == {"A", "B", "C", "D"} for p in prepared)
    # Not all 30 shuffles should leave the correct answer in position 0.
    first_position_hits = sum(1 for p in prepared if p.options[0] == "A")
    assert first_position_hits < 30
