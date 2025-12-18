"""
AI Tutor Platform - Lesson Generator Agent
LangChain-based agent for generating personalized educational lessons
"""
import json
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings


class LessonGenerator:
    """
    The Creator Agent 🎨
    
    Generates rich, engaging, grade-appropriate lesson content
    using LLM to explain educational concepts.
    """

    PROMPT_TEMPLATE = """You are an expert teacher who creates AMAZING lessons 
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

    def __init__(self):
        self.prompt = ChatPromptTemplate.from_template(self.PROMPT_TEMPLATE)
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
                    temperature=0.7,  # Creative but consistent
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

    def _get_age_range(self, grade: int) -> str:
        """Convert grade level to age range."""
        age_ranges = {
            1: "6-7",
            2: "7-8", 
            3: "8-9",
            4: "9-10",
            5: "10-11",
            6: "11-12",
            7: "12-13",
        }
        return age_ranges.get(grade, "6-13")

    async def generate(
        self,
        subject: str,
        topic: str,
        subtopic: str,
        grade: int = 1,
        style: str = "story"
    ) -> dict:
        """
        Generate a complete lesson for the given topic.
        
        Args:
            subject: The subject (e.g., "Mathematics")
            topic: The topic (e.g., "Addition")
            subtopic: The specific subtopic (e.g., "Adding single digits")
            grade: Grade level (1, 2, or 3)
            style: Teaching style ("story", "facts", "visual")
            
        Returns:
            Dictionary with lesson content matching LessonContent schema
        """
        chain = self.prompt | self.llm | StrOutputParser()
        
        result = await chain.ainvoke({
            "subject": subject,
            "topic": topic,
            "subtopic": subtopic,
            "grade": grade,
            "age_range": self._get_age_range(grade),
            "style": style
        })
        
        # Parse JSON from response
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()
        
        parsed = json.loads(result)
        
        # Ensure required fields exist
        if "sections" not in parsed:
            parsed["sections"] = []
        if "fun_fact" not in parsed:
            parsed["fun_fact"] = None
            
        return parsed

    def get_model_name(self) -> str:
        """Return the name of the model being used."""
        if settings.LLM_PROVIDER == "openai":
            return settings.OPENAI_MODEL
        return settings.ANTHROPIC_MODEL


# Singleton instance
lesson_generator = LessonGenerator()
