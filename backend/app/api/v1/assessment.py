"""
AI Tutor Platform - Assessment API
Endpoints for starting and submitting topic assessments
"""
import uuid
from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, Student
from app.models.curriculum import Topic, Subject
from app.models.assessment import AssessmentResult
from app.schemas.assessment import (
    AssessmentStartResponse,
    AssessmentSubmitRequest,
    AssessmentResultResponse,
    AssessmentQuestion,
    QuestionResultDetail,
    AssessmentFeedbackResponse
)
from app.ai.agents.examiner import examiner_agent as question_generator, QuestionDifficulty
from app.ai.agents.feedback import feedback_agent, FeedbackType
from app.services.assessment_grading import prepare_question
from app.services.assessment_store import persist_prepared, grade_submissions

router = APIRouter(prefix="/assessments", tags=["Assessments"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

@router.post("/start/{topic_id}", response_model=AssessmentStartResponse)
async def start_assessment(
    topic_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
    subtopic_id: uuid.UUID | None = None
):
    """
    Start a new assessment for a topic or specific subtopic.
    Generates a set of 5 questions covering the topic/subtopic.
    
    Query Parameters:
    - subtopic_id: Optional. If provided, assessment focuses on this subtopic only.
    """
    from app.models.curriculum import Subtopic
    
    # 1. Verify access via student profile
    student = await _get_student_profile(current_user, db)
    
    # 2. Get topic details
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    
    # 3. Get subtopic if specified
    subtopic = None
    subtopic_name = topic.name  # Default to topic name
    if subtopic_id:
        subtopic = await db.get(Subtopic, subtopic_id)
        if not subtopic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subtopic not found"
            )
        # Verify subtopic belongs to this topic
        if subtopic.topic_id != topic_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subtopic does not belong to this topic"
            )
        subtopic_name = subtopic.name
        
    # 4. Generate questions (Mix of difficulties)
    questions: list[AssessmentQuestion] = []
    
    try:
        # We'll generate 2 Easy, 2 Medium, 1 Hard
        difficulties = [
            QuestionDifficulty.EASY, 
            QuestionDifficulty.EASY,
            QuestionDifficulty.MEDIUM,
            QuestionDifficulty.MEDIUM,
            QuestionDifficulty.HARD
        ]
        
        
        # Session for tracking
        assessment_session_id = f"assessment_{uuid.uuid4().hex}"

        # Generate ALL 5 questions in ONE batch
        questions_batch = await question_generator.generate_batch(
            subject=topic.name,
            topic_distribution=[(topic.name, subtopic_name, 5)],
            difficulty_distribution=difficulties,
            grade=student.grade_level or 1,
            session_id=assessment_session_id
        )

        # Prepare each question server-side: shuffle options and capture the
        # answer key (D1). The key is persisted; the client only sees options.
        prepared = [
            prepare_question(
                question=q_data.question,
                answer=q_data.answer,
                options=q_data.options or [],
                correct_answers=getattr(q_data, "correct_answers", None),
                question_type=getattr(q_data, "question_type", "multiple_choice"),
                difficulty=getattr(q_data, "difficulty", "easy"),
            )
            for q_data in questions_batch[:5]
        ]

        await persist_prepared(
            db,
            session_id=assessment_session_id,
            student_id=student.id,
            origin="assessment",
            prepared=prepared,
            subtopic_id=subtopic_id,
            topic_id=topic_id,
        )

        questions = [
            AssessmentQuestion(
                question_id=p.question_id,
                question=p.question,
                options=p.options,
                question_type=p.question_type,
            )
            for p in prepared
        ]

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating assessment: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate assessment. Please try again."
        )

    # Persist the answer keys before returning the questions.
    await db.commit()

    # Include subtopic name in response if specified
    assessment_title = f"{topic.name}: {subtopic_name}" if subtopic else topic.name

    return AssessmentStartResponse(
        assessment_id=assessment_session_id,  # echoed back at submit for audit
        topic_name=assessment_title,
        questions=questions
    )


