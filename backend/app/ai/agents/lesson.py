"""
AI Tutor Platform - Lesson Agent
Generates personalized, engaging lesson content.
Refactored from lesson_generator.py to use Agentic Architecture.
"""
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.ai.core.telemetry import get_tracer


@dataclass
class LessonContent:
    """Schema for generated lesson content."""
    title: str
    hook: str
    introduction: str
    sections: List[Dict[str, str]]
    summary: str
    fun_fact: Optional[str] = None


class LessonAgent(BaseAgent):
    """
    The Lesson Creator Agent 🎨
    
    Generates rich, engaging, grade-appropriate lesson content
    using LLM to explain educational concepts.
    
    Uses the Plan-Execute pattern:
    - Plan: Determine lesson parameters and style
    - Execute: Generate lesson content via LLM
    """
    
    name = "LessonAgent"
    description = "Generates engaging educational lesson content"
    version = "2.0.0"
    
    SYSTEM_PROMPT = """You are an expert teacher who creates AMAZING lessons 
that make learning fun and memorable. You specialize in teaching grades 1-7.

Create a complete lesson about the following topic:
- Subject: {subject}
- Topic: {topic}
- Subtopic: {subtopic}
- Grade Level: {grade} (ages {age_range})
- Teaching Style: {style}

LESSON REQUIREMENTS:
1. **Hook**: Start with something that grabs attention (a question, fun fact, or scenario)
2. **Introduction**: Briefly explain what we'll learn (1-2 sentences)
3. **Sections**: Create 2-3 teaching sections, each with:
   - A clear title
   - Simple explanation using age-appropriate language
   - A relatable example (use everyday objects: apples, toys, animals)
4. **Summary**: 2-3 bullet points of what we learned
5. **Fun Fact**: One cool related fact kids will want to share

STYLE GUIDELINES for Grade {grade}:
- Use simple words (imagine explaining to a {age_range} year old)
- Include emojis to make it fun 🎉
- Use "you" and "we" to be friendly
- Keep sentences short
- Make examples relatable (toys, snacks, pets, playground)

TEACHING STYLE "{style}" means:
- "story": Frame the lesson as a mini-adventure or story
- "facts": Focus on clear facts with visual descriptions
- "visual": Describe things that can be drawn or imagined

Respond with ONLY valid JSON in this exact format:
{{
    "title": "A fun, engaging title for the lesson",
    "hook": "An attention-grabbing opener (1-2 sentences)",
    "introduction": "What we'll learn today (1-2 sentences)",
    "sections": [
        {{
            "title": "Section Title",
            "content": "The main teaching content (2-4 sentences)",
            "example": "A worked example or scenario"
        }}
    ],
    "summary": "Key takeaways as a short paragraph or bullet list",
    "fun_fact": "One cool fact kids will love"
}}

Generate the lesson now. Output ONLY the JSON, no markdown formatting."""

    AGE_RANGES = {
        1: "6-7", 2: "7-8", 3: "8-9", 4: "9-10",
        5: "10-11", 6: "11-12", 7: "12-13",
    }

    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """
        Plan the lesson generation.
        """
        metadata = context.metadata
        grade = metadata.get("grade", 1)
        
        return {
            "action": "generate_lesson",
            "params": {
                "subject": metadata.get("subject", "General"),
                "topic": metadata.get("topic", ""),
                "subtopic": metadata.get("subtopic", ""),
                "grade": grade,
                "age_range": self.AGE_RANGES.get(grade, "6-13"),
                "style": metadata.get("style", "story"),
            }
        }
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """
        Execute the lesson generation.
        """
        tracer = get_tracer()
        
        with tracer.start_as_current_span("generate_lesson") as span:
            try:
                params = plan["params"]
                
                span.set_attribute("lesson.subject", params["subject"])
                span.set_attribute("lesson.topic", params["topic"])
                span.set_attribute("lesson.grade", params["grade"])
                span.set_attribute("lesson.style", params["style"])
                
                # Generate lesson via LLM
                response = await self.llm.generate_json(
                    prompt="Generate the lesson now.",
                    system_prompt=self.SYSTEM_PROMPT,
                    context=params,
                    agent_name=self.name,
                )
                
                # Normalize response
                if "sections" not in response:
                    response["sections"] = []
                if "fun_fact" not in response:
                    response["fun_fact"] = None
                
                lesson = LessonContent(
                    title=response.get("title", ""),
                    hook=response.get("hook", ""),
                    introduction=response.get("introduction", ""),
                    sections=response.get("sections", []),
                    summary=response.get("summary", ""),
                    fun_fact=response.get("fun_fact"),
                )
                
                span.set_attribute("lesson.sections_count", len(lesson.sections))
                
                return AgentResult(
                    success=True,
                    output=response,  # Return dict for API compatibility
                    state=AgentState.COMPLETED,
                    metadata={"params": params},
                )
                
            except Exception as e:
                span.record_exception(e)
                return AgentResult(
                    success=False,
                    output=None,
                    state=AgentState.ERROR,
                    error=str(e),
                )
    
    async def generate(
        self,
        subject: str,
        topic: str,
        subtopic: str,
        grade: int = 1,
        style: str = "story",
    ) -> dict:
        """
        Convenience method matching the old API.
        """
        result = await self.run(
            user_input=f"Generate a lesson about {subtopic}",
            metadata={
                "subject": subject,
                "topic": topic,
                "subtopic": subtopic,
                "grade": grade,
                "style": style,
            }
        )
        
        if result.success:
            return result.output
        else:
            raise Exception(result.error or "Failed to generate lesson")


# Singleton instance for backward compatibility
lesson_agent = LessonAgent()

# Alias for backward compatibility
lesson_generator = lesson_agent
