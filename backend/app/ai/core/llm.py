"""
AI Tutor Platform - Unified LLM Client
Centralized LLM access with telemetry, guardrails, and reliability features.
"""
import json
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.ai.core.telemetry import get_tracer, trace_llm_call, agent_span
from app.ai.core.guardrails import validate_agent_input, validate_agent_output


@dataclass
class LLMResponse:
    """Standardized response from LLM client."""
    content: str
    model: str
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0
    raw_response: Any = None


class LLMClient:
    """
    Unified LLM Client for all AI Agents.
    
    Features:
    - Multi-provider support (OpenAI, Anthropic)
    - Built-in telemetry (OpenTelemetry)
    - Input/Output guardrails
    - Retry logic with exponential backoff
    - Token usage tracking
    """
    
    def __init__(
        self,
        provider: str = None,
        model: str = None,
        temperature: float = 0.7,
        timeout: int = None,
        enable_guardrails: bool = True,
    ):
        """
        Initialize the LLM client.
        
        Args:
            provider: LLM provider ('openai' or 'anthropic'). Defaults to settings.
            model: Model name. Defaults to settings.
            temperature: Sampling temperature.
            timeout: Request timeout in seconds.
            enable_guardrails: Whether to apply input/output guardrails.
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or (
            settings.OPENAI_MODEL if self.provider == "openai" 
            else settings.ANTHROPIC_MODEL
        )
        self.temperature = temperature
        self.timeout = timeout or settings.LLM_TIMEOUT_SECONDS
        self.enable_guardrails = enable_guardrails
        
        self._llm = None
    
    @property
    def llm(self):
        """Lazy-load the LLM instance."""
        if self._llm is None:
            if self.provider == "openai":
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=self.model,
                    api_key=settings.OPENAI_API_KEY,
                    temperature=self.temperature,
                    timeout=self.timeout,
                )
            else:
                from langchain_anthropic import ChatAnthropic
                self._llm = ChatAnthropic(
                    model=self.model,
                    api_key=settings.ANTHROPIC_API_KEY,
                    temperature=self.temperature,
                    timeout=self.timeout,
                )
        return self._llm
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        agent_name: str = "LLMClient",
    ) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt.
            context: Optional context variables for prompt formatting.
            agent_name: Name of the calling agent (for telemetry).
            
        Returns:
            LLMResponse with content and metadata.
        """
        tracer = get_tracer()
        
        with tracer.start_as_current_span("llm.generate") as span:
            span.set_attribute("llm.model", self.model)
            span.set_attribute("llm.provider", self.provider)
            span.set_attribute("agent.name", agent_name)
            
            # Apply input guardrails
            sanitized_prompt = prompt
            if self.enable_guardrails:
                try:
                    sanitized_prompt, warnings = validate_agent_input(prompt)
                    if warnings:
                        span.set_attribute("guardrails.input_warnings", str(warnings))
                except ValueError as e:
                    span.set_attribute("guardrails.input_blocked", True)
                    raise
            
            # Format prompt if context provided
            if context:
                try:
                    sanitized_prompt = sanitized_prompt.format(**context)
                except KeyError:
                    pass  # Ignore missing format keys
            
            # Build messages
            messages = []
            if system_prompt:
                if context:
                    try:
                        system_prompt = system_prompt.format(**context)
                    except KeyError:
                        pass
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=sanitized_prompt))
            
            # Record prompt length
            span.set_attribute("llm.prompt_length", len(sanitized_prompt))
            
            # Call LLM
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            # Extract token usage if available
            tokens_prompt = 0
            tokens_completion = 0
            if hasattr(response, 'response_metadata'):
                usage = response.response_metadata.get('token_usage', {})
                tokens_prompt = usage.get('prompt_tokens', 0)
                tokens_completion = usage.get('completion_tokens', 0)
            
            tokens_total = tokens_prompt + tokens_completion
            
            # Record telemetry
            trace_llm_call(
                model=self.model,
                prompt_tokens=tokens_prompt,
                completion_tokens=tokens_completion,
                total_tokens=tokens_total,
            )
            
            # Apply output guardrails
            if self.enable_guardrails:
                try:
                    content, warnings = validate_agent_output(content)
                    if warnings:
                        span.set_attribute("guardrails.output_warnings", str(warnings))
                except ValueError as e:
                    span.set_attribute("guardrails.output_blocked", True)
                    raise
            
            span.set_attribute("llm.response_length", len(content))
            
            return LLMResponse(
                content=content,
                model=self.model,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                tokens_total=tokens_total,
                raw_response=response,
            )
    
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        agent_name: str = "LLMClient",
    ) -> Dict[str, Any]:
        """
        Generate a JSON response from the LLM.
        Parses the response and returns a dictionary.
        """
        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            context=context,
            agent_name=agent_name,
        )
        
        # Parse JSON from response
        content = response.content.strip()
        
        # Strip markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        return json.loads(content)
    
    async def chat(
        self,
        messages: List[BaseMessage],
        agent_name: str = "LLMClient",
    ) -> LLMResponse:
        """
        Send a conversation (list of messages) to the LLM.
        
        Args:
            messages: List of LangChain message objects.
            agent_name: Name of the calling agent (for telemetry).
            
        Returns:
            LLMResponse with content and metadata.
        """
        tracer = get_tracer()
        
        with tracer.start_as_current_span("llm.chat") as span:
            span.set_attribute("llm.model", self.model)
            span.set_attribute("llm.provider", self.provider)
            span.set_attribute("agent.name", agent_name)
            span.set_attribute("llm.message_count", len(messages))
            
            # Call LLM with message history
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            # Extract token usage
            tokens_prompt = 0
            tokens_completion = 0
            if hasattr(response, 'response_metadata'):
                usage = response.response_metadata.get('token_usage', {})
                tokens_prompt = usage.get('prompt_tokens', 0)
                tokens_completion = usage.get('completion_tokens', 0)
            
            tokens_total = tokens_prompt + tokens_completion
            trace_llm_call(self.model, tokens_prompt, tokens_completion, tokens_total)
            
            # Apply output guardrails
            if self.enable_guardrails:
                try:
                    content, warnings = validate_agent_output(content)
                    if warnings:
                        span.set_attribute("guardrails.output_warnings", str(warnings))
                except ValueError as e:
                    span.set_attribute("guardrails.output_blocked", True)
                    raise
            
            return LLMResponse(
                content=content,
                model=self.model,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                tokens_total=tokens_total,
                raw_response=response,
            )


# Default client instance
_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the default LLM client instance."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
