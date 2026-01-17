"""
AI Tutor Platform - LangGraph Base Utilities
Provides base state definitions and utilities for LangGraph workflows.
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from dataclasses import dataclass, field
from enum import Enum
import operator


class GraphStatus(str, Enum):
    """Status of graph execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_RETRY = "needs_retry"


class GraphState(TypedDict, total=False):
    """
    Base state for LangGraph workflows.
    
    Uses TypedDict for LangGraph compatibility.
    All fields are optional to allow partial state updates.
    """
    # Execution tracking
    status: GraphStatus
    current_step: str
    steps_completed: List[str]
    error: Optional[str]
    retry_count: int
    
    # User context
    user_id: str
    document_id: Optional[str]
    
    # Content
    input_text: str
    output_text: str
    
    # Metadata
    metadata: Dict[str, Any]


@dataclass
class GraphCheckpoint:
    """Checkpoint for resumable graph execution."""
    graph_id: str
    state: Dict[str, Any]
    step: str
    timestamp: float = field(default_factory=lambda: __import__('time').time())


def create_graph_checkpoint(
    graph_id: str,
    state: Dict[str, Any],
    step: str,
) -> GraphCheckpoint:
    """Create a checkpoint for graph state."""
    return GraphCheckpoint(
        graph_id=graph_id,
        state=state,
        step=step,
    )


def merge_lists(left: List[Any], right: List[Any]) -> List[Any]:
    """Reducer for merging lists in state."""
    return left + right


def update_dict(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """Reducer for updating dicts in state."""
    result = left.copy()
    result.update(right)
    return result


# Annotated types for LangGraph state reducers
Messages = Annotated[List[str], merge_lists]
Metadata = Annotated[Dict[str, Any], update_dict]
