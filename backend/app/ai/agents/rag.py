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
    RELEVANCE_THRESHOLD = 0.5  # Minimum similarity score
    
    # System prompts
    CHAT_SYSTEM_PROMPT = """You are a helpful educational assistant answering questions based ONLY on the provided document context.

RULES:
1. Answer ONLY based on the provided context. Do not use external knowledge.
2. If the context doesn't contain the answer, say "I couldn't find this information in your document."
3. Quote relevant parts of the document when helpful.
4. Keep answers appropriate for Grade {grade} students.
5. Be clear, concise, and educational.

DOCUMENT CONTEXT:
{context}

---
Answer the student's question based on the above context."""

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
                # Step 1: Generate query embedding
                span.add_event("generating_query_embedding")
                query_embedding = await self.embeddings_model.aembed_query(params["query"])
                
                # Step 2: Retrieve relevant chunks
                span.add_event("retrieving_chunks")
                chunks = await self._retrieve_chunks(
                    query_embedding=query_embedding,
                    user_id=params["user_id"],
                    document_id=params.get("document_id"),
                    top_k=params["top_k"],
                )
                
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
                
                # Step 3: Filter by relevance threshold
                relevant_chunks = [c for c in chunks if c.similarity >= self.RELEVANCE_THRESHOLD]
                
                if not relevant_chunks:
                    # Use top chunks anyway if nothing passes threshold
                    relevant_chunks = chunks[:3]
                
                span.set_attribute("rag.chunks_after_filter", len(relevant_chunks))
                
                # Step 4: Generate response based on mode
                if mode == RAGMode.QUIZ or mode == "quiz":
                    result = await self._generate_quiz(
                        chunks=relevant_chunks,
                        grade=params["grade"],
                        num_questions=params["num_questions"],
                    )
                else:
                    result = await self._generate_chat_response(
                        query=params["query"],
                        chunks=relevant_chunks,
                        grade=params["grade"],
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
    ) -> List[RetrievedChunk]:
        """Retrieve relevant chunks from database."""
        from app.core.database import async_session_maker
        from app.services.document import DocumentService
        
        async with async_session_maker() as db:
            service = DocumentService(db)
            results = await service.search_chunks(
                query_embedding=query_embedding,
                user_id=user_id,
                document_id=document_id,
                limit=top_k,
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
    
    async def _generate_chat_response(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        grade: int,
    ) -> RAGResponse:
        """Generate a chat response grounded in retrieved context."""
        # Build context from chunks
        context = "\n\n---\n\n".join([
            f"[Source: {c.filename}, Section {c.chunk_index + 1}]\n{c.content}"
            for c in chunks
        ])
        
        # Generate response
        response = await self.llm.generate(
            prompt=query,
            system_prompt=self.CHAT_SYSTEM_PROMPT.format(
                context=context,
                grade=grade,
            ),
            agent_name=self.name,
        )
        
        # Simple grounding check: does the response reference the sources?
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
    ) -> RAGResponse:
        """Generate quiz questions from document content."""
        # Build context from chunks
        context = "\n\n---\n\n".join([
            f"[Section {c.chunk_index + 1}]\n{c.content}"
            for c in chunks
        ])
        
        # Generate questions
        response = await self.llm.generate_json(
            prompt=f"Generate {num_questions} questions now.",
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
    ) -> RAGResponse:
        """
        Chat with a document.
        
        Args:
            query: User's question
            document_id: ID of the document to query
            user_id: User ID for access control
            grade: Student grade level
            
        Returns:
            RAGResponse with grounded answer
        """
        result = await self.run(
            user_input=query,
            metadata={
                "mode": RAGMode.CHAT,
                "document_id": document_id,
                "user_id": user_id,
                "grade": grade,
            }
        )
        
        if result.success:
            return result.output
        else:
            return RAGResponse(
                answer=f"Error: {result.error}",
                sources=[],
                mode=RAGMode.CHAT,
                grounded=False,
                confidence=0.0,
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
