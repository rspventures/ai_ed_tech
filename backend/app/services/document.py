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
from fastapi import BackgroundTasks
from app.core.database import async_session_maker

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
        background_tasks: Optional[BackgroundTasks] = None,
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
        if background_tasks:
            print(f"[DocumentService] Scheduling background task for document {document.id}")
            background_tasks.add_task(
                process_document_background,
                document_id=str(document.id),
                file_path=str(file_path),
                user_id=user_id,
                student_id=student_id,
                subject=subject,
                grade_level=grade_level,
            )
        else:
            print(f"[DocumentService] WARNING: No background_tasks provided, processing not started.")
            
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
        metadata_filter: Optional[Dict[str, Any]] = None,
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
                """
                params = [embedding_str, uuid.UUID(user_id), uuid.UUID(document_id)]
                
                if metadata_filter:
                    sql += " AND dc.chunk_metadata @> $4::jsonb"
                    import json
                    params.append(json.dumps(metadata_filter))
                    # limit is now $5
                    sql += " ORDER BY dc.embedding <=> $1::vector LIMIT $5"
                    params.append(limit)
                else:
                    # limit is $4
                    sql += " ORDER BY dc.embedding <=> $1::vector LIMIT $4"
                    params.append(limit)

                rows = await asyncpg_conn.fetch(sql, *params)
                print(f"[DocumentService] Vector search (doc_id={document_id}) found {len(rows)} rows")
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
                """
                params = [embedding_str, uuid.UUID(user_id)]
                
                if metadata_filter:
                    sql += " AND dc.chunk_metadata @> $3::jsonb"
                    import json
                    params.append(json.dumps(metadata_filter))
                    # limit is now $4
                    sql += " ORDER BY dc.embedding <=> $1::vector LIMIT $4"
                    params.append(limit)
                else:
                    # limit is $3
                    sql += " ORDER BY dc.embedding <=> $1::vector LIMIT $3"
                    params.append(limit)

                rows = await asyncpg_conn.fetch(sql, *params)
                print(f"[DocumentService] Vector search (global) found {len(rows)} rows")
            
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
    
    async def hybrid_search_chunks(
        self,
        query: str,
        query_embedding: List[float],
        user_id: str,
        document_id: Optional[str] = None,
        limit: int = 5,
        use_reranker: bool = True,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector similarity and BM25 keyword search.
        
        This method:
        1. Performs vector similarity search
        2. Performs BM25 keyword search
        3. Fuses results using Reciprocal Rank Fusion (RRF)
        4. Optionally reranks using Cohere cross-encoder
        
        Args:
            query: Original text query (for BM25 and reranking)
            query_embedding: Query vector (1536 dimensions)
            user_id: User ID for access control
            document_id: Optional specific document to search
            limit: Max results to return
            use_reranker: Whether to apply cross-encoder reranking
            
        Returns:
            List of chunks with hybrid scores
        """
        try:
            from app.ai.core.hybrid_retrieval import hybrid_search, HybridSearchResult
            from app.ai.core.bm25_search import bm25_search_chunks
        except ImportError as e:
            print(f"[DocumentService] Hybrid search not available: {e}")
            # Fall back to vector-only search
            return await self.search_chunks(query_embedding, user_id, document_id, limit)
        
        # Step 1: Get vector search results
        vector_results = await self.search_chunks(
            query_embedding=query_embedding,
            user_id=user_id,
            document_id=document_id,
            limit=limit * 3,  # Get more for fusion
            metadata_filter=metadata_filter,
        )
        print(f"[DocumentService] Vector search returned {len(vector_results)} results")
        
        # Step 2: Get all chunks for BM25 indexing
        all_chunks = await self._get_all_chunks_for_bm25(user_id, document_id, metadata_filter)
        print(f"[DocumentService] Found {len(all_chunks)} chunks for BM25 indexing")
        
        # Step 3: Perform hybrid search with fusion and reranking
        hybrid_results = await hybrid_search(
            query=query,
            vector_results=vector_results,
            all_chunks=all_chunks,
            top_k=limit,
            use_reranker=use_reranker,
        )
        print(f"[DocumentService] Hybrid search returned {len(hybrid_results)} results")
        
        # Convert to dict format
        return [
            {
                "chunk_id": r.chunk_id,
                "content": r.content,
                "chunk_index": r.chunk_index,
                "document_id": r.document_id,
                "filename": r.filename,
                # Use rerank_score if available, otherwise use vector_score (normalized 0-1)
                # Note: fusion_score is RRF-based (~0.01-0.03) so not suitable for thresholding
                "similarity": r.rerank_score if r.rerank_score is not None else r.vector_score,
                "vector_score": r.vector_score,
                "bm25_score": r.bm25_score,
                "fusion_score": r.fusion_score,
                "rerank_score": r.rerank_score,
            }
            for r in hybrid_results
        ]
    
    async def _get_all_chunks_for_bm25(
        self,
        user_id: str,
        document_id: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get all chunks for BM25 indexing."""
        query = select(DocumentChunk, UserDocument).join(
            UserDocument, DocumentChunk.document_id == UserDocument.id
        ).where(
            UserDocument.user_id == uuid.UUID(user_id)
        )
        
        if document_id:
            query = query.where(DocumentChunk.document_id == uuid.UUID(document_id))
            
        if metadata_filter:
            # SQLAlchemy JSONB filtering
            query = query.where(DocumentChunk.chunk_metadata.contains(metadata_filter))
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "chunk_id": str(chunk.id),
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "document_id": str(chunk.document_id),
                "filename": doc.original_filename,
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


async def process_document_background(
    document_id: str,
    file_path: str,
    user_id: str,
    student_id: Optional[str],
    subject: Optional[str],
    grade_level: Optional[int],
) -> None:
    """
    Background task to process a document.
    Creates its own DB session since the request session will be closed.
    """
    print(f"[DocumentService] Starting background processing for document {document_id}")
    
    async with async_session_maker() as session:
        try:
            # Re-fetch document to ensure it's attached to this session
            result = await session.execute(
                select(UserDocument).where(UserDocument.id == uuid.UUID(document_id))
            )
            document = result.scalar_one_or_none()
            
            if not document:
                print(f"[DocumentService] Document {document_id} not found in background task")
                return
            
            # Process document
            print(f"[DocumentService] calling document_agent.process_file for {file_path}")
            result = await document_agent.process_file(
                file_path=file_path,
                user_id=user_id,
                student_id=student_id,
                subject=subject,
                grade_level=grade_level,
            )
            
            if result.status == "completed":
                print(f"[DocumentService] process_file completed, running RAG ingestion for {document_id}")
                # Get full result with chunks and embeddings
                agent_result = await document_agent.run(
                    user_input=f"Process document: {file_path}",
                    metadata={
                        "file_path": file_path,
                        "user_id": user_id,
                        "student_id": student_id,
                        "subject": subject,
                        "grade_level": grade_level,
                    }
                )
                
                if agent_result.success:
                    output = agent_result.output
                    
                    # Store chunks with contexts
                    chunks = output.get("chunks", [])
                    embeddings = output.get("embeddings", [])
                    token_counts = output.get("token_counts", [])
                    chunk_metadata = output.get("chunk_metadata", [])
                    contexts = output.get("contexts", [])
                    
                    # Store document summary
                    summary = output.get("summary", "")
                    if summary:
                        document.summary = summary
                    
                    print(f"[DocumentService] Storing {len(chunks)} chunks for {document_id}")
                    for i, chunk_text in enumerate(chunks):
                        # Build chunk metadata with type
                        meta = chunk_metadata[i] if i < len(chunk_metadata) else {}
                        meta["type"] = "content"  # Mark as content chunk for filtering
                        meta["chunk_index"] = i
                        
                        chunk = DocumentChunk(
                            id=uuid.uuid4(),
                            document_id=document.id,
                            content=chunk_text,
                            chunk_index=i,
                            token_count=token_counts[i] if i < len(token_counts) else 0,
                            chunk_metadata=meta,
                            context=contexts[i] if i < len(contexts) else None,
                        )
                        
                        # Add embedding if available
                        if embeddings and i < len(embeddings):
                            try:
                                chunk.embedding = embeddings[i]
                            except AttributeError:
                                pass
                        
                        session.add(chunk)
                    
                    # NEW: Create a "Summary Chunk" for meta-query handling
                    # This allows queries like "What is the syllabus?" to match the summary
                    if summary:
                        print(f"[DocumentService] Creating Summary Meta-Chunk for {document_id}")
                        try:
                            from langchain_openai import OpenAIEmbeddings
                            from app.core.config import settings
                            
                            embeddings_model = OpenAIEmbeddings(
                                model="text-embedding-3-small",
                                openai_api_key=settings.OPENAI_API_KEY
                            )
                            
                            # Generate embedding for the summary
                            summary_embedding = await embeddings_model.aembed_documents([summary])
                            
                            summary_chunk = DocumentChunk(
                                id=uuid.uuid4(),
                                document_id=document.id,
                                content=f"[DOCUMENT SUMMARY] {summary}",
                                chunk_index=-1,  # Special index for summary
                                token_count=len(summary.split()),
                                chunk_metadata={"type": "summary", "is_meta_chunk": True},
                                context=None,
                            )
                            
                            if summary_embedding and len(summary_embedding) > 0:
                                summary_chunk.embedding = summary_embedding[0]
                            
                            session.add(summary_chunk)
                            print(f"[DocumentService] Summary Meta-Chunk created successfully")
                        except Exception as e:
                            print(f"[DocumentService] Failed to create summary chunk: {e}")
                    
                    # NEW: Store section summaries as meta-chunks for hierarchical retrieval
                    section_summaries = output.get("section_summaries", [])
                    if section_summaries:
                        print(f"[DocumentService] Creating {len(section_summaries)} section meta-chunks")
                        try:
                            section_chunk_index = -2  # Start from -2 for sections (doc summary is -1)
                            for section_data in section_summaries:
                                section_content = f"[SECTION: {section_data.get('section_title', 'Unknown')}] {section_data['summary']}"
                                
                                # Generate embedding for section summary
                                section_embedding = await embeddings_model.aembed_documents([section_content])
                                
                                section_chunk = DocumentChunk(
                                    id=uuid.uuid4(),
                                    document_id=document.id,
                                    content=section_content,
                                    chunk_index=section_chunk_index,
                                    token_count=len(section_content.split()),
                                    chunk_metadata={
                                        "type": "section_summary",
                                        "is_meta_chunk": True,
                                        "section_number": section_data.get("section_number", ""),
                                        "section_title": section_data.get("section_title", ""),
                                    },
                                    context=None,
                                )
                                
                                if section_embedding and len(section_embedding) > 0:
                                    section_chunk.embedding = section_embedding[0]
                                
                                session.add(section_chunk)
                                section_chunk_index -= 1
                                
                            print(f"[DocumentService] {len(section_summaries)} section meta-chunks created")
                        except Exception as e:
                            print(f"[DocumentService] Failed to create section chunks: {e}")
                    
                    # Validating
                    document.status = DocumentStatus.VALIDATING
                    await session.commit()
                    
                    # Store chunks count (include summary + section chunks)
                    meta_chunk_count = (1 if summary else 0) + len(section_summaries)
                    document.chunk_count = len(chunks) + meta_chunk_count
                    document.total_tokens = sum(token_counts)
                    
                    # Validation
                    print(f"[DocumentService] Validating document {document_id}")
                    sample_chunks = chunks[:3] if len(chunks) >= 3 else chunks
                    
                    validation_result = await document_validator_agent.validate(
                        content_samples=sample_chunks,
                        target_grade=grade_level or 5,
                        subject=subject,
                    )
                    
                    document.validation_result = {
                        "is_appropriate": validation_result.is_appropriate,
                        "grade_match": validation_result.grade_match.value,
                        "feedback": validation_result.reason
                    }
                    
                    if validation_result.is_appropriate:
                        document.status = DocumentStatus.COMPLETED
                    else:
                        document.status = DocumentStatus.FAILED
                        document.error_message = f"Validation failed: {validation_result.reason}"
                        
                    await session.commit()
                    print(f"[DocumentService] Document {document_id} processing completed successfully")
                    
                else:
                    print(f"[DocumentService] Agent run failed: {agent_result.error}")
                    document.status = DocumentStatus.FAILED
                    document.error_message = agent_result.error or "Processing failed"
                    await session.commit()
            else:
                 print(f"[DocumentService] process_file failed: {result.error}")
                 document.status = DocumentStatus.FAILED
                 document.error_message = result.error or "Processing failed"
                 await session.commit()
                 
        except Exception as e:
            print(f"[DocumentService] Background processing fatal error: {e}")
            import traceback
            traceback.print_exc()
            try:
                # Try to update status if session is still valid
                document.status = DocumentStatus.FAILED
                document.error_message = f"System error: {str(e)}"
                await session.commit()
            except Exception:
                pass
