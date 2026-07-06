"""
Unit tests for the server-authoritative grading core (Phase 0, D1).

These cover the pure functions only (no DB, no web stack) so they run anywhere,
including the exit-criteria proof that a tampered submission cannot forge a score.
"""
import random

from app.services.assessment_grading import (
    is_answer_correct,
    prepare_question,
    to_answer_set,
)


def test_prepare_shuffles_and_captures_key():
    # Correct answer starts first (the old examiner convention).
    rng = random.Random(1)
    p = prepare_question(
        question="2 + 2 = ?",
        answer="4",
        options=["4", "3", "5", "6"],
        rng=rng,
    )
    assert set(p.options) == {"4", "3", "5", "6"}      # same options, order may differ
    assert p.correct_answer == "4"                       # key captured from `answer`
    assert p.correct_answers == ["4"]
    assert "correct" not in p.client_view()              # client never sees the key
    assert p.client_view()["options"] == p.options


def test_shuffle_breaks_position_predictability():
    # Over many questions, the correct answer must not always land at index 0.
    rng = random.Random(42)
    first_index_hits = 0
    n = 200
    for _ in range(n):
        p = prepare_question(
            question="q", answer="A", options=["A", "B", "C", "D"], rng=rng
        )
        if p.options[0] == "A":
            first_index_hits += 1
    # With 4 options, "always pick A" should win ~25% of the time, not ~100%.
    assert first_index_hits < n * 0.45


def test_grade_uses_stored_key_only():
    assert is_answer_correct(student_answer="4", correct_answer="4") is True
    assert is_answer_correct(student_answer="5", correct_answer="4") is False
    # Empty answer is never correct.
    assert is_answer_correct(student_answer="", correct_answer="4") is False
    assert is_answer_correct(student_answer=None, correct_answer="4") is False


def test_tampered_submission_cannot_forge_score():
    """
    The exit-criteria proof: the grader signature accepts NO client correctness
    field, so a student echoing answer == "their claimed correct answer" gains
    nothing. Grading depends solely on the server-stored key.
    """
    stored_correct = "Paris"
    # Attacker submits a wrong answer but (in the old flow) would have also sent
    # correct_answer="London" to force a match. That channel no longer exists;
    # grading only sees the stored key.
    forged_answer = "London"
    assert is_answer_correct(student_answer=forged_answer, correct_answer=stored_correct) is False
    # Only the genuinely correct value scores.
    assert is_answer_correct(student_answer="Paris", correct_answer=stored_correct) is True


def test_multi_select_set_equality():
    assert is_answer_correct(
        student_answer=["red", "blue"],
        correct_answers=["blue", "red"],
    ) is True
    assert is_answer_correct(
        student_answer=["red"],
        correct_answers=["blue", "red"],
    ) is False
    assert is_answer_correct(
        student_answer=["red", "blue", "green"],
        correct_answers=["blue", "red"],
    ) is False


def test_lenient_single_answer_containment():
    # Matches the legacy practice grader ("it is 5" counts as "5").
    assert is_answer_correct(student_answer="it is 5", correct_answer="5") is True
    assert is_answer_correct(student_answer="5", correct_answer="5") is True


def test_case_and_whitespace_insensitive():
    assert to_answer_set("  Hello ") == {"hello"}
    assert is_answer_correct(student_answer=" PARIS ", correct_answer="paris") is True


if __name__ == "__main__":  # allow running without pytest: python -m tests.test_assessment_grading
    import sys

    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL {name}: {e}")
    sys.exit(1 if failures else 0)
