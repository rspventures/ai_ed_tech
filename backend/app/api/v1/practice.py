"""
AI Tutor Platform - Practice Session API
Endpoints for AI-powered practice sessions
"""
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.models.curriculum import Subject, Topic, Subtopic
from app.models.user import User
from app.ai.agents.feedback import feedback_agent, FeedbackType

router = APIRouter(prefix="/practice", tags=["Practice"])


# Request/Response schemas
class StartPracticeRequest(BaseModel):
    """Request to start a practice session."""
    subtopic_id: Optional[UUID] = None
    topic_slug: Optional[str] = None
    subject_slug: Optional[str] = None
    
class QuestionResponse(BaseModel):
    """AI-generated question response."""
    question_id: str
    question: str
    question_type: str = "open_ended"
    options: Optional[list[str]] = None
    hint: str
    subject: str
    topic: str
    subtopic: str
    difficulty: str

class AnswerRequest(BaseModel):
    """Request to submit an answer."""
    question_id: str
    answer: str | list[str]

class AnswerFeedback(BaseModel):
    """Feedback for submitted answer."""
    is_correct: bool
    score: float = Field(ge=0.0, le=1.0)
    feedback: str
    explanation: str
    correct_answer: str
    hint_for_retry: Optional[str] = None


class PracticeSessionFeedback(BaseModel):
    """Session-end feedback for practice."""
    session_summary: str
    total_questions: int
    correct_count: int
    score_percentage: float
    strengths: list[str]
    areas_to_improve: list[str]
    recommendations: list[str]
    pattern_analysis: str
    encouraging_message: str
    next_topic_suggestion: Optional[str] = None


# Simple in-memory storage for demo (replace with Redis in production)
_active_questions: dict[str, dict] = {}

# Track recent questions per student to avoid repetition (stores last 5 question texts)
_recent_questions: dict[str, list[str]] = {}
MAX_RECENT_QUESTIONS = 5

# Track session answers per student for session feedback
_session_answers: dict[str, list[dict]] = {}  # {user_id: [{question, answer, correct_answer, is_correct}]}

# BATCH PRE-FETCHING: Question queue per user/subtopic
# Key: "{user_id}_{subtopic_id}", Value: list of pre-generated question dicts
_question_queue: dict[str, list[dict]] = {}
BATCH_SIZE = 5  # Generate 5 questions at once (10 was timing out)
REFILL_THRESHOLD = 2  # Refill when queue drops to 2


