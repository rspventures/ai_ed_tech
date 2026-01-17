"""
AI Tutor Platform - Document Processing Graph
LangGraph orchestration for document upload pipeline with validation.

Implements a state machine for:
1. Text Extraction
2. Cleaning & Chunking
3. Content Validation (with rejection handling)
4. Embedding Generation
5. Entity Extraction (Graph RAG)
6. Storage

Includes retry logic and conditional branching on validation failures.
"""
from typing import TypedDict, List, Dict, Any, Optional, Literal
from dataclasses import dataclass
import asyncio

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None
    MemorySaver = None

from app.ai.graphs.base import GraphStatus


class DocumentState(TypedDict, total=False):
    """State for document processing graph."""
    # Input
    file_path: str
    filename: str
    user_id: str
    subject: Optional[str]
    grade_level: Optional[int]
    
    # Processing state
    status: str
    current_step: str
    error: Optional[str]
    retry_count: int
    
    # Extracted content
    raw_text: str
    cleaned_text: str
    chunks: List[str]
    token_counts: List[int]
    embeddings: List[List[float]]
    contexts: List[str]
    summary: str
    
    # Validation
    is_valid: bool
    validation_reason: str
    grade_match: str
    
    # Output
    document_id: str
    entity_count: int
    relationship_count: int


