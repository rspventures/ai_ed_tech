"""
AI Tutor Platform - Document Service
Handles document storage, retrieval, and RAG operations.
"""
import uuid
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import UserDocument, DocumentChunk, DocumentStatus, GeneratedImage, ValidationStatus
from app.ai.agents.document import document_agent, DocumentResult
from app.ai.agents.document_validator import document_validator_agent, GradeMatch


# Upload directory
UPLOAD_DIR = Path("uploads/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class DocumentService:
    """
    Service layer for document operations.
    
    Handles:
    - File upload and storage
    - Document processing via DocumentAgent
    - Vector similarity search
    - Document CRUD operations
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        user_id: str,
        student_id: Optional[str] = None,
        subject: Optional[str] = None,
        grade_level: Optional[int] = None,
        description: Optional[str] = None,
    ) -> UserDocument:
        """
        Upload and process a document.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            user_id: Uploading user ID
            student_id: Optional student ID
            subject: Optional subject categorization
            grade_level: Optional grade level
            description: Optional description
            
        Returns:
            UserDocument model instance
        """
        # Generate unique filename
        file_ext = Path(filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Create document record
        document = UserDocument(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            student_id=uuid.UUID(student_id) if student_id else None,
            filename=unique_filename,
            original_filename=filename,
            file_type=file_ext,
            file_size=len(file_content),
            file_path=str(file_path),
            subject=subject,
            grade_level=grade_level,
            description=description,
            status=DocumentStatus.PROCESSING,
        )
        
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        
        # Process document asynchronously
        try:
            result = await document_agent.process_file(
                file_path=str(file_path),
                user_id=user_id,
                student_id=student_id,
                subject=subject,
                grade_level=grade_level,
            )
            
            if result.status == "completed":
                # Get full result with chunks and embeddings
                agent_result = await document_agent.run(
                    user_input=f"Process document: {file_path}",
                    metadata={
                        "file_path": str(file_path),
                        "user_id": user_id,
                        "student_id": student_id,
                        "subject": subject,
                        "grade_level": grade_level,
                    }
                )
                
                if agent_result.success:
                    output = agent_result.output
                    
                    # Store chunks
                    chunks = output.get("chunks", [])
                    embeddings = output.get("embeddings", [])
                    token_counts = output.get("token_counts", [])
                    chunk_metadata = output.get("chunk_metadata", [])
                    
                    for i, chunk_text in enumerate(chunks):
                        chunk = DocumentChunk(
                            id=uuid.uuid4(),
                            document_id=document.id,
                            content=chunk_text,
                            chunk_index=i,
                            token_count=token_counts[i] if i < len(token_counts) else 0,
                            chunk_metadata=chunk_metadata[i] if i < len(chunk_metadata) else {},
                        )
                        
                        # Add embedding if available and pgvector is enabled
                        if embeddings and i < len(embeddings):
                            try:
                                chunk.embedding = embeddings[i]
                            except AttributeError:
                                # pgvector not available
                                pass
                        
                        self.db.add(chunk)
                    
                    # Validate document for grade-appropriateness
                    document.status = DocumentStatus.VALIDATING
                    await self.db.commit()
                    
                    # Get sample chunks for validation
                    sample_chunks = chunks[:3] if len(chunks) >= 3 else chunks
                    
                    validation_result = await document_validator_agent.validate(
                        content_samples=sample_chunks,
                        target_grade=grade_level or 5,  # Default to grade 5 if not specified
                        subject=subject,
                    )
                    
                    # Store validation result
                    document.validation_result = {
                        "is_appropriate": validation_result.is_appropriate,
                        "grade_match": validation_result.grade_match.value,
                        "estimated_grade_range": list(validation_result.estimated_grade_range),
                        "reason": validation_result.reason,
                        "educational_value": validation_result.educational_value,
                        "content_warnings": validation_result.content_warnings,
                    }
                    
                    # Determine final status based on validation
                    if validation_result.is_appropriate:
                        if validation_result.grade_match == GradeMatch.INAPPROPRIATE:
                            # Edge case: marked appropriate but grade match says inappropriate
                            document.status = DocumentStatus.REJECTED
                            document.validation_status = ValidationStatus.REJECTED
                            document.error_message = validation_result.reason
                        elif validation_result.grade_match in [GradeMatch.EXACT, GradeMatch.CLOSE]:
                            document.status = DocumentStatus.COMPLETED
                            document.validation_status = ValidationStatus.APPROVED
                        else:
                            # TOO_EASY or TOO_HARD - allow with review status
                            document.status = DocumentStatus.COMPLETED
                            document.validation_status = ValidationStatus.NEEDS_REVIEW
                    else:
                        # Not appropriate - reject the document
                        document.status = DocumentStatus.REJECTED
                        document.validation_status = ValidationStatus.REJECTED
                        document.error_message = validation_result.reason
                    
                    # Set metadata if approved
                    if document.status == DocumentStatus.COMPLETED:
                        document.chunk_count = len(chunks)
                        document.total_tokens = sum(token_counts)
                        document.processed_at = datetime.utcnow()
                else:
                    document.status = DocumentStatus.FAILED
                    document.error_message = agent_result.error
            else:
                document.status = DocumentStatus.FAILED
                document.error_message = result.error
                
        except Exception as e:
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
        
        await self.db.commit()
        await self.db.refresh(document)
        
        return document
    
    async def get_document(self, document_id: str, user_id: str) -> Optional[UserDocument]:
        """Get a document by ID, ensuring user access."""
        result = await self.db.execute(
            select(UserDocument).where(
                UserDocument.id == uuid.UUID(document_id),
                UserDocument.user_id == uuid.UUID(user_id)
            )
        )
        return result.scalar_one_or_none()
    
    async def list_documents(
        self, 
        user_id: str,
        student_id: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[UserDocument]:
        """List documents for a user."""
        query = select(UserDocument).where(
            UserDocument.user_id == uuid.UUID(user_id)
        )
        
        if student_id:
            query = query.where(UserDocument.student_id == uuid.UUID(student_id))
        
        if subject:
            query = query.where(UserDocument.subject == subject)
        
        query = query.order_by(UserDocument.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def delete_document(self, document_id: str, user_id: str) -> bool:
        """Delete a document and its chunks."""
        document = await self.get_document(document_id, user_id)
        
        if not document:
            return False
        
        # Delete file from disk
        try:
            if document.file_path and os.path.exists(document.file_path):
                os.remove(document.file_path)
        except Exception:
            pass
        
        # Delete from database (cascade will delete chunks)
        await self.db.delete(document)
        await self.db.commit()
        
        return True
    
    async def search_chunks(
        self,
        query_embedding: List[float],
        user_id: str,
        document_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity.
        
        Args:
            query_embedding: Query vector (1536 dimensions)
            user_id: User ID for access control
            document_id: Optional specific document to search
            limit: Max results to return
            
        Returns:
            List of chunks with similarity scores
        """
        # Check if pgvector is available
        try:
            from pgvector.sqlalchemy import Vector
        except ImportError:
            # Fallback to text search if pgvector not available
            return await self._text_search_fallback(
                query_embedding, user_id, document_id, limit
            )
        
        # Use raw connection to handle pgvector properly with asyncpg
        # asyncpg doesn't support named parameters in text() well with vectors
        from sqlalchemy import text
        
        # Format embedding as PostgreSQL array literal
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        
        try:
            # Use raw SQL execution through the connection
            connection = await self.db.connection()
            raw_conn = await connection.get_raw_connection()
            asyncpg_conn = raw_conn.driver_connection
            
            if document_id:
                sql = """
                    SELECT 
                        dc.id,
                        dc.content,
                        dc.chunk_index,
                        dc.document_id,
                        ud.original_filename,
                        1 - (dc.embedding <=> $1::vector) as similarity
                    FROM document_chunks dc
                    JOIN user_documents ud ON dc.document_id = ud.id
                    WHERE ud.user_id = $2::uuid
                    AND dc.document_id = $3::uuid
                    AND dc.embedding IS NOT NULL
                    ORDER BY dc.embedding <=> $1::vector
                    LIMIT $4
                """
                rows = await asyncpg_conn.fetch(
                    sql, embedding_str, uuid.UUID(user_id), uuid.UUID(document_id), limit
                )
            else:
                sql = """
                    SELECT 
                        dc.id,
                        dc.content,
                        dc.chunk_index,
                        dc.document_id,
                        ud.original_filename,
                        1 - (dc.embedding <=> $1::vector) as similarity
                    FROM document_chunks dc
                    JOIN user_documents ud ON dc.document_id = ud.id
                    WHERE ud.user_id = $2::uuid
                    AND dc.embedding IS NOT NULL
                    ORDER BY dc.embedding <=> $1::vector
                    LIMIT $3
                """
                rows = await asyncpg_conn.fetch(
                    sql, embedding_str, uuid.UUID(user_id), limit
                )
            
            return [
                {
                    "chunk_id": str(row["id"]),
                    "content": row["content"],
                    "chunk_index": row["chunk_index"],
                    "document_id": str(row["document_id"]),
                    "filename": row["original_filename"],
                    "similarity": float(row["similarity"]) if row["similarity"] else 0.5,
                }
                for row in rows
            ]
            
        except Exception as e:
            print(f"[DocumentService] Vector search failed: {e}")
            # Fall back to text search
            return await self._text_search_fallback(
                query_embedding, user_id, document_id, limit
            )
    
    async def _text_search_fallback(
        self,
        query_embedding: List[float],
        user_id: str,
        document_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Fallback to simple retrieval when pgvector not available."""
        query = select(DocumentChunk, UserDocument).join(
            UserDocument, DocumentChunk.document_id == UserDocument.id
        ).where(
            UserDocument.user_id == uuid.UUID(user_id)
        )
        
        if document_id:
            query = query.where(DocumentChunk.document_id == uuid.UUID(document_id))
        
        query = query.limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "chunk_id": str(chunk.id),
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "document_id": str(chunk.document_id),
                "filename": doc.original_filename,
                "similarity": 0.5,  # Placeholder
            }
            for chunk, doc in rows
        ]
    
    async def get_document_chunks(
        self, 
        document_id: str, 
        user_id: str
    ) -> List[DocumentChunk]:
        """Get all chunks for a document."""
        # First verify user has access
        document = await self.get_document(document_id, user_id)
        if not document:
            return []
        
        result = await self.db.execute(
            select(DocumentChunk).where(
                DocumentChunk.document_id == uuid.UUID(document_id)
            ).order_by(DocumentChunk.chunk_index)
        )
        
        return list(result.scalars().all())


def get_document_service(db: AsyncSession) -> DocumentService:
    """Factory function for DocumentService."""
    return DocumentService(db)
