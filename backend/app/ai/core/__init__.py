# AI Core Module - Agentic Architecture Foundation
# Phase 3A: Safety Infrastructure

from app.ai.core.llm import LLMClient, LLMResponse, get_llm_client
from app.ai.core.memory import AgentMemory
from app.ai.core.telemetry import get_tracer, agent_span
from app.ai.core.guardrails import (
    InputGuardrails, 
    OutputGuardrails, 
    validate_agent_input, 
    validate_agent_output
)

# Phase 3A: Safety Pipeline Components
from app.ai.core.pii_redactor import PIIRedactor, get_pii_redactor, redact_pii
from app.ai.core.injection_detector import InjectionDetector, get_injection_detector, check_for_injection
from app.ai.core.content_moderator import ContentModerator, get_content_moderator, moderate_content
from app.ai.core.safety_pipeline import (
    SafetyPipeline, 
    get_safety_pipeline, 
    validate_user_input, 
    validate_user_input, 
    validate_ai_output
)

# Phase 3B: Observability
from app.ai.core.observability import init_observability, get_observer

__all__ = [
    # LLM
    "LLMClient", "LLMResponse", "get_llm_client",
    # Memory
    "AgentMemory",
    # Telemetry
    "get_tracer", "agent_span",
    # Legacy Guardrails
    "InputGuardrails", "OutputGuardrails", "validate_agent_input", "validate_agent_output",
    # Phase 3A Safety
    "PIIRedactor", "get_pii_redactor", "redact_pii",
    "InjectionDetector", "get_injection_detector", "check_for_injection",
    "ContentModerator", "get_content_moderator", "moderate_content",
    "SafetyPipeline", "get_safety_pipeline", "validate_user_input", "validate_ai_output",
    # Phase 3B Observability
    "init_observability", "get_observer",
]
