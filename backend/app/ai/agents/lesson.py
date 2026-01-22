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


# ============================================================================
# LESSON 2.0 - Interactive Module Playlist Generator
# ============================================================================

class LessonAgentV2(BaseAgent):
    """
    The Lesson Creator Agent V2 🎨
    
    Generates Interactive Lesson Playlists with multiple module types:
    - Hook, Text, Flashcard, Fun Fact, Quiz, Activity
    
    Uses the Plan-Execute pattern per INSTRUCTIONS.md.
    Safety and Observability are automatically applied via BaseAgent.
    """
    
    name = "LessonAgentV2"
    description = "Generates interactive lesson playlists with flashcards, quizzes, and activities"
    version = "2.0.0"
    
    # Module mix recommendations by grade band
    GRADE_PROFILES = {
        "explorer": {  # Grades 1-4
            "max_text_modules": 2,
            "min_flashcards": 2,
            "min_activities": 1,
            "style_preference": "story",
        },
        "scholar": {  # Grades 5-10
            "max_text_modules": 4,
            "min_flashcards": 1,
            "min_activities": 0,
            "style_preference": "factual",
        }
    }
    
    SYSTEM_PROMPT_V2 = """You are an expert teacher creating COMPREHENSIVE INTERACTIVE LESSON PLAYLISTS.
Your goal is to make learning FUN, THOROUGH, and MEMORABLE.

Create a lesson about:
- Subject: {subject}
- Topic: {topic}
- Subtopic: {subtopic}
- Grade Level: {grade} (ages {age_range})

LESSON FORMAT:
Generate a playlist of 12-20 modules covering ALL aspects of the subtopic. Each module is ONE of these types:

1. "hook" - Attention-grabbing opener (question or fun scenario)
   {{"type": "hook", "content": "Did you know...?", "emoji": "🤔"}}

2. "text" - Explanation section (MAX 4 sentences, use emojis for engagement!)
   {{"type": "text", "content": "Plants have tiny factories called chloroplasts..."}}

3. "flashcard" - Key term/definition to remember
   {{"type": "flashcard", "front": "Chloroplast", "back": "The tiny factory in plants that makes food from sunlight"}}

4. "fun_fact" - Mind-blowing fact kids will want to share
   {{"type": "fun_fact", "content": "A single tree can absorb 48 pounds of CO2 per year!"}}

5. "quiz_single" - Check understanding (2-4 options)
   {{"type": "quiz_single", "question": "What do plants need?", "options": ["Pizza", "Sunlight", "Sand"], "correct_answer": "Sunlight"}}

6. "activity" - Real-world hands-on task
   {{"type": "activity", "content": "Find a green leaf and count its veins!", "activity_type": "solo"}}

7. "example" - Worked example with steps (IMPORTANT for understanding!)
   {{"type": "example", "title": "Calculating Plant Growth", "problem": "A plant grows 2cm per week. How tall after 4 weeks?", "steps": ["Start: 0cm", "Week 1: 2cm", "Week 2: 4cm", "Week 3: 6cm", "Week 4: 8cm"], "answer": "8cm tall"}}

8. "summary" - Key takeaways at the END of the lesson
   {{"type": "summary", "title": "Key Takeaways", "points": ["Plants make their own food", "Chloroplasts are the food factories", "Sunlight is essential"]}}

COMPREHENSIVE COVERAGE RULES:
1. Start with a HOOK to grab attention
2. Include 3-5 TEXT sections covering different aspects
3. Include 3-5 FLASHCARDS for key vocabulary
4. Include 2-3 EXAMPLES with worked problems/scenarios
5. Include 2-3 QUIZ_SINGLE to check understanding
6. Include 1-2 FUN_FACTS to make it memorable
7. Include 1-2 ACTIVITIES for hands-on learning
8. END with a SUMMARY of key takeaways

GRADE {grade} ADJUSTMENTS:
- Use simple words for younger grades (1-4)
- More examples and activities for younger grades
- More depth and complexity for older grades (5-10)
- Use emojis generously! 🎉

OUTPUT FORMAT (JSON only, no markdown):
{{
    "title": "Comprehensive title for the lesson",
    "modules": [
        {{"type": "hook", "content": "...", "emoji": "🌟"}},
        {{"type": "text", "content": "..."}},
        {{"type": "flashcard", "front": "...", "back": "..."}},
        {{"type": "example", "title": "...", "problem": "...", "steps": [...], "answer": "..."}},
        {{"type": "quiz_single", "question": "...", "options": [...], "correct_answer": "..."}},
        ... (12-20 modules total)
        {{"type": "summary", "title": "Key Takeaways", "points": [...]}}
    ],
    "estimated_duration_minutes": 10
}}

Generate the COMPREHENSIVE lesson now. Cover ALL aspects of the subtopic. Output ONLY valid JSON."""

    AGE_RANGES = {
        1: "6-7", 2: "7-8", 3: "8-9", 4: "9-10",
        5: "10-11", 6: "11-12", 7: "12-13",
        8: "13-14", 9: "14-15", 10: "15-16",
    }

    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """
        Plan the lesson generation based on grade level.
        """
        metadata = context.metadata
        grade = metadata.get("grade", 5)
        
        # Determine profile based on grade
        profile_key = "explorer" if grade <= 4 else "scholar"
        profile = self.GRADE_PROFILES[profile_key]
        
        return {
            "action": "generate_lesson_v2",
            "params": {
                "subject": metadata.get("subject", "General"),
                "topic": metadata.get("topic", ""),
                "subtopic": metadata.get("subtopic", ""),
                "grade": grade,
                "age_range": self.AGE_RANGES.get(grade, "6-16"),
                "profile": profile,
            }
        }
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """
        Execute the lesson generation with structured output.
        """
        tracer = get_tracer()
        
        with tracer.start_as_current_span("generate_lesson_v2") as span:
            try:
                params = plan["params"]
                
                span.set_attribute("lesson.subject", params["subject"])
                span.set_attribute("lesson.topic", params["topic"])
                span.set_attribute("lesson.subtopic", params["subtopic"])
                span.set_attribute("lesson.grade", params["grade"])
                span.set_attribute("lesson.version", "2.0")
                
                # Generate lesson via LLM
                response = await self.llm.generate_json(
                    prompt="Generate the interactive lesson playlist now.",
                    system_prompt=self.SYSTEM_PROMPT_V2,
                    context=params,
                    agent_name=self.name,
                )
                
                # Validate and normalize response
                if "modules" not in response:
                    response["modules"] = []
                
                if "title" not in response:
                    response["title"] = f"Learning {params['subtopic']}"
                
                if "estimated_duration_minutes" not in response:
                    response["estimated_duration_minutes"] = len(response["modules"]) + 2
                
                # Count module types for observability
                module_types = [m.get("type", "unknown") for m in response.get("modules", [])]
                span.set_attribute("lesson.module_count", len(response["modules"]))
                span.set_attribute("lesson.module_types", str(module_types))
                
                return AgentResult(
                    success=True,
                    output=response,
                    state=AgentState.COMPLETED,
                    metadata={"params": params, "module_count": len(response["modules"])},
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
        grade: int = 5,
    ) -> dict:
        """
        Convenience method for generating a lesson.
        
        Returns the raw lesson content dict matching Lesson2Content schema.
        """
        result = await self.run(
            user_input=f"Generate an interactive lesson about {subtopic}",
            metadata={
                "subject": subject,
                "topic": topic,
                "subtopic": subtopic,
                "grade": grade,
            }
        )
        
        if result.success:
            return result.output
        else:
            raise Exception(result.error or "Failed to generate lesson v2")


# Singleton instance for V2
lesson_agent_v2 = LessonAgentV2()
