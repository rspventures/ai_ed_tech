"""
AI Tutor Platform - Grader Agent
Evaluates student answers with detailed, encouraging feedback.
Refactored from answer_evaluator.py to use Agentic Architecture.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass

from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.ai.core.telemetry import get_tracer


@dataclass
class EvaluationResult:
    """Schema for answer evaluation results."""
    is_correct: bool
    score: float
    feedback: str
    detailed_explanation: str
    hint_for_retry: Optional[str] = None
    common_mistake: Optional[str] = None


class GraderAgent(BaseAgent):
    """
    The Grader Agent ✅
    
    Evaluates student answers with:
    - Correctness assessment
    - Encouraging feedback
    - Detailed explanations
    - Hints for retry
    
    Uses the Plan-Execute pattern:
    - Plan: Analyze the question and answers
    - Execute: Generate evaluation via LLM
    """
    
    name = "GraderAgent"
    description = "Evaluates student answers with encouraging feedback"
    version = "2.0.0"
    
    SYSTEM_PROMPT = """You are a kind and encouraging elementary school teacher evaluating 
a student's answer. Always be positive and supportive, even when the answer is incorrect.

Student Information:
- Grade: {grade}
- Subject: {subject}
- Topic: {topic}

Question: {question}
Correct Answer: {correct_answer}
Student's Answer: {student_answer}

Evaluate the student's answer and provide:
1. Whether it's correct (consider partial credit for close answers)
2. A score from 0.0 to 1.0
3. Encouraging feedback appropriate for a grade {grade} student
4. A detailed explanation they can learn from
5. If incorrect, a hint to help them try again
6. If incorrect, explain the common mistake they might have made

Be encouraging! Use positive language and celebrate effort.

Respond with ONLY this JSON (no markdown):
{{
    "is_correct": true or false,
    "score": 0.0 to 1.0,
    "feedback": "Encouraging feedback for the student",
    "detailed_explanation": "Explanation of the correct answer",
    "hint_for_retry": "Hint if incorrect, null if correct",
    "common_mistake": "Common mistake explanation if incorrect, null if correct"
}}"""

    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """
        Plan the evaluation.
        
        Validates input and prepares evaluation parameters.
        """
        metadata = context.metadata
        
        return {
            "action": "evaluate_answer",
            "params": {
                "question": metadata.get("question", ""),
                "correct_answer": metadata.get("correct_answer", ""),
                "student_answer": metadata.get("student_answer", ""),
                "subject": metadata.get("subject", "General"),
                "topic": metadata.get("topic", ""),
                "grade": metadata.get("grade", 1),
            }
        }
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """
        Execute the answer evaluation.
        """
        tracer = get_tracer()
        
        with tracer.start_as_current_span("evaluate_answer") as span:
            try:
                params = plan["params"]
                
                span.set_attribute("evaluation.subject", params["subject"])
                span.set_attribute("evaluation.topic", params["topic"])
                
                # Evaluate via LLM
                response = await self.llm.generate_json(
                    prompt="Evaluate the student's answer now.",
                    system_prompt=self.SYSTEM_PROMPT,
                    context=params,
                    agent_name=self.name,
                )
                
                # Create result object
                result = EvaluationResult(
                    is_correct=response.get("is_correct", False),
                    score=float(response.get("score", 0.0)),
                    feedback=response.get("feedback", ""),
                    detailed_explanation=response.get("detailed_explanation", ""),
                    hint_for_retry=response.get("hint_for_retry"),
                    common_mistake=response.get("common_mistake"),
                )
                
                span.set_attribute("evaluation.is_correct", result.is_correct)
                span.set_attribute("evaluation.score", result.score)
                
                return AgentResult(
                    success=True,
                    output=result,
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
    
    async def evaluate(
        self,
        question: str,
        correct_answer: str,
        student_answer: str,
        subject: str,
        topic: str,
        grade: int,
    ) -> EvaluationResult:
        """
        Convenience method matching the old API.
        
        This provides backward compatibility with existing code.
        """
        result = await self.run(
            user_input=f"Evaluate answer: {student_answer}",
            metadata={
                "question": question,
                "correct_answer": correct_answer,
                "student_answer": student_answer,
                "subject": subject,
                "topic": topic,
                "grade": grade,
            }
        )
        
        if result.success:
            return result.output
        else:
            raise Exception(result.error or "Failed to evaluate answer")


# Singleton instance for backward compatibility
grader_agent = GraderAgent()

# Alias for backward compatibility with old imports
answer_evaluator = grader_agent
