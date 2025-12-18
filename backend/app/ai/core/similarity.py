"""
Semantic Similarity Service 🧠

Provides functionality to calculate semantic similarity between texts
using vector embeddings (OpenAI).
Used by ValidatorAgent to detect duplicate or semantically identical questions.
"""
import math
from typing import List, Optional
import os

from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

class SemanticSimilarityService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SemanticSimilarityService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._enabled = False
        self._embeddings = None
        
        # Check for API key
        api_key = settings.OPENAI_API_KEY
        if api_key:
            try:
                # Initialize OpenAI Embeddings (using small model for speed/cost)
                self._embeddings = OpenAIEmbeddings(
                    openai_api_key=api_key,
                    model="text-embedding-3-small"
                )
                self._enabled = True
            except Exception as e:
                print(f"⚠️ Failed to initialize Embeddings: {e}")
        
        self._initialized = True
        
    @property
    def is_enabled(self) -> bool:
        return self._enabled
        
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get vector embedding for text."""
        if not self._enabled:
            return None
            
        try:
            # LangChain's embed_query is synchronous but fast enough or we can run in executor
            # For strict async, we might wrap it, but it typically makes HTTP req.
            # OpenAIEmbeddings.aembed_query is async supported in recent versions
            return await self._embeddings.aembed_query(text)
        except Exception as e:
            print(f"⚠️ Embedding error: {e}")
            return None

    def calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate Cosine Similarity between two vectors.
        Result is between 0.0 (no similarity) and 1.0 (identical).
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
            
        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Magnitude (norm) - OpenAI embeddings are usually normalized, 
        # so magnitude is close to 1, but we calculate to be safe.
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)

# Singleton instance
similarity_service = SemanticSimilarityService()
