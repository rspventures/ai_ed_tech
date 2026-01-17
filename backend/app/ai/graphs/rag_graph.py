"""
AI Tutor Platform - RAG Query Graph
LangGraph orchestration for Corrective RAG with self-correction.

Implements Corrective RAG pattern:
1. Retrieve relevant chunks
2. Grade document relevance
3. If not relevant: rewrite query and retry (max 2x)
4. Generate response
5. Self-critique and verify grounding
6. Regenerate if not grounded

This provides more accurate responses by detecting and correcting
retrieval failures before generating answers.
"""
from typing import TypedDict, List, Dict, Any, Optional, Literal
from dataclasses import dataclass

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None
    MemorySaver = None


class RAGState(TypedDict, total=False):
    """State for RAG query graph."""
    # Input
    query: str
    original_query: str
    user_id: str
    document_id: Optional[str]
    grade: int
    
    # Retrieval state
    query_embedding: List[float]
    retrieved_chunks: List[Dict[str, Any]]
    chunks_relevant: bool
    relevance_scores: List[float]
    
    # Query rewriting
    rewrite_count: int
    rewritten_query: Optional[str]
    
    # Generation
    response: str
    is_grounded: bool
    confidence: float
    
    # Control flow
    current_step: str
    status: str
    error: Optional[str]


