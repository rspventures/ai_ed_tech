"""
AI Tutor Platform - Guardrails Module
Input/Output validation and safety checks for AI Agents
"""
import re
from typing import Optional, List, Any, Dict
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, ValidationError


class GuardrailResult(Enum):
    """Result of a guardrail check."""
    PASS = "pass"
    WARN = "warn"  # Proceed with caution
    BLOCK = "block"  # Do not proceed


@dataclass
class GuardrailResponse:
    """Response from a guardrail check."""
    result: GuardrailResult
    message: str
    sanitized_input: Optional[str] = None
    violations: List[str] = None
    
    def __post_init__(self):
        if self.violations is None:
            self.violations = []


# ==================== INPUT GUARDRAILS ====================

class InputGuardrails:
    """
    Validate and sanitize user inputs before they reach the LLM.
    """
    
    # Patterns that might indicate prompt injection attempts
    INJECTION_PATTERNS = [
        r"ignore\s+(previous|above|all)\s+(instructions?|prompts?)",
        r"you\s+are\s+now\s+in\s+(developer|admin|jailbreak)\s+mode",
        r"system\s*:\s*",  # Trying to inject system prompts
        r"<\|.*?\|>",  # Special tokens
        r"\bDAN\b",  # "Do Anything Now" jailbreak
        r"pretend\s+you\s+are\s+(not|an?\s+ai)",
    ]
    
    # Common PII patterns
    PII_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "ssn": r"\b\d{3}[-]?\d{2}[-]?\d{4}\b",
    }
    
    # Blocked topics for educational context
    BLOCKED_TOPICS = [
        "violence",
        "weapons",
        "drugs",
        "inappropriate",
        "adult content",
    ]
    
    @classmethod
    def check_injection(cls, text: str) -> GuardrailResponse:
        """Check for potential prompt injection attempts."""
        text_lower = text.lower()
        
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return GuardrailResponse(
                    result=GuardrailResult.BLOCK,
                    message="Input rejected: Potential prompt manipulation detected.",
                    violations=["prompt_injection"]
                )
        
        return GuardrailResponse(
            result=GuardrailResult.PASS,
            message="No injection detected."
        )
    
    @classmethod
    def mask_pii(cls, text: str) -> GuardrailResponse:
        """Detect and mask PII in the input."""
        masked_text = text
        found_pii = []
        
        for pii_type, pattern in cls.PII_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                found_pii.append(pii_type)
                masked_text = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", masked_text)
        
        if found_pii:
            return GuardrailResponse(
                result=GuardrailResult.WARN,
                message=f"PII detected and masked: {', '.join(found_pii)}",
                sanitized_input=masked_text,
                violations=[f"pii_{p}" for p in found_pii]
            )
        
        return GuardrailResponse(
            result=GuardrailResult.PASS,
            message="No PII detected.",
            sanitized_input=text
        )
    
    @classmethod
    def check_topic_relevance(cls, text: str, allowed_topics: List[str] = None) -> GuardrailResponse:
        """Check if the input is relevant to educational topics."""
        text_lower = text.lower()
        
        # Check for explicitly blocked topics
        for blocked in cls.BLOCKED_TOPICS:
            if blocked in text_lower:
                return GuardrailResponse(
                    result=GuardrailResult.BLOCK,
                    message="This topic is not appropriate for the educational context.",
                    violations=["blocked_topic"]
                )
        
        return GuardrailResponse(
            result=GuardrailResult.PASS,
            message="Topic is appropriate."
        )
    
    @classmethod
    def validate_input(cls, text: str) -> GuardrailResponse:
        """
        Run all input guardrails and return combined result.
        """
        # Check for injection first
        injection_result = cls.check_injection(text)
        if injection_result.result == GuardrailResult.BLOCK:
            return injection_result
        
        # Check topic relevance
        topic_result = cls.check_topic_relevance(text)
        if topic_result.result == GuardrailResult.BLOCK:
            return topic_result
        
        # Mask PII (always run, returns sanitized text)
        pii_result = cls.mask_pii(text)
        
        # Combine violations
        all_violations = (
            injection_result.violations + 
            topic_result.violations + 
            pii_result.violations
        )
        
        return GuardrailResponse(
            result=pii_result.result if pii_result.violations else GuardrailResult.PASS,
            message="Input validated.",
            sanitized_input=pii_result.sanitized_input or text,
            violations=all_violations
        )


