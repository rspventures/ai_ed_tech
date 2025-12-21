"""
AI Tutor Platform - Reviewer Agent
Intelligent spaced repetition and review scheduling.
Refactored from review_agent.py to use Agentic Architecture.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.ai.core.telemetry import get_tracer
from app.models.curriculum import Progress, Subtopic, Topic, Subject
from app.models.user import Student


@dataclass
class ReviewItem:
    """A topic that needs to be reviewed."""
    subtopic_id: uuid.UUID
    subtopic_name: str
    topic_name: str
    subject_name: str
    mastery_level: float
    last_practiced: Optional[datetime]
    days_since_review: int
    priority: str  # "high", "medium", "low"
    review_reason: str


class ReviewerAgent(BaseAgent):
    """
    The Reviewer Agent 🧠
    
    An intelligent spaced repetition system that:
    - Analyzes student learning patterns
    - Schedules optimal review times
    - Generates personalized review insights
    
    Uses the Plan-Execute pattern:
    - Plan: Determine what review action to take
    - Execute: Get due reviews, update schedules, or generate insights
    """
    
    name = "ReviewerAgent"
    description = "Intelligent spaced repetition and review scheduling"
    version = "2.0.0"
    
    # SRS intervals based on performance (SM-2 inspired)
    SRS_INTERVALS = {
        "struggling": [1, 2, 4],      # Mastery < 0.4
        "learning": [1, 3, 7],        # Mastery 0.4-0.6
        "proficient": [3, 7, 14],     # Mastery 0.6-0.8
        "mastered": [7, 14, 30]       # Mastery > 0.8
    }
    
    INSIGHT_PROMPT = """You are a learning science expert analyzing a student's review needs.

Given this student's review data:
- Student: {student_name}
- Topics due for review: {review_count}
- High priority items: {high_priority_count}
- Subjects: {subjects}
- Average mastery level: {avg_mastery}%
- Sample topics needing review: {sample_topics}

Generate a brief, personalized insight about their learning patterns and what they should focus on.
Be encouraging but honest. Use emojis to make it engaging for kids.

