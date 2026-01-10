"""
AI Tutor Platform - Document API Endpoints
Handles document upload, retrieval, and RAG operations.
"""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
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
    
    class Config:
        from_attributes = True


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


class ChatResponse(BaseModel):
    """Chat with document response."""
    answer: str
    grounded: bool
    confidence: float
    sources: List[SearchResult]


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
    
    # Run RAG agent
    try:
        response = await rag_agent.chat(
            query=request.query,
            document_id=document_id,
            user_id=str(current_user.id),
            grade=request.grade,
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

