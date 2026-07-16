# AI Agents Package - Specialized Agents for Educational Tasks
from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.ai.agents.examiner import ExaminerAgent, examiner_agent
from app.ai.agents.grader import GraderAgent, grader_agent
from app.ai.agents.lesson import LessonAgent, lesson_agent
from app.ai.agents.reviewer import ReviewerAgent, reviewer_agent
from app.ai.agents.validator import ValidatorAgent, validator_agent
from app.ai.agents.feedback import FeedbackAgent, feedback_agent, FeedbackType, FeedbackResult
from app.ai.agents.document import DocumentAgent, document_agent, DocumentResult, ChunkResult
from app.ai.agents.rag import RAGAgent, rag_agent, RAGMode, RAGResponse, RetrievedChunk, QuizQuestion
from app.ai.agents.document_validator import (
    DocumentValidatorAgent,
    document_validator_agent,
    ValidationResult,
    GradeMatch
)
from app.ai.agents.image_agent import ImageAgent, image_agent, ImageResult

# Removed in Phase 2 (dormant / never adopted): TutorAgent (chat uses the legacy
# tutor_chat path), AnalyzerAgent (superseded by FeedbackAgent), GamificationAgent
# (services/gamification.py does rule-based XP without it), EntityExtractorAgent
# (Graph RAG deleted).

__all__ = [
    # Base
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    "AgentState",

    # Specialized Agents
    "ExaminerAgent",
    "GraderAgent",
    "LessonAgent",
    "ReviewerAgent",
    "ValidatorAgent",
    "FeedbackAgent",
    "DocumentAgent",
    "RAGAgent",
    "DocumentValidatorAgent",
    "ImageAgent",

    # Singleton Instances
    "examiner_agent",
    "grader_agent",
    "lesson_agent",
    "reviewer_agent",
    "validator_agent",
    "feedback_agent",
    "document_agent",
    "rag_agent",
    "document_validator_agent",
    "image_agent",

    # Feedback Types
    "FeedbackType",
    "FeedbackResult",

    # Document Types
    "DocumentResult",
    "ChunkResult",

    # RAG Types
    "RAGMode",
    "RAGResponse",
    "RetrievedChunk",
    "QuizQuestion",

    # Validation Types
    "ValidationResult",
    "GradeMatch",

    # Image Types
    "ImageResult",
]
