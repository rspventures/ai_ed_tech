"""
AI Tutor Platform - Document Validator Agent
Validates uploaded documents for grade-level appropriateness.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

from app.ai.agents.base import BaseAgent, AgentResult, AgentContext, AgentState
from app.ai.core.llm import LLMClient


class GradeMatch(str, Enum):
    """How well the document matches the target grade."""
    EXACT = "exact"          # Perfect match for grade
    CLOSE = "close"          # Within 1-2 grades
    TOO_EASY = "too_easy"    # Below grade level
    TOO_HARD = "too_hard"    # Above grade level
    INAPPROPRIATE = "inappropriate"  # Not suitable for students


@dataclass
class ValidationResult:
    """Result of document validation."""
    is_appropriate: bool
    grade_match: GradeMatch
    estimated_grade_range: tuple  # (min, max) suggested grade
    reason: str
    educational_value: Optional[str] = None  # What can be learned
    content_warnings: List[str] = field(default_factory=list)


class DocumentValidatorAgent(BaseAgent):
    """
    Validates documents for grade-level appropriateness.
    
    Uses LLM to analyze document content and determine:
    - Is it appropriate for the student's grade?
    - What is the estimated reading level?
    - What educational value does it provide?
    - Are there any content concerns?
    """
    
    name = "document_validator"
    description = "Validates documents for grade-appropriateness"
    version = "1.0.0"
    
    VALIDATION_SYSTEM_PROMPT = """You are an expert educational content evaluator for K-12 students.
Your task is to analyze document content and determine if it's appropriate for a specific grade level.

## Evaluation Criteria:
1. **Reading Complexity**: Vocabulary, sentence structure, concepts
2. **Content Appropriateness**: No adult themes, violence, or inappropriate content for children
3. **Educational Value**: Can the student learn something from this?
4. **Grade Relevance**: Is this material relevant to the target grade's learning?

## Grade Level Guidelines:
- Grades 1-2: Simple words, short sentences, basic concepts, picture books level
- Grades 3-4: Intermediate vocabulary, paragraphs, basic comprehension
- Grades 5-6: More complex texts, multiple concepts, structured content
- Grades 7-8: Advanced vocabulary, abstract concepts, longer texts
- Grades 9-10: Complex analysis, mature themes (age-appropriate), technical content
- Grades 11-12: College-prep level, sophisticated arguments, research material

## Content Types That Are INAPPROPRIATE (reject):
- Professional resumes, CVs, job applications
- Business documents, contracts, legal papers
- Adult content, explicit material
- Personal emails, private correspondence
- Technical manuals for professional use
- Political propaganda or hate speech

## Content Types That ARE APPROPRIATE (approve with reasoning):
- Story books, novels (age-appropriate)
- Educational articles, encyclopedias
- News articles for children/teens
- Science explanations, history texts
- Study guides, worksheets
- Creative writing, poetry
- Biographies (appropriate for age)

Respond with a JSON object:
{
    "is_appropriate": true/false,
    "grade_match": "exact" | "close" | "too_easy" | "too_hard" | "inappropriate",
    "estimated_grade_min": <number 1-12>,
    "estimated_grade_max": <number 1-12>,
    "reason": "<clear explanation for students/parents>",
    "educational_value": "<what the student can learn, or null if inappropriate>",
    "content_warnings": ["<any concerns>"]
}"""

    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """Planning phase - extract validation parameters from context."""
        return {
            "action": "validate_document",
            "content_samples": context.metadata.get("content_samples", []),
            "target_grade": context.metadata.get("target_grade", 5),
            "subject": context.metadata.get("subject"),
        }
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """Execute the validation."""
        content_samples = plan.get("content_samples", [])
        target_grade = plan.get("target_grade", 5)
        subject = plan.get("subject")
        
        if not content_samples:
            return AgentResult(
                success=False,
                output=None,
                state=AgentState.ERROR,
                error="No content samples provided for validation"
            )
        
        try:
            result = await self.validate(content_samples, target_grade, subject)
            return AgentResult(
                success=True,
                output=result,
                state=AgentState.COMPLETED,
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output=None,
                state=AgentState.ERROR,
                error=str(e)
            )

    async def validate(
        self,
        content_samples: List[str],
        target_grade: int,
        subject: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate document content for grade appropriateness.
        
        Args:
            content_samples: List of text chunks from the document
            target_grade: Student's grade level (1-12)
            subject: Optional subject context
            
        Returns:
            ValidationResult with approval status and details
        """
        # Combine samples for analysis
        combined_content = "\n\n---\n\n".join(content_samples[:3])  # Max 3 chunks
        
        # Truncate if too long
        if len(combined_content) > 4000:
            combined_content = combined_content[:4000] + "...[truncated]"
        
        prompt = f"""Analyze this document for a Grade {target_grade} student{f' studying {subject}' if subject else ''}.

## Document Content (Sample):
{combined_content}

## Target Grade: {target_grade}

Evaluate if this content is appropriate and educational for this grade level."""

        try:
            response = await self.llm.generate_json(
                prompt=prompt,
                system_prompt=self.VALIDATION_SYSTEM_PROMPT,
                agent_name=self.name,
            )
            
            # Parse response
            is_appropriate = response.get("is_appropriate", False)
            grade_match_str = response.get("grade_match", "inappropriate")
            
            try:
                grade_match = GradeMatch(grade_match_str)
            except ValueError:
                grade_match = GradeMatch.INAPPROPRIATE if not is_appropriate else GradeMatch.CLOSE
            
            return ValidationResult(
                is_appropriate=is_appropriate,
                grade_match=grade_match,
                estimated_grade_range=(
                    response.get("estimated_grade_min", 1),
                    response.get("estimated_grade_max", 12)
                ),
                reason=response.get("reason", "Unable to determine appropriateness"),
                educational_value=response.get("educational_value"),
                content_warnings=response.get("content_warnings", []),
            )
            
        except Exception as e:
            # On error, be cautious - mark needs review
            return ValidationResult(
                is_appropriate=True,  # Don't block on validation errors
                grade_match=GradeMatch.CLOSE,
                estimated_grade_range=(1, 12),
                reason=f"Validation could not be completed: {str(e)}. Document allowed for manual review.",
                educational_value=None,
                content_warnings=["Automatic validation failed"],
            )


# Singleton instance
document_validator_agent = DocumentValidatorAgent()
