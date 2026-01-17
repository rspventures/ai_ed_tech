"""
AI Tutor Platform - Reranker
Cross-encoder reranking for improved retrieval precision.
Uses Cohere Rerank API as primary, with fallback options.
"""
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class RerankResult:
    """Result from reranking."""
    chunk_id: str
    content: str
    chunk_index: int
    document_id: str
    filename: str
    relevance_score: float
    original_rank: int


class CohereReranker:
    """
    Reranker using Cohere Rerank API.
    
    Cross-encoders provide more accurate relevance scoring
    by jointly encoding query and document together.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'COHERE_API_KEY', None) or os.getenv('COHERE_API_KEY')
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Cohere client."""
        if self._client is None:
            try:
                import cohere
                if not self.api_key:
                    raise ValueError("COHERE_API_KEY not set")
                self._client = cohere.Client(self.api_key)
            except ImportError:
                raise ImportError("cohere not installed. Run: pip install cohere")
        return self._client
    
    async def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5,
        model: str = "rerank-english-v3.0",
    ) -> List[RerankResult]:
        """
        Rerank chunks using Cohere.
        
        Args:
            query: The search query
            chunks: List of chunk dicts with 'content' and metadata
            top_k: Number of top results to return
            model: Cohere rerank model to use
            
        Returns:
            List of RerankResult sorted by relevance
        """
        if not chunks:
            return []
        
        try:
            client = self._get_client()
            
            # Extract documents for reranking
            documents = [chunk.get("content", "") for chunk in chunks]
            
            # Call Cohere Rerank API (sync, will work in async context)
            response = client.rerank(
                query=query,
                documents=documents,
                top_n=min(top_k, len(documents)),
                model=model,
            )
            
            # Build results
            results = []
            for item in response.results:
                original_chunk = chunks[item.index]
                results.append(RerankResult(
                    chunk_id=original_chunk.get("chunk_id", ""),
                    content=original_chunk.get("content", ""),
                    chunk_index=original_chunk.get("chunk_index", 0),
                    document_id=original_chunk.get("document_id", ""),
                    filename=original_chunk.get("filename", ""),
                    relevance_score=item.relevance_score,
                    original_rank=item.index,
                ))
            
            print(f"[Reranker] Cohere reranked {len(results)} chunks successfully")
            return results
            
        except Exception as e:
            print(f"[Reranker] Cohere rerank failed: {e}")
            # Fallback: return original order with placeholder scores
            return self._fallback_rerank(chunks, top_k)
    
    def _fallback_rerank(
        self, 
        chunks: List[Dict[str, Any]], 
        top_k: int
    ) -> List[RerankResult]:
        """Fallback when Cohere is unavailable."""
        results = []
        for i, chunk in enumerate(chunks[:top_k]):
            results.append(RerankResult(
                chunk_id=chunk.get("chunk_id", ""),
                content=chunk.get("content", ""),
                chunk_index=chunk.get("chunk_index", 0),
                document_id=chunk.get("document_id", ""),
                filename=chunk.get("filename", ""),
                relevance_score=1.0 - (i * 0.1),  # Decreasing score
                original_rank=i,
            ))
        return results


class SimpleReranker:
    """
    Simple reranker using keyword overlap.
    Used as fallback when Cohere is not available.
    """
    
    def _tokenize(self, text: str) -> set:
        """Simple tokenization."""
        import re
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return set(text.split())
    
    async def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[RerankResult]:
        """
        Rerank using keyword overlap scoring.
        
        Args:
            query: The search query
            chunks: List of chunk dicts
            top_k: Number of results
            
        Returns:
            List of RerankResult
        """
        query_tokens = self._tokenize(query)
        
        scored_chunks = []
        for i, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            content_tokens = self._tokenize(content)
            
            # Jaccard similarity
            if query_tokens and content_tokens:
                overlap = len(query_tokens & content_tokens)
                union = len(query_tokens | content_tokens)
                score = overlap / union if union > 0 else 0
            else:
                score = 0
            
            scored_chunks.append((i, chunk, score))
        
        # Sort by score descending
        scored_chunks.sort(key=lambda x: x[2], reverse=True)
        
        # Build results
        results = []
        for original_idx, chunk, score in scored_chunks[:top_k]:
            results.append(RerankResult(
                chunk_id=chunk.get("chunk_id", ""),
                content=chunk.get("content", ""),
                chunk_index=chunk.get("chunk_index", 0),
                document_id=chunk.get("document_id", ""),
                filename=chunk.get("filename", ""),
                relevance_score=score,
                original_rank=original_idx,
            ))
        
        return results


# Factory function
def get_reranker(use_cohere: bool = True) -> CohereReranker | SimpleReranker:
    """
    Get appropriate reranker based on configuration.
    
    Args:
        use_cohere: Whether to try Cohere first
        
    Returns:
        Reranker instance
    """
    if use_cohere:
        api_key = getattr(settings, 'COHERE_API_KEY', None) or os.getenv('COHERE_API_KEY')
        if api_key:
            print("[Reranker] Initializing Cohere reranker")
            return CohereReranker(api_key)
        else:
            print("[Reranker] COHERE_API_KEY not found, falling back to simple reranker")
    
    return SimpleReranker()
