"""
AI Tutor Platform - Base Agent
Abstract base class for all AI Agents in the platform.
"""
import uuid
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

from app.ai.core.llm import LLMClient, LLMResponse, get_llm_client
from app.ai.core.memory import AgentMemory
from app.ai.core.telemetry import get_tracer, agent_span


class AgentState(Enum):
    """Agent execution states."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentContext:
    """Context passed to agent during execution."""
    session_id: str
    user_input: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentResult:
    """Result from agent execution."""
    success: bool
    output: Any
    state: AgentState
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Abstract base class for AI Agents.
    
    Each agent follows the Plan-Execute pattern:
    1. plan() - Determine what actions to take
    2. execute() - Perform the actions
    
    Agents have:
    - Memory: Conversation/context persistence
    - LLM: Language model access
    - Tools: Registered capabilities
    - State: Current execution state
    """
    
    # Agent metadata (override in subclasses)
    name: str = "BaseAgent"
    description: str = "Base agent class"
    version: str = "1.0.0"
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        memory: Optional[AgentMemory] = None,
        temperature: float = 0.7,
        enable_telemetry: bool = True,
    ):
        """
        Initialize the agent.
        
        Args:
            llm_client: Custom LLM client (uses default if not provided).
            memory: Custom memory instance.
            temperature: LLM temperature for this agent.
            enable_telemetry: Whether to emit telemetry.
        """
        self.llm = llm_client or LLMClient(temperature=temperature)
        self.memory = memory or AgentMemory(agent_name=self.name)
        self.enable_telemetry = enable_telemetry
        
        self._state = AgentState.IDLE
        self._tools: Dict[str, callable] = {}
        
        # Register default tools
        self._register_tools()
    
    @property
    def state(self) -> AgentState:
        """Get current agent state."""
        return self._state
    
    def _register_tools(self) -> None:
        """
        Register tools/capabilities for this agent.
        Override in subclasses to add specific tools.
        """
        pass
    
    def register_tool(self, name: str, func: callable, description: str = "") -> None:
        """Register a tool that the agent can use."""
        self._tools[name] = {
            "function": func,
            "description": description,
        }
    
    async def _create_session(self) -> str:
        """Create a new session ID."""
        return str(uuid.uuid4())
    
    @abstractmethod
    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """
        Planning phase: Determine what actions to take.
        
        Args:
            context: The agent context with user input and history.
            
        Returns:
            A plan dictionary with actions to execute.
        """
        pass
    
    @abstractmethod
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """
        Execution phase: Perform the planned actions.
        
        Args:
            context: The agent context.
            plan: The plan from the planning phase.
            
        Returns:
            AgentResult with the execution outcome.
        """
        pass
    
    async def run(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Run the agent with the given input.
        
        This is the main entry point for agent execution.
        It orchestrates the plan-execute cycle.
        
        Args:
            user_input: The user's input/request.
            session_id: Optional session ID for continuity.
            metadata: Optional metadata for the request.
            
        Returns:
            AgentResult with the final output.
        """
        tracer = get_tracer()
        
        with tracer.start_as_current_span(f"{self.name}.run") as span:
            span.set_attribute("agent.name", self.name)
            span.set_attribute("agent.version", self.version)
            
            try:
                # Initialize session
                session_id = session_id or await self._create_session()
                span.set_attribute("session.id", session_id)
                
                # Get conversation history
                history = await self.memory.get_history(session_id)
                
                # Build context
                context = AgentContext(
                    session_id=session_id,
                    user_input=user_input,
                    metadata=metadata or {},
                    history=history,
                )
                
                # Add user message to memory
                await self.memory.add_message(
                    session_id=session_id,
                    role="user",
                    content=user_input,
                )
                
                # Planning phase
                self._state = AgentState.PLANNING
                span.add_event("planning_started")
                
                with tracer.start_as_current_span(f"{self.name}.plan"):
                    plan = await self.plan(context)
                
                span.add_event("planning_completed", {"plan_keys": str(list(plan.keys()))})
                
                # Execution phase
                self._state = AgentState.EXECUTING
                span.add_event("execution_started")
                
                with tracer.start_as_current_span(f"{self.name}.execute"):
                    result = await self.execute(context, plan)
                
                span.add_event("execution_completed", {"success": result.success})
                
                # Store assistant response in memory
                if result.success and result.output:
                    output_str = str(result.output) if not isinstance(result.output, str) else result.output
                    await self.memory.add_message(
                        session_id=session_id,
                        role="assistant",
                        content=output_str[:1000],  # Truncate for storage
                    )
                
                self._state = AgentState.COMPLETED
                return result
                
            except Exception as e:
                self._state = AgentState.ERROR
                span.record_exception(e)
                
                return AgentResult(
                    success=False,
                    output=None,
                    state=AgentState.ERROR,
                    error=str(e),
                )
    
    async def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get the conversation history for a session."""
        return await self.memory.get_history(session_id)
    
    async def clear_session(self, session_id: str) -> None:
        """Clear a session's memory."""
        await self.memory.clear_session(session_id)
    
    def __repr__(self) -> str:
        return f"<{self.name} v{self.version} state={self.state.value}>"
