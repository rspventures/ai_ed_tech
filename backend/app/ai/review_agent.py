"""
AI Tutor Platform - Review Agent (Spaced Repetition System)
LangChain-based agent for intelligent topic review scheduling

This agent follows the Agentic AI paradigm:
1. PERCEIVE: Analyze student's learning history and patterns
2. REASON: Determine which topics need review based on SRS intervals
3. ACT: Generate personalized review recommendations
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.curriculum import Progress, Subtopic, Topic, Subject
from app.models.user import Student


class ReviewItem:
    """A topic that needs to be reviewed."""
    def __init__(
        self,
        subtopic_id: uuid.UUID,
        subtopic_name: str,
        topic_name: str,
        subject_name: str,
        mastery_level: float,
        last_practiced: Optional[datetime],
        days_since_review: int,
        priority: str,  # "high", "medium", "low"
        review_reason: str
    ):
        self.subtopic_id = subtopic_id
        self.subtopic_name = subtopic_name
        self.topic_name = topic_name
        self.subject_name = subject_name
        self.mastery_level = mastery_level
        self.last_practiced = last_practiced
        self.days_since_review = days_since_review
        self.priority = priority
        self.review_reason = review_reason


class ReviewAgent:
    """
    The Review Agent 🧠
    
    An Agentic AI component that intelligently schedules topic reviews
    using Spaced Repetition principles combined with LLM reasoning.
    
    Architecture:
    - Uses LangChain for LLM integration
    - Applies SM-2 style intervals: 1, 3, 7, 14, 30 days
    - Can be extended with tools for more complex reasoning
    """
    
    # SRS intervals based on performance
    SRS_INTERVALS = {
        "struggling": [1, 2, 4],      # Mastery < 0.4
        "learning": [1, 3, 7],        # Mastery 0.4-0.6
        "proficient": [3, 7, 14],     # Mastery 0.6-0.8
        "mastered": [7, 14, 30]       # Mastery > 0.8
    }
    
    INSIGHT_PROMPT = """You are a learning science expert analyzing a student's review needs.

Given this student's review data:
{review_data}

Generate a brief, personalized insight about their learning patterns and what they should focus on.
Be encouraging but honest. Use emojis to make it engaging for kids.

Keep the insight to 2-3 sentences maximum.
Format: Just return the insight text, no markdown or JSON."""

    def __init__(self):
        self.insight_prompt = ChatPromptTemplate.from_template(self.INSIGHT_PROMPT)
        self._llm = None

    @property
    def llm(self):
        """Lazy load the LLM based on configuration."""
        if self._llm is None:
            if settings.LLM_PROVIDER == "openai":
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL,
                    api_key=settings.OPENAI_API_KEY,
                    temperature=0.7,
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
            else:
                from langchain_anthropic import ChatAnthropic
                self._llm = ChatAnthropic(
                    model=settings.ANTHROPIC_MODEL,
                    api_key=settings.ANTHROPIC_API_KEY,
                    temperature=0.7,
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
        return self._llm

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
        
        # Find the next interval in the sequence
        for interval in intervals:
            if interval > current_interval:
                return interval
        
        # If all intervals passed, return the last one
        return intervals[-1]

    def _get_priority(self, mastery: float, days_overdue: int) -> str:
        """Determine review priority based on mastery and how overdue it is."""
        if mastery < 0.4 or days_overdue > 7:
            return "high"
        elif mastery < 0.6 or days_overdue > 3:
            return "medium"
        else:
            return "low"

    async def get_due_reviews(
        self, 
        db: AsyncSession, 
        student_id: uuid.UUID,
        limit: int = 10
    ) -> List[ReviewItem]:
        """
        PERCEIVE: Get all topics due for review.
        
        Uses the SRS algorithm to find topics that need reviewing:
        1. Topics with next_review_at <= now
        2. Topics practiced but never scheduled (fallback to 1 day)
        3. Topics with low mastery that haven't been practiced recently
        """
        now = datetime.utcnow()
        
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
            # Skip if no subtopic (shouldn't happen but safety check)
            if not progress.subtopic:
                continue
            
            # Determine if this needs review
            needs_review = False
            days_since = 0
            review_reason = ""
            
            if progress.last_practiced_at:
                days_since = (now - progress.last_practiced_at).days
            
            # Check SRS schedule
            if progress.next_review_at and progress.next_review_at <= now:
                needs_review = True
                review_reason = "Scheduled for review today"
            # Fallback: If practiced but no next_review, use default interval
            elif progress.last_practiced_at and not progress.next_review_at:
                level = self._get_mastery_level_label(progress.mastery_level)
                default_interval = self.SRS_INTERVALS[level][0]
                if days_since >= default_interval:
                    needs_review = True
                    review_reason = f"Not reviewed in {days_since} days"
            # Low mastery topics should be reviewed more frequently
            elif progress.mastery_level < 0.4 and days_since >= 1:
                needs_review = True
                review_reason = "Needs more practice (low mastery)"
            
            if needs_review:
                days_overdue = 0
                if progress.next_review_at:
                    days_overdue = max(0, (now - progress.next_review_at).days)
                
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
        
        # Sort by priority (high first) and then by mastery (lowest first)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        review_items.sort(key=lambda x: (priority_order[x.priority], x.mastery_level))
        
        return review_items[:limit]

    async def update_review_schedule(
        self, 
        db: AsyncSession, 
        student_id: uuid.UUID,
        subtopic_id: uuid.UUID,
        performance_score: float  # 0.0 to 1.0 based on how well they did
    ) -> None:
        """
        ACT: Update the review schedule after a practice session.
        
        This implements the core SRS logic:
        - Good performance (>0.7): Increase interval
        - Medium performance (0.4-0.7): Keep interval
        - Poor performance (<0.4): Reset to short interval
        """
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
            new_interval = progress.review_interval_days  # Keep same
        else:
            new_interval = 1  # Reset to 1 day
        
        # Update progress
        progress.mastery_level = new_mastery
        progress.review_interval_days = new_interval
        progress.next_review_at = datetime.utcnow() + timedelta(days=new_interval)
        progress.last_practiced_at = datetime.utcnow()
        
        await db.commit()

    async def generate_review_insight(
        self, 
        student_name: str,
        review_items: List[ReviewItem]
    ) -> str:
        """
        REASON: Use LLM to generate personalized insight about the review session.
        
        This is the "Agentic" part - the AI reasons about the student's
        learning patterns and provides meaningful guidance.
        """
        if not review_items:
            return f"🌟 Great job, {student_name}! You're all caught up on your reviews. Keep learning new things!"
        
        # Prepare data for the LLM
        high_priority = [r for r in review_items if r.priority == "high"]
        subjects = list(set(r.subject_name for r in review_items))
        avg_mastery = sum(r.mastery_level for r in review_items) / len(review_items)
        
        review_data = f"""
Student: {student_name}
Topics due for review: {len(review_items)}
High priority items: {len(high_priority)}
Subjects: {', '.join(subjects)}
Average mastery level: {avg_mastery:.0%}
Sample topics needing review: {', '.join(r.subtopic_name for r in review_items[:3])}
"""
        
        chain = self.insight_prompt | self.llm | StrOutputParser()
        
        try:
            insight = await chain.ainvoke({"review_data": review_data})
            return insight.strip()
        except Exception as e:
            # Fallback if LLM fails
            return f"📚 You have {len(review_items)} topics to review today. Let's keep those skills sharp!"


# Singleton instance
review_agent = ReviewAgent()
