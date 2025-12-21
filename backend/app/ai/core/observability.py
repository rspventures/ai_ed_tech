"""
AI Tutor Platform - Observability Module
Langfuse v3.x integration for LLM observability, tracing, and cost tracking.
"""
import os
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from contextlib import asynccontextmanager

# Langfuse imports with graceful fallback
try:
    from langfuse import Langfuse
    from langfuse.decorators import observe, langfuse_context
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None
    observe = lambda **kwargs: lambda f: f  # No-op decorator
    langfuse_context = None


@dataclass
class ObservabilityConfig:
    """Configuration for observability."""
    enabled: bool = True
    public_key: Optional[str] = None
    secret_key: Optional[str] = None
    host: str = "http://langfuse:3000"
    debug: bool = False
    
    @classmethod
    def from_env(cls) -> "ObservabilityConfig":
        """Load configuration from environment variables."""
        return cls(
            enabled=os.getenv("LANGFUSE_ENABLED", "true").lower() == "true",
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://langfuse:3000"),
            debug=os.getenv("LANGFUSE_DEBUG", "false").lower() == "true"
        )


# Per-model cost configuration (USD per 1M tokens)
MODEL_COSTS = {
    # OpenAI GPT-4 family
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Embeddings
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
    "text-embedding-ada-002": {"input": 0.10, "output": 0.0},
    # Image generation (per image, not tokens)
    "dall-e-3": {"input": 0.04, "output": 0.0},  # Standard 1024x1024
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int = 0) -> float:
    """
    Calculate cost for an LLM call.
    
    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        
    Returns:
        Cost in USD
    """
    prices = MODEL_COSTS.get(model, {"input": 0, "output": 0})
    input_cost = (input_tokens / 1_000_000) * prices["input"]
    output_cost = (output_tokens / 1_000_000) * prices["output"]
    return round(input_cost + output_cost, 6)


class LangfuseObserver:
    """
    Langfuse client wrapper for LLM observability.
    
    Provides:
    - Trace management for LLM calls
    - Cost tracking
    - User feedback collection
    - Metrics aggregation
    """
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize Langfuse observer."""
        self.config = config or ObservabilityConfig.from_env()
        self._client: Optional[Langfuse] = None
        self._initialized = False
        
        if self.config.enabled and LANGFUSE_AVAILABLE:
            self._init_client()
    
    def _init_client(self):
        """Initialize Langfuse client."""
        try:
            if self.config.public_key and self.config.secret_key:
                self._client = Langfuse(
                    public_key=self.config.public_key,
                    secret_key=self.config.secret_key,
                    host=self.config.host,
                    debug=self.config.debug
                )
            else:
                # Try to connect without keys (for local dev)
                self._client = Langfuse(
                    host=self.config.host,
                    debug=self.config.debug
                )

            # Verification
            if self._client.auth_check():
                print(f"[Observability] ✅ Langfuse connected successfully to {self.config.host}")
                self._initialized = True
            else:
                print(f"[Observability] ❌ Langfuse authentication failed for {self.config.host}")
                self._initialized = False

        except Exception as e:
            print(f"[Observability] Failed to initialize Langfuse: {e}")
            self._initialized = False
    
    @property
    def is_enabled(self) -> bool:
        """Check if observability is enabled and initialized."""
        return self._initialized and self._client is not None
    
    def create_trace(
        self,
        name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        input: Optional[Any] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ):
        """
        Create a new trace for an LLM operation.
        
        Args:
            name: Trace name (e.g., "TutorAgent.run")
            user_id: Student ID for per-user analytics
            session_id: Session ID for conversation tracking
            input: Input data to log
            metadata: Additional metadata
            tags: Tags for filtering
            
        Returns:
            Trace object or None if disabled
        """
        if not self.is_enabled:
            return None
        
        try:
            trace = self._client.trace(
                name=name,
                user_id=user_id,
                session_id=session_id,
                input=input,
                metadata=metadata or {},
                tags=tags or []
            )
            # Flush immediately in dev/debug mode to see results instantly
            if self.config.debug:
                self._client.flush()
            return trace
        except Exception as e:
            print(f"[Observability] Failed to create trace: {e}")
            return None
    
    def create_generation(
        self,
        trace,
        name: str,
        model: str,
        input: Any,
        output: Optional[Any] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: Optional[float] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Create a generation span within a trace.
        
        Args:
            trace: Parent trace object
            name: Generation name (e.g., "openai_completion")
            model: Model name
            input: Prompt/input
            output: Response output
            input_tokens: Input token count
            output_tokens: Output token count
            latency_ms: Latency in milliseconds
            metadata: Additional metadata
        """
        if trace is None:
            return None
        
        try:
            generation = trace.generation(
                name=name,
                model=model,
                input=input,
                output=output,
                usage={
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": input_tokens + output_tokens,
                    "unit": "TOKENS"
                },
                metadata=metadata or {}
            )
            
            # Add cost calculation
            if input_tokens or output_tokens:
                cost = calculate_cost(model, input_tokens, output_tokens)
                generation.update(metadata={"cost_usd": cost})
            
            return generation
        except Exception as e:
            print(f"[Observability] Failed to create generation: {e}")
            return None
    
    def create_span(
        self,
        trace,
        name: str,
        input: Optional[Any] = None,
        metadata: Optional[Dict] = None
    ):
        """Create a span within a trace for non-LLM operations."""
        if trace is None:
            return None
        
        try:
            return trace.span(
                name=name,
                input=input,
                metadata=metadata or {}
            )
        except Exception:
            return None
    
    def score(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: Optional[str] = None
    ):
        """
        Add a score to a trace (for user feedback).
        
        Args:
            trace_id: ID of the trace to score
            name: Score name (e.g., "user_feedback")
            value: Score value (0-1 for thumbs up/down)
            comment: Optional comment
        """
        if not self.is_enabled:
            return
        
        try:
            self._client.score(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment
            )
        except Exception as e:
            print(f"[Observability] Failed to add score: {e}")
    
    def flush(self):
        """Flush pending events to Langfuse."""
        if self.is_enabled:
            try:
                self._client.flush()
            except Exception:
                pass
    
    def shutdown(self):
        """Shutdown the client gracefully."""
        if self.is_enabled:
            try:
                self._client.shutdown()
            except Exception:
                pass


