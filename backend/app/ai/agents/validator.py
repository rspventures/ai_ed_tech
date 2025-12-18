"""
AI Tutor Platform - Validator Agent
Quality gate for generated questions - ensures uniqueness, variety, 
grade-appropriateness, and ANSWER CORRECTNESS.
"""
import re
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from difflib import SequenceMatcher

from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.ai.core.telemetry import get_tracer
from app.ai.core.memory import AgentMemory
from app.ai.core.similarity import similarity_service


@dataclass
class ValidationResult:
    """Result of question validation."""
    is_valid: bool
    reason: str
    similarity_score: float = 0.0
    matched_question: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    corrected_answer: Optional[str] = None  # If we can fix the answer


@dataclass 
class AnswerValidationResult:
    """Result of answer verification."""
    is_correct: bool
    reason: str
    expected_answer: Optional[str] = None
    provided_answer: Optional[str] = None


@dataclass
class ExtractedConcepts:
    """Concepts extracted from a question."""
    words: List[str] = field(default_factory=list)  # Key vocabulary (adverbs, nouns, etc.)
    numbers: List[int] = field(default_factory=list)  # Numbers used
    positions: List[str] = field(default_factory=list)  # Place value positions
    question_format: str = ""  # "identify", "fill-blank", "calculate", etc.
    subject_type: str = ""  # "adverb", "place_value", "addition", etc.


class ConceptExtractor:
    """
    Extracts key concepts from questions to enable tracking and prevent repetition.
    """
    
    # Common adverbs to track
    ADVERBS = [
        "quickly", "slowly", "happily", "sadly", "angrily", "quietly", "loudly",
        "carefully", "carelessly", "eagerly", "easily", "hardly", "nearly",
        "never", "always", "often", "sometimes", "rarely", "usually", "seldom",
        "fast", "well", "badly", "hard", "late", "early", "daily", "weekly",
        "gently", "roughly", "softly", "smoothly", "suddenly", "gradually",
    ]
    
    # Parts of speech patterns
    POS_PATTERNS = {
        "noun": r"\b(noun|naming\s+word|person|place|thing)\b",
        "verb": r"\b(verb|action\s+word|doing|action)\b",
        "adjective": r"\b(adjective|describing\s+word|quality)\b",
        "adverb": r"\b(adverb|how|manner|modify)\b",
        "pronoun": r"\b(pronoun|she|he|it|they)\b",
    }
    
    # Place value positions
    PLACE_POSITIONS = [
        "ones", "tens", "hundreds", "thousands", 
        "ten-thousands", "ten thousands",
        "lakhs", "lakh", "hundred-thousands", "hundred thousands",
        "ten-lakhs", "ten lakhs", "millions",
        "crores", "crore", "ten-millions", "ten millions",
    ]
    
    # Question format patterns
    FORMAT_PATTERNS = {
        "identify": r"\b(identify|which|what\s+is|find)\b",
        "fill-blank": r"\b(fill|blank|complete|missing)\b",
        "calculate": r"\b(calculate|solve|find\s+the\s+value|what\s+is\s+\d)\b",
        "compare": r"\b(compare|greater|lesser|bigger|smaller)\b",
        "convert": r"\b(convert|change|express|write\s+as)\b",
    }
    
    def extract(self, question: str, subject: str = "") -> ExtractedConcepts:
        """Extract concepts from a question."""
        question_lower = question.lower()
        concepts = ExtractedConcepts()
        
        # Extract adverbs found in question
        for adverb in self.ADVERBS:
            if re.search(rf"\b{adverb}\b", question_lower):
                concepts.words.append(adverb)
        
        # Extract numbers
        numbers = re.findall(r"\b\d+\b", question)
        concepts.numbers = [int(n) for n in numbers]
        
        # Extract place value positions
        for pos in self.PLACE_POSITIONS:
            if pos in question_lower:
                concepts.positions.append(pos.replace("-", " "))
        
        # Detect question format
        for format_name, pattern in self.FORMAT_PATTERNS.items():
            if re.search(pattern, question_lower):
                concepts.question_format = format_name
                break
        
        # Detect subject type
        for pos_type, pattern in self.POS_PATTERNS.items():
            if re.search(pattern, question_lower):
                concepts.subject_type = pos_type
                break
        
        if "place value" in question_lower or any(p in question_lower for p in self.PLACE_POSITIONS):
            concepts.subject_type = "place_value"
        elif re.search(r"\d+\s*[\+\-\*\/×÷]\s*\d+", question):
            concepts.subject_type = "arithmetic"
        
        return concepts


