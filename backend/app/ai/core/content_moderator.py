"""
AI Tutor Platform - Content Moderator
Grade-aware content moderation for student safety.
"""
import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class ModerationResult(str, Enum):
    """Result of content moderation."""
    ALLOWED = "allowed"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class ContentCategory(str, Enum):
    """Categories of content concern."""
    VIOLENCE = "violence"
    ADULT = "adult"
    DRUGS = "drugs"
    WEAPONS = "weapons"
    SELF_HARM = "self_harm"
    PROFANITY = "profanity"
    BULLYING = "bullying"
    OFF_TOPIC = "off_topic"
    AGE_INAPPROPRIATE = "age_inappropriate"


@dataclass
class ModerationResponse:
    """Response from content moderation."""
    result: ModerationResult
    categories: List[ContentCategory] = field(default_factory=list)
    reason: str = ""
    suggested_action: str = ""
    is_educational: bool = True


class ContentModerator:
    """
    Grade-aware content moderation for educational platform.
    
    Enforces different rules based on student grade level:
    - Grades 1-3: Whitelist only, no open-ended generation
    - Grades 4-6: Curriculum + creative, strict filtering
    - Grades 7-12: Broader curriculum, standard filtering
    """
    
    # Blocked terms by category (educational context)
    BLOCKED_TERMS = {
        ContentCategory.VIOLENCE: [
            "kill", "murder", "blood", "gore", "torture", "assault", 
            "shoot", "stab", "attack", "beat up", "fight", "war crime",
            "terrorist", "terrorism", "bomb", "explosion",
        ],
        ContentCategory.ADULT: [
            "sexy", "nude", "naked", "porn", "xxx", "erotic",
            "sex", "sexual", "intimate", "provocative", "seductive",
            "kiss", "kissing", "romance", "romantic", "date", "dating",
            "girlfriend", "boyfriend", "crush", "love interest",
        ],
        ContentCategory.DRUGS: [
            "drug", "cocaine", "heroin", "meth", "marijuana", "weed",
            "alcohol", "beer", "wine", "drunk", "smoking", "cigarette",
            "vape", "vaping", "intoxicated", "high", "stoned",
        ],
        ContentCategory.WEAPONS: [
            "gun", "rifle", "pistol", "shotgun", "weapon", "sword",
            "knife", "blade", "grenade", "missile", "ammunition",
        ],
        ContentCategory.SELF_HARM: [
            "suicide", "self-harm", "cut myself", "hurt myself",
            "end my life", "kill myself", "depression", "die",
        ],
        ContentCategory.PROFANITY: [
            # Basic profanity list - extend as needed
            "damn", "hell", "crap", "stupid", "idiot", "dumb",
        ],
        ContentCategory.BULLYING: [
            "bully", "bullying", "humiliate", "embarrass", "mock",
            "tease", "make fun of", "loser",
        ],
    }
    
    # Educational topics whitelist
    EDUCATIONAL_TOPICS = {
        "math": ["addition", "subtraction", "multiplication", "division", "algebra", 
                 "geometry", "trigonometry", "calculus", "statistics", "probability",
                 "fraction", "decimal", "percentage", "equation", "number"],
        "science": ["physics", "chemistry", "biology", "environment", "ecosystem",
                    "atom", "molecule", "cell", "organism", "energy", "force",
                    "gravity", "electricity", "magnet", "plant", "animal", "human body",
                    "water cycle", "photosynthesis", "solar system", "planet"],
        "english": ["grammar", "vocabulary", "reading", "writing", "essay", "poem",
                    "story", "comprehension", "spelling", "sentence", "paragraph",
                    "noun", "verb", "adjective", "tense", "punctuation"],
        "social_studies": ["history", "geography", "civics", "economics", "culture",
                          "india", "world", "democracy", "government", "map",
                          "river", "mountain", "country", "state", "capital"],
        "general": ["learn", "study", "practice", "quiz", "test", "homework",
                    "explain", "understand", "question", "answer", "help with"],
    }
    
    # Grade-specific restrictions
    GRADE_RESTRICTIONS = {
        # Grades 1-3: Very strict, whitelist only
        "primary": {
            "grades": [1, 2, 3],
            "allowed_topics": ["math", "english", "science", "general"],
            "max_response_complexity": "simple",
            "allow_creative_writing": False,
            "blocked_terms_strict": True,
            "extra_blocked": ["scary", "monster", "ghost", "horror", "nightmare", "dead", "death"],
        },
        # Grades 4-6: Moderate restrictions
        "middle": {
            "grades": [4, 5, 6],
            "allowed_topics": ["math", "science", "english", "social_studies", "general"],
            "max_response_complexity": "moderate",
            "allow_creative_writing": True,
            "blocked_terms_strict": True,
            "extra_blocked": ["scary", "horror"],
        },
        # Grades 7-9: Standard restrictions
        "secondary_lower": {
            "grades": [7, 8, 9],
            "allowed_topics": ["math", "science", "english", "social_studies", "general"],
            "max_response_complexity": "advanced",
            "allow_creative_writing": True,
            "blocked_terms_strict": False,
            "extra_blocked": [],
        },
        # Grades 10-12: Minimal restrictions
        "secondary_upper": {
            "grades": [10, 11, 12],
            "allowed_topics": ["math", "science", "english", "social_studies", "general"],
            "max_response_complexity": "expert",
            "allow_creative_writing": True,
            "blocked_terms_strict": False,
            "extra_blocked": [],
        },
    }
    
    def __init__(self, default_grade: int = 5):
        """
        Initialize content moderator.
        
        Args:
            default_grade: Default grade level if not specified
        """
        self.default_grade = default_grade
        
        # Pre-compile blocked term patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficient matching."""
        self._blocked_patterns = {}
        for category, terms in self.BLOCKED_TERMS.items():
            patterns = [re.compile(rf'\b{re.escape(term)}\b', re.IGNORECASE) for term in terms]
            self._blocked_patterns[category] = patterns
    
    def _get_restriction_level(self, grade: int) -> Dict:
        """Get restriction configuration for a grade level."""
        for level_name, config in self.GRADE_RESTRICTIONS.items():
            if grade in config["grades"]:
                return config
        return self.GRADE_RESTRICTIONS["middle"]  # Default to middle if unknown
    
    def _check_blocked_terms(self, 
                             text: str, 
                             grade: int,
                             extra_blocked: List[str] = None) -> List[ContentCategory]:
        """Check text against blocked term lists."""
        violations = []
        text_lower = text.lower()
        
        for category, patterns in self._blocked_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    violations.append(category)
                    break  # One match per category is enough
        
        # Check extra blocked terms for this grade level
        if extra_blocked:
            for term in extra_blocked:
                if term.lower() in text_lower:
                    violations.append(ContentCategory.AGE_INAPPROPRIATE)
                    break
        
        return violations
    
    def _check_educational_relevance(self, 
                                     text: str, 
                                     allowed_topics: List[str]) -> bool:
        """Check if text is related to educational topics."""
        text_lower = text.lower()
        
        for topic in allowed_topics:
            if topic in self.EDUCATIONAL_TOPICS:
                for keyword in self.EDUCATIONAL_TOPICS[topic]:
                    if keyword in text_lower:
                        return True
        
        # If no educational keywords found but it's a short simple request
        if len(text.split()) < 10:
            return True  # Allow short requests
        
        return False
    
    def moderate(self, 
                 text: str, 
                 grade: Optional[int] = None,
                 is_user_input: bool = True) -> ModerationResponse:
        """
        Moderate content based on grade level.
        
        Args:
            text: Text to moderate
            grade: Student grade level (1-12)
            is_user_input: Whether this is user input (True) or AI output (False)
            
        Returns:
            ModerationResponse with result and details
        """
        if not text or not text.strip():
            return ModerationResponse(
                result=ModerationResult.ALLOWED,
                reason="Empty input"
            )
        
        grade = grade or self.default_grade
        restrictions = self._get_restriction_level(grade)
        
        # Check blocked terms
        violations = self._check_blocked_terms(
            text, 
            grade, 
            restrictions.get("extra_blocked", [])
        )
        
        # Immediate block for serious violations
        serious_categories = {
            ContentCategory.VIOLENCE, 
            ContentCategory.ADULT, 
            ContentCategory.DRUGS,
            ContentCategory.SELF_HARM,
            ContentCategory.WEAPONS,
        }
        
        serious_violations = [v for v in violations if v in serious_categories]
        
        if serious_violations:
            return ModerationResponse(
                result=ModerationResult.BLOCKED,
                categories=serious_violations,
                reason=f"Content contains inappropriate material for educational context: {', '.join(v.value for v in serious_violations)}",
                suggested_action="Please ask about educational topics like math, science, or English.",
                is_educational=False
            )
        
        # Check for profanity/bullying (warning for older students, block for younger)
        minor_violations = [v for v in violations if v not in serious_categories]
        
        if minor_violations:
            if restrictions.get("blocked_terms_strict", False):
                return ModerationResponse(
                    result=ModerationResult.BLOCKED,
                    categories=minor_violations,
                    reason=f"Content not appropriate for your grade level: {', '.join(v.value for v in minor_violations)}",
                    suggested_action="Please use polite and respectful language.",
                    is_educational=False
                )
            else:
                return ModerationResponse(
                    result=ModerationResult.NEEDS_REVIEW,
                    categories=minor_violations,
                    reason="Content may not be appropriate",
                    suggested_action="Consider rephrasing your request.",
                    is_educational=True
                )
        
        # Check educational relevance for younger students
        if grade <= 6:
            is_educational = self._check_educational_relevance(
                text, 
                restrictions.get("allowed_topics", [])
            )
            
            if not is_educational:
                return ModerationResponse(
                    result=ModerationResult.NEEDS_REVIEW,
                    categories=[ContentCategory.OFF_TOPIC],
                    reason="Request doesn't appear to be about educational topics",
                    suggested_action="Try asking about subjects like Math, Science, or English!",
                    is_educational=False
                )
        
        return ModerationResponse(
            result=ModerationResult.ALLOWED,
            reason="Content is appropriate for educational context",
            is_educational=True
        )
    
    def moderate_output(self, 
                        output: str, 
                        grade: int,
                        original_query: str = "") -> ModerationResponse:
        """
        Moderate AI-generated output before returning to student.
        
        Args:
            output: AI-generated text
            grade: Student grade level
            original_query: Original user query (for context)
            
        Returns:
            ModerationResponse
        """
        return self.moderate(output, grade, is_user_input=False)
    
    def get_safe_topics_for_grade(self, grade: int) -> List[str]:
        """Get list of safe topics for a specific grade."""
        restrictions = self._get_restriction_level(grade)
        allowed_topic_names = restrictions.get("allowed_topics", [])
        
        safe_topics = []
        for topic_name in allowed_topic_names:
            if topic_name in self.EDUCATIONAL_TOPICS:
                safe_topics.extend(self.EDUCATIONAL_TOPICS[topic_name])
        
        return safe_topics


# Singleton instance
_content_moderator: Optional[ContentModerator] = None


def get_content_moderator() -> ContentModerator:
    """Get or create singleton ContentModerator instance."""
    global _content_moderator
    if _content_moderator is None:
        _content_moderator = ContentModerator()
    return _content_moderator


def moderate_content(text: str, grade: int = 5) -> ModerationResponse:
    """
    Convenience function to moderate content.
    
    Returns:
        ModerationResponse
    """
    moderator = get_content_moderator()
    return moderator.moderate(text, grade)
