"""
AI Tutor Platform - AI Question Generator
LangChain-based question generation for educational content
"""
from typing import Literal, Optional, List
import json
import random

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic.v1 import BaseModel, Field

from app.core.config import settings


class GeneratedQuestion(BaseModel):
    """Schema for AI-generated questions."""
    question: str = Field(description="The question text")
    answer: str = Field(description="The correct answer (just the value, e.g. '5' not '5 apples')")
    hint: str = Field(description="A helpful hint for the student")
    explanation: str = Field(description="Explanation of the answer")
    difficulty: str = Field(default="easy")
    question_type: str = Field(default="multiple_choice")
    options: List[str] = Field(default_factory=list, description="4 options for multiple choice")


from enum import Enum

class QuestionDifficulty(str, Enum):
    """Difficulty levels for questions."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionGenerator:
    """Generate age-appropriate educational questions using LLM."""

    PROMPT_TEMPLATE = """You are an expert elementary school teacher creating MULTIPLE CHOICE questions.
Your answers must be MATHEMATICALLY CORRECT. Double-check all calculations before responding.

Create a question for:
- Subject: {subject}
- Topic: {topic}
- Subtopic: {subtopic}
- Grade Level: {grade}
- Difficulty: {difficulty}

CRITICAL RULES:
1. VERIFY YOUR MATH: If the question involves arithmetic, calculate the answer step by step.
   Example: "3 + 5 = ?" → 3 + 5 = 8, so answer is "8"
   Example: "10 - 4 = ?" → 10 - 4 = 6, so answer is "6"
   
2. FACT CHECK: Ensure all factual answers are correct.
   Example: "How many sides does a triangle have?" → A triangle has 3 sides, so answer is "3"
   Example: "How many legs does a dog have?" → A dog has 4 legs, so answer is "4"

3. The "answer" field must match EXACTLY one of the "options"
4. The CORRECT answer must be the FIRST option in the array
5. Create 3 plausible but WRONG distractor options

Respond with ONLY this JSON (no markdown, no explanation):
{{
    "question": "Your question here?",
    "options": ["CORRECT_ANSWER", "wrong1", "wrong2", "wrong3"],
    "answer": "CORRECT_ANSWER",
    "hint": "A helpful hint",
    "explanation": "Why this answer is correct",
    "difficulty": "{difficulty}",
    "question_type": "multiple_choice"
}}

REMEMBER: 
- First option = correct answer
- Double-check your arithmetic
- The "answer" value must match the first option exactly
"""

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
                    temperature=0.5,  # Lower temperature for accuracy
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
            else:
                from langchain_anthropic import ChatAnthropic
                self._llm = ChatAnthropic(
                    model=settings.ANTHROPIC_MODEL,
                    api_key=settings.ANTHROPIC_API_KEY,
                    temperature=0.5,  # Lower temperature for accuracy
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
        return self._llm

    async def generate(
        self,
        subject: str,
        topic: str,
        subtopic: str,
        difficulty: "QuestionDifficulty | str" = QuestionDifficulty.EASY,
        question_type: Literal["multiple_choice", "fill_blank", "true_false", "open_ended"] = "multiple_choice",
        grade: int = 1,
        temperature: float = 0.9,
    ) -> GeneratedQuestion:
        """
        Generate a question for the given topic and parameters.
        """
        chain = self.prompt | self.llm | StrOutputParser()
        
        # Add randomness hint to get different questions
        random_seed = random.randint(1, 10000)
        
        # Convert enum to string if needed
        diff_value = difficulty.value if isinstance(difficulty, QuestionDifficulty) else difficulty
        
        result = await chain.ainvoke({
            "subject": subject,
            "topic": topic,
            "subtopic": f"{subtopic} (Variation #{random_seed})",
            "grade": grade,
            "difficulty": diff_value,
            "question_type": question_type,
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
        
        # Ensure options exist
        if "options" not in parsed or not parsed["options"]:
            parsed["options"] = [parsed["answer"], "A", "B", "C"]
        
        # CRITICAL: Ensure the correct answer is FIRST in options array
        # The frontend relies on options[0] being the correct answer
        correct_answer = parsed.get("answer", "")
        options = parsed.get("options", [])
        
        # If correct answer is not first, reorder
        if options and options[0] != correct_answer:
            # Remove the correct answer from its current position
            if correct_answer in options:
                options.remove(correct_answer)
            # Insert at the beginning
            options.insert(0, correct_answer)
            # Limit to 4 options
            parsed["options"] = options[:4]
        
        return GeneratedQuestion(**parsed)


# Singleton instance
question_generator = QuestionGenerator()