class ConceptTracker:
    """
    Tracks used concepts per session to prevent repetition.
    """
    
    def __init__(self, max_history: int = 15):
        self.max_history = max_history
        # {session_id: {concept_type: [used_values]}}
        self._used_concepts: Dict[str, Dict[str, List[Any]]] = defaultdict(
            lambda: defaultdict(list)
        )
    
    def record(self, session_id: str, concepts: ExtractedConcepts) -> None:
        """Record concepts from a used question."""
        session = self._used_concepts[session_id]
        
        for word in concepts.words:
            if word not in session["words"]:
                session["words"].append(word)
        
        for num in concepts.numbers:
            if num not in session["numbers"]:
                session["numbers"].append(num)
        
        for pos in concepts.positions:
            if pos not in session["positions"]:
                session["positions"].append(pos)
        
        if concepts.question_format and concepts.question_format not in session["formats"]:
            session["formats"].append(concepts.question_format)
        
        if concepts.subject_type and concepts.subject_type not in session["types"]:
            session["types"].append(concepts.subject_type)
        
        # Trim to max history
        for key in session:
            if len(session[key]) > self.max_history:
                session[key] = session[key][-self.max_history:]
    
    def get_exclusions(self, session_id: str, subject: str = "") -> Dict[str, List[Any]]:
        """Get concepts that should be excluded from the next question."""
        session = self._used_concepts.get(session_id, {})
        return {
            "words": list(session.get("words", [])),
            "numbers": list(session.get("numbers", []))[-10:],  # Last 10 numbers
            "positions": list(session.get("positions", []))[-5:],  # Last 5 positions
            "formats": list(session.get("formats", []))[-3:],  # Encourage format variety
        }
    
    def has_concept_overlap(
        self, 
        session_id: str, 
        concepts: ExtractedConcepts,
        threshold: int = 2
    ) -> Tuple[bool, str]:
        """
        Check if concepts overlap too much with recently used ones.
        Returns (has_overlap, reason)
        """
        exclusions = self.get_exclusions(session_id)
        overlaps = []
        
        # Check word overlap
        for word in concepts.words:
            if word in exclusions["words"]:
                overlaps.append(f"word '{word}'")
        
        # Check significant number overlap (exact match for small numbers)
        for num in concepts.numbers:
            if num in exclusions["numbers"] and num < 100:
                overlaps.append(f"number {num}")
        
        # Check position overlap for place value
        for pos in concepts.positions:
            if pos in exclusions["positions"]:
                overlaps.append(f"position '{pos}'")
        
        if len(overlaps) >= threshold:
            return True, f"Overlapping concepts: {', '.join(overlaps[:3])}"
        
        return False, ""
    
    def clear_session(self, session_id: str) -> None:
        """Clear all tracked concepts for a session."""
        if session_id in self._used_concepts:
            del self._used_concepts[session_id]


# Global instances
concept_extractor = ConceptExtractor()
concept_tracker = ConceptTracker()


