"""
AI Tutor Platform - Gamification Agent
AI-powered XP and reward decisions based on student effort and behavior patterns.
This agent intelligently evaluates student engagement beyond simple metrics.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, date, timedelta

from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.ai.core.telemetry import get_tracer


@dataclass
class EffortAnalysis:
    """Analysis of student effort and engagement."""
    effort_score: float  # 0.0 to 1.0
    effort_level: str  # "exceptional", "good", "moderate", "low"
    bonus_xp: int
    reason: str
    encouragement: str
    badges_earned: List[str]


class GamificationAgent(BaseAgent):
    """
    The Gamification Agent 🎮
    
    An AI-powered agent that intelligently analyzes student behavior
    to award XP and recognize effort beyond simple metrics.
    
    This agent can recognize:
    - Extra practice sessions (going beyond requirements)
    - Improvement trends (getting better over time)
    - Persistence (trying again after failures)
    - Consistency (regular study habits)
    - Curiosity (exploring different topics)
    
    Uses the Plan-Execute pattern:
    - Plan: Gather student activity data
    - Execute: Analyze patterns and determine rewards via LLM
    """
    
    name = "GamificationAgent"
    description = "Intelligently rewards student effort and engagement"
    version = "1.0.0"
    
    SYSTEM_PROMPT = """You are an AI tutor analyzing a student's learning behavior to recognize 
and reward their effort. Your goal is to identify genuine effort and engagement, not just scores.

Student Activity Summary:
- Name: {student_name}
- Grade Level: {grade_level}
- Current Streak: {current_streak} days
- Longest Streak: {longest_streak} days
- Total XP: {total_xp}
- Current Level: {level}

Recent Activity (last 7 days):
{recent_activity}

Session Details:
- Activity Type: {activity_type}
- Score: {score}%
- Time Spent: {time_spent} minutes
- Questions Attempted: {questions_attempted}
- Retries: {retries}

Behavioral Indicators:
- Sessions Today: {sessions_today}
- Average Session Length: {avg_session_length} minutes
- Topics Explored This Week: {topics_explored}
- Improvement Trend: {improvement_trend}

Analyze this student's EFFORT (not just performance) and determine:
1. An effort score from 0.0 to 1.0
2. Whether they deserve bonus XP for going above and beyond
3. Any special badges they might have earned

Consider these effort indicators:
- Persistence: Did they retry after failures?
- Extra Practice: Did they do more than required?
- Consistency: Are they studying regularly?
- Improvement: Are they getting better over time?
- Curiosity: Are they exploring different topics?
- Time Investment: Did they spend quality time learning?

Respond with ONLY valid JSON:
{{
    "effort_score": 0.0 to 1.0,
    "effort_level": "exceptional" | "good" | "moderate" | "low",
    "bonus_xp": 0 to 100 (only award if truly deserved),
    "reason": "Brief explanation of why this effort level was determined",
    "encouragement": "A personalized, warm message for the student",
    "badges_earned": ["badge_name"] or [] (only if truly earned)
}}

