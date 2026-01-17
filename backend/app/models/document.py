"""
AI Tutor Platform - Document Models
SQLAlchemy models for RAG document storage with pgvector support.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Try to import pgvector, fall back gracefully
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    Vector = None

if TYPE_CHECKING:
    from app.models.user import User, Student


class DocumentStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class ValidationStatus(str, Enum):
    """Document validation status for grade-appropriateness."""
    PENDING = "pending"
    APPROVED = "approved"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class UserDocument(Base):
    """
    User-uploaded documents for RAG.
    
    These are study materials uploaded by parents/students
    for personalized learning and question generation.
    """
    
    __tablename__ = "user_documents"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Owner - link to User (parent) who uploaded
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    
    # Optional: Link to specific student (for student-specific docs)
    student_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("students.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Document metadata
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50))  # pdf, txt, docx, md
    file_size: Mapped[int] = mapped_column(Integer)  # bytes
    file_path: Mapped[str] = mapped_column(String(500))  # storage path
    
    # Educational context
    subject: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    grade_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Processing status
    status: Mapped[DocumentStatus] = mapped_column(
        String(50), 
        default=DocumentStatus.PENDING
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Stats
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    
    # Validation for grade-appropriateness
    validation_status: Mapped[str] = mapped_column(
        String(50), 
        default=ValidationStatus.PENDING
    )
    validation_result: Mapped[Optional[dict]] = mapped_column(
        JSONB, 
        nullable=True,
        default=None
    )  # {is_appropriate, grade_match, reason, suggested_grade_range, educational_value}
    
    # Privacy
    is_private: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Document summary for hierarchical retrieval
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Relationships
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<UserDocument {self.filename} ({self.status})>"


class DocumentChunk(Base):
    """
    Text chunks from documents with vector embeddings.
    
    Each document is split into chunks for efficient retrieval.
    Embeddings are stored using pgvector for similarity search.
    """
    
    __tablename__ = "document_chunks"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("user_documents.id", ondelete="CASCADE"),
        index=True
    )
    
    # Chunk content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer)  # Position in document
    
    # Token count for this chunk
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata (page number, section, etc.)
    chunk_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, default={}, nullable=True)
    
    # Contextual Retrieval - LLM-generated context explaining chunk relevance
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    # Relationship back to document
    document: Mapped["UserDocument"] = relationship(
        "UserDocument", 
        back_populates="chunks"
    )
    
    def __repr__(self) -> str:
        return f"<DocumentChunk {self.chunk_index} of {self.document_id}>"


# Conditional embedding column - added dynamically if pgvector available
if PGVECTOR_AVAILABLE and Vector is not None:
    # Add vector column for embeddings (OpenAI dimension = 1536)
    DocumentChunk.embedding = mapped_column(
        Vector(1536), 
        nullable=True
    )


class GeneratedImage(Base):
    """
    AI-generated images for visual concept explanations.
    """
    
    __tablename__ = "generated_images"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Owner
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    student_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("students.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Generation details
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    enhanced_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    concept: Mapped[str] = mapped_column(String(255))
    grade_level: Mapped[int] = mapped_column(Integer)
    
    # Result
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    provider: Mapped[str] = mapped_column(String(50))  # dalle3, imagen3, etc.
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<GeneratedImage '{self.concept}' grade {self.grade_level}>"


class DocumentQuizHistory(Base):
    """
    Tracks previously generated quiz questions per document.
    
    Used to prevent repetition when generating new quizzes.
    Only stores the last N questions per document for deduplication.
    """
    
    __tablename__ = "document_quiz_history"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("user_documents.id", ondelete="CASCADE"),
        index=True
    )
    
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<DocumentQuizHistory {self.document_id[:8]}... '{self.question_text[:30]}...'>"