Keep the insight to 2-3 sentences maximum.
Respond with ONLY the insight text, no JSON or markdown."""

    def _get_mastery_level_label(self, mastery: float) -> str:
        """Convert numeric mastery to label."""
        if mastery >= 0.8:
            return "mastered"
        elif mastery >= 0.6:
            return "proficient"
        elif mastery >= 0.4:
            return "learning"
        else:
            return "struggling"
    
    def _calculate_next_review(self, mastery: float, current_interval: int) -> int:
        """Calculate the next review interval based on mastery."""
        level = self._get_mastery_level_label(mastery)
        intervals = self.SRS_INTERVALS[level]
        
        for interval in intervals:
            if interval > current_interval:
                return interval
        
        return intervals[-1]
    
    def _get_priority(self, mastery: float, days_overdue: int) -> str:
        """Determine review priority based on mastery and how overdue it is."""
        if mastery < 0.4 or days_overdue > 7:
            return "high"
        elif mastery < 0.6 or days_overdue > 3:
            return "medium"
        else:
            return "low"

    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """
        Plan the review action.
        """
        metadata = context.metadata
        action = metadata.get("action", "get_due_reviews")
        
        if action == "get_due_reviews":
            return {
                "action": "get_due_reviews",
                "params": {
                    "student_id": metadata.get("student_id"),
                    "limit": metadata.get("limit", 10),
                }
            }
        elif action == "update_schedule":
            return {
                "action": "update_schedule",
                "params": {
                    "student_id": metadata.get("student_id"),
                    "subtopic_id": metadata.get("subtopic_id"),
                    "performance_score": metadata.get("performance_score", 0.5),
                }
            }
        elif action == "generate_insight":
            return {
                "action": "generate_insight",
                "params": {
                    "student_name": metadata.get("student_name", "Student"),
                    "review_items": metadata.get("review_items", []),
                }
            }
        
        return {"action": "unknown", "params": {}}
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """
        Execute the review action.
        Note: Database operations require passing db session via metadata.
        """
        tracer = get_tracer()
        action = plan["action"]
        params = plan["params"]
        
        with tracer.start_as_current_span(f"reviewer_{action}") as span:
            span.set_attribute("reviewer.action", action)
            
            try:
                if action == "generate_insight":
                    return await self._execute_generate_insight(params, span)
                else:
                    # For DB operations, return instructions (db passed separately)
                    return AgentResult(
                        success=True,
                        output={"action": action, "params": params},
                        state=AgentState.COMPLETED,
                        metadata={"requires_db": True},
                    )
            except Exception as e:
                span.record_exception(e)
                return AgentResult(
                    success=False,
                    output=None,
                    state=AgentState.ERROR,
                    error=str(e),
                )
    
    async def _execute_generate_insight(self, params: dict, span) -> AgentResult:
        """Generate personalized review insight via LLM."""
        student_name = params.get("student_name", "Student")
        review_items = params.get("review_items", [])
        
        if not review_items:
            insight = f"🌟 Great job, {student_name}! You're all caught up on your reviews. Keep learning new things!"
            return AgentResult(
                success=True,
                output={"insight": insight},
                state=AgentState.COMPLETED,
            )
        
        # Prepare data for LLM
        high_priority = [r for r in review_items if r.priority == "high"]
        subjects = list(set(r.subject_name for r in review_items))
        avg_mastery = sum(r.mastery_level for r in review_items) / len(review_items)
        
        span.set_attribute("reviewer.review_count", len(review_items))
        span.set_attribute("reviewer.high_priority_count", len(high_priority))
        
        try:
            response = await self.llm.generate(
                prompt="Generate the review insight now.",
                system_prompt=self.INSIGHT_PROMPT,
                context={
                    "student_name": student_name,
                    "review_count": len(review_items),
                    "high_priority_count": len(high_priority),
                    "subjects": ", ".join(subjects),
                    "avg_mastery": f"{avg_mastery:.0%}",
                    "sample_topics": ", ".join(r.subtopic_name for r in review_items[:3]),
                },
                agent_name=self.name,
            )
            
            insight = response.content.strip()
            
        except Exception as e:
            # Fallback if LLM fails
            insight = f"📚 You have {len(review_items)} topics to review today. Let's keep those skills sharp!"
        
        return AgentResult(
            success=True,
            output={"insight": insight},
            state=AgentState.COMPLETED,
        )
    
    # =========================================================================
    # Convenience methods for backward compatibility
    # =========================================================================
    
    async def get_due_reviews(
        self,
        db: AsyncSession,
        student_id: uuid.UUID,
        limit: int = 10
    ) -> List[ReviewItem]:
        """
        PERCEIVE: Get all topics due for review.
        Uses SRS algorithm to find topics needing review.
        """
        tracer = get_tracer()
        
        with tracer.start_as_current_span("get_due_reviews") as span:
            span.set_attribute("reviewer.student_id", str(student_id))
            
            now = datetime.now(timezone.utc)
            
            # Query progress with subtopic, topic, and subject info
            query = select(Progress).options(
                selectinload(Progress.subtopic).selectinload(Subtopic.topic).selectinload(Topic.subject)
            ).where(
                and_(
                    Progress.student_id == student_id,
                    Progress.last_practiced_at.isnot(None)
                )
            )
            
            result = await db.execute(query)
            all_progress = result.scalars().all()
            
            review_items = []
            
            for progress in all_progress:
                if not progress.subtopic:
                    continue
                
                needs_review = False
                days_since = 0
                review_reason = ""
                
                if progress.last_practiced_at:
                    # Ensure timezone-aware comparison
                    last_practiced = progress.last_practiced_at
                    if last_practiced.tzinfo is None:
                        last_practiced = last_practiced.replace(tzinfo=timezone.utc)
                    days_since = (now - last_practiced).days
                
                # Check SRS schedule
                next_review = progress.next_review_at
                if next_review and next_review.tzinfo is None:
                    next_review = next_review.replace(tzinfo=timezone.utc)
                if next_review and next_review <= now:
                    needs_review = True
                    review_reason = "Scheduled for review today"
                elif progress.last_practiced_at and not progress.next_review_at:
                    level = self._get_mastery_level_label(progress.mastery_level)
                    default_interval = self.SRS_INTERVALS[level][0]
                    if days_since >= default_interval:
                        needs_review = True
                        review_reason = f"Not reviewed in {days_since} days"
                elif progress.mastery_level < 0.4 and days_since >= 1:
                    needs_review = True
                    review_reason = "Needs more practice (low mastery)"
                
                if needs_review:
                    days_overdue = 0
                    if progress.next_review_at:
                        next_review = progress.next_review_at
                        if next_review.tzinfo is None:
                            next_review = next_review.replace(tzinfo=timezone.utc)
                        days_overdue = max(0, (now - next_review).days)
                    
                    review_items.append(ReviewItem(
                        subtopic_id=progress.subtopic_id,
                        subtopic_name=progress.subtopic.name,
                        topic_name=progress.subtopic.topic.name,
                        subject_name=progress.subtopic.topic.subject.name,
                        mastery_level=progress.mastery_level,
                        last_practiced=progress.last_practiced_at,
                        days_since_review=days_since,
                        priority=self._get_priority(progress.mastery_level, days_overdue),
                        review_reason=review_reason
                    ))
            
            # Sort by priority and mastery
            priority_order = {"high": 0, "medium": 1, "low": 2}
            review_items.sort(key=lambda x: (priority_order[x.priority], x.mastery_level))
            
            span.set_attribute("reviewer.items_found", len(review_items))
            
            return review_items[:limit]
    
    async def update_review_schedule(
        self,
        db: AsyncSession,
        student_id: uuid.UUID,
        subtopic_id: uuid.UUID,
        performance_score: float
    ) -> None:
        """
        ACT: Update the review schedule after a practice session.
        Implements SRS logic for interval adjustment.
        """
        tracer = get_tracer()
        
        with tracer.start_as_current_span("update_review_schedule") as span:
            span.set_attribute("reviewer.performance", performance_score)
            
            query = select(Progress).where(
                and_(
                    Progress.student_id == student_id,
                    Progress.subtopic_id == subtopic_id
                )
            )
            result = await db.execute(query)
            progress = result.scalar_one_or_none()
            
            if not progress:
                return
            
            # Adjust mastery based on performance
            new_mastery = progress.mastery_level * 0.7 + performance_score * 0.3
            new_mastery = max(0.0, min(1.0, new_mastery))
            
            # Calculate next interval
            if performance_score >= 0.7:
                new_interval = self._calculate_next_review(new_mastery, progress.review_interval_days)
            elif performance_score >= 0.4:
                new_interval = progress.review_interval_days
            else:
                new_interval = 1
            
            # Update progress
            progress.mastery_level = new_mastery
            progress.review_interval_days = new_interval
            progress.next_review_at = datetime.now(timezone.utc) + timedelta(days=new_interval)
            progress.last_practiced_at = datetime.now(timezone.utc)
            
            span.set_attribute("reviewer.new_mastery", new_mastery)
            span.set_attribute("reviewer.new_interval", new_interval)
            
            await db.commit()
    
    async def generate_review_insight(
        self,
        student_name: str,
        review_items: List[ReviewItem]
    ) -> str:
        """
        REASON: Generate personalized insight about review session.
        """
        result = await self.run(
            user_input=f"Generate review insight for {student_name}",
            metadata={
                "action": "generate_insight",
                "student_name": student_name,
                "review_items": review_items,
            }
        )
        
        if result.success:
            return result.output.get("insight", "Keep up the great work!")
        else:
            return f"📚 You have {len(review_items)} topics to review today!"


# Singleton instance for backward compatibility
reviewer_agent = ReviewerAgent()

# Alias for backward compatibility
review_agent = reviewer_agent
