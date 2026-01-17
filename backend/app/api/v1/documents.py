"""
AI Tutor Platform - Document API Endpoints
Handles document upload, retrieval, and RAG operations.
"""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api import deps
from app.models.user import User
from app.models.document import DocumentStatus
from app.services.document import DocumentService, get_document_service
from app.core.database import get_db


router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class DocumentResponse(BaseModel):
    """Response schema for a document."""
    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    subject: Optional[str] = None
    grade_level: Optional[int] = None
    description: Optional[str] = None
    status: str
    chunk_count: int
    total_tokens: int
    error_message: Optional[str] = None
    created_at: str
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response for document listing."""
    documents: List[DocumentResponse]
    total: int


class ChunkResponse(BaseModel):
    """Response schema for a document chunk."""
    id: str
    content: str
    chunk_index: int
    token_count: int
    context: Optional[str] = None  # NEW: Contextual description
    
    class Config:
        from_attributes = True


class ProcessingStep(BaseModel):
    """A processing step with status."""
    name: str
    status: str  # pending, running, completed, failed
    message: Optional[str] = None


class ProcessingStatusResponse(BaseModel):
    """Detailed processing status for a document."""
    document_id: str
    status: str
    progress_percent: int
    current_step: str
    steps: List[ProcessingStep]
    error_message: Optional[str] = None
    error_suggestion: Optional[str] = None  # User-friendly fix suggestion
    chunk_count: int = 0
    entity_count: int = 0
    estimated_time_remaining: Optional[int] = None  # seconds


class ValidationDetailResponse(BaseModel):
    """Detailed validation information."""
    is_appropriate: bool
    grade_match: str
    reason: str
    suggested_grade_range: Optional[str] = None
    educational_value: Optional[str] = None


class SearchResult(BaseModel):
    """Search result with similarity score."""
    chunk_id: str
    content: str
    chunk_index: int
    document_id: str
    filename: str
    similarity: float


class SearchRequest(BaseModel):
    """Search request."""
    query: str
    document_id: Optional[str] = None
    limit: int = 5


class SearchResponse(BaseModel):
    """Search response."""
    results: List[SearchResult]
    query: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    subject: Optional[str] = Form(None),
    grade_level: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    student_id: Optional[str] = Form(None),
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document for RAG processing.
    
    Supported formats: PDF, DOCX, TXT, MD
    
    The document will be:
    1. Saved to storage
    2. Text extracted
    3. Chunked into segments
    4. Embedded for vector search
    """
    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".txt", ".md", ".markdown"}
    filename = file.filename or "unknown"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {allowed_extensions}"
        )
    
    # Validate file size (max 10MB)
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: 10MB"
        )
    
    # Process document
    service = get_document_service(db)
    
    try:
        document = await service.upload_document(
            file_content=content,
            filename=filename,
            user_id=str(current_user.id),
            student_id=student_id,
            subject=subject,
            grade_level=grade_level,
            description=description,
            background_tasks=background_tasks,
        )
        
        return DocumentResponse(
            id=str(document.id),
            filename=document.filename,
            original_filename=document.original_filename,
            file_type=document.file_type,
            file_size=document.file_size,
            subject=document.subject,
            grade_level=document.grade_level,
            description=document.description,
            status=document.status.value if isinstance(document.status, DocumentStatus) else document.status,
            chunk_count=document.chunk_count,
            total_tokens=document.total_tokens,
            error_message=document.error_message,
            created_at=document.created_at.isoformat(),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )


@router.get("/list", response_model=DocumentListResponse)
@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    student_id: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents for the current user."""
    service = get_document_service(db)
    
    documents = await service.list_documents(
        user_id=str(current_user.id),
        student_id=student_id,
        subject=subject,
        limit=limit,
        offset=offset,
    )
    
    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=str(doc.id),
                filename=doc.filename,
                original_filename=doc.original_filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                subject=doc.subject,
                grade_level=doc.grade_level,
                description=doc.description,
                status=doc.status.value if isinstance(doc.status, DocumentStatus) else doc.status,
                chunk_count=doc.chunk_count,
                total_tokens=doc.total_tokens,
                error_message=doc.error_message,
                created_at=doc.created_at.isoformat(),
            )
            for doc in documents
        ],
        total=len(documents),
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific document by ID."""
    service = get_document_service(db)
    
    document = await service.get_document(document_id, str(current_user.id))
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(
        id=str(document.id),
        filename=document.filename,
        original_filename=document.original_filename,
        file_type=document.file_type,
        file_size=document.file_size,
        subject=document.subject,
        grade_level=document.grade_level,
        description=document.description,
        status=document.status.value if isinstance(document.status, DocumentStatus) else document.status,
        chunk_count=document.chunk_count,
        total_tokens=document.total_tokens,
        error_message=document.error_message,
        created_at=document.created_at.isoformat(),
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and all its chunks."""
    service = get_document_service(db)
    
    success = await service.delete_document(document_id, str(current_user.id))
    
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": "Document deleted successfully"}


@router.post("/{document_id}/regenerate-summary")
async def regenerate_summary_chunk(
    document_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate the summary chunk for a document.
    Useful for documents uploaded before summary indexing was implemented.
    """
    import uuid as uuid_module
    from app.models.document import DocumentChunk, UserDocument
    from sqlalchemy import select, delete
    from langchain_openai import OpenAIEmbeddings
    from app.core.config import settings
    
    # Get the document
    result = await db.execute(
        select(UserDocument).where(
            UserDocument.id == uuid_module.UUID(document_id),
            UserDocument.user_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not document.summary:
        raise HTTPException(status_code=400, detail="Document has no summary to index")
    
    # Delete existing summary chunks
    await db.execute(
        delete(DocumentChunk).where(
            DocumentChunk.document_id == document.id,
            DocumentChunk.chunk_index == -1  # Summary chunks have index -1
        )
    )
    
    # Create new summary chunk with embedding
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    summary_embedding = await embeddings_model.aembed_documents([document.summary])
    
    summary_chunk = DocumentChunk(
        id=uuid_module.uuid4(),
        document_id=document.id,
        content=f"[DOCUMENT SUMMARY] {document.summary}",
        chunk_index=-1,
        token_count=len(document.summary.split()),
        chunk_metadata={"type": "summary", "is_meta_chunk": True},
        context=None,
    )
    
    if summary_embedding and len(summary_embedding) > 0:
        summary_chunk.embedding = summary_embedding[0]
    
    db.add(summary_chunk)
    await db.commit()
    
    return {"message": "Summary chunk regenerated successfully", "document_id": document_id}


def _get_error_suggestion(error_message: str, status: str) -> Optional[str]:
    """Generate user-friendly suggestions for common errors."""
    if not error_message:
        return None
    
    error_lower = error_message.lower()
    
    if "not appropriate" in error_lower or status == "rejected":
        return "This document was rejected due to content concerns. Try uploading educational content appropriate for the selected grade level."
    
    if "extraction failed" in error_lower or "no text" in error_lower:
        return "We couldn't extract text from this document. For scanned PDFs, this is expected - we'll use OCR. For other files, ensure the file isn't corrupted."
    
    if "embedding" in error_lower:
        return "There was an issue processing this document. Please try again in a few minutes."
    
    if "timeout" in error_lower:
        return "Processing took too long. Try a smaller document or split into multiple files."
    
    return "An unexpected error occurred. Please try again or contact support if the issue persists."


@router.get("/{document_id}/status", response_model=ProcessingStatusResponse)
async def get_document_status(
    document_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed processing status for a document.
    
    Returns step-by-step progress and any error information with suggestions.
    Poll this endpoint to track upload/processing progress.
    """
    service = get_document_service(db)
    document = await service.get_document(document_id, str(current_user.id))
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Determine current step and progress
    status_value = document.status.value if hasattr(document.status, 'value') else str(document.status)
    
    steps = [
        ProcessingStep(name="Upload", status="completed", message="File received"),
        ProcessingStep(name="Extraction", status="pending", message=None),
        ProcessingStep(name="Chunking", status="pending", message=None),
        ProcessingStep(name="Embedding", status="pending", message=None),
        ProcessingStep(name="Validation", status="pending", message=None),
        ProcessingStep(name="Indexing", status="pending", message=None),
    ]
    
    progress = 10
    current_step = "Upload"
    
    if status_value in ("processing", "validating", "completed", "rejected", "failed"):
        steps[1] = ProcessingStep(name="Extraction", status="completed", message="Text extracted")
        progress = 30
        current_step = "Extraction"
    
    if status_value in ("validating", "completed", "rejected", "failed"):
        steps[2] = ProcessingStep(name="Chunking", status="completed", message=f"{document.chunk_count} chunks")
        progress = 50
        current_step = "Chunking"
    
    if status_value in ("validating", "completed", "rejected"):
        steps[3] = ProcessingStep(name="Embedding", status="completed", message="Vectors generated")
        progress = 70
        current_step = "Embedding"
    
    if status_value in ("completed", "rejected"):
        steps[4] = ProcessingStep(
            name="Validation", 
            status="completed" if status_value == "completed" else "failed",
            message="Grade-appropriate" if status_value == "completed" else "Review needed"
        )
        progress = 90
        current_step = "Validation"
    
    if status_value == "completed":
        steps[5] = ProcessingStep(name="Indexing", status="completed", message="Ready for search")
        progress = 100
        current_step = "Completed"
    
    if status_value == "failed":
        progress = min(progress, 90)
        for i, step in enumerate(steps):
            if step.status == "pending":
                steps[i] = ProcessingStep(name=step.name, status="failed", message="Error")
                current_step = step.name
                break
    
    # Count entities if available
    entity_count = 0
    try:
        from app.services.graph_store import get_graph_store
        graph_store = get_graph_store()
        if await graph_store.is_available():
            entities = await graph_store.get_document_entities(document_id)
            entity_count = len(entities)
    except Exception:
        pass
    
    return ProcessingStatusResponse(
        document_id=str(document.id),
        status=status_value,
        progress_percent=progress,
        current_step=current_step,
        steps=steps,
        error_message=document.error_message,
        error_suggestion=_get_error_suggestion(document.error_message, status_value),
        chunk_count=document.chunk_count,
        entity_count=entity_count,
        estimated_time_remaining=None if progress >= 100 else max(0, (100 - progress) // 10),
    )


@router.get("/{document_id}/chunks", response_model=List[ChunkResponse])
async def get_document_chunks(
    document_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all chunks for a document."""
    service = get_document_service(db)
    
    chunks = await service.get_document_chunks(document_id, str(current_user.id))
    
    if not chunks:
        raise HTTPException(status_code=404, detail="Document not found or has no chunks")
    
    return [
        ChunkResponse(
            id=str(chunk.id),
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            token_count=chunk.token_count,
        )
        for chunk in chunks
    ]


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search documents using semantic similarity.
    
    Generates an embedding for the query and finds similar chunks.
    """
    from langchain_openai import OpenAIEmbeddings
    from app.core.config import settings
    
    # Generate query embedding
    try:
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.OPENAI_API_KEY
        )
        query_embedding = await embeddings_model.aembed_query(request.query)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate query embedding: {str(e)}"
        )
    
    # Search
    service = get_document_service(db)
    
    results = await service.search_chunks(
        query_embedding=query_embedding,
        user_id=str(current_user.id),
        document_id=request.document_id,
        limit=request.limit,
    )
    
    return SearchResponse(
        results=[SearchResult(**r) for r in results],
        query=request.query,
    )


# =============================================================================
# RAG CHAT & QUIZ ENDPOINTS
# =============================================================================

class ChatRequest(BaseModel):
    """Chat with document request."""
    query: str
    grade: int = 5
    session_id: Optional[str] = None  # For chat history persistence


class ChatResponse(BaseModel):
    """Chat with document response."""
    answer: str
    grounded: bool
    confidence: float
    sources: List[SearchResult]
    session_id: Optional[str] = None  # For chat history continuity


class QuizRequest(BaseModel):
    """Generate quiz from document request."""
    num_questions: int = 5
    grade: int = 5


class QuizQuestionResponse(BaseModel):
    """A quiz question."""
    question: str
    options: List[str]
    correct_answer: str
    explanation: str


class QuizResponse(BaseModel):
    """Quiz generation response."""
    questions: List[QuizQuestionResponse]
    document_id: str
    total_questions: int


@router.post("/{document_id}/chat", response_model=ChatResponse)
async def chat_with_document(
    document_id: str,
    request: ChatRequest,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Chat with a document using RAG.
    
    Ask questions about the document content and get grounded answers.
    The response will be based only on the document content.
    """
    from app.ai.agents.rag import rag_agent, RAGMode
    from app.services.chat import ChatService
    from app.models.chat import MessageRole
    import uuid as uuid_module
    
    # Verify document exists and user has access
    service = get_document_service(db)
    document = await service.get_document(document_id, str(current_user.id))
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Document is not ready. Status: {document.status}"
        )
    
    # Initialize ChatService for message persistence
    chat_service = ChatService(db)
    session_id = request.session_id
    
    # Create or get session
    if session_id:
        try:
            session_uuid = uuid_module.UUID(session_id)
            session = await chat_service.get_session(session_uuid)
            if not session:
                # Session doesn't exist, create new one
                session = await chat_service.create_session(
                    user_id=current_user.id,
                    title=f"Chat with {document.original_filename}"
                )
                session_id = str(session.id)
        except ValueError:
            # Invalid UUID, create new session
            session = await chat_service.create_session(
                user_id=current_user.id,
                title=f"Chat with {document.original_filename}"
            )
            session_id = str(session.id)
    else:
        # No session_id provided, create new session
        session = await chat_service.create_session(
            user_id=current_user.id,
            title=f"Chat with {document.original_filename}"
        )
        session_id = str(session.id)
    
    # Save user message
    await chat_service.add_message(
        session_id=uuid_module.UUID(session_id),
        role=MessageRole.USER,
        content=request.query
    )
    
    # Run RAG agent
    try:
        response = await rag_agent.chat(
            query=request.query,
            document_id=document_id,
            user_id=str(current_user.id),
            grade=request.grade,
            session_id=session_id,
        )
        
        # Save assistant response
        await chat_service.add_message(
            session_id=uuid_module.UUID(session_id),
            role=MessageRole.ASSISTANT,
            content=response.answer
        )
        
        return ChatResponse(
            answer=response.answer,
            grounded=response.grounded,
            confidence=response.confidence,
            sources=[
                SearchResult(
                    chunk_id=s.chunk_id,
                    content=s.content[:500],  # Truncate for response
                    chunk_index=s.chunk_index,
                    document_id=s.document_id,
                    filename=s.filename,
                    similarity=s.similarity,
                )
                for s in response.sources[:3]  # Top 3 sources
            ],
            session_id=session_id,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat failed: {str(e)}"
        )


@router.post("/{document_id}/quiz", response_model=QuizResponse)
async def generate_quiz_from_document(
    document_id: str,
    request: QuizRequest,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate quiz questions from a document.
    
    Creates multiple-choice questions based on the document content.
    These questions are private to the student who uploaded the document.
    """
    from app.ai.agents.rag import rag_agent, RAGMode
    
    # Verify document exists and user has access
    service = get_document_service(db)
    document = await service.get_document(document_id, str(current_user.id))
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Document is not ready. Status: {document.status}"
        )
    
    # Run RAG agent in quiz mode
    try:
        result = await rag_agent.run(
            user_input=f"Generate {request.num_questions} quiz questions",
            metadata={
                "mode": RAGMode.QUIZ,
                "document_id": document_id,
                "user_id": str(current_user.id),
                "grade": request.grade,
                "num_questions": request.num_questions,
                "top_k": 15,
            }
        )
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        # Extract questions from RAG response
        questions = []
        
        # Check for quiz_questions attribute attached by the RAG agent
        if hasattr(result.output, 'quiz_questions') and result.output.quiz_questions:
            for q in result.output.quiz_questions:
                questions.append(QuizQuestionResponse(
                    question=q.get("question", ""),
                    options=q.get("options", []),
                    correct_answer=q.get("correct_answer", ""),
                    explanation=q.get("explanation", ""),
                ))
        
        return QuizResponse(
            questions=questions,
            document_id=document_id,
            total_questions=len(questions),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Quiz generation failed: {str(e)}"
        )


# =============================================================================
# DOCUMENT CHAT HISTORY ENDPOINT
# =============================================================================

class DocumentChatMessageResponse(BaseModel):
    """A chat message in document chat history."""
    role: str
    content: str
    created_at: str


class DocumentChatHistoryResponse(BaseModel):
    """Response for document chat history."""
    session_id: str
    messages: List[DocumentChatMessageResponse]


@router.get("/{document_id}/chat/history/{session_id}", response_model=DocumentChatHistoryResponse)
async def get_document_chat_history(
    document_id: str,
    session_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get chat history for a document session.
    
    Returns all messages from the specified session.
    """
    from app.services.chat import ChatService
    import uuid as uuid_module
    
    # Verify document exists and user has access
    service = get_document_service(db)
    document = await service.get_document(document_id, str(current_user.id))
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get chat history
    chat_service = ChatService(db)
    
    try:
        session_uuid = uuid_module.UUID(session_id)
        session = await chat_service.get_session(session_uuid)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Verify user owns this session
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get all messages (use larger limit for full history)
        messages = await chat_service.get_history(session_uuid, limit=100)
        
        return DocumentChatHistoryResponse(
            session_id=session_id,
            messages=[
                DocumentChatMessageResponse(
                    role=msg.role.value if hasattr(msg.role, 'value') else str(msg.role),
                    content=msg.content,
                    created_at=msg.created_at.isoformat()
                )
                for msg in messages
            ]
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