@router.post("/start", response_model=QuestionResponse)
async def start_practice(
    request: StartPracticeRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Start a practice session and generate an AI question.
    """
    import uuid
    
    # Find the subtopic to practice
    subtopic = None
    topic = None
    subject = None
    
    if request.subtopic_id:
        result = await db.execute(
            select(Subtopic).where(Subtopic.id == request.subtopic_id)
        )
        subtopic = result.scalar_one_or_none()
        if subtopic:
            result = await db.execute(select(Topic).where(Topic.id == subtopic.topic_id))
            topic = result.scalar_one_or_none()
            if topic:
                result = await db.execute(select(Subject).where(Subject.id == topic.subject_id))
                subject = result.scalar_one_or_none()
    
    elif request.topic_slug:
        result = await db.execute(
            select(Topic).where(Topic.slug == request.topic_slug)
        )
        topic = result.scalar_one_or_none()
        if topic:
            result = await db.execute(select(Subject).where(Subject.id == topic.subject_id))
            subject = result.scalar_one_or_none()
            # Get first subtopic
            result = await db.execute(
                select(Subtopic)
                .where(Subtopic.topic_id == topic.id, Subtopic.is_active == True)
                .order_by(Subtopic.display_order)
                .limit(1)
            )
            subtopic = result.scalar_one_or_none()
    
    elif request.subject_slug:
        result = await db.execute(
            select(Subject).where(Subject.slug == request.subject_slug)
        )
        subject = result.scalar_one_or_none()
        if subject:
            # Get first topic
            result = await db.execute(
                select(Topic)
                .where(Topic.subject_id == subject.id, Topic.is_active == True)
                .order_by(Topic.display_order)
                .limit(1)
            )
            topic = result.scalar_one_or_none()
            if topic:
                result = await db.execute(
                    select(Subtopic)
                    .where(Subtopic.topic_id == topic.id, Subtopic.is_active == True)
                    .order_by(Subtopic.display_order)
                    .limit(1)
                )
                subtopic = result.scalar_one_or_none()
    
    if not all([subject, topic, subtopic]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find content to practice. Please select a valid subject, topic, or subtopic."
        )
    
    # Generate question using AI (or fallback to mock)
    question_id = str(uuid.uuid4())
    
    # Get user's recent questions for duplicate checking
    user_id = str(current_user.id)
    recent_questions = _recent_questions.get(user_id, [])
    
    # Try to generate with AI first
    MAX_RETRIES = 3
    question_data = None
    difficulty_str = subtopic.difficulty.value if hasattr(subtopic.difficulty, 'value') else str(subtopic.difficulty)
    
    # Try AI generation using BATCH PRE-FETCHING
    if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
        try:
            from app.ai.agents.examiner import examiner_agent as question_generator
            
            # Build queue key
            queue_key = f"{user_id}_{subtopic.id}"
            
            # Check if we have questions in queue
            if queue_key not in _question_queue or len(_question_queue[queue_key]) == 0:
                # Generate a BATCH of 10 questions at once!
                print(f"🚀 Generating batch of {BATCH_SIZE} questions for: {subject.name} > {topic.name} > {subtopic.name}")
                
                # Build topic distribution for batch
                topic_distribution = [(topic.name, subtopic.name, BATCH_SIZE)]
                
                # Generate all 10 questions in ONE call
                batch = await question_generator.generate_batch(
                    subject=subject.name,
                    topic_distribution=topic_distribution,
                    difficulty_distribution=[difficulty_str] * BATCH_SIZE,
                    grade=topic.grade_level or 1,
                    session_id=f"practice_{user_id}_{subtopic.id}"
                )
                
                # Convert to queue format
                _question_queue[queue_key] = []
                for gen in batch:
                    _question_queue[queue_key].append({
                        "question": gen.question,
                        "answer": gen.answer,
                        "correct_answers": gen.correct_answers,
                        "options": gen.options or [],
                        "hint": gen.hint,
                        "explanation": gen.explanation,
                        "subject": subject.name,
                        "topic": topic.name,
                        "subtopic": subtopic.name,
                        "subtopic_id": subtopic.id,
                        "difficulty": difficulty_str,
                        "question_type": gen.question_type or "multiple_choice",
                    })
                
                print(f"✅ Generated {len(_question_queue[queue_key])} questions, ready to serve!")
            
            # Pop a question from queue
            if _question_queue[queue_key]:
                question_data = _question_queue[queue_key].pop(0)
                print(f"📋 Serving from queue ({len(_question_queue[queue_key])} remaining): {question_data['question'][:50]}...")
                
                # Check if we need to refill (background refill when low)
                if len(_question_queue[queue_key]) <= REFILL_THRESHOLD:
                    print(f"⚠️ Queue low ({len(_question_queue[queue_key])} left), will refill on next request")
            
        except Exception as e:
            print(f"⚠️ Batch generation failed: {e}, will fallback to mock questions")
    
    # Fallback to mock questions if AI failed or no API key
    if question_data is None:
        import random
        
        print(f"📚 Using mock question pool for: {subject.name}")
        
        # Expanded pool of mock questions
        mock_question_pools = {
            "Mathematics": {
                "easy": [
                    {"q": "What is 2 + 3?", "a": "5", "hint": "Count on your fingers!"},
                    {"q": "What is 4 + 2?", "a": "6", "hint": "Count up from 4"},
                    {"q": "What is 5 - 2?", "a": "3", "hint": "Take 2 away from 5"},
                    {"q": "What is 3 + 4?", "a": "7", "hint": "Count 3, then 4 more"},
                    {"q": "What is 1 + 1?", "a": "2", "hint": "One plus one equals..."},
                    {"q": "What is 6 - 3?", "a": "3", "hint": "Half of 6"},
                    {"q": "What is 2 + 2?", "a": "4", "hint": "Two pairs make..."},
                    {"q": "What is 5 + 1?", "a": "6", "hint": "Add one to 5"},
                    {"q": "What is 8 - 4?", "a": "4", "hint": "Half of 8"},
                    {"q": "What is 3 + 3?", "a": "6", "hint": "Double of 3"},
                ],
                "medium": [
                    {"q": "What is 7 × 8?", "a": "56", "hint": "Think of 7 groups of 8"},
                    {"q": "What is 9 × 6?", "a": "54", "hint": "9 times 6"},
                    {"q": "What is 12 × 5?", "a": "60", "hint": "12 groups of 5"},
                    {"q": "What is 24 ÷ 6?", "a": "4", "hint": "How many 6s in 24?"},
                    {"q": "What is 8 × 7?", "a": "56", "hint": "8 groups of 7"},
                    {"q": "What is 36 ÷ 9?", "a": "4", "hint": "9 times what is 36?"},
                    {"q": "What is 15 + 27?", "a": "42", "hint": "Add 15 and 27"},
                    {"q": "What is 50 - 18?", "a": "32", "hint": "Subtract 18 from 50"},
                ],
                "hard": [
                    {"q": "What is 144 ÷ 12?", "a": "12", "hint": "12 × 12 = 144"},
                    {"q": "What is 15 × 15?", "a": "225", "hint": "15 squared"},
                    {"q": "What is 256 ÷ 16?", "a": "16", "hint": "16 × 16 = 256"},
                    {"q": "What is 13 × 12?", "a": "156", "hint": "13 groups of 12"},
                    {"q": "What is 225 ÷ 15?", "a": "15", "hint": "Square root of 225"},
                    {"q": "What is 18 × 11?", "a": "198", "hint": "18 times 11"},
                ],
            },
            "English": {
                "easy": [
                    {"q": "What letter comes after 'A'?", "a": "B", "hint": "A, B, C..."},
                    {"q": "What letter comes before 'D'?", "a": "C", "hint": "A, B, C, D"},
                    {"q": "How many vowels are in 'apple'?", "a": "2", "hint": "Vowels are A, E, I, O, U"},
                    {"q": "Which word rhymes with 'cat'?", "a": "hat", "hint": "Think of things that sound like 'cat'"},
                    {"q": "What is the first letter of 'dog'?", "a": "D", "hint": "D-O-G"},
                    {"q": "How many letters in 'sun'?", "a": "3", "hint": "S-U-N"},
                ],
                "medium": [
                    {"q": "What is the opposite of 'happy'?", "a": "sad", "hint": "How do you feel when you're not happy?"},
                    {"q": "What is the plural of 'child'?", "a": "children", "hint": "More than one child"},
                    {"q": "What is the past tense of 'run'?", "a": "ran", "hint": "Yesterday I ___"},
                    {"q": "What is the opposite of 'hot'?", "a": "cold", "hint": "Winter is..."},
                    {"q": "What is the opposite of 'big'?", "a": "small", "hint": "An ant is..."},
                    {"q": "Complete: 'She ___ to school yesterday.'", "a": "went", "hint": "Past tense of 'go'"},
                ],
                "hard": [
                    {"q": "What is a word that means the same as 'big'?", "a": "large", "hint": "Another way to say big"},
                    {"q": "What is the noun in: 'The cat sleeps'?", "a": "cat", "hint": "A noun is a person, place, or thing"},
                    {"q": "What is the verb in: 'She runs fast'?", "a": "runs", "hint": "A verb is an action word"},
                    {"q": "What is the antonym of 'brave'?", "a": "cowardly", "hint": "Opposite of courageous"},
                    {"q": "Which word is an adjective: 'The quick fox'?", "a": "quick", "hint": "Adjectives describe nouns"},
                ],
            },
            "Science": {
                "easy": [
                    {"q": "What do plants need to grow?", "a": "water", "hint": "Plants get thirsty too!"},
                    {"q": "What is the closest star to Earth?", "a": "Sun", "hint": "It's very bright in the sky"},
                    {"q": "How many legs does a spider have?", "a": "8", "hint": "More than 6"},
                    {"q": "What do we breathe?", "a": "air", "hint": "It's all around us"},
                    {"q": "What color is grass?", "a": "green", "hint": "Parks are full of it"},
                ],
                "medium": [
                    {"q": "What planet is known as the Red Planet?", "a": "Mars", "hint": "Named after the god of war"},
                    {"q": "What is the largest organ in the human body?", "a": "skin", "hint": "It covers your whole body"},
                    {"q": "What gas do plants produce?", "a": "oxygen", "hint": "What we breathe in"},
                    {"q": "How many bones in the human body?", "a": "206", "hint": "More than 200"},
                    {"q": "What is H2O commonly known as?", "a": "water", "hint": "You drink it"},
                ],
                "hard": [
                    {"q": "What is the powerhouse of the cell?", "a": "mitochondria", "hint": "It produces energy"},
                    {"q": "What element has the symbol 'Fe'?", "a": "iron", "hint": "It's magnetic"},
                    {"q": "What is the speed of light (approx)?", "a": "300000 km/s", "hint": "Very fast!"},
                    {"q": "What is the process plants use to make food?", "a": "photosynthesis", "hint": "Uses sunlight"},
                ],
            }
        }
        
        # Get question pool for subject
        subject_pools = mock_question_pools.get(subject.name, mock_question_pools["Mathematics"])
        difficulty_pool = subject_pools.get(difficulty_str, subject_pools["easy"])
        
        # Filter out recently asked questions
        available_questions = [q for q in difficulty_pool if q["q"] not in recent_questions]
        
        # If all questions were recently asked, use full pool
        if not available_questions:
            available_questions = difficulty_pool
            print("⚠️ All mock questions were recently asked, reusing pool")
        else:
            print(f"✅ {len(available_questions)} fresh mock questions available")
        
        # Randomly select a question from available pool
        mock = random.choice(available_questions)
        
        # Generate options for the mock question
        correct_ans = mock["a"]
        mock_options = [correct_ans]
        
        # Add distractors based on subject
        if subject.name == "Mathematics":
            # For math, generate plausible wrong answers
            try:
                correct_num = int(correct_ans)
                mock_options.extend([str(correct_num + 1), str(correct_num - 1), str(correct_num + 2)])
            except:
                mock_options.extend(["4", "7", "10"])  # Fallback
        elif subject.name == "English":
            # For English, add plausible alternatives
            if "letter" in mock["q"].lower():
                mock_options.extend(["A", "E", "Z"])
            else:
                mock_options.extend(["word", "letter", "sentence"])
        else:
            mock_options.extend(["Option A", "Option B", "Option C"])
        
        # Ensure we have exactly 4 unique options
        mock_options = list(dict.fromkeys(mock_options))[:4]
        while len(mock_options) < 4:
            mock_options.append(f"Option {len(mock_options) + 1}")
        
        question_data = {
            "question": mock["q"],
            "answer": mock["a"],
            "correct_answers": [mock["a"]],  # For multi-select compatibility
            "options": mock_options,
            "hint": mock["hint"],
            "explanation": f"The correct answer is {mock['a']}.",
            "subject": subject.name,
            "topic": topic.name,
            "subtopic": subtopic.name,
            "subtopic_id": subtopic.id,
            "difficulty": difficulty_str,
            "question_type": "multiple_choice",
        }
    
    # ============================================================
    # SHUFFLE OPTIONS so correct answer isn't always first
    # ============================================================
    import random as rnd
    
    options = question_data.get("options", [])
    if options and len(options) > 1:
        # Shuffle the options randomly
        shuffled_options = options.copy()
        rnd.shuffle(shuffled_options)
        question_data["options"] = shuffled_options
        print(f"🔀 Shuffled options: {shuffled_options}")
    
    # ============================================================
    # TRACK RECENT QUESTIONS to avoid repetition in future
    # ============================================================
    question_text = question_data["question"]
    
    # Add to recent questions list
    if user_id in _recent_questions:
        _recent_questions[user_id].append(question_text)
        # Keep only last N questions
        if len(_recent_questions[user_id]) > MAX_RECENT_QUESTIONS:
            _recent_questions[user_id].pop(0)
    else:
        _recent_questions[user_id] = [question_text]
    
    print(f"📝 Recent questions for user: {len(_recent_questions[user_id])} tracked")
    
    # Store for answer validation
    _active_questions[question_id] = question_data
    
    return QuestionResponse(
        question_id=question_id,
        question=question_data["question"],
        question_type="multiple_choice",
        options=question_data.get("options"),
        hint=question_data["hint"],
        subject=question_data["subject"],
        topic=question_data["topic"],
        subtopic=question_data["subtopic"],
        difficulty=question_data["difficulty"],
    )


@router.post("/answer", response_model=AnswerFeedback)
async def submit_answer(
    request: AnswerRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Submit an answer and get AI-powered feedback.
    """
    from datetime import datetime, timezone
    from app.models.curriculum import Progress, Subtopic
    from app.models.user import Student, UserRole
    
    question_data = _active_questions.get(request.question_id)
    
    if not question_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found. It may have expired."
        )
    
    correct_answer = question_data["answer"]
    
    # Handle multi-select answer matching
    if isinstance(request.answer, list):
        user_answer_set = {str(a).strip().lower() for a in request.answer}
    else:
        user_answer_set = {str(request.answer).strip().lower()}

    # Get correct answers (support both new list format and legacy string format)
    if "correct_answers" in question_data and question_data["correct_answers"]:
        correct_answer_set = {str(a).strip().lower() for a in question_data["correct_answers"]}
    else:
        correct_answer_set = {str(correct_answer).strip().lower()}
    
    # Check for correctness (Set equality for multi-select, or inclusion for single custom answers)
    is_correct = user_answer_set == correct_answer_set
    
    # Fallback for single open-ended string answers (fuzzy match)
    if not is_correct and len(user_answer_set) == 1 and len(correct_answer_set) == 1:
        u_val = list(user_answer_set)[0]
        c_val = list(correct_answer_set)[0]
        if c_val in u_val:  # Lenient check e.g. "5" in "it is 5"
            is_correct = True
    
    # AI Evaluation result placeholder
    evaluation_result = None
    
    # Try AI evaluation
    try:
        if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
            from app.ai.agents.grader import answer_evaluator  # BaseAgent-compliant alias
            
            evaluation = await answer_evaluator.evaluate(
                question=question_data["question"],
                correct_answer=correct_answer,
                student_answer=request.answer,
                subject=question_data["subject"],
                topic=question_data["topic"],
                grade=2,  # Default grade
            )
            evaluation_result = evaluation
            is_correct = evaluation.is_correct
    except Exception as e:
        print(f"AI evaluation failed, using simple check: {e}")
    
    # Determine feedback and score
    if evaluation_result:
        feedback = evaluation_result.feedback
        score = evaluation_result.score
        explanation = evaluation_result.detailed_explanation
        hint_for_retry = evaluation_result.hint_for_retry
    else:
        if is_correct:
            feedback = "🎉 Excellent work! You got it right!"
            score = 1.0
            explanation = question_data["explanation"]
        else:
            feedback = "Not quite, but great effort! Keep trying!"
            score = 0.0
            explanation = question_data["explanation"]
        hint_for_retry = question_data["hint"] if not is_correct else None

    # --- PROGRESS TRACKING ---
    try:
        # 1. Get or Create Student Profile
        # For simple MVP, we treat the current user as the parent and find/create a default child profile
        result = await db.execute(select(Student).where(Student.parent_id == current_user.id))
        student = result.scalars().first()
        
        if not student:
            # Create default student profile if none exists
            student = Student(
                parent_id=current_user.id,
                first_name="My Student",
                last_name=current_user.last_name,
                grade_level=2
            )
            db.add(student)
            await db.flush() # Get ID
            
        # 2. Update Progress if we have subtopic_id
        if "subtopic_id" in question_data:
            subtopic_id = question_data["subtopic_id"]
            
            # Fetch existing progress
            result = await db.execute(
                select(Progress).where(
                    Progress.student_id == student.id,
                    Progress.subtopic_id == subtopic_id
                )
            )
            progress = result.scalars().first()
            
            if not progress:
                progress = Progress(
                    student_id=student.id,
                    subtopic_id=subtopic_id,
                    questions_attempted=0,
                    questions_correct=0,
                    current_streak=0,
                    best_streak=0,
                    mastery_level=0.0
                )
                db.add(progress)
            
            # Update stats
            progress.questions_attempted += 1
            progress.last_practiced_at = datetime.now(timezone.utc)
            
            if is_correct:
                progress.questions_correct += 1
                progress.current_streak += 1
                if progress.current_streak > progress.best_streak:
                    progress.best_streak = progress.current_streak
            else:
                progress.current_streak = 0
            
            # Calculate mastery (simple version)
            # 5 continuous correct answers = 100% mastery for this session context
            # Or just raw accuracy
            if progress.questions_attempted > 0:
                progress.mastery_level = round(progress.questions_correct / progress.questions_attempted, 2)
            
            await db.commit()
            
            # Award XP for practice answer
            try:
                from app.services.gamification import GamificationService
                gamification = GamificationService(db)
                if is_correct:
                    await gamification.award_xp(student.id, "question_correct")  # +10 XP
                else:
                    await gamification.award_xp(student.id, "question_incorrect")  # +2 XP
                await gamification.update_streak(student.id)
            except Exception as gam_err:
                print(f"Gamification error (non-critical): {gam_err}")
            
    except Exception as e:
        print(f"Failed to track progress: {e}")
        # Don't fail the request if progress tracking fails
    
    # Track session answer for end-of-session feedback
    user_id = str(current_user.id)
    if user_id not in _session_answers:
        _session_answers[user_id] = []
    
    _session_answers[user_id].append({
        "question": question_data["question"],
        "answer": request.answer,
        "correct_answer": correct_answer,
        "is_correct": is_correct,
        "subject": question_data.get("subject", ""),
        "subtopic": question_data.get("subtopic", "")
    })
    
    # Clean up
    del _active_questions[request.question_id]
    
    return AnswerFeedback(
        is_correct=is_correct,
        score=score,
        feedback=feedback,
        explanation=explanation,
        correct_answer=correct_answer,
        hint_for_retry=hint_for_retry,
    )


