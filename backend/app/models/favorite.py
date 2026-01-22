"""
AI Tutor Platform - Favorites Model
Stores student-starred lesson modules for quick review.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class StudentFavorite(Base):
    """
    Stores lesson modules that students mark as favorites.
    
    Enables "Quick Review" feature at subtopic/topic/subject level.
    """
    __tablename__ = "student_favorites"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Student reference
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    
    # Lesson and module reference
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("generated_lessons.id"), nullable=False)
    module_index = Column(Integer, nullable=False)  # Position in lesson.modules array
    module_type = Column(String(50), nullable=False)  # hook, text, flashcard, etc.
    module_content = Column(JSON, nullable=False)  # Snapshot of the module
    
    # Hierarchy for filtering
    subtopic_id = Column(UUID(as_uuid=True), ForeignKey("subtopics.id"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships (no back_populates to avoid requiring changes to other models)
    student = relationship("Student")
    lesson = relationship("GeneratedLesson")
    subtopic = relationship("Subtopic")
    topic = relationship("Topic")
    subject = relationship("Subject")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_favorites_student_id", "student_id"),
        Index("ix_favorites_subtopic_id", "subtopic_id"),
        Index("ix_favorites_topic_id", "topic_id"),
        Index("ix_favorites_subject_id", "subject_id"),
        Index("ix_favorites_student_lesson", "student_id", "lesson_id"),
    )
    
    def __repr__(self):
        return f"<StudentFavorite {self.module_type} from lesson {self.lesson_id}>"
