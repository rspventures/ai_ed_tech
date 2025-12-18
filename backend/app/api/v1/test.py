"""
AI Tutor Platform - Test API
Endpoints for Topic-level tests (10 questions from subtopics)
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, Student
from app.models.curriculum import Topic, Subtopic
from app.models.test import TestResult
from app.schemas.test import (
    TestStartRequest,
    TestStartResponse,
    TestSubmitRequest,
    TestResultResponse,
    TestHistoryItem,
    TestQuestion,
    QuestionExplanation,
    TestFeedbackResponse,
)
from app.ai.agents.examiner import examiner_agent as question_generator, QuestionDifficulty
from app.ai.agents.feedback import feedback_agent, FeedbackType

router = APIRouter(prefix="/tests", tags=["Tests"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

# Standard test configuration
TEST_QUESTIONS = 10
DEFAULT_TIME_LIMIT_MINUTES = 10


@router.post("/start", response_model=TestStartResponse)
async def start_test(
    request: TestStartRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession
):
    """
    Start a new topic test.
    Generates 10 questions distributed across subtopics within the topic.
    """
    # 1. Verify student profile
    student = await _get_student_profile(current_user, db)
    
    # 2. Get topic with subtopics
    result = await db.execute(
        select(Topic)
        .where(Topic.id == request.topic_id)
        .options(selectinload(Topic.subtopics))
    )
    topic = result.scalar_one_or_none()
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    
    # 3. Get subtopics - use all subtopics from the topic
    subtopics = list(topic.subtopics)
    
    if not subtopics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No subtopics available for this topic"
        )
    
    # 4. Generate questions from subtopics
    questions: list[TestQuestion] = []
    seen_questions: set[str] = set()
    
    def normalize(q: str) -> str:
        return q.lower().strip().replace(" ", "").replace("?", "")
    
    # Distribute questions across subtopics
    questions_per_subtopic = TEST_QUESTIONS // len(subtopics)
    remainder = TEST_QUESTIONS % len(subtopics)
    
    # Difficulty distribution
    difficulties = [
        QuestionDifficulty.EASY,
        QuestionDifficulty.EASY,
        QuestionDifficulty.MEDIUM,
        QuestionDifficulty.MEDIUM,
        QuestionDifficulty.MEDIUM,
        QuestionDifficulty.MEDIUM,
        QuestionDifficulty.HARD,
        QuestionDifficulty.HARD,
        QuestionDifficulty.MEDIUM,
        QuestionDifficulty.EASY,
    ]
    
    # Difficulty distribution (hardcoded for 10 questions)
    difficulty_distribution = [
        QuestionDifficulty.EASY,
        QuestionDifficulty.EASY,
        QuestionDifficulty.MEDIUM,
        QuestionDifficulty.MEDIUM,
        QuestionDifficulty.MEDIUM,
        QuestionDifficulty.MEDIUM,
        QuestionDifficulty.HARD,
        QuestionDifficulty.HARD,
        QuestionDifficulty.MEDIUM,
        QuestionDifficulty.EASY,
    ]
    
    # Create shared session
    test_session_id = f"test_{uuid.uuid4().hex}"
    
    # Build topic distribution for batch generation
    topic_distribution = []
    for i, subtopic in enumerate(subtopics):
        count = questions_per_subtopic + (1 if i < remainder else 0)
        topic_distribution.append((topic.name, subtopic.name, count))
    
    try:
        # Generate all 10 questions in ONE batch
        questions_batch = await question_generator.generate_batch(
            subject=topic.name,
            topic_distribution=topic_distribution,
            difficulty_distribution=difficulty_distribution[:TEST_QUESTIONS],
            grade=student.grade_level or topic.grade_level or 1,
            session_id=test_session_id
        )
        
        # Convert to TestQuestion format
        questions: list[TestQuestion] = []
        q_idx = 0
        
        for subtopic_idx, (topic_name, subtopic_name, count) in enumerate(topic_distribution):
            subtopic_obj = subtopics[subtopic_idx]
            
            for _ in range(count):
                if q_idx < len(questions_batch) and q_idx < TEST_QUESTIONS:
                    q_data = questions_batch[q_idx]
                    questions.append(TestQuestion(
                        question_id=f"test_q_{q_idx}_{uuid.uuid4().hex[:8]}",
                        question=q_data.question,
                        options=q_data.options or [],
                        subtopic_id=str(subtopic_obj.id),
                        subtopic_name=subtopic_obj.name
                    ))
                    q_idx += 1
                    
    except Exception as e:
        print(f"Error generating test questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate test questions. Please try again."
        )
    
    # 5. Calculate time limit
    time_limit_seconds = None
    if request.time_limit_minutes:
        time_limit_seconds = request.time_limit_minutes * 60
    
    return TestStartResponse(
        test_id=uuid.uuid4().hex,
        topic_name=topic.name,
        topic_id=topic.id,
        questions=questions,
        time_limit_seconds=time_limit_seconds,
        total_questions=len(questions)
    )


@router.post("/submit", response_model=TestResultResponse)
async def submit_test(
    request: TestSubmitRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession
):
    """
    Submit test answers.
    Grades answers and generates per-question explanations for wrong answers.
    """
    student = await _get_student_profile(current_user, db)
    
    # 1. Get topic
    topic = await db.get(Topic, request.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    # 2. Grade answers and generate explanations
    correct_count = 0
    question_results: list[QuestionExplanation] = []
    wrong_questions = []
    
    for item in request.answers:
        # Handle list vs string comparison
        if isinstance(item.answer, list):
            u_set = {str(x).strip().lower() for x in item.answer}
        else:
            u_set = {str(item.answer).strip().lower()}
            
        if isinstance(item.correct_answer, list):
            c_set = {str(x).strip().lower() for x in item.correct_answer}
        else:
            c_set = {str(item.correct_answer).strip().lower()}
            
        is_correct = u_set == c_set
        
        if is_correct:
            correct_count += 1
            question_results.append(QuestionExplanation(
                question=item.question,
                student_answer=item.answer,
                correct_answer=item.correct_answer,
                is_correct=True,
                explanation="Correct! Great job! ✓"
            ))
        else:
            wrong_questions.append(item)
            # Generate AI explanation for wrong answer
            explanation = await _generate_explanation(
                question=item.question,
                student_answer=item.answer,
                correct_answer=item.correct_answer,
                topic_name=request.topic_name
            )
            question_results.append(QuestionExplanation(
                question=item.question,
                student_answer=item.answer,
                correct_answer=item.correct_answer,
                is_correct=False,
                explanation=explanation
            ))
    
    # 3. Calculate score
    score = (correct_count / len(request.answers)) * 100 if request.answers else 0
    
    # 4. Generate AI-powered overall feedback
    try:
        # Build questions detail for AI analysis
        questions_detail = "\n\n".join([
            f"Q: {qr.question}\nStudent Answer: {qr.student_answer}\nCorrect Answer: {qr.correct_answer}\nResult: {'✅ Correct' if qr.is_correct else '❌ Incorrect'}"
            for qr in question_results
        ])
        
        feedback_result = await feedback_agent.generate_feedback(
            feedback_type=FeedbackType.TEST,
            subject=request.topic_name,
            topic=request.topic_name,
            score=score,
            correct=correct_count,
            total=len(request.answers),
            questions_detail=questions_detail,
            grade=student.grade_level or 1
        )
        
        # Convert to TestFeedbackResponse
        feedback = TestFeedbackResponse(
            summary=feedback_result.overall_interpretation,
            strengths=feedback_result.strengths,
            weaknesses=feedback_result.areas_to_improve,
            recommendations=feedback_result.specific_recommendations,
            encouragement=feedback_result.encouraging_message
        )
    except Exception as e:
        print(f"Error generating test feedback: {e}")
        # Fallback
        feedback = _generate_test_feedback(
            topic_name=request.topic_name,
            score=score,
            correct=correct_count,
            total=len(request.answers),
            wrong_count=len(wrong_questions)
        )
    
    # 5. Save result
    result = TestResult(
        student_id=student.id,
        topic_id=topic.id,
        score=score,
        total_questions=len(request.answers),
        correct_questions=correct_count,
        duration_seconds=request.duration_seconds,
        details=[qr.model_dump() for qr in question_results],
        feedback=feedback.model_dump()
    )
    
    db.add(result)
    await db.commit()
    await db.refresh(result)
    
    # 6. Award XP
    try:
        from app.services.gamification import GamificationService
        gamification = GamificationService(db)
        if score == 100:
            await gamification.award_xp(student.id, "test_perfect")
        elif score >= 80:
            await gamification.award_xp(student.id, "test_excellent")
        else:
            await gamification.award_xp(student.id, "test_complete")
        await gamification.update_streak(student.id)
    except Exception as gam_err:
        print(f"Gamification error (non-critical): {gam_err}")
    
    return TestResultResponse(
        id=result.id,
        score=result.score,
        total_questions=result.total_questions,
        correct_questions=result.correct_questions,
        duration_seconds=result.duration_seconds,
        completed_at=result.completed_at,
        topic_name=topic.name,
        question_results=question_results,
        feedback=feedback
    )


@router.get("/history", response_model=list[TestHistoryItem])
async def get_test_history(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession
):
    """Get history of tests taken by the student."""
    student = await _get_student_profile(current_user, db)
    
    result = await db.execute(
        select(TestResult)
        .where(TestResult.student_id == student.id)
        .order_by(TestResult.completed_at.desc())
        .options(selectinload(TestResult.topic))
    )
    
    history = result.scalars().all()
    
    response = []
    for h in history:
        response.append(TestHistoryItem(
            id=h.id,
            score=h.score,
            total_questions=h.total_questions,
            correct_questions=h.correct_questions,
            topic_name=h.topic.name if h.topic else "Unknown",
            completed_at=h.completed_at
        ))
    
    return response


async def _get_student_profile(user: User, db: AsyncSession) -> Student:
    """Helper to get student profile."""
    result = await db.execute(select(Student).where(Student.parent_id == user.id))
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return student


async def _generate_explanation(
    question: str,
    student_answer: str,
    correct_answer: str,
    topic_name: str
) -> str:
    """Generate AI explanation for wrong answer."""
    # Simple explanatory template - can be enhanced with LLM
    # Format answers for display
    def fmt(ans):
        if isinstance(ans, list):
            return ", ".join(ans)
        return str(ans)

    return (
        f"The correct answer is '{fmt(correct_answer)}'. "
        f"You chose '{fmt(student_answer)}'. "
        f"Review your understanding of {topic_name} to master this concept."
    )


def _generate_test_feedback(
    topic_name: str,
    score: float,
    correct: int,
    total: int,
    wrong_count: int
) -> TestFeedbackResponse:
    """Generate feedback for the test."""
    
    # Summary based on score
    if score >= 90:
        summary = f"Outstanding! You scored {round(score)}% on {topic_name}. You've mastered this topic!"
    elif score >= 80:
        summary = f"Excellent work! {round(score)}% shows strong understanding of {topic_name}."
    elif score >= 70:
        summary = f"Good job! You scored {round(score)}%. A bit more practice will help you excel."
    elif score >= 60:
        summary = f"Decent effort with {round(score)}%. Focus on reviewing the incorrect answers."
    else:
        summary = f"You scored {round(score)}%. Don't worry - review the explanations and try again!"
    
    # Strengths
    strengths = []
    if correct > 0:
        strengths.append(f"You got {correct} out of {total} questions correct")
    if score >= 60:
        strengths.append(f"You have a foundational understanding of {topic_name}")
    
    # Weaknesses  
    weaknesses = []
    if wrong_count > 0:
        weaknesses.append(f"Review the {wrong_count} questions you missed")
    if score < 60:
        weaknesses.append(f"Consider re-studying {topic_name} fundamentals")
    
    # Recommendations
    recommendations = [
        "Read through the explanations for each wrong answer",
        "Practice more questions on this topic",
    ]
    if score < 80:
        recommendations.append("Try the practice mode before retaking the test")
    
    # Encouragement
    if score >= 80:
        encouragement = "Keep up the amazing work! You're a star learner! ⭐"
    elif score >= 60:
        encouragement = "You're making great progress. Keep practicing! 💪"
    else:
        encouragement = "Every mistake is a learning opportunity. You've got this! 🚀"
    
    return TestFeedbackResponse(
        summary=summary,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations,
        encouragement=encouragement
    )