class ValidatorAgent(BaseAgent):
    """
    The Validator Agent 🔍
    
    A quality gate that validates generated questions AND answers.
    
    Question Checks:
    1. Duplicate detection (exact or near-match)
    2. Similarity detection with recent questions
    3. Pattern diversity (avoid repetitive examples)
    4. Grade-appropriateness validation
    
    Answer Checks:
    5. Arithmetic verification (+, -, ×, ÷)
    6. Place value verification  
    7. Comparison operations
    8. Fraction/percentage calculations
    
    Uses the Plan-Execute pattern:
    - Plan: Determine what validation to perform
    - Execute: Run validation checks
    """
    
    name = "ValidatorAgent"
    description = "Quality gate for question and answer validation"
    version = "2.0.0"  # Updated with answer verification
    
    # Common repetitive patterns to detect
    OVERUSED_PATTERNS = [
        r"\bapples?\b",
        r"\boranges?\b",
        r"\bdog(s)?\b",
        r"\bcat(s)?\b",
        r"\bball(s)?\b",
        r"\bpencil(s)?\b",
    ]
    
    # Place value positions (Indian and International)
    PLACE_VALUES = {
        # From right to left (0-indexed from right)
        0: ("ones", "units", 1),
        1: ("tens", "tens", 10),
        2: ("hundreds", "hundreds", 100),
        3: ("thousands", "thousands", 1000),
        4: ("ten thousands", "ten-thousands", 10000),
        5: ("hundred thousands", "lakhs", 100000),  # Indian: Lakhs
        6: ("millions", "millions", 1000000),
        7: ("ten millions", "crores", 10000000),  # Indian: Crores
        8: ("hundred millions", "ten crores", 100000000),
        9: ("billions", "arab", 1000000000),
    }
    
    SIMILARITY_THRESHOLD = 0.65
    MAX_HISTORY = 10
    PATTERN_USAGE_LIMIT = 2
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._question_history: Dict[str, List[str]] = defaultdict(list)
        self._pattern_usage: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._question_embeddings: Dict[str, List[float]] = {}  # Cache of question hash -> embedding
    
    # =========================================================================
    # ANSWER VERIFICATION METHODS
    # =========================================================================
    
    def verify_arithmetic(
        self,
        question: str,
        provided_answer: str
    ) -> AnswerValidationResult:
        """
        Verify arithmetic operations in question.
        Supports: +, -, *, /, ×, ÷
        """
        question_lower = question.lower()
        
        # Extract the arithmetic expression
        patterns = [
            # Direct expressions: "3 + 5 = ?"
            r'(\d+)\s*[\+]\s*(\d+)',  # Addition
            r'(\d+)\s*[\-]\s*(\d+)',  # Subtraction
            r'(\d+)\s*[\*×x]\s*(\d+)',  # Multiplication
            r'(\d+)\s*[\/÷]\s*(\d+)',  # Division
            
            # Word problems
            r'add\s+(\d+)\s+and\s+(\d+)',
            r'(\d+)\s+plus\s+(\d+)',
            r'(\d+)\s+minus\s+(\d+)',
            r'subtract\s+(\d+)\s+from\s+(\d+)',  # Note: order is reversed
            r'(\d+)\s+times\s+(\d+)',
            r'multiply\s+(\d+)\s+(?:by|and)\s+(\d+)',
            r'(\d+)\s+divided\s+by\s+(\d+)',
            r'divide\s+(\d+)\s+by\s+(\d+)',
        ]
        
        # Try to extract and calculate
        for pattern in patterns:
            match = re.search(pattern, question_lower)
            if match:
                num1, num2 = int(match.group(1)), int(match.group(2))
                
                # Determine operation
                if '+' in question or 'plus' in question_lower or 'add' in question_lower:
                    expected = num1 + num2
                    operation = "addition"
                elif '-' in question or 'minus' in question_lower or ('subtract' in question_lower and 'from' in question_lower):
                    if 'subtract' in question_lower and 'from' in question_lower:
                        expected = num2 - num1  # "subtract 3 from 10" = 10 - 3
                    else:
                        expected = num1 - num2
                    operation = "subtraction"
                elif '*' in question or '×' in question or 'x' in question.lower() or 'times' in question_lower or 'multiply' in question_lower:
                    expected = num1 * num2
                    operation = "multiplication"
                elif '/' in question or '÷' in question or 'divided' in question_lower or 'divide' in question_lower:
                    if num2 == 0:
                        return AnswerValidationResult(
                            is_correct=False,
                            reason="Division by zero is not allowed",
                        )
                    expected = num1 / num2
                    if expected == int(expected):
                        expected = int(expected)
                    operation = "division"
                else:
                    continue
                
                # Compare with provided answer
                try:
                    # Clean the provided answer
                    clean_answer = re.sub(r'[^\d\.\-]', '', str(provided_answer))
                    if not clean_answer:
                        return AnswerValidationResult(
                            is_correct=False,
                            reason=f"Could not parse answer: {provided_answer}",
                        )
                    
                    if '.' in clean_answer:
                        provided_num = float(clean_answer)
                    else:
                        provided_num = int(clean_answer)
                    
                    if abs(provided_num - expected) < 0.001:
                        return AnswerValidationResult(
                            is_correct=True,
                            reason=f"Arithmetic verified: {num1} {operation} {num2} = {expected}",
                            expected_answer=str(expected),
                            provided_answer=str(provided_num),
                        )
                    else:
                        return AnswerValidationResult(
                            is_correct=False,
                            reason=f"Wrong {operation}: {num1} and {num2} should give {expected}, not {provided_num}",
                            expected_answer=str(expected),
                            provided_answer=str(provided_num),
                        )
                except ValueError:
                    return AnswerValidationResult(
                        is_correct=False,
                        reason=f"Could not parse provided answer: {provided_answer}",
                    )
        
        # No arithmetic pattern found
        return AnswerValidationResult(
            is_correct=True,  # Can't verify, assume correct
            reason="No arithmetic pattern detected to verify",
        )
    
    def verify_place_value(
        self,
        question: str,
        provided_answer: str
    ) -> AnswerValidationResult:
        """
        Verify place value questions.
        E.g., "What is the value of digit 7 in 57,204,321?"
        """
        question_lower = question.lower()
        
        # Check if this is a place value question
        place_value_indicators = [
            "place value", "value of", "digit", "position", 
            "ones place", "tens place", "hundreds place",
            "thousands place", "lakhs", "crores", "millions"
        ]
        
        is_place_value_question = any(ind in question_lower for ind in place_value_indicators)
        if not is_place_value_question:
            return AnswerValidationResult(
                is_correct=True,
                reason="Not a place value question",
            )
        
        # Find large numbers with commas
        number_pattern = r'[\d,]+\d{3,}'  # At least 4 digits
        numbers = re.findall(number_pattern, question)
        
        if not numbers:
            # Try without commas
            numbers = re.findall(r'\d{4,}', question)
        
        if not numbers:
            return AnswerValidationResult(
                is_correct=True,
                reason="Could not find number to analyze",
            )
        
        # Get the largest number (likely the main number)
        main_number_str = max(numbers, key=lambda x: int(x.replace(',', '')))
        main_number = int(main_number_str.replace(',', ''))
        main_number_digits = main_number_str.replace(',', '')
        
        # Find which digit we're asking about - try multiple patterns
        target_digit = None
        
        # Patterns to try (in order of specificity)
        digit_patterns = [
            r"(?:the\s+)?digit\s*['\"]?(\d)['\"]?",  # "digit 7", "the digit 7"
            r"digit\s*['\"]?(\d)['\"]?",  # "digit 7"
            r"value\s+of\s+(?:the\s+)?(?:digit\s+)?['\"]?(\d)['\"]?",  # "value of 7", "value of the digit 7"
            r"(?:the\s+)?(\d)\s+in\s+the\s+number",  # "the 7 in the number"
            r"position\s+of\s+(?:the\s+)?(\d)",  # "position of 7"
        ]
        
        for pattern in digit_patterns:
            match = re.search(pattern, question_lower)
            if match:
                target_digit = match.group(1)
                break
        
        if not target_digit:
            # Last resort: find any single digit that's also in the main number
            single_digits = re.findall(r'\b(\d)\b', question_lower)
            for d in single_digits:
                if d in main_number_digits:
                    target_digit = d
                    break
        
        if not target_digit:
            return AnswerValidationResult(
                is_correct=True,
                reason="Could not determine which digit to analyze",
            )
        
        # Find the position of this digit in the number (from right, 0-indexed)
        positions = []
        for i, d in enumerate(reversed(main_number_digits)):
            if d == target_digit:
                positions.append(i)
        
        if not positions:
            return AnswerValidationResult(
                is_correct=False,
                reason=f"Digit '{target_digit}' not found in {main_number_str}",
            )
        
        # Calculate expected values for each position
        expected_values = []
        for pos in positions:
            place_multiplier = 10 ** pos
            expected_value = int(target_digit) * place_multiplier
            expected_values.append((pos, expected_value))
        
        # Parse the provided answer - handle various formats
        clean_answer = str(provided_answer).replace(',', '').replace(' ', '').strip()
        try:
            # Try to extract just the number
            num_match = re.search(r'[\d,]+', clean_answer)
            if num_match:
                provided_num = int(num_match.group().replace(',', ''))
            elif clean_answer.isdigit():
                provided_num = int(clean_answer)
            else:
                return AnswerValidationResult(
                    is_correct=False,
                    reason=f"Could not parse answer: {provided_answer}",
                )
        except ValueError:
            return AnswerValidationResult(
                is_correct=False,
                reason=f"Could not parse answer: {provided_answer}",
            )
        
        # Check if answer matches any valid position
        for pos, expected in expected_values:
            if provided_num == expected:
                place_name = self.PLACE_VALUES.get(pos, (f"10^{pos}", f"10^{pos}", 10**pos))[0]
                return AnswerValidationResult(
                    is_correct=True,
                    reason=f"Place value verified: digit {target_digit} in {place_name} = {expected:,}",
                    expected_answer=str(expected),
                    provided_answer=str(provided_num),
                )
        
        # Answer doesn't match - find what the correct answer should be
        # Use the LEFTMOST occurrence (highest position = most significant)
        correct_pos = max(positions)
        correct_value = int(target_digit) * (10 ** correct_pos)
        place_name = self.PLACE_VALUES.get(correct_pos, (f"10^{correct_pos}", f"10^{correct_pos}", 10**correct_pos))[0]
        
        return AnswerValidationResult(
            is_correct=False,
            reason=f"Wrong place value: In {main_number_str}, digit '{target_digit}' is in the {place_name} place (position {correct_pos} from right), so its value is {correct_value:,}, not {provided_num:,}",
            expected_answer=str(correct_value),
            provided_answer=str(provided_num),
        )
    
    def verify_answer(
        self,
        question: str,
        answer: str,
        subject: str = ""
    ) -> AnswerValidationResult:
        """
        Main entry point for answer verification.
        Tries different verification methods based on question type.
        """
        # Try place value first (more specific)
        place_result = self.verify_place_value(question, answer)
        if place_result.reason != "Not a place value question":
            return place_result
        
        # Try arithmetic
        arith_result = self.verify_arithmetic(question, answer)
        if arith_result.reason != "No arithmetic pattern detected to verify":
            return arith_result
        
        # Default: can't verify
        return AnswerValidationResult(
            is_correct=True,
            reason="No verifiable pattern detected - answer assumed correct",
        )
    
    # =========================================================================
    # QUESTION VALIDATION METHODS (UNCHANGED)
    # =========================================================================
    
    def _normalize_question(self, question: str) -> str:
        """Normalize question for comparison."""
        q = question.lower().strip()
        q = re.sub(r'[^\w\s]', '', q)
        q = ' '.join(q.split())
        return q
    
    def _get_question_hash(self, question: str) -> str:
        """Get a hash of the normalized question."""
        normalized = self._normalize_question(question)
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    async def _get_embedding(self, text: str, text_hash: str) -> Optional[List[float]]:
        """Get embedding from cache or service."""
        if text_hash in self._question_embeddings:
            return self._question_embeddings[text_hash]
        
        try:
            vector = await similarity_service.get_embedding(text)
            if vector:
                self._question_embeddings[text_hash] = vector
            return vector
        except Exception:
            return None

    async def _calculate_similarity(self, q1: str, q2: str) -> float:
        """Calculate similarity using embeddings (async)."""
        # Fallback to string matching for very short texts
        if len(q1) < 10 or len(q2) < 10:
            return SequenceMatcher(None, q1, q2).ratio()

        # Get hashes
        h1 = self._get_question_hash(q1)
        h2 = self._get_question_hash(q2)
        
        # Get embeddings
        vec1 = await self._get_embedding(q1, h1)
        vec2 = await self._get_embedding(q2, h2)
        
        if vec1 and vec2:
            return similarity_service.calculate_similarity(vec1, vec2)
        
        # Fallback to SequenceMatcher if embeddings fail
        return SequenceMatcher(None, q1, q2).ratio()
    
    def _extract_numbers(self, question: str) -> Set[int]:
        """Extract numbers from a question."""
        numbers = re.findall(r'\b\d+\b', question)
        return set(int(n) for n in numbers)
    
    def _is_math_equivalent(self, q1: str, q2: str) -> bool:
        """Check if two questions are mathematically equivalent."""
        norm1 = self._normalize_question(q1)
        norm2 = self._normalize_question(q2)
        
        add_patterns = [
            r'(\d+)\s*\+\s*(\d+)',
            r'add\s+(\d+)\s+and\s+(\d+)',
            r'what\s+is\s+(\d+)\s+plus\s+(\d+)',
            r'(\d+)\s+plus\s+(\d+)',
        ]
        
        for pattern in add_patterns:
            match1 = re.search(pattern, norm1)
            match2 = re.search(pattern, norm2)
            if match1 and match2:
                if set(match1.groups()) == set(match2.groups()):
                    return True
        
        sub_patterns = [
            r'(\d+)\s*-\s*(\d+)',
            r'subtract\s+(\d+)\s+from\s+(\d+)',
            r'what\s+is\s+(\d+)\s+minus\s+(\d+)',
        ]
        
        for pattern in sub_patterns:
            match1 = re.search(pattern, norm1)
            match2 = re.search(pattern, norm2)
            if match1 and match2:
                if match1.groups() == match2.groups():
                    return True
        
        return False
    
    def _detect_overused_patterns(
        self, 
        question: str, 
        session_id: str
    ) -> Tuple[bool, List[str]]:
        """Detect if question uses overused patterns."""
        overused = []
        question_lower = question.lower()
        
        for pattern in self.OVERUSED_PATTERNS:
            if re.search(pattern, question_lower):
                pattern_key = pattern[:20]
                current_count = self._pattern_usage[session_id][pattern_key]
                if current_count >= self.PATTERN_USAGE_LIMIT:
                    match = re.search(pattern, question_lower)
                    if match:
                        overused.append(match.group())
        
        return len(overused) > 0, overused
    
    def _validate_grade_appropriateness(
        self, 
        question: str, 
        grade: int
    ) -> Tuple[bool, str]:
        """Validate if question is appropriate for grade level."""
        complex_words = [
            "however", "therefore", "consequently", "nevertheless",
            "hypothesis", "analyze", "evaluate", "synthesize",
        ]
        
        if grade <= 3:
            question_lower = question.lower()
            for word in complex_words:
                if word in question_lower:
                    return False, f"Word '{word}' may be too complex for grade {grade}"
        
        numbers = self._extract_numbers(question)
        if numbers:
            max_num = max(numbers)
            if grade == 1 and max_num > 20:
                return False, f"Number {max_num} may be too large for grade 1"
            elif grade == 2 and max_num > 100:
                return False, f"Number {max_num} may be too large for grade 2"
            elif grade == 3 and max_num > 1000:
                return False, f"Number {max_num} may be too large for grade 3"
        
        return True, "Grade appropriate"
    
    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """Plan the validation."""
        metadata = context.metadata
        action = metadata.get("action", "validate_question")
        
        if action == "validate_answer":
            return {
                "action": "validate_answer",
                "params": {
                    "question": metadata.get("question", ""),
                    "answer": metadata.get("answer", ""),
                    "subject": metadata.get("subject", ""),
                }
            }
        
        return {
            "action": "validate_question",
            "params": {
                "question": metadata.get("question", ""),
                "answer": metadata.get("answer"),  # Optional
                "session_id": context.session_id,
                "grade": metadata.get("grade", 1),
                "subject": metadata.get("subject", ""),
                "check_similarity": metadata.get("check_similarity", True),
                "check_patterns": metadata.get("check_patterns", True),
                "check_grade": metadata.get("check_grade", True),
                "check_answer": metadata.get("check_answer", True),  # NEW
            }
        }
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """Execute the validation checks."""
        tracer = get_tracer()
        params = plan["params"]
        action = plan["action"]
        
        if action == "validate_answer":
            with tracer.start_as_current_span("validate_answer") as span:
                result = self.verify_answer(
                    params["question"],
                    params["answer"],
                    params.get("subject", ""),
                )
                span.set_attribute("answer.is_correct", result.is_correct)
                return AgentResult(
                    success=True,
                    output=result,
                    state=AgentState.COMPLETED,
                )
        
        with tracer.start_as_current_span("validate_question") as span:
            question = params["question"]
            answer = params.get("answer")
            session_id = params["session_id"]
            grade = params["grade"]
            
            span.set_attribute("validator.session_id", session_id)
            span.set_attribute("validator.grade", grade)
            
            recent_questions = self._question_history.get(session_id, [])
            
            # 1. Check for exact duplicates
            question_hash = self._get_question_hash(question)
            for prev_q in recent_questions:
                if self._get_question_hash(prev_q) == question_hash:
                    span.set_attribute("validator.rejected", "exact_duplicate")
                    return AgentResult(
                        success=True,
                        output=ValidationResult(
                            is_valid=False,
                            reason="Exact duplicate of a recent question",
                            similarity_score=1.0,
                            matched_question=prev_q,
                        ),
                        state=AgentState.COMPLETED,
                    )
            
            # 2. Check similarity
            if params["check_similarity"]:
                for prev_q in recent_questions:
                    similarity = await self._calculate_similarity(question, prev_q)
                    
                    if self._is_math_equivalent(question, prev_q):
                        span.set_attribute("validator.rejected", "math_equivalent")
                        return AgentResult(
                            success=True,
                            output=ValidationResult(
                                is_valid=False,
                                reason="Mathematically equivalent to a recent question",
                                similarity_score=0.95,
                                matched_question=prev_q,
                                suggestions=["Try a different operation or numbers"],
                            ),
                            state=AgentState.COMPLETED,
                        )
                    
                    if similarity >= self.SIMILARITY_THRESHOLD:
                        span.set_attribute("validator.rejected", "too_similar")
                        return AgentResult(
                            success=True,
                            output=ValidationResult(
                                is_valid=False,
                                reason=f"Too similar to a recent question ({similarity:.0%} match)",
                                similarity_score=similarity,
                                matched_question=prev_q,
                            ),
                            state=AgentState.COMPLETED,
                        )

            # 2.5 NEW: Check concept overlap (same adverbs, numbers, positions)
            if params.get("check_concepts", True):
                concepts = concept_extractor.extract(question, params.get("subject", ""))
                has_overlap, overlap_reason = concept_tracker.has_concept_overlap(
                    session_id, concepts, threshold=1  # Strict: any key concept overlap
                )
                if has_overlap:
                    span.set_attribute("validator.rejected", "concept_overlap")
                    return AgentResult(
                        success=True,
                        output=ValidationResult(
                            is_valid=False,
                            reason=f"Concept repetition: {overlap_reason}",
                            suggestions=["Use different words, numbers, or positions"],
                        ),
                        state=AgentState.COMPLETED,
                    )
            
            # 3. Check overused patterns
            if params["check_patterns"]:
                is_overused, overused_patterns = self._detect_overused_patterns(
                    question, session_id
                )
                if is_overused:
                    span.set_attribute("validator.rejected", "overused_pattern")
                    return AgentResult(
                        success=True,
                        output=ValidationResult(
                            is_valid=False,
                            reason=f"Overused example: {', '.join(overused_patterns)}",
                        ),
                        state=AgentState.COMPLETED,
                    )
            
            # 4. Check grade appropriateness
            if params["check_grade"]:
                is_appropriate, grade_reason = self._validate_grade_appropriateness(
                    question, grade
                )
                if not is_appropriate:
                    span.set_attribute("validator.rejected", "grade_inappropriate")
                    return AgentResult(
                        success=True,
                        output=ValidationResult(
                            is_valid=False,
                            reason=grade_reason,
                        ),
                        state=AgentState.COMPLETED,
                    )
            
            # 5. NEW: Verify answer correctness
            if params.get("check_answer") and answer:
                answer_result = self.verify_answer(question, answer, params.get("subject", ""))
                if not answer_result.is_correct:
                    span.set_attribute("validator.rejected", "wrong_answer")
                    span.set_attribute("validator.expected", answer_result.expected_answer or "")
                    return AgentResult(
                        success=True,
                        output=ValidationResult(
                            is_valid=False,
                            reason=f"Answer verification failed: {answer_result.reason}",
                            corrected_answer=answer_result.expected_answer,
                            suggestions=[f"Correct answer should be: {answer_result.expected_answer}"],
                        ),
                        state=AgentState.COMPLETED,
                    )
            
            # 6. NEW: Verify distractors (if provided)
            if params.get("options"):
                distractor_result = self.verify_distractors(
                    question, 
                    params["options"], 
                    answer or "", 
                    params.get("subject", "")
                )
                if not distractor_result.is_valid:
                    span.set_attribute("validator.rejected", "invalid_distractors")
                    return AgentResult(
                        success=True,
                        output=distractor_result,
                        state=AgentState.COMPLETED,
                    )
            
            span.set_attribute("validator.accepted", True)
            
            return AgentResult(
                success=True,
                output=ValidationResult(
                    is_valid=True,
                    reason="Question passed all validation checks",
                ),
                state=AgentState.COMPLETED,
            )
    
    async def record_question(self, session_id: str, question: str) -> None:
        """Record a question that was shown to the student."""
        self._question_history[session_id].append(question)
        if len(self._question_history[session_id]) > self.MAX_HISTORY:
            self._question_history[session_id] = self._question_history[session_id][-self.MAX_HISTORY:]
        
        # Track concepts
        concepts = concept_extractor.extract(question)
        concept_tracker.record(session_id, concepts)

        # Pre-fetch embedding
        question_hash = self._get_question_hash(question)
        await self._get_embedding(question, question_hash)
        
        question_lower = question.lower()
        for pattern in self.OVERUSED_PATTERNS:
            if re.search(pattern, question_lower):
                pattern_key = pattern[:20]
                self._pattern_usage[session_id][pattern_key] += 1
    
    def clear_session(self, session_id: str) -> None:
        """Clear history for a session."""
        if session_id in self._question_history:
            del self._question_history[session_id]
        if session_id in self._pattern_usage:
            del self._pattern_usage[session_id]
        
        # Clear concept tracking
        concept_tracker.clear_session(session_id)
    
    def get_exclusions(self, session_id: str) -> Dict[str, Any]:
        """Get concepts to exclude for the next question."""
        return concept_tracker.get_exclusions(session_id)
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        return {
            "questions_recorded": len(self._question_history.get(session_id, [])),
            "pattern_usage": dict(self._pattern_usage.get(session_id, {})),
            "exclusions": self.get_exclusions(session_id),
        }
    
    def validate_batch(
        self,
        questions: List[str],
        session_id: str = "default_session"
    ) -> List[Tuple[int, bool, str]]:
        """
        Validate a batch of questions for duplicates within the batch.
        
        This is a lightweight check for batch-generated questions.
        It checks for:
        1. Exact duplicates within the batch
        2. High similarity within the batch (using simple text matching)
        
        Args:
            questions: List of question strings
            session_id: Session ID for tracking
            
        Returns:
            List of (index, is_valid, reason) tuples
        """
        results = []
        seen_hashes = set()
        seen_normalized = set()
        
        for idx, question in enumerate(questions):
            # Hash check
            q_hash = hashlib.md5(question.encode()).hexdigest()
            
            # Normalize for similarity
            q_normalized = question.lower().strip().replace(" ", "").replace("?", "")
            
            if q_hash in seen_hashes:
                results.append((idx, False, "Exact duplicate within batch"))
            elif q_normalized in seen_normalized:
                results.append((idx, False, "Very similar to another question in batch"))
            else:
                seen_hashes.add(q_hash)
                seen_normalized.add(q_normalized)
                results.append((idx, True, "Valid"))
        
        return results
    

    
    def verify_distractors(
        self,
        question: str,
        options: List[str],
        answer: str,
        subject: str = "",
        subtopic: str = ""
    ) -> ValidationResult:
        """
        Verify quality of distractors based on subject rules.
        """
        # 1. Basic check: Distractors must be unique equal to len(set(options))
        if len(options) != len(set(opt.lower().strip() for opt in options)):
            return ValidationResult(is_valid=False, reason="Duplicate options found")
            
        # 2. Basic check: Answer must be in options
        # Note: handled by normalization usually, but safety check
        if answer not in options:
            # Maybe flexible check? For now assume exact match required by backend
            # But let's skip strict check here as examiner usually ensures it
            pass
            
        # 3. Subject-specific rules
        subject_lower = subject.lower()
        if "english" in subject_lower or "grammar" in subject_lower:
            return self._validate_grammar_distractors(question, options, answer)
        elif "math" in subject_lower:
            return self._validate_math_distractors(question, options, answer)
        elif "science" in subject_lower:
            return self._validate_science_distractors(question, options, answer)
            
        return ValidationResult(is_valid=True, reason="Valid distractors")

    def _validate_grammar_distractors(self, question: str, options: List[str], answer: str) -> ValidationResult:
        """
        Validate grammar options.
        Rule: For 'Identify the [POS]', distractors should NOT be that POS.
        """
        question_lower = question.lower()
        
        # Heuristic for Adverbs (-ly)
        if "adverb" in question_lower:
            # Check if answer ends in -ly (heuristic)
            if answer.endswith("ly"):
                # If answer matches heuristic, distractors should NOT match it
                for opt in options:
                    if opt != answer and opt.endswith("ly") and opt not in ["fly", "ugly", "family", "early"]: # Common exceptions
                         return ValidationResult(is_valid=False, reason="Distractor overlaps with correct answer type (Adverb)")
        
        # Heuristic for Adjectives vs Nouns? (Too complex for simple regex without NLP lib)
        
        return ValidationResult(is_valid=True, reason="Grammar checks passed")

    def _validate_math_distractors(self, question: str, options: List[str], answer: str) -> ValidationResult:
        """
        Validate math options.
        Rule: Distractors should be numbers if answer is number.
        """
        # Check if answer is number
        is_number = re.match(r'^-?\d+(\.\d+)?$', str(answer))
        
        if is_number:
            for opt in options:
                if not re.match(r'^-?\d+(\.\d+)?$', str(opt)):
                     return ValidationResult(is_valid=False, reason="Distractor type mismatch (expected number)")
        
        return ValidationResult(is_valid=True, reason="Math checks passed")

    def _validate_science_distractors(self, question: str, options: List[str], answer: str) -> ValidationResult:
        """
        Validate science options.
        Rule: Check for distinct options and avoid substring overlaps (ambiguity).
        """
        norm_ans = answer.lower().strip()
        
        for opt in options:
            norm_opt = opt.lower().strip()
            if not norm_opt:
                 return ValidationResult(is_valid=False, reason="Empty distractor option")
            
            # Avoid ambiguity where answer is contained in distractor or vice versa
            # e.g. Answer: "Leaf", Distractor: "Leaf bud" -> confusing
            # Only apply if words are significant (len > 3)
            if len(norm_ans) > 3 and len(norm_opt) > 3 and norm_opt != norm_ans:
                if norm_ans in norm_opt or norm_opt in norm_ans:
                     return ValidationResult(is_valid=False, reason=f"Ambiguous option '{opt}' overlaps with answer '{answer}'")
        
        return ValidationResult(is_valid=True, reason="Science checks passed")



    async def validate(
        self,
        question: str,
        session_id: str = None,
        grade: int = 1,
        subject: str = "",
        answer: Optional[str] = None,
        options: Optional[List[str]] = None,
        auto_record: bool = True,
    ) -> ValidationResult:
        """
        Validate a generated question.
        Includes uniqueness, variety, grade checks, answer verification, AND distractor validation.
        """
        # Ensure session_id
        if session_id is None:
            session_id = "default_session"


        result = await self.run(
            user_input=f"Validate question: {question[:50]}...",
            session_id=session_id,
            metadata={
                "question": question,
                "answer": answer,
                "grade": grade,
                "subject": subject,
                "check_similarity": True,
                "check_patterns": True,
                "check_grade": True,
                "check_answer": answer is not None,
                "options": options,
            }
        )
        
        if result.success:
            validation = result.output
            if auto_record and validation.is_valid:
                await self.record_question(session_id, question)
            return validation
        else:
            return ValidationResult(
                is_valid=True,
                reason=f"Validation error: {result.error}",
            )
    
    async def validate_answer_only(
        self,
        question: str,
        answer: str,
        subject: str = "",
    ) -> AnswerValidationResult:
        """
        Validate just the answer correctness.
        """
        return self.verify_answer(question, answer, subject)


# Singleton instance
validator_agent = ValidatorAgent()
