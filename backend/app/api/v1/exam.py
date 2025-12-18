"""
AI Tutor Platform - Exam API
Endpoints for subject-level exams covering multiple topics
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
from app.models.curriculum import Subject, Topic
from app.models.exam import ExamResult
from app.schemas.exam import (
    ExamStartRequest,
    ExamStartResponse,
    ExamSubmitRequest,
    ExamResultResponse,
    ExamHistoryItem,
    ExamQuestion,
    ExamTopicSelection,
    TopicBreakdown,
    ExamFeedbackResponse,
)
from app.ai.agents.examiner import examiner_agent as question_generator, QuestionDifficulty
from app.ai.agents.feedback import feedback_agent, FeedbackType

router = APIRouter(prefix="/exams", tags=["Exams"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/start", response_model=ExamStartResponse)
async def start_exam(
    request: ExamStartRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession
):
    """
    Start a new exam for a subject covering multiple topics.
    Generates a set of questions distributed across selected topics.
    """
    # 1. Verify student profile
    student = await _get_student_profile(current_user, db)
    
    # 2. Get subject
    subject = await db.get(Subject, request.subject_id)
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found"
        )
    
    # 3. Get and validate topics
    topics_data: list[ExamTopicSelection] = []
    topic_objects: list[Topic] = []
    
    for topic_id in request.topic_ids:
        topic = await db.get(Topic, topic_id)
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic {topic_id} not found"
            )
        if topic.subject_id != request.subject_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Topic {topic.name} does not belong to this subject"
            )
        topics_data.append(ExamTopicSelection(topic_id=topic.id, topic_name=topic.name))
        topic_objects.append(topic)
    
    # 4. Distribute questions across topics
    num_topics = len(topic_objects)
    questions_per_topic = request.num_questions // num_topics
    remainder = request.num_questions % num_topics
    
    # 5. Generate ALL questions in ONE batch for better diversity
    exam_session_id = f"exam_{uuid.uuid4().hex}"
    
    # Build topic distribution for batch generation
    topic_distribution = []
    difficulty_distribution = []
    
    # Difficulty pattern: 40% easy, 40% medium, 20% hard
    difficulties = [QuestionDifficulty.EASY, QuestionDifficulty.MEDIUM, QuestionDifficulty.HARD]
    
    for i, topic in enumerate(topic_objects):
        # Questions for this topic
        topic_question_count = questions_per_topic + (1 if i < remainder else 0)
        
        # Add to distribution
        topic_distribution.append((topic.name, topic.name, topic_question_count))
        
        # Add difficulties for this topic's questions
        for j in range(topic_question_count):
            diff_idx = (len(difficulty_distribution)) % 3
            if diff_idx == 0:
                difficulty_distribution.append(QuestionDifficulty.EASY)
            elif diff_idx == 1:
                difficulty_distribution.append(QuestionDifficulty.MEDIUM)
            else:
                difficulty_distribution.append(QuestionDifficulty.HARD)
    
    try:
        # Generate all questions in ONE call
        questions_batch = await question_generator.generate_batch(
            subject=subject.name,
            topic_distribution=topic_distribution,
            difficulty_distribution=difficulty_distribution,
            grade=student.grade_level or 1,
            session_id=exam_session_id
        )
        
        
        # Convert to ExamQuestion format
        # Questions come back in same order as topic_distribution
        questions: list[ExamQuestion] = []
        q_idx = 0
        
        for topic_idx, (topic_name, subtopic_name, count) in enumerate(topic_distribution):
            topic_obj = topic_objects[topic_idx]
            
            for _ in range(count):
                if q_idx < len(questions_batch):
                    q_data = questions_batch[q_idx]
                    questions.append(ExamQuestion(
                        question_id=f"exam_q_{q_idx}_{uuid.uuid4().hex[:8]}",
                        question=q_data.question,
                        options=q_data.options or [],
                        topic_id=str(topic_obj.id),
                        topic_name=topic_obj.name
                    ))
                    q_idx += 1

                
    except Exception as e:
        print(f"Error generating exam questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to generate exam questions: {str(e)}"
        )

    
    # 6. Calculate time limit
    time_limit_seconds = None
    if request.time_limit_minutes:
        time_limit_seconds = request.time_limit_minutes * 60
    
    return ExamStartResponse(
        exam_id=uuid.uuid4().hex,
        subject_name=subject.name,
        topics=topics_data,
        questions=questions,
        time_limit_seconds=time_limit_seconds,
        total_questions=len(questions)
    )


@router.post("/submit", response_model=ExamResultResponse)
async def submit_exam(
    request: ExamSubmitRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession
):
    """
    Submit exam answers.
    Grades answers, calculates per-topic breakdown, and generates AI feedback.
    """
    student = await _get_student_profile(current_user, db)
    
    # 1. Get subject
    subject = await db.get(Subject, request.subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # 2. Grade answers and build topic breakdown
    correct_count = 0
    topic_scores: dict[str, dict] = {}  # { topic_id: { correct, total, name } }
    details = []
    
    for item in request.answers:
        is_correct = item.answer.strip().lower() == item.correct_answer.strip().lower()
        
        if is_correct:
            correct_count += 1
        
        # Track per-topic
        if item.topic_id not in topic_scores:
            topic_scores[item.topic_id] = {"correct": 0, "total": 0, "name": "Unknown"}
        
        topic_scores[item.topic_id]["total"] += 1
        if is_correct:
            topic_scores[item.topic_id]["correct"] += 1
        
        # Get topic name from question data
        # (We'll update this from the first occurrence)
        
        details.append({
            "question": item.question,
            "student_answer": item.answer,
            "correct_answer": item.correct_answer,
            "is_correct": is_correct,
            "topic_id": item.topic_id
        })
    
    # 3. Get topic names
    for topic_id_str in topic_scores.keys():
        try:
            topic = await db.get(Topic, uuid.UUID(topic_id_str))
            if topic:
                topic_scores[topic_id_str]["name"] = topic.name
        except:
            pass
    
    # 4. Calculate overall score
    score = (correct_count / len(request.answers)) * 100 if request.answers else 0
    
    # 5. Build topic breakdown response
    topic_breakdown_list: list[TopicBreakdown] = []
    for tid, data in topic_scores.items():
        percentage = (data["correct"] / data["total"]) * 100 if data["total"] > 0 else 0
        topic_breakdown_list.append(TopicBreakdown(
            topic_id=tid,
            topic_name=data["name"],
            correct=data["correct"],
            total=data["total"],
            percentage=round(percentage, 1)
        ))
    
    
    # 6. Generate AI feedback using FeedbackAgent
    feedback_data = None
    try:
        # Build questions detail for AI analysis
        questions_detail = "\n\n".join([
            f"Q: {d['question']}\nStudent Answer: {d['student_answer']}\nCorrect Answer: {d['correct_answer']}\nResult: {'✅ Correct' if d['is_correct'] else '❌ Incorrect'}"
            for d in details
        ])
        
        # Get AI-powered feedback
        feedback_result = await feedback_agent.generate_feedback(
            feedback_type=FeedbackType.EXAM,
            subject=request.subject_name,
            topic=", ".join([tb.topic_name for tb in topic_breakdown_list]),
            score=score,
            correct=correct_count,
            total=len(request.answers),
            questions_detail=questions_detail,
            grade=student.grade_level or 1,
            topic_breakdown=topic_breakdown_list
        )
        
        # Convert FeedbackResult to ExamFeedbackResponse
        feedback_data = ExamFeedbackResponse(
            overall_interpretation=feedback_result.overall_interpretation,
            topic_analysis=[f"{tb.topic_name}: {tb.percentage}%" for tb in topic_breakdown_list],
            strengths=feedback_result.strengths,
            areas_to_focus=feedback_result.areas_to_improve,
            study_recommendations=feedback_result.specific_recommendations,
            encouraging_message=feedback_result.encouraging_message
        )
    except Exception as e:
        print(f"Error generating exam feedback: {e}")
        # Fallback feedback
        feedback_data = ExamFeedbackResponse(
            overall_interpretation=f"You scored {round(score)}%! {'Excellent work!' if score >= 80 else 'Good effort!' if score >= 60 else 'Keep practicing!'}",
            topic_analysis=[f"{tb.topic_name}: {tb.percentage}%" for tb in topic_breakdown_list],
            strengths=["You completed the entire exam!"],
            areas_to_focus=[tb.topic_name for tb in topic_breakdown_list if tb.percentage < 60],
            study_recommendations=["Review topics where you scored below 60%", "Practice more questions daily"],
            encouraging_message="Every exam is a step towards mastery! Keep going! 🌟"
        )

    
    # 7. Save result
    result = ExamResult(
        student_id=student.id,
        subject_id=subject.id,
        topic_ids=[str(tid) for tid in request.topic_ids],
        score=score,
        total_questions=len(request.answers),
        correct_questions=correct_count,
        duration_seconds=request.duration_seconds,
        topic_breakdown={tid: data for tid, data in topic_scores.items()},
        details=details,
        feedback=feedback_data.model_dump() if feedback_data else None
    )
    
    db.add(result)
    await db.commit()
    await db.refresh(result)
    
    # 8. Award XP
    try:
        from app.services.gamification import GamificationService
        gamification = GamificationService(db)
        if score == 100:
            await gamification.award_xp(student.id, "exam_perfect")  # +150 XP
        elif score >= 80:
            await gamification.award_xp(student.id, "exam_excellent")  # +75 XP
        else:
            await gamification.award_xp(student.id, "exam_complete")  # +50 XP
        await gamification.update_streak(student.id)
    except Exception as gam_err:
        print(f"Gamification error (non-critical): {gam_err}")
    
    return ExamResultResponse(
        id=result.id,
        score=result.score,
        total_questions=result.total_questions,
        correct_questions=result.correct_questions,
        duration_seconds=result.duration_seconds,
        completed_at=result.completed_at,
        subject_name=subject.name,
        topic_breakdown=topic_breakdown_list,
        feedback=feedback_data
    )


@router.get("/history", response_model=list[ExamHistoryItem])
async def get_exam_history(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession
):
    """Get history of exams taken by the student."""
    student = await _get_student_profile(current_user, db)
    
    result = await db.execute(
        select(ExamResult)
        .where(ExamResult.student_id == student.id)
        .order_by(ExamResult.completed_at.desc())
        .options(selectinload(ExamResult.subject))
    )
    
    history = result.scalars().all()
    
    response = []
    for h in history:
        response.append(ExamHistoryItem(
            id=h.id,
            score=h.score,
            total_questions=h.total_questions,
            correct_questions=h.correct_questions,
            subject_name=h.subject.name if h.subject else "Unknown",
            topics_count=len(h.topic_ids) if h.topic_ids else 0,
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


async def _generate_exam_feedback(
    subject_name: str,
    topic_breakdown: list[TopicBreakdown],
    score: float,
    grade: int
) -> ExamFeedbackResponse:
    """Generate AI-powered feedback for exam results."""
    # Build topic analysis
    topic_analysis = []
    strengths = []
    areas_to_focus = []
    
    for tb in topic_breakdown:
        if tb.percentage >= 80:
            topic_analysis.append(f"✅ {tb.topic_name}: Excellent ({tb.percentage}%)")
            strengths.append(f"Strong understanding of {tb.topic_name}")
        elif tb.percentage >= 60:
            topic_analysis.append(f"📊 {tb.topic_name}: Good ({tb.percentage}%)")
        else:
            topic_analysis.append(f"📚 {tb.topic_name}: Needs practice ({tb.percentage}%)")
            areas_to_focus.append(tb.topic_name)
    
    # Overall interpretation
    if score >= 90:
        overall = f"Outstanding! You scored {round(score)}% - you've mastered this material!"
    elif score >= 80:
        overall = f"Excellent work! Your score of {round(score)}% shows strong understanding."
    elif score >= 70:
        overall = f"Good job! You scored {round(score)}%. A bit more practice will help you excel."
    elif score >= 60:
        overall = f"Decent effort with {round(score)}%. Focus on the weaker topics to improve."
    else:
        overall = f"You scored {round(score)}%. Don't worry - with practice, you'll improve!"
    
    # Recommendations
    recommendations = []
    if areas_to_focus:
        recommendations.append(f"Focus on: {', '.join(areas_to_focus[:3])}")
    recommendations.append("Practice 10-15 minutes daily on weak areas")
    recommendations.append("Take topic-specific tests before retaking the exam")
    
    return ExamFeedbackResponse(
        overall_interpretation=overall,
        topic_analysis=topic_analysis,
        strengths=strengths if strengths else ["You completed the entire exam!"],
        areas_to_focus=areas_to_focus if areas_to_focus else ["Keep practicing to maintain your skills"],
        study_recommendations=recommendations,
        encouraging_message="Every exam teaches you something new. Keep up the great work! 🚀"
    )
