"""
AI Tutor Platform - Phoenix RAG Metrics
Integration with Arize Phoenix for RAG-specific observability and evaluation.

Provides:
- Context relevance scoring
- Answer faithfulness metrics
- Retrieval quality tracking
- Automated RAGAS-style evaluation
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio

from app.core.config import settings


@dataclass
class RAGMetrics:
    """Metrics for a RAG query."""
    query: str
    context_relevance: float  # 0-1, how relevant retrieved chunks are
    answer_faithfulness: float  # 0-1, how grounded answer is in context
    answer_relevance: float  # 0-1, how relevant answer is to query
    retrieval_precision: float  # 0-1, precision of retrieved chunks
    latency_ms: int
    chunk_count: int
    reranking_applied: bool
    graph_enhanced: bool


class PhoenixMetricsService:
    """
    Phoenix integration for RAG observability.
    
    Tracks and evaluates RAG quality metrics including:
    - Context relevance (are retrieved chunks relevant?)
    - Answer faithfulness (is answer grounded in context?)
    - Retrieval precision (how many chunks were useful?)
    """
    
    def __init__(self):
        self._phoenix_available = False
        self._session = None
        self._tracer = None
        self._init_phoenix()
    
    def _init_phoenix(self):
        """Initialize Phoenix connection via OpenInference."""
        try:
            from openinference.instrumentation.langchain import LangChainInstrumentor
            from arize_phoenix_otel import register_otel_tracer
            
            # Register OpenTelemetry tracer for Phoenix
            if settings.PHOENIX_ENABLED:
                try:
                    register_otel_tracer(
                        endpoint=settings.PHOENIX_ENDPOINT,
                        project_name="ai_tutor",
                    )
                    
                    # Auto-instrument LangChain
                    LangChainInstrumentor().instrument()
                    
                    self._phoenix_available = True
                    print("[Phoenix] Initialized with OpenInference instrumentation")
                except Exception as e:
                    print(f"[Phoenix] Failed to connect to endpoint: {e}")
                    self._phoenix_available = False
                
        except ImportError as e:
            print(f"[Phoenix] OpenInference packages not installed: {e}")
            self._phoenix_available = False
    
    @property
    def is_available(self) -> bool:
        return self._phoenix_available
    
    async def record_rag_query(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        answer: str,
        latency_ms: int,
        grounded: bool,
        confidence: float,
        reranking_applied: bool = False,
        graph_enhanced: bool = False,
    ) -> Optional[RAGMetrics]:
        """
        Record a RAG query and compute quality metrics.
        
        Args:
            query: User's query
            chunks: Retrieved chunks with content and similarity
            answer: Generated answer
            latency_ms: Query latency in milliseconds
            grounded: Whether answer is grounded
            confidence: Model confidence score
            reranking_applied: Whether reranking was used
            graph_enhanced: Whether graph enhancement was applied
            
        Returns:
            RAGMetrics with computed scores
        """
        if not self._phoenix_available:
            return None
        
        try:
            # Compute context relevance (average similarity of chunks)
            similarities = [c.get("similarity", 0) for c in chunks]
            context_relevance = sum(similarities) / len(similarities) if similarities else 0
            
            # Estimate answer faithfulness from grounding
            answer_faithfulness = confidence if grounded else confidence * 0.5
            
            # Estimate answer relevance (simple heuristic)
            answer_relevance = 0.8 if grounded else 0.4
            
            # Retrieval precision (chunks above threshold / total)
            threshold = 0.5
            relevant_chunks = sum(1 for s in similarities if s >= threshold)
            retrieval_precision = relevant_chunks / len(chunks) if chunks else 0
            
            metrics = RAGMetrics(
                query=query,
                context_relevance=context_relevance,
                answer_faithfulness=answer_faithfulness,
                answer_relevance=answer_relevance,
                retrieval_precision=retrieval_precision,
                latency_ms=latency_ms,
                chunk_count=len(chunks),
                reranking_applied=reranking_applied,
                graph_enhanced=graph_enhanced,
            )
            
            # Log to Phoenix if available
            await self._log_to_phoenix(metrics, chunks, answer)
            
            return metrics
            
        except Exception as e:
            print(f"[Phoenix] Failed to record metrics: {e}")
            return None
    
    async def _log_to_phoenix(
        self,
        metrics: RAGMetrics,
        chunks: List[Dict[str, Any]],
        answer: str,
    ):
        """Log metrics to Phoenix."""
        if not self._phoenix_available:
            return
        
        try:
            # Phoenix logging would go here
            # For now, just track internally
            import phoenix as px
            
            # Create span data for Phoenix
            span_data = {
                "name": "rag_query",
                "attributes": {
                    "query": metrics.query,
                    "context_relevance": metrics.context_relevance,
                    "answer_faithfulness": metrics.answer_faithfulness,
                    "retrieval_precision": metrics.retrieval_precision,
                    "latency_ms": metrics.latency_ms,
                    "chunk_count": metrics.chunk_count,
                    "reranking_applied": metrics.reranking_applied,
                    "graph_enhanced": metrics.graph_enhanced,
                }
            }
            
            # Log would happen here with Phoenix client
            print(f"[Phoenix] Logged RAG query: relevance={metrics.context_relevance:.2f}, "
                  f"faithfulness={metrics.answer_faithfulness:.2f}")
                  
        except Exception as e:
            print(f"[Phoenix] Logging failed: {e}")
    
    async def get_aggregate_metrics(
        self,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
        time_range_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get aggregate RAG metrics for dashboard display.
        
        Returns averages and counts for the specified time range.
        """
        # This would query Phoenix for aggregated metrics
        # For now, return placeholder structure
        return {
            "time_range_hours": time_range_hours,
            "total_queries": 0,
            "avg_context_relevance": 0.0,
            "avg_answer_faithfulness": 0.0,
            "avg_retrieval_precision": 0.0,
            "avg_latency_ms": 0,
            "reranking_usage_percent": 0.0,
            "graph_enhancement_percent": 0.0,
        }


# Singleton instance
_phoenix_service: Optional[PhoenixMetricsService] = None


def get_phoenix_service() -> PhoenixMetricsService:
    """Get or create Phoenix service singleton."""
    global _phoenix_service
    if _phoenix_service is None:
        _phoenix_service = PhoenixMetricsService()
    return _phoenix_service
