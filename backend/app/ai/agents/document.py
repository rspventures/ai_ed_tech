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
                print(f"[DocumentAgent] Extracting text from {params['filename']} (method: {params['extraction_method']})")
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
                print(f"[DocumentAgent] Cleaning text...")
                cleaned_text = self._clean_text(text)
                
                # Step 3: Chunk text
                span.add_event("chunking_text")
                print(f"[DocumentAgent] Chunking text...")
                chunk_result = self._chunk_text(
                    cleaned_text,
                    params["chunk_size"],
                    params["chunk_overlap"]
                )
                print(f"[DocumentAgent] Created {len(chunk_result.chunks)} chunks")
                
                span.set_attribute("document.chunk_count", len(chunk_result.chunks))
                span.set_attribute("document.total_tokens", chunk_result.total_tokens)
                
                # Step 4: Generate embeddings (if embedding service available)
                span.add_event("generating_embeddings")
                print(f"[DocumentAgent] Generating embeddings for {len(chunk_result.chunks)} chunks...")
                embeddings = await self._generate_embeddings(chunk_result.chunks)
                
                # Step 5: Generate chunk contexts (Contextual Retrieval)
                span.add_event("generating_contexts")
                print(f"[DocumentAgent] Generating contextual retrieval contexts...")
                contexts = await self._generate_chunk_contexts(
                    chunks=chunk_result.chunks,
                    filename=params["filename"],
                    subject=params.get("subject"),
                )
                
                # Step 6: Generate document summary
                span.add_event("generating_summary")
                print(f"[DocumentAgent] Generating document summary...")
                summary = await self._generate_document_summary(
                    text=cleaned_text,
                    filename=params["filename"],
                    subject=params.get("subject"),
                )
                
                # Step 7: Generate section summaries for large documents
                section_summaries = []
                if len(cleaned_text) > 20000:  # Only for large documents
                    span.add_event("generating_section_summaries")
                    print(f"[DocumentAgent] Large document detected, generating section summaries...")
                    section_summaries = await self._generate_section_summaries(
                        text=cleaned_text,
                        filename=params["filename"],
                        subject=params.get("subject"),
                    )
                
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
                        "contexts": contexts,
                        "summary": summary,
                        "section_summaries": section_summaries,  # NEW: Section-level summaries
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
        """
        Extract text from PDF file.
        
        Enhanced to detect image-based (scanned) pages and use
        Vision OCR for better extraction.
        """
        if not PYPDF_AVAILABLE:
            raise ImportError("pypdf is not installed. Run: pip install pypdf")
        
        def _read_pdf_with_images():
            """Read PDF and identify pages that need OCR."""
            reader = PdfReader(file_path)
            text_parts = []
            pages_needing_ocr = []
            
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                
                # Check if page has meaningful text
                if text and len(text.strip()) > 50:
                    text_parts.append((i, text, False))  # (page_num, text, needs_ocr)
                else:
                    # Page might be image-based (scanned)
                    # Check if page has images
                    has_images = False
                    try:
                        if hasattr(page, 'images') and page.images:
                            has_images = True
                        elif '/XObject' in page.get('/Resources', {}):
                            has_images = True
                    except Exception:
                        pass
                    
                    if has_images or len(text.strip()) < 20:
                        pages_needing_ocr.append(i)
                        text_parts.append((i, text or "", True))
                    else:
                        text_parts.append((i, text or "", False))
            
            return reader, text_parts, pages_needing_ocr
        
        # Run sync operation in executor
        loop = asyncio.get_event_loop()
        reader, text_parts, pages_needing_ocr = await loop.run_in_executor(
            None, _read_pdf_with_images
        )
        
        # If there are pages needing OCR, try Vision OCR
        if pages_needing_ocr:
            try:
                text_parts = await self._process_scanned_pages(
                    file_path, text_parts, pages_needing_ocr
                )
            except Exception as e:
                print(f"[DocumentAgent] Vision OCR failed, using basic extraction: {e}")
        
        # Combine all text
        final_text = "\n\n".join([
            part[1] for part in sorted(text_parts, key=lambda x: x[0])
            if part[1].strip()
        ])
        
        return final_text
    
    async def _process_scanned_pages(
        self,
        file_path: str,
        text_parts: list,
        pages_needing_ocr: list,
    ) -> list:
        """Process scanned pages using Vision OCR."""
        try:
            from app.ai.agents.vision_ocr import vision_ocr_agent
            import fitz  # PyMuPDF for image extraction
        except ImportError:
            # PyMuPDF not available, return original
            return text_parts
        
        try:
            doc = fitz.open(file_path)
            
            for page_num in pages_needing_ocr:
                if page_num >= len(doc):
                    continue
                
                page = doc[page_num]
                
                # Render page as image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                img_bytes = pix.tobytes("png")
                
                import base64
                img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                
                # Run OCR
                ocr_result = await vision_ocr_agent.ocr_image(
                    image_data=img_base64,
                    page_number=page_num + 1,
                )
                
                if ocr_result.text:
                    # Update the text for this page
                    for i, part in enumerate(text_parts):
                        if part[0] == page_num:
                            text_parts[i] = (page_num, ocr_result.text, False)
                            break
            
            doc.close()
            
        except Exception as e:
            print(f"[DocumentAgent] Page OCR processing failed: {e}")
        
        return text_parts
    
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
    
    async def _generate_chunk_contexts(
        self, 
        chunks: List[str],
        filename: str,
        subject: Optional[str] = None,
        batch_size: int = 5,
    ) -> List[str]:
        """
        Generate contextual descriptions for each chunk.
        
        This implements Contextual Retrieval where each chunk is enriched
        with LLM-generated context explaining its relevance to the document.
        
        Args:
            chunks: List of chunk texts
            filename: Document filename for context
            subject: Optional subject for better context
            batch_size: Number of chunks to process in parallel
            
        Returns:
            List of context strings, one per chunk
        """
        if not chunks:
            return []
        
        # Check if contextual retrieval is enabled (disabled by default for speed)
        enable_contexts = os.getenv("ENABLE_CONTEXTUAL_RETRIEVAL", "false").lower() == "true"
        if not enable_contexts:
            print(f"[DocumentAgent] Contextual retrieval disabled (set ENABLE_CONTEXTUAL_RETRIEVAL=true to enable)")
            return [""] * len(chunks)
        
        contexts = []
        
        # System prompt for context generation
        context_system_prompt = """You are a document analyst. Given a chunk of text from a document, 
generate a brief 1-2 sentence context explaining:
1. What this chunk is about
2. How it might relate to the broader document topic

Be concise and factual. Focus on key concepts and terms that would help find this chunk later.
Do not include phrases like "This chunk..." - just state the context directly."""

        try:
            # Process in batches to avoid rate limits
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                
                # Generate contexts in parallel for each batch
                batch_contexts = []
                for j, chunk in enumerate(batch):
                    chunk_preview = chunk[:500] if len(chunk) > 500 else chunk
                    
                    prompt = f"""Document: {filename}
{f'Subject: {subject}' if subject else ''}
Chunk {i + j + 1}:
{chunk_preview}

Generate a brief context (1-2 sentences) for this chunk:"""

                    try:
                        response = await self.llm.generate(
                            prompt=prompt,
                            system_prompt=context_system_prompt,
                            agent_name=self.name,
                        )
                        batch_contexts.append(response.content.strip())
                    except Exception as e:
                        print(f"[DocumentAgent] Context generation failed for chunk {i + j}: {e}")
                        batch_contexts.append("")
                
                contexts.extend(batch_contexts)
            
            return contexts
            
        except Exception as e:
            print(f"[DocumentAgent] Context generation failed: {e}")
            # Return empty contexts - graceful degradation
            return [""] * len(chunks)
    
    async def _generate_document_summary(
        self,
        text: str,
        filename: str,
        subject: Optional[str] = None,
    ) -> str:
        """
        Generate a comprehensive summary of the entire document using map-reduce approach.
        
        Processes the document in batches to ensure complete coverage of all content,
        which is critical for academic/educational documents.
        
        Args:
            text: Full document text
            filename: Document filename
            subject: Optional subject
            
        Returns:
            Comprehensive document summary covering all sections
        """
        text_length = len(text)
        print(f"[DocumentAgent] Summarizing document ({text_length} chars)...")
        
        # For short documents, summarize directly
        if text_length <= 10000:
            return await self._summarize_text_chunk(text, filename, subject, is_final=True)
        
        # For longer documents, use map-reduce approach
        # Step 1: MAP - Split into chunks and summarize each
        chunk_size = 8000  # Characters per chunk (fits well in context window)
        chunks = []
        
        for i in range(0, text_length, chunk_size):
            chunk = text[i:i + chunk_size]
            chunks.append(chunk)
        
        print(f"[DocumentAgent] Processing {len(chunks)} chunks for comprehensive summary...")
        
        # Generate summary for each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            print(f"[DocumentAgent] Summarizing chunk {i+1}/{len(chunks)}...")
            try:
                chunk_summary = await self._summarize_text_chunk(
                    chunk, 
                    filename, 
                    subject, 
                    chunk_num=i+1,
                    total_chunks=len(chunks),
                    is_final=False
                )
                if chunk_summary:
                    chunk_summaries.append(f"[Section {i+1}] {chunk_summary}")
            except Exception as e:
                print(f"[DocumentAgent] Failed to summarize chunk {i+1}: {e}")
                continue
        
        if not chunk_summaries:
            print("[DocumentAgent] No chunk summaries generated, using fallback")
            return await self._summarize_text_chunk(text[:10000], filename, subject, is_final=True)
        
        # Step 2: REDUCE - Combine all chunk summaries into final comprehensive summary
        print(f"[DocumentAgent] Combining {len(chunk_summaries)} section summaries...")
        combined_summaries = "\n\n".join(chunk_summaries)
        
        reduce_prompt = f"""Document: {filename}
{f'Subject: {subject}' if subject else ''}
Total document length: ~{text_length // 1000}k characters ({len(chunks)} sections)

The following are summaries of each section of the document:

{combined_summaries}

Based on ALL the section summaries above, create a comprehensive document summary that:
1. Describes the overall purpose and scope of the document
2. Lists ALL major topics, chapters, or units covered
3. Highlights key concepts, formulas, or important points throughout
4. Identifies the syllabus structure or learning progression if applicable
5. Notes any important examples, exercises, or assessment sections

Write a detailed, comprehensive summary (8-15 sentences) that captures everything important in this educational document:"""

        try:
            response = await self.llm.generate(
                prompt=reduce_prompt,
                system_prompt="You are an educational document summarizer. Create comprehensive summaries that capture ALL major topics and sections, as this will be used to help students understand the full scope of their study material.",
                agent_name=self.name,
            )
            final_summary = response.content.strip()
            print(f"[DocumentAgent] Comprehensive summary generated ({len(final_summary)} chars)")
            return final_summary
        except Exception as e:
            print(f"[DocumentAgent] Final summary generation failed: {e}")
            # Fallback: join chunk summaries
            return " ".join([s.replace(f"[Section {i+1}] ", "") for i, s in enumerate(chunk_summaries)])
    
    async def _summarize_text_chunk(
        self,
        text: str,
        filename: str,
        subject: Optional[str] = None,
        chunk_num: int = 0,
        total_chunks: int = 0,
        is_final: bool = False,
    ) -> str:
        """Summarize a single chunk of text."""
        if is_final:
            prompt = f"""Document: {filename}
{f'Subject: {subject}' if subject else ''}

Content:
{text}

Generate a comprehensive summary of this document that includes:
- Main topics and purpose
- Key sections or chapters
- Important concepts and learning points
- Target audience or grade level

Write a detailed summary (4-8 sentences):"""
        else:
            prompt = f"""Document: {filename} (Section {chunk_num} of {total_chunks})
{f'Subject: {subject}' if subject else ''}

Content from this section:
{text}

Summarize the key topics, concepts, and important points covered in this section (2-4 sentences):"""

        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt="You are an educational content summarizer. Extract and summarize all important topics, concepts, and learning points.",
                agent_name=self.name,
            )
            return response.content.strip()
        except Exception as e:
            print(f"[DocumentAgent] Chunk summary failed: {e}")
            return ""
    
    async def _generate_section_summaries(
        self,
        text: str,
        filename: str,
        subject: Optional[str] = None,
    ) -> List[dict]:
        """
        Detect sections/chapters in the document and generate summaries for each.
        
        Returns a list of section summaries with metadata for indexing.
        """
        import re
        
        # Patterns to detect section headers
        section_patterns = [
            r'(?:^|\n)\s*(?:CHAPTER|Chapter|UNIT|Unit)\s*[:\-]?\s*(\d+|[IVXivx]+)[\s:.\-]*([^\n]+)',
            r'(?:^|\n)\s*(?:SECTION|Section)\s*[:\-]?\s*(\d+|[A-Za-z])[\s:.\-]*([^\n]+)',
            r'(?:^|\n)\s*(?:PART|Part)\s*[:\-]?\s*(\d+|[IVXivx]+|[A-Z])[\s:.\-]*([^\n]+)',
            r'(?:^|\n)\s*(\d+)\.\s*([A-Z][^\n]{5,50})',  # "1. Topic Name" format
            r'(?:^|\n)\s*([IVXivx]+)\.\s*([A-Z][^\n]{5,50})',  # "IV. Topic Name" format
        ]
        
        sections = []
        
        # Find all section headers
        for pattern in section_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                section_num = match.group(1)
                section_title = match.group(2).strip() if match.lastindex >= 2 else ""
                start_pos = match.start()
                
                sections.append({
                    "number": section_num,
                    "title": section_title,
                    "start": start_pos,
                    "header": match.group(0).strip(),
                })
        
        if not sections:
            print(f"[DocumentAgent] No sections detected in document")
            return []
        
        # Sort by position and remove duplicates
        sections = sorted(sections, key=lambda x: x["start"])
        
        # Deduplicate overlapping sections
        unique_sections = []
        last_start = -1000
        for s in sections:
            if s["start"] - last_start > 100:  # At least 100 chars apart
                unique_sections.append(s)
                last_start = s["start"]
        sections = unique_sections
        
        if len(sections) > 50:
            # Too many sections indicates fragmentation.
            # Try filtering for only "Major" headers (Chapter/Unit/Part)
            major_sections = [s for s in sections if any(x in s['header'].upper() for x in ['CHAPTER', 'UNIT', 'PART'])]
            
            if len(major_sections) >= 3:
                print(f"[DocumentAgent] High fragmentation ({len(sections)} sections). Switching to Major Headers only.")
                sections = major_sections
        
        # Check for fragmentation again
        avg_len = len(text) / max(1, len(sections))
        is_fragmented = len(sections) > 40 and avg_len < 3000
        
        # Fallback: Page-based grouping if sections are poor or too fragmented
        if not sections or is_fragmented:
            print(f"[DocumentAgent] Section detection inadequate (Count: {len(sections)}, AvgLen: {int(avg_len)}). Using Page-Based Grouping.")
            
            # Group text into 10-page chunks (approx 20-30k chars) 
            # consistently covering the WHOLE document
            total_chars = len(text)
            chunk_size = 25000  # Approx 8-10 pages worth of text
            sections = []
            
            for i in range(0, total_chars, chunk_size):
                end = min(i + chunk_size, total_chars)
                page_est_start = (i // 3000) + 1
                page_est_end = (end // 3000) + 1
                
                sections.append({
                    "number": f"{page_est_start}-{page_est_end}",
                    "title": f"Pages {page_est_start}-{page_est_end}",
                    "start": i,
                    "header": f"Pages {page_est_start}-{page_est_end}",
                })

        print(f"[DocumentAgent] Final Sections: {len(sections)}. Generating summaries...")
        
        # Extract content for each section and generate summaries
        section_summaries = []
        for i, section in enumerate(sections):
            # Get section content (text between this header and next)
            start = section["start"]
            end = sections[i + 1]["start"] if i + 1 < len(sections) else len(text)
            
            # Increased limit to 15000 chars per section
            section_content = text[start:min(start + 15000, end)]
            
            if len(section_content) < 100:  # Skip very short sections
                continue
            
            try:
                prompt = f"""Section: {section.get("title", "Unknown")}

Content:
{section_content}

Summarize this section's main topics and key points (2-3 sentences):"""

                response = await self.llm.generate(
                    prompt=prompt,
                    system_prompt="You are summarizing educational content. Be concise and capture key learning points.",
                    agent_name=self.name,
                )
                
                section_summaries.append({
                    "section_number": section["number"],
                    "section_title": section.get("title", ""),
                    "summary": response.content.strip(),
                    "type": "section_summary",
                    "is_meta_chunk": True,
                })
                
                print(f"[DocumentAgent] Summarized section {i+1}: {section.get('title', 'Unknown')[:30]}...")
                
            except Exception as e:
                print(f"[DocumentAgent] Failed to summarize section {i+1}: {e}")
                continue
        
        print(f"[DocumentAgent] Generated {len(section_summaries)} section summaries")
        return section_summaries
    
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
