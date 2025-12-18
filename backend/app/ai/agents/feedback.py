"""
AI Tutor Platform - Feedback Agent
Unified AI-powered feedback generation for all assessment types.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.ai.core.telemetry import get_tracer


class FeedbackType(str, Enum):
    """Types of assessments that can receive feedback."""
    EXAM = "exam"
    TEST = "test"
    ASSESSMENT = "assessment"
    PRACTICE = "practice"


@dataclass
class TopicInsight:
    """Insight for a specific topic in an exam."""
    topic_name: str
    score_percentage: float
    status: str  # "excellent", "good", "needs_work"
    insight: str


@dataclass
class FeedbackResult:
    """Unified feedback structure for all assessment types."""
    overall_interpretation: str
    strengths: List[str]
    areas_to_improve: List[str]
    specific_recommendations: List[str]
    practice_activities: List[str]
    pattern_analysis: str
    encouraging_message: str
    topic_insights: Optional[List[TopicInsight]] = None
    next_steps: Optional[str] = None


class FeedbackAgent(BaseAgent):
    """
    Generate rich, AI-powered feedback for all assessment types.
    
    This agent analyzes actual Q&A data to provide:
    - Personalized score interpretation
    - Pattern detection in mistakes
    - Age-appropriate recommendations
    - Fun practice activities
    """
    
    SYSTEM_PROMPT = """You are a warm, encouraging elementary school teacher providing feedback 
to a young student about their learning assessment. Your feedback should be:

- Age-appropriate and easy to understand (for grade {grade} student)
- Encouraging and positive, even when scores are low
- Specific and actionable (not generic advice)
- Fun and engaging (make learning exciting!)
- Based on actual patterns in the student's answers

Always find something positive to say, and present areas for improvement as exciting 
opportunities to learn more. Use simple words and short sentences. Be like a supportive 
friend who believes in the student! Use emojis sparingly but appropriately (1-2 per section)."""

    FEEDBACK_PROMPT = """Analyze this {assessment_type} result and provide detailed feedback.

📊 Assessment Details:
- Type: {assessment_type}
- Subject: {subject}
- Topic(s): {topic}
- Score: {score}% ({correct}/{total} correct)
- Grade Level: {grade}

{topic_breakdown_section}

📝 Questions & Answers:
{questions_detail}

Based on the above, provide feedback with:
1. overall_interpretation: Brief, encouraging score interpretation (1-2 sentences)
2. strengths: List of 2-3 specific things the student did well
3. areas_to_improve: List of 2-3 areas needing work (phrase positively!)
4. specific_recommendations: List of 3-4 actionable study tips
5. practice_activities: List of 2-3 fun practice exercises or games
6. pattern_analysis: Brief analysis of any patterns in mistakes (1-2 sentences)
7. encouraging_message: Warm, motivating closing message (1 sentence with emoji)
{extra_instructions}

