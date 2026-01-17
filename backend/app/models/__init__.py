"""AI Tutor Platform - Models initialization."""
from app.models.user import User, Student, RefreshToken, UserRole
from app.models.curriculum import (
    Subject,
    Topic,
    Subtopic,
    Progress,
    DifficultyLevel,
)
from app.models.lesson import GeneratedLesson, StudentLessonProgress
from app.models.assessment import AssessmentResult
from app.models.exam import ExamResult
from app.models.test import TestResult
from app.models.document import (
    UserDocument,
    DocumentChunk,
    GeneratedImage,
    DocumentStatus,
)
from app.models.chat import (
    ChatSession,
    ChatMessage,
    MessageRole,
)


__all__ = [
    # User models
    "User",
    "Student",
    "RefreshToken",
    "UserRole",
    # Curriculum models
    "Subject",
    "Topic",
    "Subtopic",
    "Progress",
    "DifficultyLevel",
    # Lesson models
    "GeneratedLesson",
    "StudentLessonProgress",
    # Assessment, Exam & Test models
    "AssessmentResult",
    "ExamResult",
    "TestResult",
    # Document models (RAG)
    "UserDocument",
    "DocumentChunk",
    "GeneratedImage",
    "DocumentStatus",
    # Chat models
    "ChatSession",
    "ChatMessage",
    "MessageRole",
]