@router.post("/submit", response_model=AssessmentResultResponse)
async def submit_assessment(
    request: AssessmentSubmitRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession
):
    """
    Submit assessment answers.
    Grades answers and generates AI feedback with detailed analysis.
    """
    student = await _get_student_profile(current_user, db)
    
    # 1. Get Topic
    topic = await db.get(Topic, request.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    # 2. Grade each answer SERVER-SIDE against the stored key (D1).
    #    The client-supplied `correct_answer` on each item is ignored.
    graded = await grade_submissions(
        db,
        student_id=student.id,
        submissions=[
            {"question_id": item.question_id, "answer": item.answer, "question": item.question}
            for item in request.answers
        ],
    )

    def _as_text(value) -> str:
        return ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)

    details: list[QuestionResultDetail] = []
    correct_count = 0
    questions_detail_for_ai = []

    for g in graded:
        if g.is_correct:
            correct_count += 1

        details.append(QuestionResultDetail(
            question=g.question,
            student_answer=_as_text(g.student_answer),
            correct_answer=_as_text(g.correct_answer),
            is_correct=g.is_correct,
            explanation="" if g.found else "This question could not be verified.",
        ))

        result_label = "✓ Correct" if g.is_correct else "✗ Incorrect"
        questions_detail_for_ai.append(
            f"Q: {g.question}\n"
            f"   Student's Answer: {_as_text(g.student_answer)}\n"
            f"   Correct Answer: {_as_text(g.correct_answer)}\n"
            f"   Result: {result_label}"
        )

    graded_total = len(graded)
    score = (correct_count / graded_total) * 100 if graded_total else 0
    
    # 3. Generate AI Feedback using FeedbackAgent
    feedback_data = None
    try:
        # Use unified FeedbackAgent for consistency across all endpoints
        feedback_result = await feedback_agent.generate_feedback(
            feedback_type=FeedbackType.ASSESSMENT,
            subject=request.subject_name or "Subject",
            topic=request.topic_name or topic.name,
            score=score,
            correct=correct_count,
            total=graded_total,
            questions_detail="\n\n".join(questions_detail_for_ai),
            grade=student.grade_level or 1
        )
        
        feedback_data = {
            "overall_score_interpretation": feedback_result.overall_interpretation,
            "strengths": feedback_result.strengths,
            "areas_of_improvement": feedback_result.areas_to_improve,
            "ways_to_improve": feedback_result.specific_recommendations,
            "practical_assignments": feedback_result.practice_activities,
            "encouraging_words": feedback_result.encouraging_message,
            "pattern_analysis": feedback_result.pattern_analysis
        }
    except Exception as e:
        print(f"Error generating AI feedback: {e}")
        # Fallback feedback
        feedback_data = {
            "overall_score_interpretation": f"You scored {round(score)}%! {'Great job!' if score >= 70 else 'Keep practicing!'}",
            "strengths": ["You completed the assessment!", "You're working hard to learn!"],
            "areas_of_improvement": ["Keep practicing to improve your score."],
            "ways_to_improve": ["Practice a little bit every day", "Ask for help when you're stuck"],
            "practical_assignments": ["Try the practice mode for more questions"],
            "encouraging_words": "Every attempt makes you smarter! Keep going! 🌟",
            "pattern_analysis": "Complete more assessments to see your progress patterns."
        }

    
    # 4. Save Result
    result = AssessmentResult(
        student_id=student.id,
        topic_id=topic.id,
        score=score,
        total_questions=graded_total,
        correct_questions=correct_count,
        details=[d.model_dump() for d in details],
        feedback=feedback_data
    )
    
    db.add(result)
    await db.commit()
    await db.refresh(result)
    
    # Award XP for assessment completion
    try:
        from app.services.gamification import GamificationService
        gamification = GamificationService(db)
        if score == 100:
            await gamification.award_xp(student.id, "assessment_perfect")  # +100 XP
        else:
            await gamification.award_xp(student.id, "assessment_complete")  # +25 XP
        await gamification.update_streak(student.id)
    except Exception as gam_err:
        print(f"Gamification error (non-critical): {gam_err}")
    
    # 5. Build response with feedback
    response = AssessmentResultResponse(
        id=result.id,
        score=result.score,
        total_questions=result.total_questions,
        correct_questions=result.correct_questions,
        completed_at=result.completed_at,
        details=details,
        topic_name=topic.name,
        feedback=AssessmentFeedbackResponse(**feedback_data) if feedback_data else None
    )
    
    return response


@router.get("/history", response_model=list[AssessmentResultResponse])
async def get_assessment_history(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession
):
    """Get history of assessments with feedback."""
    student = await _get_student_profile(current_user, db)
    
    result = await db.execute(
        select(AssessmentResult)
        .where(AssessmentResult.student_id == student.id)
        .order_by(AssessmentResult.completed_at.desc())
        .options(selectinload(AssessmentResult.topic))
    )
    
    history = result.scalars().all()
    
    # Enrich with topic name and feedback
    response = []
    for h in history:
        feedback = None
        if h.feedback:
            feedback = AssessmentFeedbackResponse(**h.feedback)
        
        resp = AssessmentResultResponse(
            id=h.id,
            score=h.score,
            total_questions=h.total_questions,
            correct_questions=h.correct_questions,
            completed_at=h.completed_at,
            details=h.details,
            topic_name=h.topic.name if h.topic else None,
            feedback=feedback
        )
        response.append(resp)
        
    return response


async def _get_student_profile(user: User, db: AsyncSession) -> Student:
    """Helper to get student profile."""
    result = await db.execute(select(Student).where(Student.parent_id == user.id))
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return student