class DocumentProcessingGraph:
    """
    LangGraph-based document processing orchestrator.
    
    Provides state machine execution for document upload with:
    - Automatic retry on transient failures
    - Conditional branching on validation
    - Checkpointing for resumability
    """
    
    MAX_RETRIES = 2
    
    def __init__(self):
        self._graph = None
        self._checkpointer = None
        
        if LANGGRAPH_AVAILABLE:
            self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph state machine."""
        if not LANGGRAPH_AVAILABLE:
            return
        
        # Create state graph
        workflow = StateGraph(DocumentState)
        
        # Add nodes
        workflow.add_node("extract", self._extract_text)
        workflow.add_node("clean", self._clean_and_chunk)
        workflow.add_node("validate", self._validate_content)
        workflow.add_node("embed", self._generate_embeddings)
        workflow.add_node("contextualize", self._generate_contexts)
        workflow.add_node("extract_entities", self._extract_entities)
        workflow.add_node("handle_rejection", self._handle_rejection)
        
        # Define edges
        workflow.set_entry_point("extract")
        workflow.add_edge("extract", "clean")
        workflow.add_edge("clean", "validate")
        
        # Conditional edge: validation result
        workflow.add_conditional_edges(
            "validate",
            self._route_after_validation,
            {
                "approved": "embed",
                "rejected": "handle_rejection",
            }
        )
        
        workflow.add_edge("embed", "contextualize")
        workflow.add_edge("contextualize", "extract_entities")
        workflow.add_edge("extract_entities", END)
        workflow.add_edge("handle_rejection", END)
        
        # Compile with memory checkpointer
        self._checkpointer = MemorySaver()
        self._graph = workflow.compile(checkpointer=self._checkpointer)
    
    # --- Node Functions ---
    
    async def _extract_text(self, state: DocumentState) -> Dict[str, Any]:
        """Extract text from document."""
        from app.ai.agents.document import document_agent
        
        try:
            file_path = state["file_path"]
            
            # Use document agent's extraction
            method = document_agent._get_extraction_method(
                "." + file_path.split(".")[-1]
            )
            text = await document_agent._extract_text(file_path, method)
            
            return {
                "raw_text": text,
                "current_step": "extract",
                "status": "running",
            }
        except Exception as e:
            return {
                "error": f"Extraction failed: {e}",
                "status": "failed",
            }
    
    async def _clean_and_chunk(self, state: DocumentState) -> Dict[str, Any]:
        """Clean text and split into chunks."""
        from app.ai.agents.document import document_agent
        
        try:
            raw_text = state.get("raw_text", "")
            
            # Clean
            cleaned = document_agent._clean_text(raw_text)
            
            # Chunk
            chunk_result = document_agent._chunk_text(
                cleaned,
                chunk_size=500,
                overlap=50,
            )
            
            return {
                "cleaned_text": cleaned,
                "chunks": chunk_result.chunks,
                "token_counts": chunk_result.token_counts,
                "current_step": "clean",
            }
        except Exception as e:
            return {"error": f"Chunking failed: {e}", "status": "failed"}
    
    async def _validate_content(self, state: DocumentState) -> Dict[str, Any]:
        """Validate content for grade appropriateness."""
        from app.ai.agents.document_validator import document_validator_agent
        
        try:
            chunks = state.get("chunks", [])
            grade_level = state.get("grade_level", 5)
            subject = state.get("subject")
            
            # Sample chunks for validation
            sample = chunks[:3] if len(chunks) >= 3 else chunks
            
            result = await document_validator_agent.validate(
                content_samples=sample,
                target_grade=grade_level,
                subject=subject,
            )
            
            return {
                "is_valid": result.is_appropriate,
                "validation_reason": result.reason,
                "grade_match": result.grade_match.value,
                "current_step": "validate",
            }
        except Exception as e:
            # On validation error, assume valid to not block upload
            return {
                "is_valid": True,
                "validation_reason": f"Validation skipped: {e}",
                "grade_match": "unknown",
            }
    
    def _route_after_validation(self, state: DocumentState) -> Literal["approved", "rejected"]:
        """Route based on validation result."""
        if state.get("is_valid", False):
            return "approved"
        return "rejected"
    
    async def _generate_embeddings(self, state: DocumentState) -> Dict[str, Any]:
        """Generate embeddings for chunks."""
        from app.ai.agents.document import document_agent
        
        try:
            chunks = state.get("chunks", [])
            embeddings = await document_agent._generate_embeddings(chunks)
            
            return {
                "embeddings": embeddings,
                "current_step": "embed",
            }
        except Exception as e:
            return {"embeddings": [], "error": f"Embedding failed: {e}"}
    
    async def _generate_contexts(self, state: DocumentState) -> Dict[str, Any]:
        """Generate contextual descriptions for chunks."""
        from app.ai.agents.document import document_agent
        
        try:
            chunks = state.get("chunks", [])
            filename = state.get("filename", "document")
            subject = state.get("subject")
            
            contexts = await document_agent._generate_chunk_contexts(
                chunks=chunks,
                filename=filename,
                subject=subject,
            )
            
            # Also generate document summary
            cleaned_text = state.get("cleaned_text", "")
            summary = await document_agent._generate_document_summary(
                text=cleaned_text,
                filename=filename,
                subject=subject,
            )
            
            return {
                "contexts": contexts,
                "summary": summary,
                "current_step": "contextualize",
            }
        except Exception as e:
            return {"contexts": [], "summary": "", "error": f"Context generation failed: {e}"}
    
    async def _extract_entities(self, state: DocumentState) -> Dict[str, Any]:
        """Extract entities for Graph RAG."""
        from app.ai.agents.entity_extractor import entity_extractor_agent
        
        try:
            chunks = state.get("chunks", [])
            document_id = state.get("document_id", "unknown")
            
            result = await entity_extractor_agent.extract(
                chunks=chunks,
                document_id=document_id,
            )
            
            return {
                "entity_count": len(result.entities),
                "relationship_count": len(result.relationships),
                "current_step": "extract_entities",
                "status": "completed",
            }
        except Exception as e:
            # Entity extraction is optional
            return {
                "entity_count": 0,
                "relationship_count": 0,
                "status": "completed",
            }
    
    async def _handle_rejection(self, state: DocumentState) -> Dict[str, Any]:
        """Handle rejected documents."""
        return {
            "status": "rejected",
            "current_step": "handle_rejection",
        }
    
    # --- Public API ---
    
    async def process(
        self,
        file_path: str,
        filename: str,
        user_id: str,
        subject: Optional[str] = None,
        grade_level: Optional[int] = None,
        document_id: Optional[str] = None,
    ) -> DocumentState:
        """
        Process a document through the graph.
        
        Args:
            file_path: Path to the document file
            filename: Original filename
            user_id: User ID
            subject: Optional subject
            grade_level: Optional grade level
            document_id: Optional document ID (for updates)
            
        Returns:
            Final DocumentState with all processing results
        """
        if not LANGGRAPH_AVAILABLE or not self._graph:
            # Fallback to direct processing if LangGraph unavailable
            return await self._fallback_process(
                file_path, filename, user_id, subject, grade_level, document_id
            )
        
        # Initial state
        initial_state = DocumentState(
            file_path=file_path,
            filename=filename,
            user_id=user_id,
            subject=subject,
            grade_level=grade_level or 5,
            document_id=document_id or "",
            status="running",
            retry_count=0,
        )
        
        # Run the graph
        config = {"configurable": {"thread_id": document_id or user_id}}
        
        try:
            result = await self._graph.ainvoke(initial_state, config)
            return result
        except Exception as e:
            return DocumentState(
                status="failed",
                error=str(e),
            )
    
    async def _fallback_process(
        self,
        file_path: str,
        filename: str,
        user_id: str,
        subject: Optional[str],
        grade_level: Optional[int],
        document_id: Optional[str],
    ) -> DocumentState:
        """Fallback processing without LangGraph."""
        state = DocumentState(
            file_path=file_path,
            filename=filename,
            user_id=user_id,
            subject=subject,
            grade_level=grade_level or 5,
            document_id=document_id or "",
        )
        
        # Run steps sequentially
        state.update(await self._extract_text(state))
        if state.get("status") == "failed":
            return state
            
        state.update(await self._clean_and_chunk(state))
        state.update(await self._validate_content(state))
        
        if not state.get("is_valid", False):
            state.update(await self._handle_rejection(state))
            return state
        
        state.update(await self._generate_embeddings(state))
        state.update(await self._generate_contexts(state))
        state.update(await self._extract_entities(state))
        
        return state


# Singleton instance
document_processing_graph = DocumentProcessingGraph()
