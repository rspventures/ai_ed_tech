"""
AI Tutor Platform - Hybrid Retrieval
Combines vector similarity search with BM25 keyword search
using Reciprocal Rank Fusion (RRF) for optimal results.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.ai.core.bm25_search import bm25_search_chunks, BM25_AVAILABLE
from app.ai.core.reranker import get_reranker, RerankResult


@dataclass
class HybridSearchResult:
    """Result from hybrid search with fusion score."""
    chunk_id: str
    content: str
    chunk_index: int
    document_id: str
    filename: str
    vector_score: float
    bm25_score: float
    fusion_score: float
    rerank_score: Optional[float] = None


def reciprocal_rank_fusion(
    vector_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    k: int = 60,
) -> List[Dict[str, Any]]:
    """
    Combine results using Reciprocal Rank Fusion (RRF).
    
    RRF score = sum(1 / (k + rank)) for each list
    
    Args:
        vector_results: Results from vector search (with 'similarity')
        bm25_results: Results from BM25 search (with 'bm25_score')
        k: RRF constant (default 60)
        
    Returns:
        Fused results sorted by RRF score
    """
    # Build score dictionaries by chunk_id
    scores: Dict[str, Dict[str, Any]] = {}
    
    # Process vector results
    for rank, result in enumerate(vector_results):
        chunk_id = result.get("chunk_id", "")
        if not chunk_id:
            continue
            
        if chunk_id not in scores:
            scores[chunk_id] = {
                "chunk_id": chunk_id,
                "content": result.get("content", ""),
                "chunk_index": result.get("chunk_index", 0),
                "document_id": result.get("document_id", ""),
                "filename": result.get("filename", ""),
                "vector_score": result.get("similarity", 0),
                "bm25_score": 0,
                "rrf_score": 0,
            }
        
        # Add RRF contribution from vector rank
        scores[chunk_id]["rrf_score"] += 1 / (k + rank + 1)
        scores[chunk_id]["vector_score"] = result.get("similarity", 0)
    
    # Process BM25 results
    for rank, result in enumerate(bm25_results):
        chunk_id = result.get("chunk_id", "")
        if not chunk_id:
            continue
            
        if chunk_id not in scores:
            scores[chunk_id] = {
                "chunk_id": chunk_id,
                "content": result.get("content", ""),
                "chunk_index": result.get("chunk_index", 0),
                "document_id": result.get("document_id", ""),
                "filename": result.get("filename", ""),
                "vector_score": 0,
                "bm25_score": result.get("bm25_score", 0),
                "rrf_score": 0,
            }
        
        # Add RRF contribution from BM25 rank
        scores[chunk_id]["rrf_score"] += 1 / (k + rank + 1)
        scores[chunk_id]["bm25_score"] = result.get("bm25_score", 0)
    
    # Sort by RRF score
    fused_results = sorted(
        scores.values(), 
        key=lambda x: x["rrf_score"], 
        reverse=True
    )
    
    return fused_results


async def hybrid_search(
    query: str,
    vector_results: List[Dict[str, Any]],
    all_chunks: List[Dict[str, Any]],
    top_k: int = 10,
    use_reranker: bool = True,
) -> List[HybridSearchResult]:
    """
    Perform hybrid search combining vector and BM25 results.
    
    Args:
        query: Search query
        vector_results: Results from vector similarity search
        all_chunks: All chunks for BM25 indexing
        top_k: Number of final results
        use_reranker: Whether to apply reranking
        
    Returns:
        List of HybridSearchResult
    """
    # Get BM25 results
    if BM25_AVAILABLE and all_chunks:
        bm25_results = await bm25_search_chunks(
            query=query,
            chunks=all_chunks,
            top_k=top_k * 2,  # Get more for fusion
        )
    else:
        bm25_results = []
    
    # Fuse results using RRF
    fused = reciprocal_rank_fusion(
        vector_results=vector_results,
        bm25_results=bm25_results,
    )
    
    # Take top candidates for reranking
    candidates = fused[:top_k * 2]
    
    # Apply reranking if enabled
    cohere_available = False
    if use_reranker and candidates:
        import os
        cohere_api_key = os.getenv('COHERE_API_KEY')
        cohere_available = bool(cohere_api_key)
        
        reranker = get_reranker(use_cohere=True)
        rerank_results = await reranker.rerank(
            query=query,
            chunks=candidates,
            top_k=top_k,
        )
        print(f"[HybridSearch] Reranker type: {'Cohere' if cohere_available else 'Simple'}, got {len(rerank_results)} results")
        
        # Build final results with rerank scores
        results = []
        for rr in rerank_results:
            # Find original fusion data
            original = next(
                (c for c in candidates if c["chunk_id"] == rr.chunk_id), 
                None
            )
            vector_score = original["vector_score"] if original else 0
            rerank_score_raw = rr.relevance_score
            
            # CRITICAL FIX: Use the HIGHER of rerank_score and vector_score
            # Cohere can return very low scores (0.001) for meta-queries like "What is this about?"
            # while vector similarity may be more meaningful (0.2-0.3)
            final_score = max(rerank_score_raw, vector_score) if cohere_available else vector_score
            
            results.append(HybridSearchResult(
                chunk_id=rr.chunk_id,
                content=rr.content,
                chunk_index=rr.chunk_index,
                document_id=rr.document_id,
                filename=rr.filename,
                vector_score=vector_score,
                bm25_score=original["bm25_score"] if original else 0,
                fusion_score=original["rrf_score"] if original else 0,
                rerank_score=final_score,
            ))
        
        if results:
            print(f"[HybridSearch] Top result scores - vector: {results[0].vector_score:.3f}, rerank_raw: {rerank_score_raw:.3f}, final: {results[0].rerank_score:.3f}")
        
        return results
    
    # Without reranking, return fused results
    results = []
    for item in fused[:top_k]:
        results.append(HybridSearchResult(
            chunk_id=item["chunk_id"],
            content=item["content"],
            chunk_index=item["chunk_index"],
            document_id=item["document_id"],
            filename=item["filename"],
            vector_score=item["vector_score"],
            bm25_score=item["bm25_score"],
            fusion_score=item["rrf_score"],
            rerank_score=None,
        ))
    
    return results


async def hybrid_search_simple(
    query: str,
    vector_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Simple hybrid search without reranking.
    Returns dict format for backward compatibility.
    
    Args:
        query: Search query
        vector_results: Vector search results
        bm25_results: BM25 search results  
        top_k: Number of results
        
    Returns:
        List of chunk dicts with similarity scores
    """
    fused = reciprocal_rank_fusion(vector_results, bm25_results)
    
    return [
        {
            "chunk_id": item["chunk_id"],
            "content": item["content"],
            "chunk_index": item["chunk_index"],
            "document_id": item["document_id"],
            "filename": item["filename"],
            "similarity": item["rrf_score"],  # Use fusion score as similarity
        }
        for item in fused[:top_k]
    ]
