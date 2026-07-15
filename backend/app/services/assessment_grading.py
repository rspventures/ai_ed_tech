"""
Server-authoritative assessment grading (Phase 0, fixes D1).

Before this module, assessment/test/exam endpoints graded a student's answer
against a ``correct_answer`` supplied *by the client*, and the examiner always
placed the correct option first — so scores/XP were trivially forgeable and the
answer was always option A.

This module makes the server the sole source of truth:

  * ``prepare_question`` shuffles the options and captures the correct value(s)
    at generation time (the correct answer is never derivable from option order).
  * The correct value is persisted server-side (see ``QuestionInstance``); the
    client only ever receives the shuffled options.
  * ``is_answer_correct`` grades a student's answer against the *stored* key.
    A client-supplied ``correct_answer`` is ignored entirely.

The pure functions below (``prepare_question``, ``is_answer_correct``,
``to_answer_set``) depend only on the standard library so they can be unit
tested without a database or the web stack. DB persistence/loading helpers live
in ``assessment_store.py`` to keep this core dependency-free.
"""
from __future__ import annotations

import random
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass
class PreparedQuestion:
    """A question ready to be persisted server-side and shown to the client."""

    question_id: str
    question: str
    options: list[str]            # shuffled — safe to send to the client
    correct_answer: str           # the correct option value (server secret until submit)
    correct_answers: list[str]    # all correct values (multi-select); [correct_answer] for single
    question_type: str = "multiple_choice"   # "multiple_choice" | "multi_select"
    difficulty: str = "easy"
    hint: str = ""
    explanation: str = ""
    subtopic_id: str | None = None            # per-question curriculum context (optional)
    topic_id: str | None = None
    metadata: dict = field(default_factory=dict)

    def client_view(self) -> dict:
        """The subset safe to return to the client (never the correct answer)."""
        return {
            "question_id": self.question_id,
            "question": self.question,
            "options": self.options,
            "question_type": self.question_type,
        }


def _clean(value) -> str:
    return str(value).strip().lower()


def to_answer_set(answer) -> set[str]:
    """Normalize a single answer or list of answers into a comparable set."""
    if answer is None:
        return set()
    if isinstance(answer, (list, tuple, set)):
        return {_clean(a) for a in answer if str(a).strip() != ""}
    text = str(answer).strip()
    return {_clean(text)} if text else set()


def prepare_question(
    *,
    question: str,
    answer: str,
    options: Iterable[str],
    correct_answers: Iterable[str] | None = None,
    question_type: str = "multiple_choice",
    difficulty: str = "easy",
    hint: str = "",
    explanation: str = "",
    subtopic_id: str | None = None,
    topic_id: str | None = None,
    question_id: str | None = None,
    rng: random.Random | None = None,
) -> PreparedQuestion:
    """
    Build a :class:`PreparedQuestion`: shuffle the options so the correct value
    is not positionally predictable, and record the correct value(s).

    ``rng`` is injectable so tests can shuffle deterministically.
    """
    shuffler = rng or random
    opts = [str(o) for o in (options or [])]
    shuffler.shuffle(opts)

    corrects = [str(a) for a in (correct_answers or [])]
    if not corrects and answer:
        corrects = [str(answer)]

    resolved_answer = str(answer) if answer else (corrects[0] if corrects else "")

    return PreparedQuestion(
        question_id=question_id or uuid.uuid4().hex,
        question=question,
        options=opts,
        correct_answer=resolved_answer,
        correct_answers=corrects or ([resolved_answer] if resolved_answer else []),
        question_type=question_type,
        difficulty=difficulty,
        hint=hint,
        explanation=explanation,
        subtopic_id=subtopic_id,
        topic_id=topic_id,
    )


def is_answer_correct(
    *,
    student_answer,
    correct_answer: str | None = None,
    correct_answers: Iterable[str] | None = None,
) -> bool:
    """
    Grade a student's answer against the *stored* correct value(s).

    Deliberately takes NO client-supplied correctness signal. Uses set equality
    so single- and multi-select are handled uniformly; an empty student answer
    is always incorrect.
    """
    student_set = to_answer_set(student_answer)
    if not student_set:
        return False

    correct_set = to_answer_set(list(correct_answers) if correct_answers else correct_answer)
    if not correct_set:
        return False

    if student_set == correct_set:
        return True

    # Lenient single-answer containment (e.g. "it is 5" vs "5"), matching the
    # existing practice grader's behaviour so scoring stays consistent.
    if len(student_set) == 1 and len(correct_set) == 1:
        (student_val,) = tuple(student_set)
        (correct_val,) = tuple(correct_set)
        if correct_val and correct_val in student_val:
            return True

    return False
