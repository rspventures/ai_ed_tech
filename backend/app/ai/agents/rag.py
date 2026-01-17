"""
AI Tutor Platform - RAG Agent
Retrieval-Augmented Generation agent for document Q&A and quiz generation.

Implements Adaptive RAG pattern:
1. Query Analysis - Determine if retrieval is needed
2. Retrieval - Get relevant chunks from user documents
3. Relevance Check - Evaluate chunk quality (Corrective RAG)
4. Generation - Generate response grounded in retrieved context
5. Self-Check - Verify response is grounded (reduce hallucination)
"""
import uuid
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass, field
from enum import Enum

from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.ai.core.telemetry import get_tracer
from app.core.config import settings


class RAGMode(str, Enum):
    """RAG operation modes."""
    CHAT = "chat"  # Conversational Q&A with document
    QUIZ = "quiz"  # Generate questions from document


@dataclass
class RetrievedChunk:
    """A retrieved document chunk with metadata."""
    content: str
    chunk_id: str
    document_id: str
    filename: str
    similarity: float
    chunk_index: int


@dataclass
class RAGResponse:
    """Response from RAG agent."""
    answer: str
    sources: List[RetrievedChunk]
    mode: RAGMode
    grounded: bool  # Whether response is grounded in sources
    confidence: float
    session_id: Optional[str] = None  # For chat history persistence


@dataclass
class QuizQuestion:
    """A question generated from document content."""
    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    source_chunk: str  # Reference to source content


