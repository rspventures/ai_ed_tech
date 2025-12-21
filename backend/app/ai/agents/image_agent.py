"""
AI Tutor Platform - Image Agent
Generates educational images using DALL-E 3 for visual concept explanations.
Includes content guardrails for student safety.
"""
import uuid
import re
import aiohttp
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

from app.ai.agents.base import BaseAgent, AgentResult, AgentContext, AgentState
from app.ai.core.llm import LLMClient
from app.core.config import settings


@dataclass
class ImageResult:
    """Result of image generation."""
    image_url: Optional[str]  # URL from DALL-E (temporary)
    image_path: Optional[str]  # Local storage path
    image_base64: Optional[str]  # Base64 encoded image
    enhanced_prompt: str  # The enhanced prompt used
    original_prompt: str  # Original user request
    concept: str
    grade_level: int
    provider: str = "dall-e-3"
    error: Optional[str] = None
    blocked: bool = False  # True if request was blocked by guardrails
    block_reason: Optional[str] = None  # Reason for blocking


@dataclass
class ValidationResult:
    """Result of content validation."""
    is_valid: bool
    reason: str
    category: str  # educational, inappropriate, off-topic, etc.


class ImageAgent(BaseAgent):
    """
    Generates educational images using DALL-E 3.
    
    Features:
    - Content guardrails for student safety
    - Grade-appropriate prompt enhancement
    - Educational illustration style
    - Image storage and caching
    """
    
    name = "ImageAgent"
    description = "Generates educational visuals using DALL-E 3"
    version = "1.1.0"  # Updated for guardrails
    
    # Storage directory
    IMAGES_DIR = Path("uploads/generated_images")
    
    # =========================================================================
    # CONTENT GUARDRAILS
    # =========================================================================
    
    # Block list - requests containing these terms are immediately rejected
    BLOCKED_TERMS = [
        # Violence
        "violence", "violent", "weapon", "gun", "knife", "blood", "gore",
        "kill", "murder", "attack", "fight", "war", "battle", "bomb", "explosion",
        # Inappropriate content
        "kiss", "kissing", "romantic", "love", "dating", "sexy", "nude",
        "naked", "adult", "mature", "nsfw", "explicit", "inappropriate",
        # Drugs/Alcohol
        "drug", "alcohol", "beer", "wine", "cigarette", "smoking", "vaping",
        # Fear/Horror
        "scary", "horror", "monster", "ghost", "zombie", "demon", "devil",
        "death", "dead", "corpse", "skeleton",
        # Bullying/Negative
        "bully", "bullying", "hate", "racist", "discrimination",
        # Celebrities/Real people
        "celebrity", "famous person", "politician", "actor", "actress",
    ]
    
    # Educational topic categories (whitelist approach)
    EDUCATIONAL_TOPICS = [
        # Science
        "science", "biology", "chemistry", "physics", "astronomy", "space",
        "earth", "geology", "weather", "climate", "ecosystem", "environment",
        "animal", "plant", "cell", "atom", "molecule", "element", "compound",
        "photosynthesis", "respiration", "evolution", "genetics", "dna",
        "force", "energy", "electricity", "magnetism", "light", "sound",
        "solar system", "planet", "star", "galaxy", "universe", "moon",
        "water cycle", "rock cycle", "food chain", "food web",
        # Mathematics
        "math", "mathematics", "geometry", "algebra", "arithmetic", "fraction",
        "decimal", "percentage", "graph", "chart", "diagram", "shape",
        "triangle", "circle", "square", "rectangle", "polygon", "angle",
        "symmetry", "pattern", "number", "equation", "calculation",
        # History & Geography
        "history", "historical", "geography", "map", "continent", "country",
        "civilization", "ancient", "medieval", "culture", "tradition",
        "monument", "landmark", "architecture", "invention", "discovery",
        "explorer", "inventor", "scientist", "leader",
        # Language & Literature
        "alphabet", "word", "sentence", "grammar", "story", "poem", "book",
        "literature", "writing", "reading", "language", "vocabulary",
        # Art & Music
        "art", "painting", "drawing", "sculpture", "music", "instrument",
        "color", "colour", "composition", "design", "pattern",
        # Health & Body
        "body", "organ", "muscle", "bone", "heart", "brain", "lung",
        "digestive", "circulatory", "nervous system", "health", "nutrition",
        "exercise", "hygiene",
        # Technology
        "computer", "technology", "internet", "machine", "robot", "coding",
        "programming", "circuit", "electricity",
        # General Education
        "learn", "study", "concept", "explain", "process", "cycle", "system",
        "structure", "function", "diagram", "illustration", "example",
    ]
    
    # Validation prompt for LLM
    VALIDATION_PROMPT = """You are a content moderator for an educational platform for K-12 students.

Evaluate if this image request is appropriate and educational:
"{concept}"

The student is in Grade {grade}.

RULES:
1. ALLOW: Educational topics appropriate for the grade level (science, math, history, geography, language, art, music, health, technology)
2. ALLOW: Requests to visualize academic concepts, processes, diagrams, or educational illustrations
3. BLOCK: Any romantic, violent, scary, or inappropriate content
4. BLOCK: Requests involving real people, celebrities, or specific individuals
5. BLOCK: Non-educational topics like entertainment, games, or random personal requests
6. BLOCK: Anything that could be harmful, disturbing, or inappropriate for children

Respond in this exact JSON format:
{{
    "is_appropriate": true/false,
    "category": "educational" | "inappropriate" | "off-topic" | "personal" | "unsafe",
    "reason": "Brief explanation"
}}"""

    # Grade-level prompt modifiers
    GRADE_STYLES = {
        (1, 2): "colorful cartoon style with simple shapes, very friendly and playful, like a children's picture book",
        (3, 4): "colorful educational illustration, clear labels, kid-friendly style with some detail",
        (5, 6): "educational diagram style, clear and labeled, age-appropriate for pre-teens",
        (7, 8): "detailed educational illustration, scientific accuracy, suitable for middle schoolers",
        (9, 10): "accurate educational diagram, detailed labels, suitable for high school students",
        (11, 12): "technical educational illustration, scientific accuracy, college-prep level detail",
    }
    
    PROMPT_TEMPLATE = """Create an educational illustration for {grade_description} students explaining: {concept}

Style requirements:
- {style}
- No text or labels in the image (we'll add those separately)
- Safe, appropriate content for children/students
- Clear, easy to understand visual
- Educational and informative

The image should help students visualize and understand: {concept}"""

    SAFETY_KEYWORDS = [
        "educational", "child-friendly", "safe for school",
        "appropriate for students", "learning illustration"
    ]

    def __init__(self):
        super().__init__()
        self.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        self.llm = LLMClient()
    
    # =========================================================================
    # CONTENT VALIDATION
    # =========================================================================
    
    def _quick_block_check(self, concept: str) -> Tuple[bool, Optional[str]]:
        """Quick check against blocked terms list."""
        concept_lower = concept.lower()
        
        for term in self.BLOCKED_TERMS:
            if term in concept_lower:
                return True, f"Request contains inappropriate content: '{term}'"
        
        return False, None
    
    def _check_educational_keywords(self, concept: str) -> bool:
        """Check if concept contains educational keywords."""
        concept_lower = concept.lower()
        
        for topic in self.EDUCATIONAL_TOPICS:
            if topic in concept_lower:
                return True
        
        return False
    
    async def validate_content(self, concept: str, grade: int) -> ValidationResult:
        """
        Validate that the concept is appropriate for educational image generation.
        
        Uses multi-layer validation:
        1. Quick block list check
        2. Educational keyword check  
        3. LLM-based content evaluation
        """
        # Layer 1: Quick block check
        is_blocked, block_reason = self._quick_block_check(concept)
        if is_blocked:
            return ValidationResult(
                is_valid=False,
                reason=block_reason,
                category="inappropriate"
            )
        
        # Layer 2: Educational keyword presence (soft check)
        has_educational_keyword = self._check_educational_keywords(concept)
        
        # Layer 3: LLM-based validation for ambiguous cases
        try:
            validation_response = await self.llm.generate_json(
                prompt=self.VALIDATION_PROMPT.format(concept=concept, grade=grade),
                system_prompt="You are a content safety moderator. Return only valid JSON.",
                agent_name=self.name,
            )
            
            if isinstance(validation_response, dict):
                is_appropriate = validation_response.get("is_appropriate", False)
                category = validation_response.get("category", "unknown")
                reason = validation_response.get("reason", "Content review failed")
                
                if not is_appropriate:
                    return ValidationResult(
                        is_valid=False,
                        reason=reason,
                        category=category
                    )
                
                # If LLM approves but no educational keywords, still allow but log
                if not has_educational_keyword:
                    # Trust LLM validation for edge cases
                    pass
                
                return ValidationResult(
                    is_valid=True,
                    reason="Content is appropriate for educational use",
                    category="educational"
                )
        except Exception as e:
            # If LLM validation fails, be conservative
            if has_educational_keyword:
                return ValidationResult(
                    is_valid=True,
                    reason="Contains educational keywords",
                    category="educational"
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    reason="Unable to verify educational content. Please use educational terms like 'explain', 'diagram', 'process', etc.",
                    category="uncertain"
                )
        
        # Default deny for unmatched cases
        return ValidationResult(
            is_valid=False,
            reason="Request does not appear to be educational. Try phrases like 'Show photosynthesis process' or 'Explain water cycle'",
            category="off-topic"
        )
    
    # =========================================================================
    # IMAGE GENERATION
    # =========================================================================
    
    def _get_grade_style(self, grade: int) -> tuple[str, str]:
        """Get style description for the grade level."""
        for grade_range, style in self.GRADE_STYLES.items():
            if grade_range[0] <= grade <= grade_range[1]:
                if grade <= 2:
                    grade_desc = "kindergarten to 2nd grade"
                elif grade <= 4:
                    grade_desc = "3rd to 4th grade"
                elif grade <= 6:
                    grade_desc = "5th to 6th grade"
                elif grade <= 8:
                    grade_desc = "7th to 8th grade"
                elif grade <= 10:
                    grade_desc = "9th to 10th grade"
                else:
                    grade_desc = "11th to 12th grade"
                return style, grade_desc
        return self.GRADE_STYLES[(5, 6)], "elementary school"
    
    def enhance_prompt(self, concept: str, grade: int, additional_context: str = "") -> str:
        """
        Enhance user prompt to be grade-appropriate and educational.
        """
        style, grade_desc = self._get_grade_style(grade)
        
        prompt = self.PROMPT_TEMPLATE.format(
            grade_description=grade_desc,
            concept=concept,
            style=style,
        )
        
        if additional_context:
            prompt += f"\n\nAdditional context: {additional_context}"
        
        # Add safety keywords
        prompt += f"\n\nThis is an {', '.join(self.SAFETY_KEYWORDS)} image."
        
        return prompt
    
    async def generate_image(
        self,
        concept: str,
        grade: int = 5,
        size: str = "1024x1024",
        quality: str = "standard",
        additional_context: str = "",
    ) -> ImageResult:
        """
        Generate an educational image using DALL-E 3.
        Includes content validation guardrails.
        """
        # ==========================================
        # STEP 1: VALIDATE CONTENT
        # ==========================================
        validation = await self.validate_content(concept, grade)
        
        if not validation.is_valid:
            return ImageResult(
                image_url=None,
                image_path=None,
                image_base64=None,
                enhanced_prompt="",
                original_prompt=concept,
                concept=concept,
                grade_level=grade,
                provider="dall-e-3",
                error=None,
                blocked=True,
                block_reason=validation.reason,
            )
        
        # ==========================================
        # STEP 2: ENHANCE PROMPT
        # ==========================================
        enhanced_prompt = self.enhance_prompt(concept, grade, additional_context)
        
        # ==========================================
        # STEP 3: GENERATE IMAGE
        # ==========================================
        try:
            import openai
            
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            response = await client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size=size,
                quality=quality,
                n=1,
            )
            
            image_url = response.data[0].url
            revised_prompt = response.data[0].revised_prompt
            
            # Download and save image locally
            image_path = await self._save_image(image_url, concept)
            
            return ImageResult(
                image_url=image_url,
                image_path=str(image_path) if image_path else None,
                image_base64=None,
                enhanced_prompt=revised_prompt or enhanced_prompt,
                original_prompt=concept,
                concept=concept,
                grade_level=grade,
                provider="dall-e-3",
            )
            
        except Exception as e:
            return ImageResult(
                image_url=None,
                image_path=None,
                image_base64=None,
                enhanced_prompt=enhanced_prompt,
                original_prompt=concept,
                concept=concept,
                grade_level=grade,
                provider="dall-e-3",
                error=str(e),
            )
    
    async def _save_image(self, url: str, concept: str) -> Optional[Path]:
        """Download and save image from URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # Generate filename
                        safe_concept = "".join(c if c.isalnum() else "_" for c in concept[:30])
                        filename = f"{safe_concept}_{uuid.uuid4().hex[:8]}.png"
                        filepath = self.IMAGES_DIR / filename
                        
                        # Save image
                        content = await response.read()
                        filepath.write_bytes(content)
                        
                        return filepath
        except Exception as e:
            print(f"Error saving image: {e}")
        return None
    
    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """Planning phase - extract generation parameters from context."""
        return {
            "action": "generate_image",
            "concept": context.user_input,
            "grade": context.metadata.get("grade", 5),
            "size": context.metadata.get("size", "1024x1024"),
            "quality": context.metadata.get("quality", "standard"),
            "additional_context": context.metadata.get("additional_context", ""),
        }
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """Execute the image generation."""
        result = await self.generate_image(
            concept=plan["concept"],
            grade=plan["grade"],
            size=plan["size"],
            quality=plan["quality"],
            additional_context=plan["additional_context"],
        )
        
        if result.blocked:
            return AgentResult(
                success=False,
                output=result,
                state=AgentState.ERROR,
                error=f"Request blocked: {result.block_reason}",
            )
        
        if result.error:
            return AgentResult(
                success=False,
                output=result,
                state=AgentState.ERROR,
                error=result.error,
            )
        
        return AgentResult(
            success=True,
            output=result,
            state=AgentState.COMPLETED,
        )


# Singleton instance
image_agent = ImageAgent()

