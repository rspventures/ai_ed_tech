"""
AI Tutor Platform - Audit Logger
Compliance logging for COPPA/FERPA adherence.
Logs safety events without storing actual PII.
"""
import hashlib
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import Column, String, DateTime, JSON, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base


class AuditEventType(str, Enum):
    """Types of audit events."""
    # Input events
    USER_INPUT = "user_input"
    PII_DETECTED = "pii_detected"
    INJECTION_ATTEMPT = "injection_attempt"
    CONTENT_BLOCKED = "content_blocked"
    CONTENT_WARNING = "content_warning"
    
    # Output events
    LLM_CALL = "llm_call"
    OUTPUT_BLOCKED = "output_blocked"
    OUTPUT_REFINED = "output_refined"
    
    # Data lifecycle
    DATA_ACCESS = "data_access"
    DATA_DELETION = "data_deletion"
    
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    
    # Administrative
    SETTINGS_CHANGE = "settings_change"
    EXPORT_REQUEST = "export_request"


@dataclass
class AuditEvent:
    """Audit event data structure."""
    event_type: AuditEventType
    student_id: Optional[str]
    session_id: Optional[str]
    event_data: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class SafetyAuditLog(Base):
    """Database model for safety audit logs."""
    __tablename__ = "safety_audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    session_id = Column(String(100), nullable=True)
    event_data = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class AuditLogger:
    """
    Compliance-focused audit logger.
    
    Principles:
    1. Never log actual PII - only hashes and counts
    2. Log all safety-relevant events
    3. Append-only (no updates or deletes on audit logs)
    4. Structured for easy compliance reporting
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Initialize audit logger.
        
        Args:
            db_session: Database session for persistence
        """
        self.db_session = db_session
        self._buffer: List[AuditEvent] = []
        self._buffer_size = 10  # Flush after N events
    
    def _hash_text(self, text: str) -> str:
        """Create non-reversible hash of text for logging."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def _sanitize_for_log(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove any potential PII from log data."""
        sanitized = {}
        
        # Fields that are safe to log as-is
        safe_fields = [
            "event_type", "action", "result", "threat_level", 
            "pii_types", "categories", "processing_time_ms",
            "token_count", "model", "grade", "agent_name",
            "count", "iterations", "is_safe"
        ]
        
        for key, value in data.items():
            if key in safe_fields:
                sanitized[key] = value
            elif key in ["text", "input", "output", "query", "response"]:
                # Hash text content
                if isinstance(value, str):
                    sanitized[f"{key}_hash"] = self._hash_text(value)
                    sanitized[f"{key}_length"] = len(value)
            elif key == "error":
                # Truncate error messages
                sanitized["error"] = str(value)[:200] if value else None
            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, list) and all(isinstance(x, str) for x in value):
                # Allow lists of strings (like categories)
                sanitized[key] = value
        
        return sanitized
    
    async def log(self, event: AuditEvent):
        """
        Log an audit event.
        
        Args:
            event: AuditEvent to log
        """
        # Sanitize event data
        sanitized_data = self._sanitize_for_log(event.event_data)
        
        if self.db_session:
            # Persist to database
            log_entry = SafetyAuditLog(
                event_type=event.event_type.value if isinstance(event.event_type, Enum) else event.event_type,
                student_id=uuid.UUID(event.student_id) if event.student_id else None,
                session_id=event.session_id,
                event_data=sanitized_data,
                created_at=event.timestamp or datetime.utcnow()
            )
            self.db_session.add(log_entry)
            # Don't await commit here - let the caller manage transactions
        else:
            # Buffer for batch processing
            event.event_data = sanitized_data
            self._buffer.append(event)
            
            if len(self._buffer) >= self._buffer_size:
                await self._flush_buffer()
    
    async def _flush_buffer(self):
        """Flush buffered events (for file-based or batch logging)."""
        # In production, this would write to a file or send to a logging service
        self._buffer.clear()
    
    # Convenience methods for common events
    
    async def log_user_input(self,
                             student_id: str,
                             session_id: str,
                             input_text: str,
                             grade: int):
        """Log a user input event."""
        await self.log(AuditEvent(
            event_type=AuditEventType.USER_INPUT,
            student_id=student_id,
            session_id=session_id,
            event_data={
                "text": input_text,
                "grade": grade
            }
        ))
    
    async def log_pii_detection(self,
                                student_id: str,
                                session_id: str,
                                pii_types: List[str],
                                action: str = "redacted"):
        """Log PII detection event."""
        await self.log(AuditEvent(
            event_type=AuditEventType.PII_DETECTED,
            student_id=student_id,
            session_id=session_id,
            event_data={
                "pii_types": pii_types,
                "action": action,
                "count": len(pii_types)
            }
        ))
    
    async def log_injection_attempt(self,
                                    student_id: str,
                                    session_id: str,
                                    threat_level: str,
                                    patterns_detected: List[str],
                                    blocked: bool):
        """Log injection attempt event."""
        await self.log(AuditEvent(
            event_type=AuditEventType.INJECTION_ATTEMPT,
            student_id=student_id,
            session_id=session_id,
            event_data={
                "threat_level": threat_level,
                "patterns": patterns_detected,
                "blocked": blocked
            }
        ))
    
    async def log_content_block(self,
                                student_id: str,
                                session_id: str,
                                reason: str,
                                categories: List[str]):
        """Log content blocking event."""
        await self.log(AuditEvent(
            event_type=AuditEventType.CONTENT_BLOCKED,
            student_id=student_id,
            session_id=session_id,
            event_data={
                "reason": reason,
                "categories": categories
            }
        ))
    
    async def log_llm_call(self,
                           student_id: Optional[str],
                           session_id: str,
                           agent_name: str,
                           model: str,
                           token_count: int,
                           latency_ms: float):
        """Log LLM API call event."""
        await self.log(AuditEvent(
            event_type=AuditEventType.LLM_CALL,
            student_id=student_id,
            session_id=session_id,
            event_data={
                "agent_name": agent_name,
                "model": model,
                "token_count": token_count,
                "latency_ms": latency_ms
            }
        ))
    
    async def log_output_refinement(self,
                                    student_id: str,
                                    session_id: str,
                                    iterations: int,
                                    is_safe: bool,
                                    issues: List[str]):
        """Log output refinement event."""
        await self.log(AuditEvent(
            event_type=AuditEventType.OUTPUT_REFINED,
            student_id=student_id,
            session_id=session_id,
            event_data={
                "iterations": iterations,
                "is_safe": is_safe,
                "issues": issues
            }
        ))
    
    async def log_data_deletion(self,
                                student_id: str,
                                data_types: List[str],
                                requested_by: str):
        """Log data deletion event (for compliance)."""
        await self.log(AuditEvent(
            event_type=AuditEventType.DATA_DELETION,
            student_id=student_id,
            session_id=None,
            event_data={
                "data_types": data_types,
                "requested_by": requested_by
            }
        ))


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(db_session: Optional[AsyncSession] = None) -> AuditLogger:
    """Get or create AuditLogger instance."""
    global _audit_logger
    if _audit_logger is None or db_session is not None:
        _audit_logger = AuditLogger(db_session)
    return _audit_logger


async def log_safety_event(event_type: AuditEventType,
                           student_id: str,
                           session_id: str,
                           event_data: Dict[str, Any]):
    """Convenience function for logging safety events."""
    logger = get_audit_logger()
    await logger.log(AuditEvent(
        event_type=event_type,
        student_id=student_id,
        session_id=session_id,
        event_data=event_data
    ))
