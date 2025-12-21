"""
AI Tutor Platform - Safety Pipeline
Main orchestrator for all safety and content moderation operations.
Implements the Pipeline agentic pattern for consistent safety enforcement.
"""
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from app.ai.core.pii_redactor import PIIRedactor, get_pii_redactor, RedactionResult
from app.ai.core.injection_detector import InjectionDetector, get_injection_detector, InjectionAnalysis, ThreatLevel
from app.ai.core.content_moderator import ContentModerator, get_content_moderator, ModerationResponse, ModerationResult
from app.ai.core.llm import LLMClient


class SafetyAction(str, Enum):
    """Actions taken by safety pipeline."""
    ALLOW = "allow"
    SANITIZE = "sanitize"
    WARN = "warn"
    BLOCK = "block"
    RETRY = "retry"


@dataclass
class SafetyCheckResult:
    """Result of a safety pipeline check."""
    action: SafetyAction
    original_text: str
    processed_text: str
    
    # Details from each layer
    pii_detected: bool = False
    pii_types: List[str] = field(default_factory=list)
    injection_threat: ThreatLevel = ThreatLevel.SAFE
    moderation_result: ModerationResult = ModerationResult.ALLOWED
    
    # Metadata
    block_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    
    @property
    def is_blocked(self) -> bool:
        return self.action == SafetyAction.BLOCK
    
    @property
    def is_safe(self) -> bool:
        return self.action in (SafetyAction.ALLOW, SafetyAction.SANITIZE)


@dataclass
class OutputValidationResult:
    """Result of output validation with reflection."""
    is_safe: bool
    original_output: str
    validated_output: str
    iterations: int = 0
    issues_found: List[str] = field(default_factory=list)
    refinement_feedback: Optional[str] = None


