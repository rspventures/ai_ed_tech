"""
AI Tutor Platform - Document Agent
Handles document upload, processing, chunking, and embedding for RAG.
"""
import os
import uuid
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path

from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.ai.core.telemetry import get_tracer
from app.core.config import settings

# Document processing imports
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


@dataclass
class ChunkResult:
    """Result of chunking a document."""
    chunks: List[str]
    token_counts: List[int]
    total_tokens: int
    metadata: List[Dict[str, Any]]


@dataclass 
class DocumentResult:
    """Result of document processing."""
    document_id: str
    filename: str
    chunk_count: int
    total_tokens: int
    status: str
    error: Optional[str] = None


class DocumentAgent(BaseAgent):
    """
    Document Processing Agent 📄
    
    Handles the complete document ingestion pipeline:
    1. Extract text from various formats (PDF, DOCX, TXT, MD)
    2. Clean and normalize text
    3. Chunk into semantic segments
    4. Generate embeddings (via LLM client)
    5. Store in database with pgvector
    
    Uses Plan-Execute pattern:
    - Plan: Validate file, determine extraction strategy
    - Execute: Extract → Clean → Chunk → Embed → Store
    """
    
    name = "DocumentAgent"
    description = "Processes documents for RAG retrieval"
    version = "1.0.0"
    
    # Supported file types
    SUPPORTED_FORMATS = {".pdf", ".txt", ".docx", ".md", ".markdown"}
    
    # Chunking parameters
    DEFAULT_CHUNK_SIZE = 500  # tokens
    CHUNK_OVERLAP = 50  # tokens overlap between chunks
    
    # Upload directory
    UPLOAD_DIR = Path("uploads/documents")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Ensure upload directory exists
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Initialize tokenizer for counting
        self._tokenizer = None
        if TIKTOKEN_AVAILABLE:
            try:
                self._tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
            except Exception:
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self._tokenizer:
            return len(self._tokenizer.encode(text))
        # Fallback: rough estimate (4 chars per token)
        return len(text) // 4
    
    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """
        Plan document processing.
        
        Validates file and determines extraction strategy.
        """
        metadata = context.metadata
        
        file_path = metadata.get("file_path")
        user_id = metadata.get("user_id")
        student_id = metadata.get("student_id")
        subject = metadata.get("subject")
        grade_level = metadata.get("grade_level")
        
        if not file_path:
            return {
                "action": "error",
                "error": "No file path provided"
            }
        
        # Check file exists
        path = Path(file_path)
        if not path.exists():
            return {
                "action": "error", 
                "error": f"File not found: {file_path}"
            }
        
        # Check file type
        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            return {
                "action": "error",
                "error": f"Unsupported file type: {suffix}. Supported: {self.SUPPORTED_FORMATS}"
            }
        
        # Determine extraction method
        extraction_method = self._get_extraction_method(suffix)
        
        return {
            "action": "process_document",
            "params": {
                "file_path": str(path),
                "filename": path.name,
                "file_type": suffix,
                "file_size": path.stat().st_size,
                "extraction_method": extraction_method,
                "user_id": user_id,
                "student_id": student_id,
                "subject": subject,
                "grade_level": grade_level,
                "chunk_size": metadata.get("chunk_size", self.DEFAULT_CHUNK_SIZE),
                "chunk_overlap": metadata.get("chunk_overlap", self.CHUNK_OVERLAP),
            }
        }
    
    def _get_extraction_method(self, suffix: str) -> str:
        """Determine text extraction method based on file type."""
        if suffix == ".pdf":
            return "pdf"
        elif suffix == ".docx":
            return "docx"
        elif suffix in {".txt", ".md", ".markdown"}:
            return "text"
        return "text"
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """
        Execute document processing pipeline.
        """
        tracer = get_tracer()
        
        with tracer.start_as_current_span("process_document") as span:
            if plan["action"] == "error":
                return AgentResult(
                    success=False,
                    output=None,
                    state=AgentState.ERROR,
                    error=plan["error"]
                )
            
            params = plan["params"]
            span.set_attribute("document.filename", params["filename"])
            span.set_attribute("document.type", params["file_type"])
            
            try:
                # Step 1: Extract text
                span.add_event("extracting_text")
                text = await self._extract_text(
                    params["file_path"],
                    params["extraction_method"]
                )
                
                if not text or not text.strip():
                    return AgentResult(
                        success=False,
                        output=None,
                        state=AgentState.ERROR,
                        error="No text could be extracted from document"
                    )
                
                span.set_attribute("document.text_length", len(text))
                
                # Step 2: Clean text
                span.add_event("cleaning_text")
                cleaned_text = self._clean_text(text)
                
                # Step 3: Chunk text
                span.add_event("chunking_text")
                chunk_result = self._chunk_text(
                    cleaned_text,
                    params["chunk_size"],
                    params["chunk_overlap"]
                )
                
                span.set_attribute("document.chunk_count", len(chunk_result.chunks))
                span.set_attribute("document.total_tokens", chunk_result.total_tokens)
                
                # Step 4: Generate embeddings (if embedding service available)
                span.add_event("generating_embeddings")
                embeddings = await self._generate_embeddings(chunk_result.chunks)
                
                # Return result (storage happens at service layer)
                result = DocumentResult(
                    document_id=str(uuid.uuid4()),
                    filename=params["filename"],
                    chunk_count=len(chunk_result.chunks),
                    total_tokens=chunk_result.total_tokens,
                    status="completed"
                )
                
                return AgentResult(
                    success=True,
                    output={
                        "document": result,
                        "chunks": chunk_result.chunks,
                        "token_counts": chunk_result.token_counts,
                        "chunk_metadata": chunk_result.metadata,
                        "embeddings": embeddings,
                        "params": params,
                    },
                    state=AgentState.COMPLETED,
                )
                
            except Exception as e:
                span.record_exception(e)
                return AgentResult(
                    success=False,
                    output=None,
                    state=AgentState.ERROR,
                    error=str(e)
                )
    
    async def _extract_text(self, file_path: str, method: str) -> str:
        """Extract text from document based on file type."""
        if method == "pdf":
            return await self._extract_pdf(file_path)
        elif method == "docx":
            return await self._extract_docx(file_path)
        else:
            return await self._extract_text_file(file_path)
    
    async def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        if not PYPDF_AVAILABLE:
            raise ImportError("pypdf is not installed. Run: pip install pypdf")
        
        def _read_pdf():
            reader = PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n\n".join(text_parts)
        
        # Run in executor to not block async loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _read_pdf)
    
    async def _extract_docx(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx is not installed. Run: pip install python-docx")
        
        def _read_docx():
            doc = DocxDocument(file_path)
            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            return "\n\n".join(text_parts)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _read_docx)
    
    async def _extract_text_file(self, file_path: str) -> str:
        """Extract text from plain text file."""
        try:
            import aiofiles
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()
        except ImportError:
            # Fallback to sync read
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        import re
        
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove page headers/footers patterns (common in PDFs)
        text = re.sub(r'Page \d+ of \d+', '', text)
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text.strip()
    
    def _chunk_text(
        self, 
        text: str, 
        chunk_size: int, 
        overlap: int
    ) -> ChunkResult:
        """
        Split text into overlapping chunks.
        
        Uses sentence-aware splitting to avoid breaking mid-sentence.
        """
        import re
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        token_counts = []
        metadata = []
        
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)
            
            # If single sentence exceeds chunk size, split it
            if sentence_tokens > chunk_size:
                # Save current chunk if any
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append(chunk_text)
                    token_counts.append(current_tokens)
                    metadata.append({"chunk_index": chunk_index})
                    chunk_index += 1
                    current_chunk = []
                    current_tokens = 0
                
                # Split long sentence by words
                words = sentence.split()
                word_chunk = []
                word_tokens = 0
                
                for word in words:
                    word_token_count = self._count_tokens(word)
                    if word_tokens + word_token_count > chunk_size:
                        if word_chunk:
                            chunk_text = ' '.join(word_chunk)
                            chunks.append(chunk_text)
                            token_counts.append(word_tokens)
                            metadata.append({"chunk_index": chunk_index})
                            chunk_index += 1
                        word_chunk = [word]
                        word_tokens = word_token_count
                    else:
                        word_chunk.append(word)
                        word_tokens += word_token_count
                
                if word_chunk:
                    # Add remainder to current_chunk for overlap
                    current_chunk = word_chunk
                    current_tokens = word_tokens
            
            elif current_tokens + sentence_tokens > chunk_size:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                token_counts.append(current_tokens)
                metadata.append({"chunk_index": chunk_index})
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_sentences = []
                overlap_tokens = 0
                
                for s in reversed(current_chunk):
                    s_tokens = self._count_tokens(s)
                    if overlap_tokens + s_tokens <= overlap:
                        overlap_sentences.insert(0, s)
                        overlap_tokens += s_tokens
                    else:
                        break
                
                current_chunk = overlap_sentences + [sentence]
                current_tokens = overlap_tokens + sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(chunk_text)
            token_counts.append(current_tokens)
            metadata.append({"chunk_index": chunk_index})
        
        return ChunkResult(
            chunks=chunks,
            token_counts=token_counts,
            total_tokens=sum(token_counts),
            metadata=metadata
        )
    
    async def _generate_embeddings(self, chunks: List[str]) -> List[List[float]]:
        """
        Generate embeddings for chunks using OpenAI.
        
        Returns empty list if embedding fails (graceful degradation).
        """
        try:
            from langchain_openai import OpenAIEmbeddings
            
            embeddings_model = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=settings.OPENAI_API_KEY
            )
            
            # Generate embeddings in batches
            embeddings = await embeddings_model.aembed_documents(chunks)
            return embeddings
            
        except Exception as e:
            print(f"[DocumentAgent] Embedding generation failed: {e}")
            # Return empty embeddings - allows document to be stored without vectors
            return []
    
    async def process_file(
        self,
        file_path: str,
        user_id: str,
        student_id: Optional[str] = None,
        subject: Optional[str] = None,
        grade_level: Optional[int] = None,
    ) -> DocumentResult:
        """
        Convenience method to process a file.
        
        Args:
            file_path: Path to the file to process
            user_id: ID of the user uploading
            student_id: Optional student ID
            subject: Optional subject categorization
            grade_level: Optional grade level
            
        Returns:
            DocumentResult with processing outcome
        """
        result = await self.run(
            user_input=f"Process document: {file_path}",
            metadata={
                "file_path": file_path,
                "user_id": user_id,
                "student_id": student_id,
                "subject": subject,
                "grade_level": grade_level,
            }
        )
        
        if result.success:
            return result.output["document"]
        else:
            return DocumentResult(
                document_id="",
                filename=Path(file_path).name if file_path else "unknown",
                chunk_count=0,
                total_tokens=0,
                status="failed",
                error=result.error
            )


# Singleton instance
document_agent = DocumentAgent()