Return as JSON object with these exact keys."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "FeedbackAgent"
    
    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """Plan feedback generation based on assessment type."""
        metadata = context.metadata or {}
        
        return {
            "feedback_type": metadata.get("feedback_type", FeedbackType.ASSESSMENT),
            "subject": metadata.get("subject", ""),
            "topic": metadata.get("topic", ""),
            "score": metadata.get("score", 0),
            "correct": metadata.get("correct", 0),
            "total": metadata.get("total", 0),
            "questions_detail": metadata.get("questions_detail", ""),
            "grade": metadata.get("grade", 1),
            "topic_breakdown": metadata.get("topic_breakdown", []),
        }
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """Execute feedback generation."""
        try:
            feedback_type = plan["feedback_type"]
            subject = plan["subject"]
            topic = plan["topic"]
            score = plan["score"]
            correct = plan["correct"]
            total = plan["total"]
            questions_detail = plan["questions_detail"]
            grade = plan["grade"]
            topic_breakdown = plan.get("topic_breakdown", [])
            
            # Build topic breakdown section if available
            topic_breakdown_section = ""
            if topic_breakdown:
                topic_breakdown_section = "\n📚 Topic Breakdown:\n"
                for tb in topic_breakdown:
                    if hasattr(tb, 'topic_name'):
                        pct = tb.percentage if hasattr(tb, 'percentage') else (tb.correct / tb.total * 100 if tb.total > 0 else 0)
                        status = "✅" if pct >= 80 else "📊" if pct >= 60 else "📚"
                        topic_breakdown_section += f"  {status} {tb.topic_name}: {pct:.0f}%\n"
            
            # Extra instructions based on type
            extra_instructions = ""
            if feedback_type == FeedbackType.EXAM:
                extra_instructions = "8. For each topic, indicate if it's a strength or needs more work."
            elif feedback_type == FeedbackType.PRACTICE:
                extra_instructions = "8. Suggest what to practice next based on patterns."
            
            # Generate via LLM
            response = await self.llm.generate_json(
                prompt=self.FEEDBACK_PROMPT.format(
                    assessment_type=feedback_type.value,
                    subject=subject,
                    topic=topic,
                    score=round(score, 1),
                    correct=correct,
                    total=total,
                    questions_detail=questions_detail[:3000],  # Limit length
                    grade=grade,
                    topic_breakdown_section=topic_breakdown_section,
                    extra_instructions=extra_instructions
                ),
                system_prompt=self.SYSTEM_PROMPT.format(grade=grade),
                context={"assessment_type": feedback_type.value},
                agent_name=self.name
            )
            
            # Build FeedbackResult
            feedback = FeedbackResult(
                overall_interpretation=response.get("overall_interpretation", f"You scored {score}%!"),
                strengths=response.get("strengths", ["You completed the assessment!"]),
                areas_to_improve=response.get("areas_to_improve", ["Keep practicing!"]),
                specific_recommendations=response.get("specific_recommendations", ["Practice daily"]),
                practice_activities=response.get("practice_activities", ["Try practice mode"]),
                pattern_analysis=response.get("pattern_analysis", ""),
                encouraging_message=response.get("encouraging_message", "Keep up the great work! 🌟"),
                next_steps=response.get("next_steps")
            )
            
            return AgentResult(
                success=True,
                output=feedback,
                state=AgentState.COMPLETED
            )
            
        except Exception as e:
            print(f"FeedbackAgent error: {e}")
            # Return fallback
            return AgentResult(
                success=True,  # Still return success with fallback
                output=self._generate_fallback_feedback(
                    plan.get("score", 0),
                    plan.get("correct", 0),
                    plan.get("total", 0),
                    plan.get("topic", ""),
                    plan.get("feedback_type", FeedbackType.ASSESSMENT)
                ),
                state=AgentState.COMPLETED,
                error=str(e)
            )
    
    def _generate_fallback_feedback(
        self,
        score: float,
        correct: int,
        total: int,
        topic: str,
        feedback_type: FeedbackType
    ) -> FeedbackResult:
        """Generate fallback feedback when AI fails."""
        # Score-based interpretation
        if score >= 90:
            interpretation = f"Outstanding! You scored {round(score)}% - amazing work!"
            encouragement = "You're a star learner! Keep shining! ⭐"
        elif score >= 80:
            interpretation = f"Excellent! {round(score)}% shows you really understand this!"
            encouragement = "You're doing fantastic! Keep it up! 🌟"
        elif score >= 70:
            interpretation = f"Good job! You scored {round(score)}%. A bit more practice will help!"
            encouragement = "You're making great progress! 💪"
        elif score >= 60:
            interpretation = f"Nice effort with {round(score)}%! Let's work on the tricky parts."
            encouragement = "Every step forward counts! Keep going! 🚀"
        else:
            interpretation = f"You scored {round(score)}%. Don't worry - learning takes practice!"
            encouragement = "Mistakes help us learn! You've got this! 🌈"
        
        # Generic recommendations
        strengths = [
            f"You completed the entire {feedback_type.value}!",
            f"You got {correct} questions right!" if correct > 0 else "You tried your best!"
        ]
        
        areas = []
        if score < 100:
            areas.append(f"Review the questions you missed on {topic}")
        if score < 80:
            areas.append("Practice similar questions to build confidence")
        if not areas:
            areas = ["Keep practicing to maintain your skills!"]
        
        recommendations = [
            "Practice a little bit every day",
            "Read through explanations for wrong answers",
            "Try the practice mode for more questions"
        ]
        
        activities = [
            f"Do 5 practice questions on {topic}",
            "Quiz a friend or family member on what you learned"
        ]
        
        return FeedbackResult(
            overall_interpretation=interpretation,
            strengths=strengths,
            areas_to_improve=areas,
            specific_recommendations=recommendations,
            practice_activities=activities,
            pattern_analysis="Complete more assessments to see patterns in your learning!",
            encouraging_message=encouragement
        )
    
    async def generate_feedback(
        self,
        feedback_type: FeedbackType,
        subject: str,
        topic: str,
        score: float,
        correct: int,
        total: int,
        questions_detail: str,
        grade: int,
        topic_breakdown: List = None
    ) -> FeedbackResult:
        """
        Convenience method to generate feedback.
        
        Args:
            feedback_type: Type of assessment (exam, test, assessment, practice)
            subject: Subject name
            topic: Topic name(s)
            score: Percentage score (0-100)
            correct: Number of correct answers
            total: Total questions
            questions_detail: Formatted Q&A string for analysis
            grade: Student grade level
            topic_breakdown: Optional list of topic scores (for exams)
        
        Returns:
            FeedbackResult with detailed feedback
        """
        result = await self.run(
            user_input=f"Generate feedback for {feedback_type.value}",
            metadata={
                "feedback_type": feedback_type,
                "subject": subject,
                "topic": topic,
                "score": score,
                "correct": correct,
                "total": total,
                "questions_detail": questions_detail,
                "grade": grade,
                "topic_breakdown": topic_breakdown or []
            }
        )
        
        return result.output


# Singleton instance
feedback_agent = FeedbackAgent()