class SafetyPipeline:
    """
    Centralized safety orchestrator implementing Pipeline pattern.
    
    Input Pipeline:
    User Input → PII Redaction → Injection Detection → Content Moderation → Safe Input
    
    Output Pipeline:
    LLM Output → Content Moderation → Self-Critique → Safe Output
    """
    
    SELF_CRITIQUE_PROMPT = """You are a content safety reviewer for an educational AI platform serving K-12 students (grades {grade}).

Review the following AI-generated response:
<response>
{output}
</response>

Original student question: "{question}"

Check for these issues:
1. Age-inappropriate content for grade {grade} students
2. Factual accuracy concerns or potential misinformation
3. Any harmful, violent, or disturbing content
4. Privacy violations or personal information
5. Content that could be emotionally distressing to children

Respond with ONLY one of:
- SAFE: If the response is appropriate
- UNSAFE: [Brief reason] - If there are serious issues
- NEEDS_EDIT: [Specific suggestion] - If minor fixes needed"""

    REFINEMENT_PROMPT = """The previous response had this safety issue: {feedback}

Original question: "{question}"
Previous response: "{output}"

Please provide a revised response that:
1. Addresses the original question
2. Fixes the identified safety issue
3. Is appropriate for grade {grade} students

Revised response:"""

    FALLBACK_RESPONSES = {
        "general": "I'm sorry, I can't help with that request. Let's focus on your studies! Would you like help with Math, Science, or English?",
        "violence": "I can't discuss that topic. Instead, let's learn something fun! What subject would you like to explore?",
        "inappropriate": "That's not something I can help with. How about we practice some problems or read a story together?",
    }
    
    def __init__(self,
                 pii_redactor: Optional[PIIRedactor] = None,
                 injection_detector: Optional[InjectionDetector] = None,
                 content_moderator: Optional[ContentModerator] = None,
                 llm_client: Optional[LLMClient] = None):
        """
        Initialize safety pipeline with optional custom components.
        """
        self.pii_redactor = pii_redactor or get_pii_redactor()
        self.injection_detector = injection_detector or get_injection_detector()
        self.content_moderator = content_moderator or get_content_moderator()
        self.llm_client = llm_client
    
    async def validate_input(self,
                             text: str,
                             grade: int = 5,
                             student_id: Optional[str] = None) -> SafetyCheckResult:
        """
        Run full input validation pipeline.
        
        Pipeline stages:
        1. PII Detection & Redaction
        2. Injection Attack Detection
        3. Content Moderation (grade-aware)
        
        Args:
            text: User input text
            grade: Student grade level
            student_id: Optional student ID for logging
            
        Returns:
            SafetyCheckResult with action and details
        """
        start_time = datetime.now()
        warnings = []
        
        if not text or not text.strip():
            return SafetyCheckResult(
                action=SafetyAction.ALLOW,
                original_text=text,
                processed_text=text,
                processing_time_ms=0
            )
        
        current_text = text
        
        # Stage 1: PII Detection & Redaction
        pii_result = self.pii_redactor.redact(text)
        pii_detected = pii_result.has_pii
        pii_types = list(pii_result.detection_summary.keys())
        
        if pii_detected:
            current_text = pii_result.redacted_text
            warnings.append(f"PII detected and masked: {', '.join(pii_types)}")
        
        # Stage 2: Injection Detection (async)
        injection_result = await self.injection_detector.analyze(current_text)
        
        if injection_result.should_block:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            return SafetyCheckResult(
                action=SafetyAction.BLOCK,
                original_text=text,
                processed_text=current_text,
                pii_detected=pii_detected,
                pii_types=pii_types,
                injection_threat=injection_result.threat_level,
                block_reason=f"Security violation: {injection_result.reason}",
                warnings=warnings,
                processing_time_ms=elapsed
            )
        
        if injection_result.threat_level == ThreatLevel.SUSPICIOUS:
            warnings.append(f"Suspicious content: {injection_result.reason}")
        
        # Stage 3: Content Moderation
        moderation_result = self.content_moderator.moderate(current_text, grade)
        
        if moderation_result.result == ModerationResult.BLOCKED:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            return SafetyCheckResult(
                action=SafetyAction.BLOCK,
                original_text=text,
                processed_text=current_text,
                pii_detected=pii_detected,
                pii_types=pii_types,
                injection_threat=injection_result.threat_level,
                moderation_result=moderation_result.result,
                block_reason=moderation_result.reason,
                warnings=warnings,
                processing_time_ms=elapsed
            )
        
        if moderation_result.result == ModerationResult.NEEDS_REVIEW:
            warnings.append(moderation_result.reason)
        
        # Determine final action
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        
        if pii_detected:
            action = SafetyAction.SANITIZE
        elif warnings:
            action = SafetyAction.WARN
        else:
            action = SafetyAction.ALLOW
        
        return SafetyCheckResult(
            action=action,
            original_text=text,
            processed_text=current_text,
            pii_detected=pii_detected,
            pii_types=pii_types,
            injection_threat=injection_result.threat_level,
            moderation_result=moderation_result.result,
            warnings=warnings,
            processing_time_ms=elapsed
        )
    
    async def validate_output(self,
                              output: str,
                              original_question: str,
                              grade: int = 5,
                              max_retries: int = 2) -> OutputValidationResult:
        """
        Validate and optionally refine LLM output using Reflection pattern.
        
        Implements self-critique loop:
        1. Check output against content moderation
        2. Use LLM to self-critique
        3. If unsafe, regenerate with feedback
        4. Repeat until safe or max retries
        
        Args:
            output: LLM-generated output
            original_question: Original user question
            grade: Student grade level
            max_retries: Maximum refinement attempts
            
        Returns:
            OutputValidationResult
        """
        issues_found = []
        current_output = output
        
        for iteration in range(max_retries + 1):
            # Quick content moderation check
            moderation = self.content_moderator.moderate_output(current_output, grade)
            
            if moderation.result == ModerationResult.BLOCKED:
                issues_found.append(f"Iteration {iteration}: {moderation.reason}")
                
                if iteration < max_retries:
                    # Try to refine
                    current_output = await self._refine_output(
                        current_output,
                        original_question,
                        grade,
                        moderation.reason
                    )
                    continue
                else:
                    # Max retries reached, use fallback
                    return OutputValidationResult(
                        is_safe=False,
                        original_output=output,
                        validated_output=self._get_fallback_response(moderation.categories),
                        iterations=iteration + 1,
                        issues_found=issues_found,
                        refinement_feedback="Max retries reached, using fallback response"
                    )
            
            # Self-critique with LLM (if available)
            if self.llm_client and iteration == 0:
                critique_result = await self._self_critique(
                    current_output,
                    original_question,
                    grade
                )
                
                if critique_result.startswith("UNSAFE"):
                    issues_found.append(f"Self-critique: {critique_result}")
                    if iteration < max_retries:
                        current_output = await self._refine_output(
                            current_output,
                            original_question,
                            grade,
                            critique_result
                        )
                        continue
                elif critique_result.startswith("NEEDS_EDIT"):
                    # Minor edit needed
                    issues_found.append(f"Self-critique (minor): {critique_result}")
                    current_output = await self._refine_output(
                        current_output,
                        original_question,
                        grade,
                        critique_result
                    )
            
            # Output is safe
            return OutputValidationResult(
                is_safe=True,
                original_output=output,
                validated_output=current_output,
                iterations=iteration + 1,
                issues_found=issues_found
            )
        
        # Should not reach here, but safety fallback
        return OutputValidationResult(
            is_safe=False,
            original_output=output,
            validated_output=self.FALLBACK_RESPONSES["general"],
            iterations=max_retries + 1,
            issues_found=issues_found
        )
    
    async def _self_critique(self, 
                             output: str, 
                             question: str, 
                             grade: int) -> str:
        """Use LLM to self-critique the output."""
        if not self.llm_client:
            self.llm_client = LLMClient(temperature=0.0)
        
        try:
            prompt = self.SELF_CRITIQUE_PROMPT.format(
                output=output[:3000],
                question=question[:500],
                grade=grade
            )
            response = await self.llm_client.generate(prompt)
            return response.content.strip()
        except Exception as e:
            return f"SAFE (critique error: {str(e)})"
    
    async def _refine_output(self,
                             output: str,
                             question: str,
                             grade: int,
                             feedback: str) -> str:
        """Refine output based on safety feedback."""
        if not self.llm_client:
            self.llm_client = LLMClient(temperature=0.3)
        
        try:
            prompt = self.REFINEMENT_PROMPT.format(
                output=output[:2000],
                question=question[:500],
                grade=grade,
                feedback=feedback
            )
            response = await self.llm_client.generate(prompt)
            return response.content.strip()
        except Exception:
            return self.FALLBACK_RESPONSES["general"]
    
    def _get_fallback_response(self, categories: List = None) -> str:
        """Get appropriate fallback response based on violation categories."""
        if not categories:
            return self.FALLBACK_RESPONSES["general"]
        
        category_names = [c.value if hasattr(c, 'value') else str(c) for c in categories]
        
        if "violence" in category_names or "weapons" in category_names:
            return self.FALLBACK_RESPONSES["violence"]
        elif "adult" in category_names:
            return self.FALLBACK_RESPONSES["inappropriate"]
        
        return self.FALLBACK_RESPONSES["general"]


# Singleton instance
_safety_pipeline: Optional[SafetyPipeline] = None


def get_safety_pipeline() -> SafetyPipeline:
    """Get or create singleton SafetyPipeline instance."""
    global _safety_pipeline
    if _safety_pipeline is None:
        _safety_pipeline = SafetyPipeline()
    return _safety_pipeline


async def validate_user_input(text: str, grade: int = 5) -> SafetyCheckResult:
    """Convenience function for input validation."""
    pipeline = get_safety_pipeline()
    return await pipeline.validate_input(text, grade)


async def validate_ai_output(output: str, question: str, grade: int = 5) -> OutputValidationResult:
    """Convenience function for output validation."""
    pipeline = get_safety_pipeline()
    return await pipeline.validate_output(output, question, grade)