class RAGAgent(BaseAgent):
    """
    Retrieval-Augmented Generation Agent 📚
    
    Provides document-grounded responses using Adaptive RAG pattern:
    
    1. **Query Analysis**: Determine complexity and retrieval need
    2. **Adaptive Retrieval**: Fetch relevant chunks if needed
    3. **Relevance Evaluation**: Score and filter retrieved chunks
    4. **Grounded Generation**: Generate response based on context
    5. **Self-Reflection**: Verify response fidelity to sources
    
    Modes:
    - CHAT: Answer questions about uploaded documents
    - QUIZ: Generate practice questions from document content
    """
    
    name = "RAGAgent"
    description = "Document-grounded Q&A and quiz generation"
    version = "1.0.0"
    
    # Retrieval settings
    DEFAULT_TOP_K = 5
    RELEVANCE_THRESHOLD = 0.3  # Lowered from 0.5 for better recall without Cohere
    
    # System prompts
    CHAT_SYSTEM_PROMPT = """You are an educational assistant helping students with their study materials.

You will answer questions in TWO parts:

📚 **FROM YOUR DOCUMENT:**
Answer based on the provided document context. Quote or reference specific parts.
If the document doesn't cover this topic, write: "This topic is not covered in your document."

💡 **ADDITIONAL INFORMATION:**
After the document-based answer, you may add helpful context, explanations, or examples from general knowledge.
Clearly introduce this section with "💡 **Additional Information:**" so students know it's beyond their document.
Keep this appropriate for Grade {grade} level.

RULES:
1. ALWAYS clearly separate document content from additional information
2. If the question is completely unrelated to the document's subject matter, indicate this clearly
3. Be educational, clear, and age-appropriate for Grade {grade}
4. Use the document's terminology and examples when available

PREVIOUS CONVERSATION SUMMARY:
{summary}

RECENT MESSAGES:
{history}

DOCUMENT CONTEXT:
{context}

DOCUMENT SUBJECT: {subject}

---
Answer the student's question, clearly attributing what's from the document vs additional knowledge."""
    
    RELEVANCE_CHECK_PROMPT = """Analyze if this student query is relevant to the document content provided.

DOCUMENT SUMMARY: {summary}
DOCUMENT SUBJECT: {subject}

STUDENT QUERY: {query}

Respond with ONLY a JSON object:
{{
    "is_relevant": true/false,
    "relevance_score": 0.0-1.0,
    "reason": "brief explanation",
    "suggested_topic": "if irrelevant, what topic does the query relate to"
}}"""

    QUIZ_SYSTEM_PROMPT = """You are an educational quiz generator. Create questions ONLY from the provided document content.

RULES:
1. Questions must be directly answerable from the provided context.
2. Create age-appropriate questions for Grade {grade}.
3. Include a mix of difficulty levels.
4. Each question needs 4 options with exactly 1 correct answer.
5. Provide a brief explanation referencing the source text.

DOCUMENT CONTEXT:
{context}

---
Generate {num_questions} multiple-choice questions from the above content.

Return as JSON array:
[
  {{
    "question": "Question text?",
    "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
    "correct_answer": "Option A text",
    "explanation": "This is correct because the document states..."
  }}
]

IMPORTANT: The correct_answer MUST be the exact, complete text of the correct option from the options array, NOT just the letter (A, B, C, D)."""

    RELEVANCE_CHECK_PROMPT = """Evaluate if these document chunks are relevant to the question.

QUESTION: {question}

CHUNKS:
{chunks}

For each chunk, return a relevance score 0-1 and brief reason.
Return as JSON: {{"scores": [{{"chunk_id": "...", "score": 0.8, "reason": "..."}}]}}"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._embeddings_model = None
    
    @property
    def embeddings_model(self):
        """Lazy load embeddings model."""
        if self._embeddings_model is None:
            from langchain_openai import OpenAIEmbeddings
            self._embeddings_model = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=settings.OPENAI_API_KEY
            )
        return self._embeddings_model
    
    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """
        Plan the RAG operation.
        
        Analyzes query and determines retrieval strategy.
        """
        metadata = context.metadata
        
        mode = metadata.get("mode", RAGMode.CHAT)
        document_id = metadata.get("document_id")
        user_id = metadata.get("user_id")
        grade = metadata.get("grade", 5)
        num_questions = metadata.get("num_questions", 5)
        
        if not document_id and not metadata.get("search_all"):
            return {
                "action": "error",
                "error": "No document_id provided. Specify a document or set search_all=True."
            }
        
        if not user_id:
            return {
                "action": "error", 
                "error": "user_id is required for document access control."
            }
        
        # Determine retrieval strategy
        query = context.user_input
        top_k = metadata.get("top_k", self.DEFAULT_TOP_K)
        
        # For quiz mode, we need more context
        if mode == RAGMode.QUIZ:
            top_k = max(top_k, 10)
        
        return {
            "action": "rag_operation",
            "params": {
                "mode": mode,
                "query": query,
                "document_id": document_id,
                "user_id": user_id,
                "grade": grade,
                "top_k": top_k,
                "num_questions": num_questions,
                "search_all": metadata.get("search_all", False),
            }
        }
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """
        Execute RAG operation with Adaptive Retrieval.
        """
        tracer = get_tracer()
        
        with tracer.start_as_current_span("rag_operation") as span:
            if plan["action"] == "error":
                return AgentResult(
                    success=False,
                    output=None,
                    state=AgentState.ERROR,
                    error=plan["error"]
                )
            
            params = plan["params"]
            mode = params["mode"]
            
            span.set_attribute("rag.mode", mode.value if isinstance(mode, RAGMode) else mode)
            span.set_attribute("rag.document_id", str(params.get("document_id", "all")))
            
            try:
                # Fetch document metadata for context (Subject)
                subject = "General Education"
                if params.get("document_id") and params["document_id"] != "all":
                    try:
                        from app.core.database import async_session_maker
                        from app.models.document import UserDocument
                        from sqlalchemy import select
                        import uuid
                        
                        async with async_session_maker() as db:
                            result = await db.execute(
                                select(UserDocument).where(UserDocument.id == uuid.UUID(params["document_id"]))
                            )
                            doc = result.scalar_one_or_none()
                            if doc and doc.subject:
                                subject = doc.subject
                    except Exception as e:
                        print(f"[RAGAgent] Failed to fetch document subject: {e}")

                # Fetch Chat History & Summary
                session_id = params.get("session_id")
                chat_history = ""
                chat_summary = ""
                
                if session_id:
                    try:
                        from app.core.database import async_session_maker
                        from app.services.chat import ChatService
                        import uuid
                        
                        async with async_session_maker() as db:
                            chat_service = ChatService(db)
                            sid = uuid.UUID(str(session_id))
                            
                            session = await chat_service.get_session(sid)
                            if session and session.summary:
                                chat_summary = session.summary
                                
                            history_msgs = await chat_service.get_history(sid, limit=5)
                            chat_history = "\n".join([f"{m.role.capitalize()}: {m.content}" for m in history_msgs])
                            print(f"[RAGAgent] Loaded history ({len(history_msgs)} msgs) for session {session_id}")
                    except Exception as e:
                        print(f"[RAGAgent] Failed to load chat history: {e}")

                # Step 1.5: Route Query (Meta vs Detail)
                from app.ai.agents.query_router import QueryRouterAgent
                router = QueryRouterAgent()
                
                # REWRITE QUERY WITH HISTORY if available
                current_query = params["query"]
                if chat_history:
                    current_query = await self._rewrite_query_with_history(current_query, chat_history)
                    print(f"[RAGAgent] Using rewritten query for routing: {current_query}")
                
                route_result = await router.run(user_input=current_query)
                
                metadata_filter = None
                search_query = current_query
                embedding_input = current_query  # Text to embed
                
                if route_result.success:
                    route = route_result.output
                    print(f"[RAGAgent] Query routed as {route.type}: {route.reasoning}")
                    span.set_attribute("rag.route_type", route.type)
                    
                    if route.type == "META":
                        # For META queries, prioritize summary and section_summary chunks
                        metadata_filter = {"is_meta_chunk": True}
                        print(f"[RAGAgent] META query - filtering for summary/section chunks")
                        span.set_attribute("rag.using_meta_filter", True)
                    
                    elif route.type == "DETAIL":
                         span.add_event("applying_hyde")
                         print(f"[RAGAgent] Applying HyDE for DETAIL query...")
                         embedding_input = await self._apply_hyde_transformation(
                             query=search_query,
                             subject=subject,
                         )
                         span.set_attribute("rag.used_hyde", True)

                    if route.rewritten_query:
                        # Router might rewrite it further (e.g. for search keywords)
                        print(f"[RAGAgent] Router rewritten query: {route.rewritten_query}")
                        search_query = route.rewritten_query
                        if route.type != "DETAIL":
                            embedding_input = route.rewritten_query
                        span.set_attribute("rag.rewritten_query", route.rewritten_query)

                if mode == RAGMode.QUIZ or mode == "quiz":
                    # --- STRATIFIED SAMPLING FOR QUIZ ---
                    span.add_event("retrieving_chunks_stratified")
                    from app.services.document import DocumentService
                    from app.core.database import async_session_maker
                    
                    async with async_session_maker() as db:
                        service = DocumentService(db)
                        # Get all chunks for doc
                        all_chunks = await service.get_document_chunks(params["document_id"], params["user_id"])
                        
                        # Filter out very short chunks
                        valid_chunks = [c for c in all_chunks if len(c.content) > 100]
                        total_chunks = len(valid_chunks)
                        
                        if total_chunks <= params["num_questions"]:
                            # Use all chunks if document is short
                            chunks_data = valid_chunks
                        else:
                            # Stratified sampling: Beginning, Middle, End
                            stride = total_chunks // params["num_questions"]
                            chunks_data = [valid_chunks[i * stride] for i in range(params["num_questions"])]
                    
                    # Convert to RetrievedChunk objects
                    chunks = [
                        RetrievedChunk(
                            content=c.content,
                            chunk_id=str(c.id),
                            document_id=str(c.document_id),
                            filename="document", # We don't have filename in raw chunk, but quiz generator handles it
                            similarity=1.0, # Artificial score
                            chunk_index=c.chunk_index,
                        )
                        for c in chunks_data
                    ]
                    relevant_chunks = chunks # Skip filtering for quiz

                else:
                    # --- NORMAL VECTOR SEARCH FOR CHAT ---
                    span.add_event("generating_query_embedding")
                    query_embedding = await self.embeddings_model.aembed_query(embedding_input)
                    
                    # Step 2: Retrieve relevant chunks using hybrid search
                    span.add_event("retrieving_chunks_hybrid")
                    
                    # For META queries, do INTELLIGENT retrieval:
                    # 1. Always get document summary (type: "summary")
                    # 2. Get ALL section summaries (for broad questions like "what subjects are covered?")
                    # 3. Get relevant general content chunks
                    if metadata_filter and metadata_filter.get("is_meta_chunk"):
                        from app.services.document import DocumentService
                        from app.core.database import async_session_maker
                        from app.models.document import DocumentChunk
                        from sqlalchemy import select
                        import uuid as uuid_module
                        
                        document_summary_chunk = None
                        section_chunks = []
                        
                        # Step 1: Fetch document summary directly from DB (always include)
                        if params.get("document_id"):
                            try:
                                async with async_session_maker() as db:
                                    doc_id = uuid_module.UUID(params["document_id"])
                                    
                                    # Get document summary (type: "summary")
                                    summary_result = await db.execute(
                                        select(DocumentChunk).where(
                                            DocumentChunk.document_id == doc_id,
                                            DocumentChunk.chunk_metadata["type"].astext == "summary"
                                        )
                                    )
                                    summary_row = summary_result.scalar_one_or_none()
                                    
                                    if summary_row:
                                        document_summary_chunk = RetrievedChunk(
                                            content=summary_row.content,
                                            chunk_id=str(summary_row.id),
                                            document_id=str(summary_row.document_id),
                                            filename="document",
                                            similarity=1.0,  # Always relevant
                                            chunk_index=summary_row.chunk_index,
                                        )
                                        print(f"[RAGAgent] META query - found document summary chunk")
                                    
                                    # Get ALL section summaries (type: "section_summary")
                                    sections_result = await db.execute(
                                        select(DocumentChunk).where(
                                            DocumentChunk.document_id == doc_id,
                                            DocumentChunk.chunk_metadata["type"].astext == "section_summary"
                                        ).order_by(DocumentChunk.chunk_index.desc())
                                    )
                                    section_rows = sections_result.scalars().all()
                                    
                                    for sec in section_rows:
                                        section_chunks.append(RetrievedChunk(
                                            content=sec.content,
                                            chunk_id=str(sec.id),
                                            document_id=str(sec.document_id),
                                            filename="document",
                                            similarity=0.95,  # High relevance for section summaries
                                            chunk_index=sec.chunk_index,
                                        ))
                                    
                                    print(f"[RAGAgent] META query - found {len(section_chunks)} section summary chunks")
                            except Exception as e:
                                print(f"[RAGAgent] Failed to fetch meta chunks from DB: {e}")
                        
                        # Step 2: Get general content chunks (without filter)
                        general_chunks = await self._retrieve_chunks(
                            query_embedding=query_embedding,
                            user_id=params["user_id"],
                            document_id=params.get("document_id"),
                            top_k=params["top_k"],
                            query=search_query,
                            use_hybrid=True,
                            metadata_filter=None,  # No filter for general chunks
                        )
                        print(f"[RAGAgent] META query - retrieved {len(general_chunks)} general chunks")
                        
                        # Step 3: Combine: Document Summary → Section Summaries → General Chunks (deduplicated)
                        combined_chunks = []
                        seen_ids = set()
                        
                        # Add document summary first (if exists)
                        if document_summary_chunk:
                            combined_chunks.append(document_summary_chunk)
                            seen_ids.add(document_summary_chunk.chunk_id)
                        
                        # Add section summaries
                        for sc in section_chunks:
                            if sc.chunk_id not in seen_ids:
                                combined_chunks.append(sc)
                                seen_ids.add(sc.chunk_id)
                        
                        # Add general chunks (deduplicated)
                        for gc in general_chunks:
                            if gc.chunk_id not in seen_ids:
                                combined_chunks.append(gc)
                                seen_ids.add(gc.chunk_id)
                        
                        chunks = combined_chunks
                        print(f"[RAGAgent] META query - combined {len(chunks)} total chunks (1 summary + {len(section_chunks)} sections + general)")
                        span.set_attribute("rag.doc_summary_included", document_summary_chunk is not None)
                        span.set_attribute("rag.section_chunks", len(section_chunks))
                        span.set_attribute("rag.general_chunks", len(general_chunks))
                    else:
                        # Standard retrieval for DETAIL/HYBRID queries
                        chunks = await self._retrieve_chunks(
                            query_embedding=query_embedding,
                            user_id=params["user_id"],
                            document_id=params.get("document_id"),
                            top_k=params["top_k"],
                            query=search_query,
                            use_hybrid=True,
                            metadata_filter=None,
                        )
                    
                    # Fallback: If no chunks found at all
                    if not chunks:
                        return AgentResult(
                            success=True,
                            output=RAGResponse(
                                answer="I couldn't find any relevant information in your documents.",
                                sources=[],
                                mode=mode,
                                grounded=False,
                                confidence=0.0,
                            ),
                            state=AgentState.COMPLETED,
                        )
                    
                    span.set_attribute("rag.chunks_retrieved", len(chunks))
                    
                    # Log retrieved chunk scores for debugging
                    if chunks:
                        print(f"[RAGAgent] Retrieved {len(chunks)} chunks. Top 3 scores: {[f'{c.similarity:.3f}' for c in chunks[:3]]}")
                    
                    # Step 3: Filter by relevance threshold
                    relevant_chunks = [c for c in chunks if c.similarity >= self.RELEVANCE_THRESHOLD]
                    print(f"[RAGAgent] After filtering (threshold={self.RELEVANCE_THRESHOLD}): {len(relevant_chunks)} chunks remain")
                    
                    if not relevant_chunks:
                        # Use top chunks anyway if nothing passes threshold
                        print(f"[RAGAgent] No chunks passed threshold, using top 3 anyway")
                        relevant_chunks = chunks[:3]
                    
                    span.set_attribute("rag.chunks_after_filter", len(relevant_chunks))
                    
                    # Step 3.5: Enhance with knowledge graph (Graph RAG)
                    span.add_event("enhancing_with_graph")
                    relevant_chunks = await self._enhance_with_graph(
                        query=params["query"],
                        chunks=relevant_chunks,
                        user_id=params["user_id"],
                        document_id=params.get("document_id"),
                    )
                
                # Step 4: Generate response based on mode
                if mode == RAGMode.QUIZ or mode == "quiz":
                    result = await self._generate_quiz(
                        chunks=relevant_chunks,
                        grade=params["grade"],
                        num_questions=params["num_questions"],
                        document_id=params.get("document_id"),
                    )
                else:
                    result = await self._generate_chat_response(
                        query=params["query"],
                        chunks=relevant_chunks,
                        grade=params["grade"],
                        document_id=params.get("document_id"),
                        history=chat_history,
                        summary=chat_summary,
                    )
                
                span.set_attribute("rag.response_grounded", result.grounded)
                
                return AgentResult(
                    success=True,
                    output=result,
                    state=AgentState.COMPLETED,
                    metadata={"chunks_used": len(relevant_chunks)},
                )
                
            except Exception as e:
                span.record_exception(e)
                return AgentResult(
                    success=False,
                    output=None,
                    state=AgentState.ERROR,
                    error=str(e)
                )
    
    async def _retrieve_chunks(
        self,
        query_embedding: List[float],
        user_id: str,
        document_id: Optional[str],
        top_k: int,
        query: Optional[str] = None,
        use_hybrid: bool = True,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks from database using hybrid search.
        
        Combines vector similarity with BM25 keyword search and
        optionally applies cross-encoder reranking for best results.
        
        Args:
            query_embedding: Query vector for similarity search
            user_id: User ID for access control
            document_id: Optional document to scope search
            top_k: Number of results to return
            query: Original text query (for BM25 + reranking)
            use_hybrid: Whether to use hybrid search (default True)
            metadata_filter: Optional filter for chunk metadata
        """
        from app.core.database import async_session_maker
        from app.services.document import DocumentService
        
        async with async_session_maker() as db:
            service = DocumentService(db)
            
            # Use hybrid search if query text is provided
            if use_hybrid and query:
                try:
                    results = await service.hybrid_search_chunks(
                        query=query,
                        query_embedding=query_embedding,
                        user_id=user_id,
                        document_id=document_id,
                        limit=top_k,
                        use_reranker=True,
                        metadata_filter=metadata_filter,
                    )
                except Exception as e:
                    print(f"[RAGAgent] Hybrid search failed, falling back to vector: {e}")
                    results = await service.search_chunks(
                        query_embedding=query_embedding,
                        user_id=user_id,
                        document_id=document_id,
                        limit=top_k,
                        metadata_filter=metadata_filter,
                    )
            else:
                # Fall back to vector-only search
                results = await service.search_chunks(
                    query_embedding=query_embedding,
                    user_id=user_id,
                    document_id=document_id,
                    limit=top_k,
                    metadata_filter=metadata_filter,
                )
        
        return [
            RetrievedChunk(
                content=r["content"],
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                filename=r["filename"],
                similarity=r["similarity"],
                chunk_index=r.get("chunk_index", 0),
            )
            for r in results
        ]
    
    async def _enhance_with_graph(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        user_id: str,
        document_id: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """
        Enhance retrieval results using knowledge graph traversal.
        
        Extracts entities from query, finds related entities in graph,
        then retrieves additional chunks mentioning those entities.
        
        Args:
            query: User's query
            chunks: Initial retrieved chunks
            user_id: User ID for access control
            document_id: Optional document scope
            
        Returns:
            Enhanced chunk list with graph-discovered content
        """
        try:
            from app.services.graph_store import get_graph_store
            
            graph_store = get_graph_store()
            if not await graph_store.is_available():
                return chunks  # Graph not available, return original
            
            # Extract key terms from query for graph lookup
            query_terms = self._extract_query_terms(query)
            if not query_terms:
                return chunks
            
            # Find related entities in graph
            related = await graph_store.find_related_entities(
                entity_names=query_terms,
                max_hops=2,
                limit=10,
            )
            
            if not related:
                return chunks
            
            # Get document IDs that contain related entities
            related_doc_ids = set()
            for entity in related:
                if entity.get("document_id"):
                    related_doc_ids.add(entity["document_id"])
            
            # If we found related documents, we could fetch additional chunks
            # For now, just boost existing chunks that mention related entities
            related_names = {e["name"].lower() for e in related}
            
            # Re-score chunks based on graph connections
            for chunk in chunks:
                chunk_text_lower = chunk.content.lower()
                graph_boost = sum(
                    0.1 for name in related_names 
                    if name in chunk_text_lower
                )
                # Boost similarity score slightly for graph-connected chunks
                chunk.similarity = min(1.0, chunk.similarity + graph_boost)
            
            # Re-sort by boosted similarity
            chunks.sort(key=lambda c: c.similarity, reverse=True)
            
            return chunks
            
        except Exception as e:
            print(f"[RAGAgent] Graph enhancement failed: {e}")
            return chunks
    
    def _extract_query_terms(self, query: str) -> List[str]:
        """Extract key terms from query for graph lookup."""
        import re
        # Simple extraction: split on spaces, remove short/common words
        stop_words = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'what', 'why', 
                     'how', 'when', 'where', 'who', 'which', 'this', 'that', 'can',
                     'do', 'does', 'did', 'will', 'would', 'could', 'should', 'be',
                     'been', 'being', 'have', 'has', 'had', 'to', 'of', 'in', 'for',
                     'on', 'with', 'at', 'by', 'from', 'about', 'me', 'my', 'tell'}
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
        terms = [w for w in words if w not in stop_words]
        
        return terms[:5]  # Limit to top 5 terms
    
    async def _apply_hyde_transformation(
        self,
        query: str,
        subject: Optional[str] = None,
    ) -> str:
        """
        Apply HyDE (Hypothetical Document Embeddings) transformation.
        
        Generates a hypothetical answer/document that would answer the query,
        then uses that for embedding-based retrieval. This improves semantic
        matching for ambiguous or complex queries.
        
        Args:
            query: Original user query
            subject: Document subject for context
            
        Returns:
            Hypothetical document text for embedding
        """
        hyde_prompt = f"""Given this student question about {subject or 'educational content'}:

Question: {query}

Write a brief, factual paragraph (3-5 sentences) that would directly answer this question. 
Write as if you are quoting from an educational textbook.
Include specific facts, definitions, or concepts that would be relevant."""

        try:
            response = await self.llm.generate(
                prompt=hyde_prompt,
                system_prompt="You are an educational content generator. Create hypothetical document passages that would answer questions.",
                agent_name=self.name,
            )
            
            hypothetical_doc = response.content.strip()
            print(f"[RAGAgent] HyDE generated: {hypothetical_doc[:100]}...")
            return hypothetical_doc
            
        except Exception as e:
            print(f"[RAGAgent] HyDE transformation failed: {e}")
            return query  # Fallback to original query

    async def summarize_conversation(self, history: str, current_summary: str = "") -> str:
        """
        Summarize the conversation history to condense context.
        """
        prompt = f"""You are a helpful assistant summarizing a conversation for memory context.
        
        EXISTING SUMMARY:
        {current_summary or "None"}
        
        RECENT MESSAGES:
        {history}
        
        Create a concise updated summary that captures key facts, user preferences, and the current topic.
        Maintain continuity. The summary should be a paragraph.
        
        UPDATED SUMMARY:"""

        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt="You are a conversation summarizer.",
                agent_name=self.name,
            )
            summary = response.content.strip()
            print(f"[RAGAgent] Updated conversation summary. length: {len(summary)}")
            return summary
        except Exception as e:
            print(f"[RAGAgent] Summarization failed: {e}")
            return current_summary

    async def _rewrite_query_with_history(self, query: str, history: str) -> str:
        """Rewrite query to be standalone based on history."""
        if not history:
            return query
            
        prompt = f"""Given the following conversation history and a new user question, rephrase the new question to be a standalone question that captures all context.
        
        CHAT HISTORY:
        {history}
        
        NEW QUESTION:
        {query}
        
        STANDALONE QUESTION:"""

        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt="You are a query rewriting assistant. Reformulate questions to be self-contained.",
                agent_name=self.name,
            )
            rewritten = response.content.strip()
            print(f"[RAGAgent] History-aware rewrite: '{query}' -> '{rewritten}'")
            return rewritten
        except Exception as e:
            print(f"[RAGAgent] Query rewrite failed: {e}")
            return query

    async def _generate_chat_response(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        grade: int,
        document_id: Optional[str] = None,
        history: str = "",
        summary: str = "",
    ) -> RAGResponse:

        try:
            response = await self.llm.generate(
                prompt=hyde_prompt,
                system_prompt="You are an educational content generator. Create hypothetical document passages that would answer questions.",
                agent_name=self.name,
            )
            
            hypothetical_doc = response.content.strip()
            print(f"[RAGAgent] HyDE generated: {hypothetical_doc[:100]}...")
            return hypothetical_doc
            
        except Exception as e:
            print(f"[RAGAgent] HyDE transformation failed: {e}")
            return query  # Fallback to original query
    
    async def _check_query_relevance(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        document_summary: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> dict:
        """
        Check if the query is relevant to the document content.
        
        Returns dict with is_relevant, relevance_score, reason.
        """
        import json
        
        # Build summary from chunks if not provided
        if not document_summary:
            # Use first chunk or summary chunk
            summary_chunk = next((c for c in chunks if c.chunk_index == -1), None)
            if summary_chunk:
                document_summary = summary_chunk.content
            else:
                document_summary = " ".join([c.content[:200] for c in chunks[:3]])
        
        subject = subject or "General Education"
        
        try:
            response = await self.llm.generate(
                prompt=self.RELEVANCE_CHECK_PROMPT.format(
                    summary=document_summary[:1500],
                    subject=subject,
                    query=query,
                ),
                system_prompt="You are a query relevance analyzer. Respond only with valid JSON.",
                agent_name=self.name,
            )
            
            # Parse JSON response
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            result = json.loads(content)
            return {
                "is_relevant": result.get("is_relevant", True),
                "relevance_score": result.get("relevance_score", 0.5),
                "reason": result.get("reason", ""),
                "suggested_topic": result.get("suggested_topic", ""),
            }
        except Exception as e:
            print(f"[RAGAgent] Relevance check failed: {e}")
            # Default to allowing the query
            return {"is_relevant": True, "relevance_score": 0.5, "reason": "Check skipped"}
    
    async def _generate_chat_response(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        grade: int,
        document_id: Optional[str] = None,
        history: str = "",
        summary: str = "",
    ) -> RAGResponse:
        """
        Generate a chat response with clear attribution.
        
        - First checks query relevance to document
        - Provides document-grounded answer
        - Adds LLM expansion with clear attribution
        """
        # Get document metadata from database
        subject = "General Education"
        document_summary = None
        
        # Try to get document metadata from database
        if document_id:
            try:
                from app.core.database import async_session_maker
                from app.models.document import UserDocument
                from sqlalchemy import select
                import uuid
                
                async with async_session_maker() as db:
                    result = await db.execute(
                        select(UserDocument).where(UserDocument.id == uuid.UUID(document_id))
                    )
                    doc = result.scalar_one_or_none()
                    if doc:
                        subject = doc.subject or "General Education"
                        document_summary = doc.summary
            except Exception as e:
                print(f"[RAGAgent] Failed to fetch document metadata: {e}")
        
        # Also check for summary chunk in retrieved chunks
        summary_chunk = next((c for c in chunks if c.chunk_index == -1), None)
        if summary_chunk and not document_summary:
            document_summary = summary_chunk.content
        
        # Check query relevance
        relevance = await self._check_query_relevance(
            query=query,
            chunks=chunks,
            document_summary=document_summary,
            subject=subject,
        )
        
        print(f"[RAGAgent] Query relevance: {relevance}")
        
        # If query is not relevant to document, provide helpful response
        if not relevance["is_relevant"] and relevance["relevance_score"] < 0.3:
            suggested = relevance.get("suggested_topic", "this topic")
            return RAGResponse(
                answer=f"""\u274C **This question doesn't seem related to your document.**

Your document appears to be about **{subject}**, but your question is about **{suggested}**.

**What you can do:**
- Ask questions related to the content in your uploaded document
- Upload a document about {suggested} if you'd like help with that topic
- Rephrase your question if it is actually related to this document

*I'm here to help you study your uploaded materials!* \U0001F4DA""",
                sources=[],
                mode=RAGMode.CHAT,
                grounded=False,
                confidence=0.0,
            )
        
        # Build context from chunks (excluding summary chunk for context)
        content_chunks = [c for c in chunks if c.chunk_index != -1]
        context = "\n\n---\n\n".join([
            f"[Source: {c.filename}, Section {c.chunk_index + 1}]\n{c.content}"
            for c in content_chunks
        ])
        
        if not context:
            context = "\n\n---\n\n".join([
                f"[Source: {c.filename}]\n{c.content}"
                for c in chunks
            ])
        
        # Generate response with attribution
        response = await self.llm.generate(
            prompt=query,
            system_prompt=self.CHAT_SYSTEM_PROMPT.format(
                context=context,
                grade=grade,
                subject=subject,
                history=history or "No previous history.",
                summary=summary or "No conversation summary available."
            ),
            agent_name=self.name,
        )
        
        # Simple grounding check
        grounded = any(
            chunk.content[:50].lower() in response.content.lower() 
            or any(word in response.content.lower() for word in chunk.content.split()[:10])
            for chunk in chunks
        )
        
        # Average similarity as confidence
        confidence = sum(c.similarity for c in chunks) / len(chunks) if chunks else 0.0
        
        return RAGResponse(
            answer=response.content,
            sources=chunks,
            mode=RAGMode.CHAT,
            grounded=grounded,
            confidence=confidence,
        )
    
    async def _generate_quiz(
        self,
        chunks: List[RetrievedChunk],
        grade: int,
        num_questions: int,
        document_id: Optional[str] = None,
    ) -> RAGResponse:
        """Generate quiz questions from document content with deduplication."""
        import uuid as uuid_module
        from app.core.database import async_session_maker
        from app.models.document import DocumentQuizHistory
        from sqlalchemy import select, desc
        
        # Build context from chunks
        context = "\n\n---\n\n".join([
            f"[Section {c.chunk_index + 1}]\n{c.content}"
            for c in chunks
        ])
        
        # Fetch previous questions for deduplication (last 5)
        previous_questions = []
        if document_id:
            try:
                async with async_session_maker() as db:
                    result = await db.execute(
                        select(DocumentQuizHistory.question_text)
                        .where(DocumentQuizHistory.document_id == uuid_module.UUID(document_id))
                        .order_by(desc(DocumentQuizHistory.created_at))
                        .limit(5)
                    )
                    previous_questions = [row[0] for row in result.fetchall()]
                    if previous_questions:
                        print(f"[RAGAgent] Found {len(previous_questions)} previous questions to avoid")
            except Exception as e:
                print(f"[RAGAgent] Failed to fetch previous questions: {e}")
        
        # Build deduplication instruction if we have previous questions
        avoid_instruction = ""
        if previous_questions:
            avoid_list = "\n".join([f"- {q}" for q in previous_questions])
            avoid_instruction = f"""

IMPORTANT - AVOID REPETITION:
Do NOT generate questions similar to these previously asked questions:
{avoid_list}

Generate DIFFERENT questions covering OTHER aspects of the content."""
        
        # Generate questions with deduplication instruction
        response = await self.llm.generate_json(
            prompt=f"Generate {num_questions} questions now.{avoid_instruction}",
            system_prompt=self.QUIZ_SYSTEM_PROMPT.format(
                context=context,
                grade=grade,
                num_questions=num_questions,
            ),
            agent_name=self.name,
        )
        
        # Parse questions from response
        questions = []
        if isinstance(response, list):
            questions = response
        elif isinstance(response, dict) and "questions" in response:
            questions = response["questions"]
        
        # Format as quiz questions (both dataclass and dict for serialization)
        quiz_questions = []
        quiz_questions_dict = []
        for q in questions:
            quiz_q = QuizQuestion(
                question=q.get("question", ""),
                options=q.get("options", []),
                correct_answer=q.get("correct_answer", ""),
                explanation=q.get("explanation", ""),
                source_chunk=chunks[0].content[:200] if chunks else "",
            )
            quiz_questions.append(quiz_q)
            quiz_questions_dict.append({
                "question": quiz_q.question,
                "options": quiz_q.options,
                "correct_answer": quiz_q.correct_answer,
                "explanation": quiz_q.explanation,
            })
        
        # Save new questions to history for future deduplication
        if document_id and quiz_questions:
            try:
                async with async_session_maker() as db:
                    for quiz_q in quiz_questions:
                        history_entry = DocumentQuizHistory(
                            document_id=uuid_module.UUID(document_id),
                            question_text=quiz_q.question,
                        )
                        db.add(history_entry)
                    await db.commit()
                    print(f"[RAGAgent] Saved {len(quiz_questions)} questions to history")
            except Exception as e:
                print(f"[RAGAgent] Failed to save question history: {e}")
        
        # Create response with questions stored in a special attribute
        rag_response = RAGResponse(
            answer=f"Generated {len(quiz_questions)} questions from your document.",
            sources=chunks,
            mode=RAGMode.QUIZ,
            grounded=True,
            confidence=0.9 if quiz_questions else 0.0,
        )
        # Attach questions as attribute for extraction
        rag_response.quiz_questions = quiz_questions_dict  # type: ignore
        
        return rag_response
    
    # Convenience methods
    async def chat(
        self,
        query: str,
        document_id: str,
        user_id: str,
        grade: int = 5,
        session_id: Optional[str] = None,
    ) -> RAGResponse:
        """
        Chat with a document.
        
        Args:
            query: User's question
            document_id: ID of the document to query
            user_id: User ID for access control
            grade: Student grade level
            session_id: Optional session ID for chat history
            
        Returns:
            RAGResponse with grounded answer
        """
        import uuid
        
        # Generate new session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        result = await self.run(
            user_input=query,
            metadata={
                "mode": RAGMode.CHAT,
                "document_id": document_id,
                "user_id": user_id,
                "grade": grade,
                "session_id": session_id,
            }
        )
        
        if result.success:
            response = result.output
            response.session_id = session_id
            return response
        else:
            return RAGResponse(
                answer=f"Error: {result.error}",
                sources=[],
                mode=RAGMode.CHAT,
                grounded=False,
                confidence=0.0,
                session_id=session_id,
            )
    
    async def generate_quiz(
        self,
        document_id: str,
        user_id: str,
        num_questions: int = 5,
        grade: int = 5,
    ) -> List[QuizQuestion]:
        """
        Generate quiz from a document.
        
        Args:
            document_id: ID of the document
            user_id: User ID for access control
            num_questions: Number of questions to generate
            grade: Student grade level
            
        Returns:
            List of QuizQuestion objects
        """
        result = await self.run(
            user_input=f"Generate {num_questions} quiz questions",
            metadata={
                "mode": RAGMode.QUIZ,
                "document_id": document_id,
                "user_id": user_id,
                "grade": grade,
                "num_questions": num_questions,
                "top_k": 15,  # Get more context for quiz
            }
        )
        
        if result.success and hasattr(result.output, 'sources'):
            # Extract questions from the generation
            return []  # Questions are in the response
        return []


# Singleton instance
rag_agent = RAGAgent()
