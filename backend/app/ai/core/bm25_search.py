"""
AI Tutor Platform - BM25 Keyword Search
Provides keyword-based retrieval using BM25 algorithm.
Complements vector search for hybrid retrieval.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    BM25Okapi = None


@dataclass
class BM25SearchResult:
    """Result from BM25 keyword search."""
    chunk_id: str
    content: str
    chunk_index: int
    document_id: str
    filename: str
    score: float


class BM25Index:
    """
    BM25 index for keyword-based document search.
    
    This complements vector search by finding exact keyword matches
    that semantic embeddings might miss (e.g., acronyms, names, codes).
    """
    
    def __init__(self):
        self._corpus: List[str] = []
        self._metadata: List[Dict[str, Any]] = []
        self._index: Optional[BM25Okapi] = None
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple whitespace tokenization with lowercasing."""
        import re
        # Remove punctuation, split on whitespace
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return text.split()
    
    def build_index(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Build BM25 index from document chunks.
        
        Args:
            chunks: List of chunk dicts with 'content', 'chunk_id', 
                   'document_id', 'filename', 'chunk_index'
        """
        if not BM25_AVAILABLE:
            raise ImportError("rank-bm25 not installed. Run: pip install rank-bm25")
        
        self._corpus = []
        self._metadata = []
        
        for chunk in chunks:
            self._corpus.append(chunk.get("content", ""))
            self._metadata.append({
                "chunk_id": chunk.get("chunk_id", ""),
                "document_id": chunk.get("document_id", ""),
                "filename": chunk.get("filename", ""),
                "chunk_index": chunk.get("chunk_index", 0),
            })
        
        # Tokenize corpus
        tokenized_corpus = [self._tokenize(doc) for doc in self._corpus]
        
        # Build BM25 index
        self._index = BM25Okapi(tokenized_corpus)
    
    def search(self, query: str, top_k: int = 10) -> List[BM25SearchResult]:
        """
        Search the index with a query.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            
        Returns:
            List of BM25SearchResult sorted by relevance
        """
        if not self._index or not self._corpus:
            return []
        
        # Tokenize query
        tokenized_query = self._tokenize(query)
        
        if not tokenized_query:
            return []
        
        # Get BM25 scores
        scores = self._index.get_scores(tokenized_query)
        
        # Get top-k indices
        top_indices = sorted(
            range(len(scores)), 
            key=lambda i: scores[i], 
            reverse=True
        )[:top_k]
        
        # Build results
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include if there's some match
                meta = self._metadata[idx]
                results.append(BM25SearchResult(
                    chunk_id=meta["chunk_id"],
                    content=self._corpus[idx],
                    chunk_index=meta["chunk_index"],
                    document_id=meta["document_id"],
                    filename=meta["filename"],
                    score=float(scores[idx]),
                ))
        
        return results


async def bm25_search_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Convenience function for BM25 search on chunk list.
    
    Args:
        query: Search query
        chunks: List of chunk dictionaries
        top_k: Number of results
        
    Returns:
        List of chunks with BM25 scores
    """
    if not BM25_AVAILABLE:
        print("[BM25] rank-bm25 not available, returning empty results")
        return []
    
    # Build temporary index
    index = BM25Index()
    index.build_index(chunks)
    
    # Search
    results = index.search(query, top_k=top_k)
    
    # Convert to dict format
    return [
        {
            "chunk_id": r.chunk_id,
            "content": r.content,
            "chunk_index": r.chunk_index,
            "document_id": r.document_id,
            "filename": r.filename,
            "bm25_score": r.score,
        }
        for r in results
    ]
