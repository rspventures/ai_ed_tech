"""
AI Tutor Platform - AI Module Initialization
Exports the Agentic Architecture components (plus the still-live tutor_chat).
"""

# =============================================================================
# AGENTIC ARCHITECTURE
# =============================================================================
from app.ai.agents import (
    BaseAgent,
    AgentContext,
    AgentResult,
    AgentState,
    ExaminerAgent,
    GraderAgent,
    LessonAgent,
    ReviewerAgent,
    ValidatorAgent,
    examiner_agent,
    grader_agent,
    lesson_agent,
    reviewer_agent,
    validator_agent,
)
from app.ai.agents.examiner import GeneratedQuestion, QuestionDifficulty
from app.ai.agents.grader import EvaluationResult
from app.ai.agents.lesson import LessonContent
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

# Still-live legacy chat path (replaced by the LangGraph tutor agent later in
# Phase 2). Other legacy generator modules were deleted in the Phase 2 subtraction.
from app.ai.tutor_chat import TutorChatAgent, tutor_chat

__all__ = [
    # Agents
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    "AgentState",
    "ExaminerAgent",
    "GraderAgent",
    "LessonAgent",
    "ReviewerAgent",
    "ValidatorAgent",

    # Agent Instances
    "examiner_agent",
    "grader_agent",
    "lesson_agent",
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
    "ReviewItem",
    "ValidationResult",

    # Live chat path
    "TutorChatAgent",
    "tutor_chat",
]
