"""
AI Tutor Platform - Assessment Analyzer
LangChain-based analysis of assessment results with detailed feedback
"""
from typing import Optional, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic.v1 import BaseModel, Field

from app.core.config import settings


class AssessmentFeedback(BaseModel):
    """Schema for AI-generated assessment feedback."""
    overall_score_interpretation: str = Field(description="A brief, encouraging interpretation of the score")
    strengths: List[str] = Field(description="List of 2-3 specific strengths demonstrated")
    areas_of_improvement: List[str] = Field(description="List of 2-3 areas that need work")
    ways_to_improve: List[str] = Field(description="List of 3-4 specific, actionable steps to improve")
    practical_assignments: List[str] = Field(description="List of 2-3 fun practice activities or exercises")
    encouraging_words: str = Field(description="A warm, motivating message for the student")
    pattern_analysis: str = Field(description="Brief analysis of any patterns in mistakes or strengths")


class AssessmentAnalyzer:
    """Analyze assessment results and provide detailed, grade-appropriate feedback."""

    PROMPT_TEMPLATE = """You are a warm, encouraging elementary school teacher providing feedback 
to a young student (grade {grade}) about their assessment results. Your feedback should be:
- Age-appropriate and easy to understand
- Encouraging and positive, even when scores are low
- Specific and actionable
- Fun and engaging

Student's Assessment Results:
- Subject: {subject}
- Topic: {topic}
- Score: {score}% ({correct}/{total} correct)
- Grade Level: {grade}

Questions and Answers:
{questions_detail}

Based on these results, provide detailed feedback. Look for patterns in what the student 
got right and wrong. Suggest fun, practical ways to improve.

Remember: This is for a young child! Use simple words, be very encouraging, and make 
learning sound fun and exciting. Use emojis sparingly but appropriately.

{format_instructions}"""

    def __init__(self):
        self._parser = None
        self.prompt = ChatPromptTemplate.from_template(self.PROMPT_TEMPLATE)
        self._llm = None

    @property
    def parser(self):
        """Lazy load the parser."""
        if self._parser is None:
            self._parser = JsonOutputParser(pydantic_object=AssessmentFeedback)
        return self._parser

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

    async def analyze(
        self,
        subject: str,
        topic: str,
        score: float,
        correct: int,
        total: int,
        questions_detail: str,
        grade: int = 1,
    ) -> AssessmentFeedback:
        """
        Analyze assessment results and generate detailed feedback.
        
        Args:
            subject: The subject area
            topic: The specific topic tested
            score: Percentage score (0-100)
            correct: Number of correct answers
            total: Total number of questions
            questions_detail: Formatted string of Q&A with correctness
            grade: Student's grade level
        
        Returns:
            AssessmentFeedback with detailed analysis
        """
        chain = self.prompt | self.llm | self.parser
        
        result = await chain.ainvoke({
            "subject": subject,
            "topic": topic,
            "score": round(score, 1),
            "correct": correct,
            "total": total,
            "questions_detail": questions_detail,
            "grade": grade,
            "format_instructions": self.parser.get_format_instructions(),
        })
        
        return AssessmentFeedback(**result)


# Singleton instance
assessment_analyzer = AssessmentAnalyzer()