class RAGQueryGraph:
    """
    LangGraph-based Corrective RAG orchestrator.
    
    Implements self-correcting retrieval with:
    - Relevance grading of retrieved documents
    - Query rewriting on low relevance
    - Grounding verification of responses
    - Automatic regeneration if ungrounded
    """
    
    MAX_REWRITES = 2
    RELEVANCE_THRESHOLD = 0.5
    
    def __init__(self):
        self._graph = None
        self._checkpointer = None
        self._embeddings_model = None
        
        if LANGGRAPH_AVAILABLE:
            self._build_graph()
    
    @property
    def embeddings_model(self):
        """Lazy load embeddings model."""
        if self._embeddings_model is None:
            from langchain_openai import OpenAIEmbeddings
            from app.core.config import settings
            self._embeddings_model = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=settings.OPENAI_API_KEY
            )
        return self._embeddings_model
    
    def _build_graph(self):
        """Build the Corrective RAG state machine."""
        if not LANGGRAPH_AVAILABLE:
            return
        
        workflow = StateGraph(RAGState)
        
        # Add nodes
        workflow.add_node("embed_query", self._embed_query)
        workflow.add_node("retrieve", self._retrieve_chunks)
        workflow.add_node("grade_relevance", self._grade_relevance)
        workflow.add_node("rewrite_query", self._rewrite_query)
        workflow.add_node("generate", self._generate_response)
        workflow.add_node("check_grounding", self._check_grounding)
        workflow.add_node("regenerate", self._regenerate_response)
        
        # Entry point
        workflow.set_entry_point("embed_query")
        
        # Edges
        workflow.add_edge("embed_query", "retrieve")
        workflow.add_edge("retrieve", "grade_relevance")
        
        # Conditional: relevance check
        workflow.add_conditional_edges(
            "grade_relevance",
            self._route_after_grading,
            {
                "relevant": "generate",
                "not_relevant": "rewrite_query",
                "give_up": "generate",  # Use what we have
            }
        )
        
        workflow.add_edge("rewrite_query", "embed_query")  # Loop back
        workflow.add_edge("generate", "check_grounding")
        
        # Conditional: grounding check
        workflow.add_conditional_edges(
            "check_grounding",
            self._route_after_grounding,
            {
                "grounded": END,
                "not_grounded": "regenerate",
            }
        )
        
        workflow.add_edge("regenerate", END)
        
        # Compile
        self._checkpointer = MemorySaver()
        self._graph = workflow.compile(checkpointer=self._checkpointer)
    
    # --- Node Functions ---
    
    async def _embed_query(self, state: RAGState) -> Dict[str, Any]:
        """Generate embedding for the query."""
        query = state.get("rewritten_query") or state.get("query", "")
        
        try:
            embedding = await self.embeddings_model.aembed_query(query)
            return {
                "query_embedding": embedding,
                "current_step": "embed_query",
            }
        except Exception as e:
            return {"error": f"Embedding failed: {e}", "status": "failed"}
    
    async def _retrieve_chunks(self, state: RAGState) -> Dict[str, Any]:
        """Retrieve relevant chunks using hybrid search."""
        from app.core.database import async_session_maker
        from app.services.document import DocumentService
        
        try:
            query = state.get("rewritten_query") or state.get("query", "")
            embedding = state.get("query_embedding", [])
            user_id = state.get("user_id", "")
            document_id = state.get("document_id")
            
            async with async_session_maker() as db:
                service = DocumentService(db)
                
                try:
                    results = await service.hybrid_search_chunks(
                        query=query,
                        query_embedding=embedding,
                        user_id=user_id,
                        document_id=document_id,
                        limit=5,
                        use_reranker=True,
                    )
                except Exception:
                    results = await service.search_chunks(
                        query_embedding=embedding,
                        user_id=user_id,
                        document_id=document_id,
                        limit=5,
                    )
            
            return {
                "retrieved_chunks": results,
                "current_step": "retrieve",
            }
        except Exception as e:
            return {"error": f"Retrieval failed: {e}", "status": "failed"}
    
    async def _grade_relevance(self, state: RAGState) -> Dict[str, Any]:
        """Grade the relevance of retrieved chunks."""
        chunks = state.get("retrieved_chunks", [])
        
        if not chunks:
            return {
                "chunks_relevant": False,
                "relevance_scores": [],
                "current_step": "grade_relevance",
            }
        
        # Use similarity scores as relevance indicator
        scores = [c.get("similarity", 0) for c in chunks]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        relevant = avg_score >= self.RELEVANCE_THRESHOLD
        
        return {
            "chunks_relevant": relevant,
            "relevance_scores": scores,
            "current_step": "grade_relevance",
        }
    
    def _route_after_grading(self, state: RAGState) -> Literal["relevant", "not_relevant", "give_up"]:
        """Route based on relevance grading."""
        if state.get("chunks_relevant", False):
            return "relevant"
        
        rewrite_count = state.get("rewrite_count", 0)
        if rewrite_count >= self.MAX_REWRITES:
            return "give_up"
        
        return "not_relevant"
    
    async def _rewrite_query(self, state: RAGState) -> Dict[str, Any]:
        """Rewrite query for better retrieval."""
        from app.ai.core.llm import get_llm, LLMType
        
        query = state.get("query", "")
        rewrite_count = state.get("rewrite_count", 0)
        
        try:
            llm = get_llm(LLMType.FAST)
            
            prompt = f"""The following search query didn't return relevant results.
Rewrite it to be more specific and likely to match document content.

Original query: {query}

Return ONLY the rewritten query, nothing else."""

            response = await llm.generate(
                prompt=prompt,
                system_prompt="You are a query rewriting assistant.",
                agent_name="RAGQueryGraph",
            )
            
            return {
                "rewritten_query": response.content.strip(),
                "rewrite_count": rewrite_count + 1,
                "current_step": "rewrite_query",
            }
        except Exception as e:
            return {"rewritten_query": query, "rewrite_count": rewrite_count + 1}
    
    async def _generate_response(self, state: RAGState) -> Dict[str, Any]:
        """Generate response from retrieved context."""
        from app.ai.core.llm import get_llm, LLMType
        
        query = state.get("rewritten_query") or state.get("query", "")
        chunks = state.get("retrieved_chunks", [])
        grade = state.get("grade", 5)
        
        # Build context
        context = "\n\n---\n\n".join([
            f"[Source {i+1}]: {c.get('content', '')}"
            for i, c in enumerate(chunks)
        ])
        
        try:
            llm = get_llm(LLMType.SMART)
            
            system_prompt = f"""You are an educational assistant answering questions for Grade {grade} students.
Answer ONLY based on the provided context. If the context doesn't contain the answer, say so.

CONTEXT:
{context}"""

            response = await llm.generate(
                prompt=query,
                system_prompt=system_prompt,
                agent_name="RAGQueryGraph",
            )
            
            return {
                "response": response.content,
                "current_step": "generate",
            }
        except Exception as e:
            return {"response": f"Error generating response: {e}", "status": "failed"}
    
    async def _check_grounding(self, state: RAGState) -> Dict[str, Any]:
        """Check if response is grounded in sources."""
        response = state.get("response", "")
        chunks = state.get("retrieved_chunks", [])
        
        # Simple grounding check: does response contain source terms?
        chunk_texts = [c.get("content", "").lower() for c in chunks]
        response_lower = response.lower()
        
        # Check for key term overlap
        grounded = False
        for chunk_text in chunk_texts:
            # Check if significant words from chunk appear in response
            words = chunk_text.split()[:20]  # First 20 words
            overlap = sum(1 for w in words if len(w) > 4 and w in response_lower)
            if overlap >= 3:
                grounded = True
                break
        
        # Also consider if response admits lack of information
        if "couldn't find" in response_lower or "not in the document" in response_lower:
            grounded = True
        
        return {
            "is_grounded": grounded,
            "confidence": 0.8 if grounded else 0.3,
            "current_step": "check_grounding",
            "status": "completed" if grounded else "needs_verification",
        }
    
    def _route_after_grounding(self, state: RAGState) -> Literal["grounded", "not_grounded"]:
        """Route based on grounding check."""
        if state.get("is_grounded", False):
            return "grounded"
        return "not_grounded"
    
    async def _regenerate_response(self, state: RAGState) -> Dict[str, Any]:
        """Regenerate response with stronger grounding instruction."""
        from app.ai.core.llm import get_llm, LLMType
        
        query = state.get("query", "")
        chunks = state.get("retrieved_chunks", [])
        grade = state.get("grade", 5)
        
        context = "\n\n".join([
            f"[{i+1}] {c.get('content', '')}"
            for i, c in enumerate(chunks)
        ])
        
        try:
            llm = get_llm(LLMType.SMART)
            
            system_prompt = f"""You are an educational assistant for Grade {grade} students.
CRITICAL: You MUST answer ONLY using the information in the context below.
If the answer is not in the context, explicitly say "I couldn't find this in your document."
Quote specific parts of the context when answering.

CONTEXT:
{context}"""

            response = await llm.generate(
                prompt=query,
                system_prompt=system_prompt,
                agent_name="RAGQueryGraph",
            )
            
            return {
                "response": response.content,
                "is_grounded": True,  # Assume grounded after explicit instruction
                "confidence": 0.6,
                "current_step": "regenerate",
                "status": "completed",
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    # --- Public API ---
    
    async def query(
        self,
        query: str,
        user_id: str,
        document_id: Optional[str] = None,
        grade: int = 5,
    ) -> RAGState:
        """
        Execute a RAG query with self-correction.
        
        Args:
            query: User's question
            user_id: User ID for access control
            document_id: Optional document scope
            grade: Student grade level
            
        Returns:
            Final RAGState with response
        """
        initial_state = RAGState(
            query=query,
            original_query=query,
            user_id=user_id,
            document_id=document_id,
            grade=grade,
            rewrite_count=0,
            status="running",
        )
        
        if not LANGGRAPH_AVAILABLE or not self._graph:
            return await self._fallback_query(initial_state)
        
        try:
            config = {"configurable": {"thread_id": f"{user_id}:{document_id or 'all'}"}}
            result = await self._graph.ainvoke(initial_state, config)
            return result
        except Exception as e:
            return RAGState(status="failed", error=str(e))
    
    async def _fallback_query(self, state: RAGState) -> RAGState:
        """Fallback query processing without LangGraph."""
        state.update(await self._embed_query(state))
        if state.get("status") == "failed":
            return state
        
        state.update(await self._retrieve_chunks(state))
        state.update(await self._grade_relevance(state))
        
        # Simple retry logic
        if not state.get("chunks_relevant") and state.get("rewrite_count", 0) < self.MAX_REWRITES:
            state.update(await self._rewrite_query(state))
            state.update(await self._embed_query(state))
            state.update(await self._retrieve_chunks(state))
        
        state.update(await self._generate_response(state))
        state.update(await self._check_grounding(state))
        
        if not state.get("is_grounded"):
            state.update(await self._regenerate_response(state))
        
        return state


# Singleton instance
rag_query_graph = RAGQueryGraph()