@router.post("/end-session", response_model=PracticeSessionFeedback)
async def end_session(
    current_user: CurrentUser,
    db: DbSession,
):
    """
    End practice session and get AI-powered feedback summary.
    Call this when user exits practice mode or explicitly ends session.
    """
    user_id = str(current_user.id)
    
    # Get session answers
    session_answers = _session_answers.get(user_id, [])
    
    if not session_answers:
        return PracticeSessionFeedback(
            session_summary="No questions answered in this session.",
            total_questions=0,
            correct_count=0,
            score_percentage=0,
            strengths=["You started a practice session!"],
            areas_to_improve=["Try answering some questions next time"],
            recommendations=["Start with easy questions to build confidence"],
            pattern_analysis="No data yet - complete some questions to see patterns.",
            encouraging_message="Ready to start learning? Let's go! 🚀"
        )
    
    # Calculate stats
    total_questions = len(session_answers)
    correct_count = sum(1 for a in session_answers if a["is_correct"])
    score = (correct_count / total_questions) * 100
    
    # Build questions detail for AI
    questions_detail = "\n\n".join([
        f"Q: {a['question']}\nStudent Answer: {a['answer']}\nCorrect Answer: {a['correct_answer']}\nResult: {'✅ Correct' if a['is_correct'] else '❌ Incorrect'}"
        for a in session_answers
    ])
    
    # Get subject/subtopic from answers
    subject = session_answers[0].get("subject", "Practice") if session_answers else "Practice"
    subtopic = session_answers[0].get("subtopic", "General") if session_answers else "General"
    
    # Get student grade
    from sqlalchemy import select
    from app.models.user import Student
    result = await db.execute(select(Student).where(Student.parent_id == current_user.id))
    student = result.scalars().first()
    grade = student.grade_level if student else 1
    
    try:
        # Generate AI feedback
        feedback_result = await feedback_agent.generate_feedback(
            feedback_type=FeedbackType.PRACTICE,
            subject=subject,
            topic=subtopic,
            score=score,
            correct=correct_count,
            total=total_questions,
            questions_detail=questions_detail,
            grade=grade
        )
        
        response = PracticeSessionFeedback(
            session_summary=feedback_result.overall_interpretation,
            total_questions=total_questions,
            correct_count=correct_count,
            score_percentage=round(score, 1),
            strengths=feedback_result.strengths,
            areas_to_improve=feedback_result.areas_to_improve,
            recommendations=feedback_result.specific_recommendations,
            pattern_analysis=feedback_result.pattern_analysis,
            encouraging_message=feedback_result.encouraging_message,
            next_topic_suggestion=feedback_result.next_steps
        )
    except Exception as e:
        print(f"Error generating practice feedback: {e}")
        # Fallback feedback
        response = PracticeSessionFeedback(
            session_summary=f"You completed {total_questions} questions and got {correct_count} correct ({round(score)}%)!",
            total_questions=total_questions,
            correct_count=correct_count,
            score_percentage=round(score, 1),
            strengths=[f"You answered {total_questions} questions!", f"You got {correct_count} correct!"],
            areas_to_improve=["Keep practicing to improve your score"] if score < 100 else ["Great job!"],
            recommendations=["Practice a little each day", "Review the questions you missed"],
            pattern_analysis="Complete more sessions to see patterns.",
            encouraging_message="Great practice session! Keep it up! 🌟"
        )
    
    # Clear session answers after generating feedback
    _session_answers[user_id] = []
    
    return response