Available Badges:
- "persistence_star": Tried 3+ times on difficult questions
- "explorer": Studied 3+ different topics in a week
- "early_bird": Started studying before 8 AM
- "night_owl": Studied after 8 PM
- "streak_master": Maintained 7+ day streak
- "improvement_champion": Showed clear improvement trend
- "extra_mile": Did 50%+ more than required
- "comeback_kid": Improved after a low score"""

    # Base XP rewards (used when not doing AI analysis)
    BASE_XP_REWARDS = {
        "lesson_complete": 50,
        "question_correct": 10,
        "question_incorrect": 2,
        "assessment_complete": 25,
        "assessment_perfect": 100,
        "exam_complete": 50,
        "exam_excellent": 75,
        "exam_perfect": 150,
        "test_complete": 35,
        "test_excellent": 60,
        "test_perfect": 120,
        "streak_bonus": 20,
        "first_login_today": 5,
    }

    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """
        Plan the effort analysis.
        """
        metadata = context.metadata
        
        # Determine if we should do AI analysis or simple XP
        activity_type = metadata.get("activity_type", "")
        should_analyze = metadata.get("analyze_effort", False)
        
        if not should_analyze:
            # Quick path: just award base XP
            return {
                "action": "award_base_xp",
                "params": {
                    "activity_type": activity_type,
                    "multiplier": metadata.get("multiplier", 1.0),
                }
            }
        
        # Full AI analysis path
        return {
            "action": "analyze_effort",
            "params": {
                "student_name": metadata.get("student_name", "Student"),
                "grade_level": metadata.get("grade_level", 1),
                "current_streak": metadata.get("current_streak", 0),
                "longest_streak": metadata.get("longest_streak", 0),
                "total_xp": metadata.get("total_xp", 0),
                "level": metadata.get("level", 1),
                "recent_activity": metadata.get("recent_activity", "No recent activity"),
                "activity_type": activity_type,
                "score": metadata.get("score", 0),
                "time_spent": metadata.get("time_spent", 0),
                "questions_attempted": metadata.get("questions_attempted", 0),
                "retries": metadata.get("retries", 0),
                "sessions_today": metadata.get("sessions_today", 1),
                "avg_session_length": metadata.get("avg_session_length", 0),
                "topics_explored": metadata.get("topics_explored", 1),
                "improvement_trend": metadata.get("improvement_trend", "stable"),
            }
        }
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """
        Execute the gamification decision.
        """
        tracer = get_tracer()
        
        action = plan["action"]
        params = plan["params"]
        
        if action == "award_base_xp":
            # Simple XP award without AI analysis
            with tracer.start_as_current_span("award_base_xp") as span:
                activity = params["activity_type"]
                multiplier = params["multiplier"]
                
                base_xp = self.BASE_XP_REWARDS.get(activity, 0)
                xp_earned = int(base_xp * multiplier)
                
                span.set_attribute("xp.activity", activity)
                span.set_attribute("xp.earned", xp_earned)
                
                return AgentResult(
                    success=True,
                    output={
                        "xp_earned": xp_earned,
                        "effort_analyzed": False,
                        "activity": activity,
                    },
                    state=AgentState.COMPLETED,
                )
        
        # AI-powered effort analysis
        with tracer.start_as_current_span("analyze_effort") as span:
            try:
                span.set_attribute("gamification.activity", params["activity_type"])
                span.set_attribute("gamification.score", params["score"])
                span.set_attribute("gamification.streak", params["current_streak"])
                
                # Analyze via LLM
                response = await self.llm.generate_json(
                    prompt="Analyze this student's effort and determine rewards.",
                    system_prompt=self.SYSTEM_PROMPT,
                    context=params,
                    agent_name=self.name,
                )
                
                # Calculate total XP
                base_xp = self.BASE_XP_REWARDS.get(params["activity_type"], 0)
                bonus_xp = response.get("bonus_xp", 0)
                
                # Apply effort multiplier
                effort_score = response.get("effort_score", 0.5)
                effort_multiplier = 1.0 + (effort_score * 0.5)  # Up to 1.5x
                
                total_xp = int((base_xp * effort_multiplier) + bonus_xp)
                
                analysis = EffortAnalysis(
                    effort_score=effort_score,
                    effort_level=response.get("effort_level", "moderate"),
                    bonus_xp=bonus_xp,
                    reason=response.get("reason", ""),
                    encouragement=response.get("encouragement", ""),
                    badges_earned=response.get("badges_earned", []),
                )
                
                span.set_attribute("gamification.effort_score", effort_score)
                span.set_attribute("gamification.total_xp", total_xp)
                span.set_attribute("gamification.badges_count", len(analysis.badges_earned))
                
                return AgentResult(
                    success=True,
                    output={
                        "xp_earned": total_xp,
                        "effort_analyzed": True,
                        "analysis": analysis,
                        "effort_score": effort_score,
                        "effort_level": analysis.effort_level,
                        "bonus_xp": bonus_xp,
                        "encouragement": analysis.encouragement,
                        "badges_earned": analysis.badges_earned,
                    },
                    state=AgentState.COMPLETED,
                    metadata={"params": params},
                )
                
            except Exception as e:
                span.record_exception(e)
                # Fallback to base XP on error
                base_xp = self.BASE_XP_REWARDS.get(params["activity_type"], 0)
                return AgentResult(
                    success=True,  # Partial success
                    output={
                        "xp_earned": base_xp,
                        "effort_analyzed": False,
                        "error": str(e),
                    },
                    state=AgentState.COMPLETED,
                )
    
    async def award_xp(
        self,
        activity_type: str,
        multiplier: float = 1.0,
    ) -> dict:
        """
        Simple XP award without AI analysis.
        Use this for quick, routine rewards.
        """
        result = await self.run(
            user_input=f"Award XP for {activity_type}",
            metadata={
                "activity_type": activity_type,
                "multiplier": multiplier,
                "analyze_effort": False,
            }
        )
        return result.output if result.success else {"xp_earned": 0}
    
    async def analyze_and_reward(
        self,
        student_name: str,
        activity_type: str,
        score: float = 0,
        time_spent: int = 0,
        questions_attempted: int = 0,
        retries: int = 0,
        current_streak: int = 0,
        longest_streak: int = 0,
        total_xp: int = 0,
        level: int = 1,
        grade_level: int = 1,
        recent_activity: str = "",
        sessions_today: int = 1,
        avg_session_length: int = 0,
        topics_explored: int = 1,
        improvement_trend: str = "stable",
    ) -> dict:
        """
        Full AI-powered effort analysis and reward.
        Use this for important activities where effort matters.
        """
        result = await self.run(
            user_input=f"Analyze effort for {student_name}'s {activity_type}",
            metadata={
                "analyze_effort": True,
                "student_name": student_name,
                "activity_type": activity_type,
                "score": score,
                "time_spent": time_spent,
                "questions_attempted": questions_attempted,
                "retries": retries,
                "current_streak": current_streak,
                "longest_streak": longest_streak,
                "total_xp": total_xp,
                "level": level,
                "grade_level": grade_level,
                "recent_activity": recent_activity,
                "sessions_today": sessions_today,
                "avg_session_length": avg_session_length,
                "topics_explored": topics_explored,
                "improvement_trend": improvement_trend,
            }
        )
        return result.output if result.success else {"xp_earned": 0}


# Singleton instance
gamification_agent = GamificationAgent()
