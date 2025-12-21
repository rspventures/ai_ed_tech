"""
AI Tutor Platform - Data Retention Service
Automated data cleanup according to retention policies.
"""
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import text, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_log import AuditLogger, AuditEventType, get_audit_logger


class DataType(str, Enum):
    """Types of data subject to retention policies."""
    CHAT_MESSAGES = "chat_messages"
    GENERATED_IMAGES = "generated_images"
    UPLOADED_DOCUMENTS = "uploaded_documents"
    DOCUMENT_CHUNKS = "document_chunks"
    AUDIT_LOGS = "audit_logs"
    SESSION_DATA = "session_data"


@dataclass
class RetentionPolicy:
    """Data retention policy configuration."""
    data_type: DataType
    retention_days: int
    table_name: str
    date_column: str = "created_at"
    cascade_tables: List[str] = None
    
    def __post_init__(self):
        if self.cascade_tables is None:
            self.cascade_tables = []


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    data_type: DataType
    records_deleted: int
    cutoff_date: datetime
    success: bool
    error: Optional[str] = None


class DataRetentionService:
    """
    Automated data retention and cleanup service.
    
    Implements COPPA/FERPA compliant data lifecycle management:
    - Chat history: 90 days
    - Generated images: 7 days  
    - Uploaded documents: 30 days
    - Audit logs: 365 days
    """
    
    # Default retention policies
    DEFAULT_POLICIES = [
        RetentionPolicy(
            data_type=DataType.CHAT_MESSAGES,
            retention_days=90,
            table_name="agent_memory",
            date_column="created_at"
        ),
        RetentionPolicy(
            data_type=DataType.GENERATED_IMAGES,
            retention_days=7,
            table_name="generated_images",
            date_column="created_at"
        ),
        RetentionPolicy(
            data_type=DataType.UPLOADED_DOCUMENTS,
            retention_days=30,
            table_name="user_documents",
            date_column="created_at",
            cascade_tables=["document_chunks"]
        ),
        RetentionPolicy(
            data_type=DataType.DOCUMENT_CHUNKS,
            retention_days=30,
            table_name="document_chunks",
            date_column="created_at"
        ),
        RetentionPolicy(
            data_type=DataType.AUDIT_LOGS,
            retention_days=365,
            table_name="safety_audit_logs",
            date_column="created_at"
        ),
    ]
    
    def __init__(self, 
                 db_session: AsyncSession,
                 policies: List[RetentionPolicy] = None,
                 audit_logger: Optional[AuditLogger] = None):
        """
        Initialize data retention service.
        
        Args:
            db_session: Database session
            policies: Custom retention policies (uses defaults if not provided)
            audit_logger: Logger for compliance auditing
        """
        self.db_session = db_session
        self.policies = policies or self.DEFAULT_POLICIES
        self.audit_logger = audit_logger or get_audit_logger(db_session)
        
        # Build lookup by data type
        self._policy_map = {p.data_type: p for p in self.policies}
    
    async def cleanup_all(self, dry_run: bool = False) -> List[CleanupResult]:
        """
        Run cleanup for all data types according to policies.
        
        Args:
            dry_run: If True, only counts records without deleting
            
        Returns:
            List of cleanup results
        """
        results = []
        
        for policy in self.policies:
            try:
                result = await self._cleanup_data_type(policy, dry_run)
                results.append(result)
                
                # Log cleanup event
                if not dry_run and result.records_deleted > 0:
                    await self.audit_logger.log_data_deletion(
                        student_id=None,
                        data_types=[policy.data_type.value],
                        requested_by="retention_service"
                    )
                    
            except Exception as e:
                results.append(CleanupResult(
                    data_type=policy.data_type,
                    records_deleted=0,
                    cutoff_date=datetime.utcnow() - timedelta(days=policy.retention_days),
                    success=False,
                    error=str(e)
                ))
        
        return results
    
    async def cleanup_data_type(self, 
                                data_type: DataType, 
                                dry_run: bool = False) -> CleanupResult:
        """
        Run cleanup for a specific data type.
        
        Args:
            data_type: Type of data to clean up
            dry_run: If True, only counts records without deleting
            
        Returns:
            CleanupResult
        """
        policy = self._policy_map.get(data_type)
        if not policy:
            return CleanupResult(
                data_type=data_type,
                records_deleted=0,
                cutoff_date=datetime.utcnow(),
                success=False,
                error=f"No retention policy found for {data_type.value}"
            )
        
        return await self._cleanup_data_type(policy, dry_run)
    
    async def _cleanup_data_type(self, 
                                  policy: RetentionPolicy, 
                                  dry_run: bool) -> CleanupResult:
        """Internal cleanup implementation."""
        cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)
        
        # First, handle cascade deletes (e.g., document_chunks before user_documents)
        for cascade_table in policy.cascade_tables:
            await self._delete_from_table(
                cascade_table, 
                policy.date_column, 
                cutoff_date, 
                dry_run
            )
        
        # Delete from main table
        count = await self._delete_from_table(
            policy.table_name,
            policy.date_column,
            cutoff_date,
            dry_run
        )
        
        return CleanupResult(
            data_type=policy.data_type,
            records_deleted=count,
            cutoff_date=cutoff_date,
            success=True
        )
    
    async def _delete_from_table(self,
                                  table_name: str,
                                  date_column: str,
                                  cutoff_date: datetime,
                                  dry_run: bool) -> int:
        """Delete old records from a table."""
        
        if dry_run:
            # Just count
            query = text(f"""
                SELECT COUNT(*) 
                FROM {table_name} 
                WHERE {date_column} < :cutoff
            """)
            result = await self.db_session.execute(query, {"cutoff": cutoff_date})
            return result.scalar() or 0
        else:
            # Actually delete
            query = text(f"""
                DELETE FROM {table_name} 
                WHERE {date_column} < :cutoff
            """)
            result = await self.db_session.execute(query, {"cutoff": cutoff_date})
            await self.db_session.commit()
            return result.rowcount
    
    async def get_data_summary(self) -> Dict[str, Dict]:
        """
        Get summary of data by type and age.
        
        Returns:
            Dictionary with data counts and oldest records by type
        """
        summary = {}
        
        for policy in self.policies:
            try:
                # Count total and expiring records
                cutoff = datetime.utcnow() - timedelta(days=policy.retention_days)
                
                total_query = text(f"SELECT COUNT(*) FROM {policy.table_name}")
                total_result = await self.db_session.execute(total_query)
                total_count = total_result.scalar() or 0
                
                expiring_query = text(f"""
                    SELECT COUNT(*) FROM {policy.table_name} 
                    WHERE {policy.date_column} < :cutoff
                """)
                expiring_result = await self.db_session.execute(
                    expiring_query, {"cutoff": cutoff}
                )
                expiring_count = expiring_result.scalar() or 0
                
                summary[policy.data_type.value] = {
                    "total_records": total_count,
                    "records_expiring": expiring_count,
                    "retention_days": policy.retention_days,
                    "next_cleanup_cutoff": cutoff.isoformat()
                }
                
            except Exception as e:
                summary[policy.data_type.value] = {
                    "error": str(e)
                }
        
        return summary
    
    async def delete_student_data(self, 
                                   student_id: str,
                                   data_types: List[DataType] = None) -> Dict[str, int]:
        """
        Delete all data for a specific student (GDPR/COPPA right to deletion).
        
        Args:
            student_id: Student UUID
            data_types: Specific types to delete (all if not specified)
            
        Returns:
            Dictionary with deleted counts by type
        """
        results = {}
        types_to_delete = data_types or [p.data_type for p in self.policies]
        
        for data_type in types_to_delete:
            policy = self._policy_map.get(data_type)
            if not policy:
                continue
            
            # Check if table has student_id column
            try:
                query = text(f"""
                    DELETE FROM {policy.table_name} 
                    WHERE student_id = :student_id
                """)
                result = await self.db_session.execute(
                    query, {"student_id": student_id}
                )
                results[data_type.value] = result.rowcount
            except Exception:
                # Table might not have student_id column
                results[data_type.value] = 0
        
        await self.db_session.commit()
        
        # Log the deletion
        await self.audit_logger.log_data_deletion(
            student_id=student_id,
            data_types=[d.value for d in types_to_delete],
            requested_by="student_request"
        )
        
        return results


async def run_scheduled_cleanup(db_session: AsyncSession) -> List[CleanupResult]:
    """
    Entry point for scheduled cleanup task (Celery/cron).
    
    Example Celery task:
    @celery.task
    def cleanup_expired_data():
        async def _run():
            async with get_db_session() as session:
                return await run_scheduled_cleanup(session)
        return asyncio.run(_run())
    """
    service = DataRetentionService(db_session)
    return await service.cleanup_all(dry_run=False)
