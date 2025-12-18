"""
AI Tutor Platform - Analyzer Agent
Analyzes assessment results with detailed, encouraging feedback.
Refactored from assessment_analyzer.py to use Agentic Architecture.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.ai.core.telemetry import get_tracer


@dataclass
class AssessmentFeedback:
    """Schema for AI-generated assessment feedback."""
    overall_score_interpretation: str
    strengths: List[str]
    areas_of_improvement: List[str]
    ways_to_improve: List[str]
    practical_assignments: List[str]
    encouraging_words: str
    pattern_analysis: str


class AnalyzerAgent(BaseAgent):
    """
    The Analyzer Agent 📊
    
    Analyzes assessment results and provides detailed, 
    grade-appropriate feedback to help students improve.
    
    Uses the Plan-Execute pattern:
    - Plan: Prepare assessment data for analysis
    - Execute: Generate detailed feedback via LLM
    """
    
    name = "AnalyzerAgent"
    description = "Analyzes assessment results with encouraging feedback"
    version = "2.0.0"
    
    SYSTEM_PROMPT = """You are a warm, encouraging elementary school teacher providing feedback 
to a young student (grade {grade}) about their assessment results. Your feedback should be:
- Age-appropriate and easy to understand
- Encouraging and positive, even when scores are low
- Specific and actionable
- Fun and engaging

Student's Assessment Results:
- Subject: {subject}
- Topic: {topic}
- Score: {score}% ({correct}/{total} correct)
- Grade Level: {grade}

Questions and Answers:
{questions_detail}

Based on these results, provide detailed feedback. Look for patterns in what the student 
got right and wrong. Suggest fun, practical ways to improve.

Remember: This is for a young child! Use simple words, be very encouraging, and make 
learning sound fun and exciting. Use emojis sparingly but appropriately.

Respond with ONLY valid JSON:
{{
    "overall_score_interpretation": "A brief, encouraging interpretation of the score",
    "strengths": ["2-3 specific strengths demonstrated"],
    "areas_of_improvement": ["2-3 areas that need work"],
    "ways_to_improve": ["3-4 specific, actionable steps to improve"],
    "practical_assignments": ["2-3 fun practice activities or exercises"],
    "encouraging_words": "A warm, motivating message for the student",
    "pattern_analysis": "Brief analysis of any patterns in mistakes or strengths"
}}"""

    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """
        Plan the assessment analysis.
        """
        metadata = context.metadata
        
        return {
            "action": "analyze_assessment",
            "params": {
                "subject": metadata.get("subject", "General"),
                "topic": metadata.get("topic", ""),
                "score": metadata.get("score", 0),
                "correct": metadata.get("correct", 0),
                "total": metadata.get("total", 0),
                "questions_detail": metadata.get("questions_detail", ""),
                "grade": metadata.get("grade", 1),
            }
        }
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """
        Execute the assessment analysis.
        """
        tracer = get_tracer()
        
        with tracer.start_as_current_span("analyze_assessment") as span:
            try:
                params = plan["params"]
                
                span.set_attribute("analysis.subject", params["subject"])
                span.set_attribute("analysis.score", params["score"])
                span.set_attribute("analysis.total_questions", params["total"])
                
                # Analyze via LLM
                response = await self.llm.generate_json(
                    prompt="Analyze the assessment results now.",
                    system_prompt=self.SYSTEM_PROMPT,
                    context=params,
                    agent_name=self.name,
                )
                
                feedback = AssessmentFeedback(
                    overall_score_interpretation=response.get("overall_score_interpretation", ""),
                    strengths=response.get("strengths", []),
                    areas_of_improvement=response.get("areas_of_improvement", []),
                    ways_to_improve=response.get("ways_to_improve", []),
                    practical_assignments=response.get("practical_assignments", []),
                    encouraging_words=response.get("encouraging_words", ""),
                    pattern_analysis=response.get("pattern_analysis", ""),
                )
                
                span.set_attribute("analysis.strengths_count", len(feedback.strengths))
                
                return AgentResult(
                    success=True,
                    output=feedback,
                    state=AgentState.COMPLETED,
                    metadata={"params": params},
                )
                
            except Exception as e:
                span.record_exception(e)
                return AgentResult(
                    success=False,
                    output=None,
                    state=AgentState.ERROR,
                    error=str(e),
                )
    
    async def analyze(
        self,
        subject: str,
        topic: str,
        score: float,
        correct: int,
        total: int,
        questions_detail: str,
        grade: int = 1,
    ) -> AssessmentFeedback:
        """
        Convenience method matching the old API.
        """
        result = await self.run(
            user_input=f"Analyze assessment: {score}% on {topic}",
            metadata={
                "subject": subject,
                "topic": topic,
                "score": score,
                "correct": correct,
                "total": total,
                "questions_detail": questions_detail,
                "grade": grade,
            }
        )
        
        if result.success:
            return result.output
        else:
            raise Exception(result.error or "Failed to analyze assessment")


# Singleton instance for backward compatibility
analyzer_agent = AnalyzerAgent()

# Alias for backward compatibility
assessment_analyzer = analyzer_agent
