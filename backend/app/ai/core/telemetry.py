"""
AI Tutor Platform - Telemetry Module
OpenTelemetry-based observability for AI Agents
"""
import os
import functools
from typing import Optional, Callable, Any
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import Status, StatusCode


# Service name from environment or default
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "ai-tutor-backend")
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

# Global tracer instance
_tracer: Optional[trace.Tracer] = None


def init_telemetry() -> trace.Tracer:
    """
    Initialize OpenTelemetry with OTLP exporter for Jaeger.
    Call this once at application startup.
    """
    global _tracer
    
    if _tracer is not None:
        return _tracer
    
    # Create resource with service name
    resource = Resource.create({
        "service.name": SERVICE_NAME,
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Add OTLP exporter for Jaeger
    try:
        otlp_exporter = OTLPSpanExporter(
            endpoint=OTLP_ENDPOINT,
            insecure=True,  # Use insecure for local development
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    except Exception as e:
        print(f"[Telemetry] Failed to connect to OTLP endpoint: {e}")
        # Fallback to console exporter for development
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    
    # Set the global tracer provider
    trace.set_tracer_provider(provider)
    
    # Get tracer for AI module
    _tracer = trace.get_tracer("ai.agents", "1.0.0")
    
    print(f"[Telemetry] Initialized with service: {SERVICE_NAME}, endpoint: {OTLP_ENDPOINT}")
    return _tracer


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance, initializing if necessary."""
    global _tracer
    if _tracer is None:
        return init_telemetry()
    return _tracer


@contextmanager
def agent_span(
    name: str,
    agent_name: str,
    attributes: Optional[dict] = None
):
    """
    Context manager for creating agent execution spans.
    
    Usage:
        with agent_span("generate_question", "ExaminerAgent") as span:
            span.set_attribute("topic", "Math")
            result = await do_work()
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        # Set common agent attributes
        span.set_attribute("agent.name", agent_name)
        span.set_attribute("agent.operation", name)
        
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value) if value is not None else "")
        
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def traced(
    operation_name: Optional[str] = None,
    agent_name: Optional[str] = None,
):
    """
    Decorator for tracing agent methods.
    
    Usage:
        @traced("generate_question", "ExaminerAgent")
        async def generate(self, topic: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        op_name = operation_name or func.__name__
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # Try to get agent name from self if not provided
            agent = agent_name
            if agent is None and args and hasattr(args[0], '__class__'):
                agent = args[0].__class__.__name__
            agent = agent or "UnknownAgent"
            
            # Build attributes from kwargs
            attributes = {
                f"input.{k}": str(v)[:200] for k, v in kwargs.items()
                if isinstance(v, (str, int, float, bool))
            }
            
            with agent_span(op_name, agent, attributes) as span:
                result = await func(*args, **kwargs)
                
                # Record output type
                span.set_attribute("output.type", type(result).__name__)
                
                return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            agent = agent_name
            if agent is None and args and hasattr(args[0], '__class__'):
                agent = args[0].__class__.__name__
            agent = agent or "UnknownAgent"
            
            attributes = {
                f"input.{k}": str(v)[:200] for k, v in kwargs.items()
                if isinstance(v, (str, int, float, bool))
            }
            
            with agent_span(op_name, agent, attributes) as span:
                result = func(*args, **kwargs)
                span.set_attribute("output.type", type(result).__name__)
                return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def trace_llm_call(
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
):
    """
    Record LLM-specific telemetry attributes on the current span.
    Call this within an active span to add token usage metrics.
    """
    span = trace.get_current_span()
    if span:
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.tokens.prompt", prompt_tokens)
        span.set_attribute("llm.tokens.completion", completion_tokens)
        span.set_attribute("llm.tokens.total", total_tokens)


# Import asyncio for iscoroutinefunction check
import asyncio
