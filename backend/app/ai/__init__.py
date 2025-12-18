"""
AI Tutor Platform - AI Module Initialization
Exports both legacy modules and new Agentic Architecture components.
"""

# =============================================================================
# NEW AGENTIC ARCHITECTURE (Recommended)
# =============================================================================
from app.ai.agents import (
    BaseAgent,
    AgentContext,
    AgentResult,
    AgentState,
    ExaminerAgent,
    GraderAgent,
    TutorAgent,
    LessonAgent,
    AnalyzerAgent,
    GamificationAgent,
    ReviewerAgent,
    ValidatorAgent,
    examiner_agent,
    grader_agent,
    tutor_agent,
    lesson_agent,
    analyzer_agent,
    gamification_agent,
    reviewer_agent,
    validator_agent,
)
from app.ai.agents.examiner import GeneratedQuestion, QuestionDifficulty
from app.ai.agents.grader import EvaluationResult
from app.ai.agents.lesson import LessonContent
from app.ai.agents.analyzer import AssessmentFeedback
from app.ai.agents.gamification import EffortAnalysis
from app.ai.agents.reviewer import ReviewItem
from app.ai.agents.validator import ValidationResult

# Core modules
from app.ai.core.llm import LLMClient, LLMResponse, get_llm_client
from app.ai.core.telemetry import init_telemetry, get_tracer, traced, agent_span
from app.ai.core.guardrails import (
    InputGuardrails,
    OutputGuardrails,
    validate_agent_input,
    validate_agent_output,
)
from app.ai.core.memory import AgentMemory

# =============================================================================
# LEGACY COMPATIBILITY LAYER
# These imports maintain backward compatibility with existing code.
# =============================================================================
from app.ai.question_generator import QuestionGenerator, question_generator
from app.ai.answer_evaluator import AnswerEvaluator, answer_evaluator
from app.ai.tutor_chat import TutorChatAgent, tutor_chat
from app.ai.lesson_generator import LessonGenerator, lesson_generator
from app.ai.assessment_analyzer import AssessmentAnalyzer, assessment_analyzer
from app.ai.review_agent import ReviewAgent, review_agent

__all__ = [
    # New Agents
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    "AgentState",
    "ExaminerAgent",
    "GraderAgent",
    "TutorAgent",
    "LessonAgent",
    "AnalyzerAgent",
    "GamificationAgent",
    "ReviewerAgent",
    "ValidatorAgent",
    
    # Agent Instances
    "examiner_agent",
    "grader_agent",
    "tutor_agent",
    "lesson_agent",
    "analyzer_agent",
    "gamification_agent",
    "reviewer_agent",
    "validator_agent",
    
    # Core
    "LLMClient",
    "LLMResponse",
    "get_llm_client",
    "AgentMemory",
    
    # Telemetry
    "init_telemetry",
    "get_tracer",
    "traced",
    "agent_span",
    
    # Guardrails
    "InputGuardrails",
    "OutputGuardrails",
    "validate_agent_input",
    "validate_agent_output",
    
    # Data Classes
    "GeneratedQuestion",
    "QuestionDifficulty",
    "EvaluationResult",
    "LessonContent",
    "AssessmentFeedback",
    "EffortAnalysis",
    "ReviewItem",
    "ValidationResult",
    
    # Legacy (backward compatibility)
    "QuestionGenerator",
    "question_generator",
    "AnswerEvaluator",
    "answer_evaluator",
    "TutorChatAgent",
    "tutor_chat",
    "LessonGenerator",
    "lesson_generator",
    "AssessmentAnalyzer",
    "assessment_analyzer",
    "ReviewAgent",
    "review_agent",
]