# Singleton observer instance
_observer: Optional[LangfuseObserver] = None


def get_observer() -> LangfuseObserver:
    """Get or create singleton LangfuseObserver instance."""
    global _observer
    if _observer is None:
        _observer = LangfuseObserver()
    return _observer


def init_observability(config: Optional[ObservabilityConfig] = None):
    """Initialize observability with custom config."""
    global _observer
    _observer = LangfuseObserver(config)
    return _observer


# Convenience decorators and context managers

def trace_llm_call(name: str = "llm_call"):
    """
    Decorator to trace an LLM call.
    
    Usage:
        @trace_llm_call("tutor_response")
        async def generate_response(prompt: str) -> str:
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            observer = get_observer()
            trace = observer.create_trace(
                name=name,
                user_id=kwargs.get("user_id"),
                session_id=kwargs.get("session_id"),
                metadata={"function": func.__name__}
            )
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                latency_ms = (time.time() - start_time) * 1000
                
                if trace:
                    trace.update(
                        output=str(result)[:1000],
                        metadata={"latency_ms": latency_ms}
                    )
                
                return result
            except Exception as e:
                if trace:
                    trace.update(
                        level="ERROR",
                        status_message=str(e)
                    )
                raise
        return wrapper
    return decorator


@asynccontextmanager
async def trace_context(
    name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict] = None
):
    """
    Async context manager for tracing.
    
    Usage:
        async with trace_context("agent_run", user_id=student_id) as trace:
            # ... do work ...
            trace.update(output=result)
    """
    observer = get_observer()
    trace = observer.create_trace(
        name=name,
        user_id=user_id,
        session_id=session_id,
        metadata=metadata
    )
    
    start_time = time.time()
    try:
        yield trace
    except Exception as e:
        if trace:
            trace.update(level="ERROR", status_message=str(e))
        raise
    finally:
        if trace:
            latency_ms = (time.time() - start_time) * 1000
            trace.update(metadata={"latency_ms": latency_ms})
        observer.flush()


# Export convenience function
def record_user_feedback(trace_id: str, is_positive: bool, comment: Optional[str] = None):
    """
    Record user feedback (thumbs up/down) for a trace.
    
    Args:
        trace_id: ID of the trace
        is_positive: True for thumbs up, False for thumbs down
        comment: Optional feedback comment
    """
    observer = get_observer()
    observer.score(
        trace_id=trace_id,
        name="user_feedback",
        value=1.0 if is_positive else 0.0,
        comment=comment
    )
