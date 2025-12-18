"""
AI Tutor Platform - Test Result Model
Stores results from Topic-level tests (10 questions from subtopics within a topic)
"""
from datetime import datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Column, ForeignKey, Integer, Float, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import Student
    from app.models.curriculum import Topic


class TestResult(Base):
    """
    Topic-level test result.
    
    Tests draw 10 questions from all subtopics within a topic.
    Provides per-question AI explanations for wrong answers.
    """
    __tablename__ = "test_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=False)
    
    # Score data
    score = Column(Float, nullable=False)  # Percentage
    total_questions = Column(Integer, default=10)
    correct_questions = Column(Integer, default=0)
    
    # Timing
    duration_seconds = Column(Integer, nullable=True)
    time_limit_seconds = Column(Integer, nullable=True)  # If timed
    completed_at = Column(DateTime, default=datetime.utcnow)
    
    # Detailed breakdown (JSON)
    # Format: [{ question, student_answer, correct_answer, is_correct, explanation }]
    details = Column(JSON, nullable=True)
    
    # AI feedback (JSON)
    # Format: { summary, strengths, weaknesses, recommendations, encouragement }
    feedback = Column(JSON, nullable=True)
    
    # Relationships
    student = relationship("Student", back_populates="test_results")
    topic = relationship("Topic", backref="test_results")
    
    def __repr__(self):
        return f"<TestResult topic={self.topic_id} score={self.score}%>"