# ==================== OUTPUT GUARDRAILS ====================

class OutputGuardrails:
    """
    Validate LLM outputs before returning to user.
    """
    
    # Patterns that should never appear in output
    DANGEROUS_PATTERNS = [
        r"<script.*?>.*?</script>",  # XSS
        r"(?:password|api_key|secret)\s*[:=]\s*\S+",  # Credential leaks
    ]
    
    @classmethod
    def check_dangerous_content(cls, text: str) -> GuardrailResponse:
        """Check for dangerous patterns in output."""
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                return GuardrailResponse(
                    result=GuardrailResult.BLOCK,
                    message="Output contains potentially dangerous content.",
                    violations=["dangerous_content"]
                )
        
        return GuardrailResponse(
            result=GuardrailResult.PASS,
            message="Output is safe."
        )
    
    @classmethod
    def validate_json_schema(cls, data: dict, schema_class: type) -> GuardrailResponse:
        """
        Validate output against a Pydantic schema.
        """
        try:
            if issubclass(schema_class, BaseModel):
                schema_class.model_validate(data)
            return GuardrailResponse(
                result=GuardrailResult.PASS,
                message="Output matches expected schema."
            )
        except ValidationError as e:
            return GuardrailResponse(
                result=GuardrailResult.BLOCK,
                message=f"Output schema validation failed: {e}",
                violations=["schema_mismatch"]
            )
    
    @classmethod
    def check_hallucination_indicators(cls, text: str) -> GuardrailResponse:
        """
        Check for common hallucination indicators.
        Note: This is a heuristic, not foolproof.
        """
        indicators = [
            "I'm not sure, but",
            "I might be wrong",
            "I don't have access to",
            "I cannot verify",
        ]
        
        text_lower = text.lower()
        found = [i for i in indicators if i.lower() in text_lower]
        
        if found:
            return GuardrailResponse(
                result=GuardrailResult.WARN,
                message="Output contains uncertainty indicators.",
                violations=["uncertainty_detected"]
            )
        
        return GuardrailResponse(
            result=GuardrailResult.PASS,
            message="No hallucination indicators detected."
        )
    
    @classmethod
    def validate_output(cls, text: str) -> GuardrailResponse:
        """
        Run all output guardrails.
        """
        # Check dangerous content
        danger_result = cls.check_dangerous_content(text)
        if danger_result.result == GuardrailResult.BLOCK:
            return danger_result
        
        # Check hallucination indicators (warning only)
        hallucination_result = cls.check_hallucination_indicators(text)
        
        return GuardrailResponse(
            result=hallucination_result.result,
            message="Output validated.",
            violations=hallucination_result.violations
        )


# ==================== CONVENIENCE FUNCTIONS ====================

def validate_agent_input(text: str) -> tuple[str, List[str]]:
    """
    Validate and sanitize agent input.
    Returns: (sanitized_text, list_of_warnings)
    Raises: ValueError if input is blocked.
    """
    result = InputGuardrails.validate_input(text)
    
    if result.result == GuardrailResult.BLOCK:
        raise ValueError(result.message)
    
    warnings = result.violations if result.result == GuardrailResult.WARN else []
    return result.sanitized_input or text, warnings


def validate_agent_output(text: str) -> tuple[str, List[str]]:
    """
    Validate agent output.
    Returns: (output_text, list_of_warnings)
    Raises: ValueError if output is blocked.
    """
    result = OutputGuardrails.validate_output(text)
    
    if result.result == GuardrailResult.BLOCK:
        raise ValueError(result.message)
    
    warnings = result.violations if result.result == GuardrailResult.WARN else []
    return text, warnings
