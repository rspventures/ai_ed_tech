"""
AI Tutor Platform - Answer Evaluator
LangChain-based answer evaluation with detailed feedback
"""
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic.v1 import BaseModel, Field

from app.core.config import settings


class EvaluationResult(BaseModel):
    """Schema for answer evaluation results."""
    is_correct: bool = Field(description="Whether the answer is correct")
    score: float = Field(description="Score from 0.0 to 1.0", ge=0.0, le=1.0)
    feedback: str = Field(description="Encouraging feedback for the student")
    detailed_explanation: str = Field(description="Detailed explanation of the correct answer")
    hint_for_retry: Optional[str] = Field(default=None, description="Hint if student wants to retry")
    common_mistake: Optional[str] = Field(default=None, description="Common mistake if answer was wrong")


class AnswerEvaluator:
    """Evaluate student answers with detailed, encouraging feedback."""

    PROMPT_TEMPLATE = """You are a kind and encouraging elementary school teacher evaluating 
a student's answer. Always be positive and supportive, even when the answer is incorrect.

Student Information:
- Grade: {grade}
- Subject: {subject}
- Topic: {topic}

Question: {question}
Correct Answer: {correct_answer}
Student's Answer: {student_answer}

Evaluate the student's answer and provide:
1. Whether it's correct (consider partial credit for close answers)
2. A score from 0.0 to 1.0
3. Encouraging feedback appropriate for a grade {grade} student
4. A detailed explanation they can learn from
5. If incorrect, a hint to help them try again
6. If incorrect, explain the common mistake they might have made

Be encouraging! Use positive language and celebrate effort.

{format_instructions}"""

    def __init__(self):
        self._parser = None
        self.prompt = ChatPromptTemplate.from_template(self.PROMPT_TEMPLATE)
        self._llm = None

    @property
    def parser(self):
        """Lazy load the parser to avoid Pydantic v1/v2 issues at import time."""
        if self._parser is None:
            self._parser = JsonOutputParser(pydantic_object=EvaluationResult)
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
                    temperature=0.3,  # Lower temperature for more consistent evaluation
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
            else:
                from langchain_anthropic import ChatAnthropic
                self._llm = ChatAnthropic(
                    model=settings.ANTHROPIC_MODEL,
                    api_key=settings.ANTHROPIC_API_KEY,
                    temperature=0.3,
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
        return self._llm

    async def evaluate(
        self,
        question: str,
        correct_answer: str,
        student_answer: str,
        subject: str,
        topic: str,
        grade: int,
    ) -> EvaluationResult:
        """
        Evaluate a student's answer.
        
        Args:
            question: The question that was asked
            correct_answer: The correct answer
            student_answer: The student's submitted answer
            subject: The subject area
            topic: The topic being tested
            grade: Student's grade level
        
        Returns:
            Evaluation result with feedback and explanation
        """
        chain = self.prompt | self.llm | self.parser
        
        result = await chain.ainvoke({
            "question": question,
            "correct_answer": correct_answer,
            "student_answer": student_answer,
            "subject": subject,
            "topic": topic,
            "grade": grade,
            "format_instructions": self.parser.get_format_instructions(),
        })
        
        return EvaluationResult(**result)


# Singleton instance
answer_evaluator = AnswerEvaluator()
