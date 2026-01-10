"""
AI Tutor Platform - Examiner Agent
Generates educational questions for assessments, tests, and practice.
Refactored from question_generator.py to use Agentic Architecture.
"""
import json
import random
from typing import Dict, Any, List, Optional, Literal, Tuple
from dataclasses import dataclass
from enum import Enum

from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.ai.core.telemetry import get_tracer


class QuestionDifficulty(str, Enum):
    """Difficulty levels for questions."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class GeneratedQuestion:
    """Schema for AI-generated questions."""
    question: str
    answer: str
    options: List[str]
    correct_answers: List[str] = None  # List of correct answers for multi-select
    hint: str = ""
    explanation: str = ""
    difficulty: str = "easy"
    question_type: str = "multiple_choice"

    def __post_init__(self):
        if self.correct_answers is None:
            self.correct_answers = [self.answer] if self.answer else []


class ExaminerAgent(BaseAgent):
    """
    The Examiner Agent 📝
    
    Generates age-appropriate educational questions for:
    - Practice sessions
    - Assessments (subtopic level)
    - Tests (topic level)
    - Exams (subject level)
    
    Features:
    - Integrated validation (via ValidatorAgent)
    - Automatic retry for similar/duplicate questions
    - Diverse question generation
    
    Uses the Plan-Execute pattern:
    - Plan: Determine question parameters and validate input
    - Execute: Generate the question via LLM with validation
    """
    
    name = "ExaminerAgent"
    description = "Generates educational questions for assessments"
    version = "2.2.0"  # Enhanced variety and topic-specific prompts
    
    # Maximum retries for unique question generation
    MAX_RETRIES = 5  # Increased from 3 for more variety attempts
    
    # Higher default temperature for more creative questions
    DEFAULT_TEMPERATURE = 1.0  # Increased from 0.9
    
    # Diverse examples to encourage variety
    DIVERSE_EXAMPLES = [
        "toys, books, flowers, crayons, stickers",
        "birds, fish, butterflies, rabbits, frogs",
        "cookies, cupcakes, pizza slices, sandwiches",
        "stars, moons, clouds, rainbows, snowflakes",
        "cars, buses, trains, bicycles, boats",
        "marbles, beads, coins, stamps, shells",
        "kites, balloons, ribbons, candles, gifts",
    ]
    
    # Topic-specific variety hints
    VARIETY_HINTS = {
        "place value": """
FOR PLACE VALUE QUESTIONS - YOU MUST VARY:
- Ask about DIFFERENT digit positions each time (ones, tens, hundreds, thousands, ten-thousands, lakhs, crores, millions)
- Use numbers of DIFFERENT lengths (4-digit, 5-digit, 6-digit, 7-digit, 8-digit)
- Ask about DIFFERENT digits (not always the same digit like 7)
- Vary question phrasing: "What is the place value of...", "In which place is...", "What is the value of digit X...", "Which digit is in the Y place..."
- Use UNIQUE numbers - don't reuse similar patterns

THIS TIME, specifically ask about the {random_place} place using a {random_length}-digit number.
""",
        "addition": """
FOR ADDITION QUESTIONS - VARY:
- Use different number ranges (single-digit, double-digit, triple-digit)
- Mix with/without carrying
- Use word problems with different contexts
- Vary: "X + Y = ?", "Add X and Y", "What is X plus Y?", "Find the sum of X and Y"
""",
        "subtraction": """
FOR SUBTRACTION QUESTIONS - VARY:
- Use different number ranges
- Mix with/without borrowing  
- Use word problems with different contexts
- Vary: "X - Y = ?", "Subtract Y from X", "What is X minus Y?", "Find the difference"
""",
        "multiplication": """
FOR MULTIPLICATION QUESTIONS - VARY:
- Different factors (not always the same tables)
- Word problems with different scenarios (groups of items, arrays, repeated addition)
- Vary: "X × Y = ?", "Multiply X by Y", "What is X times Y?", "Find the product"
""",
        "division": """
FOR DIVISION QUESTIONS - VARY:
- Different divisors and dividends
- With/without remainders as appropriate for grade
- Equal sharing and grouping word problems
- Vary: "X ÷ Y = ?", "Divide X by Y", "X divided by Y", "How many groups of Y in X?"
""",
        "fractions": """
FOR FRACTION QUESTIONS - VARY:
- Different denominators (halves, thirds, fourths, fifths, sixths, eighths)
- Proper fractions, improper fractions, mixed numbers
- Comparing, adding, simplifying as appropriate
- Visual and word problems
""",
        "living things": """
FOR LIVING THINGS/BIOLOGY - VARY:
- Ask about different organisms (plants, mammals, birds, insects)
- Vary focus: habitat, food chains, life cycles, body parts
- Use "Which of these..." and "What is the function of..." formats
""",
        "plants": """
FOR PLANT QUESTIONS - VARY:
- Parts of plants (root, stem, leaf, flower)
- Types of plants (trees, shrubs, herbs, climbers)
- Needs of plants (sunlight, water, soil)
- Photosynthesis/Life cycle
""",
        "animals": """
FOR ANIMAL QUESTIONS - VARY:
- Domestic vs Wild
- Herbivore, Carnivore, Omnivore
- Young ones (calf, cub, kitten)
- Homes/Shelters
""",
        "matter": """
FOR MATTER/MATERIALS - VARY:
- States of matter (solid, liquid, gas)
- Properties (hard, soft, rough, smooth, waterproof)
- Material sources (wood, metal, plastic, glass)
""",
        "space": """
FOR EARTH & SPACE - VARY:
- Solar system components (planets, sun, moon)
- Day/Night cycle
- Seasons and Weather
- Stars and constellations
""",
        "default": """
VARIETY IS ESSENTIAL! Each question must be noticeably different from the last.
- Change the numbers significantly
- Change the context/story
- Change the question phrasing
- Change what you're asking for
"""
    }
    
    # Random place values for variety
    PLACE_VALUE_POSITIONS = [
        ("ones", 1), ("tens", 2), ("hundreds", 3), ("thousands", 4),
        ("ten-thousands", 5), ("lakhs", 6), ("ten-lakhs", 7), ("crores", 8)
    ]
    
    SYSTEM_PROMPT = """You are an expert elementary school teacher creating MULTIPLE CHOICE questions.
Your answers must be MATHEMATICALLY CORRECT. Double-check all calculations before responding.

DISTRACTOR QUALITY GUIDELINES:
1. For Grammar: If identifying a part of speech (e.g., Adverb), distractors MUST be distinct parts of speech (e.g., Nouns, Verbs) whenever possible. Avoid ambiguity.
2. For Math: Distractors must be plausible numbers but clearly incorrect. Ensure they are numbers if the answer is a number.
3. For Science: Distractors must be scientifically plausible concepts within the same category (e.g. if answer is a planet, distractors should be other planets, not cars).
4. Distractors must be UNIQUE. No duplicate options.
5. Correct Answer MUST be included in the options.

Create a question for:
- Subject: {subject}
- Topic: {topic}  
- Subtopic: {subtopic}
- Grade Level: {grade}
- Difficulty: {difficulty}
- Variation Seed: {variation_seed}

🚨 CRITICAL - VARIETY IS MANDATORY 🚨
{variety_hint}

PREVIOUSLY USED CONCEPTS (AVOID REPEATING THESE):
{exclusions}

Use diverse examples from: {diverse_examples}
AVOID: apples, oranges, dogs, cats, balls, pencils (overused!)

MATHEMATICAL ACCURACY RULES:
1. VERIFY YOUR MATH step by step before answering
2. For place value: Count digit positions from RIGHT (ones=1st, tens=2nd, hundreds=3rd...)
   Example: In 57,204,321 → 5 is in ten-millions (8th position) = 50,000,000
                           → 7 is in millions (7th position) = 7,000,000
                           → 2 is in hundred-thousands (6th) = 200,000
3. The "answer" field must match EXACTLY one of the "options" (for single choice)
4. The CORRECT answer must be the FIRST option in the array
5. Create 3 plausible but WRONG distractor options

For "question_type": "multi_select":
- Provide "correct_answers": ["Answer1", "Answer2"]
- "options" must include ALL correct answers + distractors
- "answer" field should be the primary/first correct answer

Respond with ONLY this JSON (no markdown, no explanation):
{{
    "question": "Your UNIQUE question here?",
    "options": ["CORRECT_ANSWER", "wrong1", "wrong2", "wrong3"],
    "answer": "CORRECT_ANSWER",
    "correct_answers": ["CORRECT_ANSWER"],
    "hint": "A helpful hint",
    "explanation": "Why this answer is correct (show your work)",
    "difficulty": "{difficulty}",
    "question_type": "multiple_choice"  // or "multi_select"
}}

FINAL CHECK: Is this question DIFFERENT from typical questions? Does it use UNIQUE numbers/context?"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validator = None
    
    @property
    def validator(self):
        """Lazy load the validator agent."""
        if self._validator is None:
            from app.ai.agents.validator import validator_agent
            self._validator = validator_agent
        return self._validator

    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """
        Plan the question generation.
        
        Validates input and determines generation parameters,
        including topic-specific variety hints.
        """
        metadata = context.metadata
        
        # Extract parameters from metadata
        subject = metadata.get("subject", "General")
        topic = metadata.get("topic", "")
        subtopic = metadata.get("subtopic", "")
        difficulty = metadata.get("difficulty", QuestionDifficulty.EASY)
        grade = metadata.get("grade", 1)
        question_type = metadata.get("question_type", "multiple_choice")
        temperature = metadata.get("temperature", self.DEFAULT_TEMPERATURE)
        session_id = metadata.get("session_id", context.session_id)
        validate = metadata.get("validate", True)
        
        # Convert enum to string if needed
        if isinstance(difficulty, QuestionDifficulty):
            difficulty = difficulty.value
        
        # Generate variety seed for uniqueness
        variation_seed = random.randint(1, 100000)
        
        # Select diverse examples
        diverse_examples = random.choice(self.DIVERSE_EXAMPLES)
        
        # Get topic-specific variety hint
        variety_hint = self._get_variety_hint(subtopic, topic, grade)
        
        return {
            "action": "generate_question",
            "params": {
                "subject": subject,
                "topic": topic,
                "subtopic": subtopic,
                "original_subtopic": subtopic,
                "difficulty": difficulty,
                "grade": grade,
                "question_type": question_type,
                "temperature": temperature,
                "diverse_examples": diverse_examples,
                "variety_hint": variety_hint,
                "variation_seed": variation_seed,
                "session_id": session_id,
                "validate": validate,
            }
        }
    
    def _get_variety_hint(self, subtopic: str, topic: str, grade: int) -> str:
        """Generate topic-specific variety hints."""
        subtopic_lower = subtopic.lower()
        topic_lower = topic.lower()
        
        # Check for topic-specific hints
        for key in self.VARIETY_HINTS:
            if key in subtopic_lower or key in topic_lower:
                hint = self.VARIETY_HINTS[key]
                
                # For place value, add specific random requirements
                if key == "place value":
                    random_place = random.choice(self.PLACE_VALUE_POSITIONS)
                    random_length = random.choice([4, 5, 6, 7, 8])
                    hint = hint.format(
                        random_place=random_place[0],
                        random_length=random_length
                    )
                
                return hint
        
        # Default variety hint
        return self.VARIETY_HINTS["default"]
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """
        Execute the question generation with validation and retry.
        """
        tracer = get_tracer()
        
        with tracer.start_as_current_span("generate_question") as span:
            params = plan["params"]
            session_id = params.get("session_id", "default")
            validate = params.get("validate", True)
            
            # Fetch concept exclusions
            try:
                exclusions_dict = self.validator.get_exclusions(session_id)
                exclusions_str = (
                    f"- Words: {', '.join(exclusions_dict.get('words', []))}\n"
                    f"- Numbers: {', '.join(map(str, exclusions_dict.get('numbers', [])))}\n"
                    f"- Place Values: {', '.join(exclusions_dict.get('positions', []))}"
                )
            except Exception:
                exclusions_str = "None"
            
            params["exclusions"] = exclusions_str
            
            span.set_attribute("question.subject", params["subject"])
            span.set_attribute("question.topic", params["topic"])
            
            last_error = None
            
            for attempt in range(self.MAX_RETRIES):
                try:
                    span.add_event(f"generation_attempt_{attempt + 1}")
                    
                    # Update random seed for each retry
                    if attempt > 0:
                        params["subtopic"] = f"{params['original_subtopic']} (Variation #{random.randint(1, 10000)})"
                        params["diverse_examples"] = random.choice(self.DIVERSE_EXAMPLES)
                    
                    # Generate question via LLM
                    response = await self.llm.generate_json(
                        prompt="Generate the question now.",
                        system_prompt=self.SYSTEM_PROMPT,
                        context=params,
                        agent_name=self.name,
                    )
                    
                    # Normalize response
                    question = self._normalize_question(response)
                    
                    # Validate the question AND answer if enabled
                    if validate:
                        validation = await self.validator.validate(
                            question=question.question,
                            session_id=session_id,
                            grade=params["grade"],
                            subject=params["subject"],
                            answer=question.answer,  # Also validate the answer!
                            options=question.options, # Pass options for distractor validation
                            auto_record=False,  # We'll record after success
                        )
                        
                        if not validation.is_valid:
                            span.add_event(f"validation_failed_{attempt + 1}", {
                                "reason": validation.reason,
                                "similarity": str(validation.similarity_score),
                            })
                            
                            # Check if we can fix the answer
                            if validation.corrected_answer:
                                span.add_event("answer_corrected", {
                                    "wrong_answer": question.answer,
                                    "corrected_answer": validation.corrected_answer,
                                })
                                # Fix the answer and continue validation
                                question.answer = validation.corrected_answer
                                # Also fix it in options (first option should be correct)
                                if question.options and question.options[0] != validation.corrected_answer:
                                    question.options[0] = validation.corrected_answer
                                
                                # Re-validate without answer check (we just fixed it)
                                validation = await self.validator.validate(
                                    question=question.question,
                                    session_id=session_id,
                                    grade=params["grade"],
                                    subject=params["subject"],
                                    answer=None,  # Skip answer validation this time
                                    auto_record=False,
                                )
                                
                                if validation.is_valid:
                                    # Question is now valid with corrected answer
                                    await self.validator.record_question(session_id, question.question)
                                    span.set_attribute("question.generated", True)
                                    span.set_attribute("question.answer_corrected", True)
                                    span.set_attribute("question.attempts", attempt + 1)
                                    
                                    return AgentResult(
                                        success=True,
                                        output=question,
                                        state=AgentState.COMPLETED,
                                        metadata={"params": params, "attempts": attempt + 1, "answer_corrected": True},
                                    )
                            
                            # Log the rejection reason
                            last_error = f"Validation failed: {validation.reason}"
                            
                            # Continue to retry
                            continue
                        
                        # Record the question as used
                        await self.validator.record_question(session_id, question.question)
                    
                    span.set_attribute("question.generated", True)
                    span.set_attribute("question.attempts", attempt + 1)
                    
                    return AgentResult(
                        success=True,
                        output=question,
                        state=AgentState.COMPLETED,
                        metadata={"params": params, "attempts": attempt + 1},
                    )
                    
                except Exception as e:
                    last_error = str(e)
                    span.record_exception(e)
            
            # All retries exhausted
            span.set_attribute("question.failed", True)
            span.set_attribute("question.attempts", self.MAX_RETRIES)
            
            return AgentResult(
                success=False,
                output=None,
                state=AgentState.ERROR,
                error=f"Failed to generate unique question after {self.MAX_RETRIES} attempts. Last error: {last_error}",
            )
    
    def _normalize_question(self, data: Dict[str, Any]) -> GeneratedQuestion:
        """
        Normalize the LLM response to ensure consistent format.
        """
        # Ensure options exist
        if "options" not in data or not data["options"]:
            data["options"] = [data.get("answer", "A"), "B", "C", "D"]
        
        # Ensure correct answer is first in options
        correct_answer = data.get("answer", "")
        options = data.get("options", [])
        
        if options and options[0] != correct_answer:
            if correct_answer in options:
                options.remove(correct_answer)
            options.insert(0, correct_answer)
            data["options"] = options[:4]
        
        return GeneratedQuestion(
            question=data.get("question", ""),
            answer=data.get("answer", ""),
            options=data.get("options", []),
            correct_answers=data.get("correct_answers", [data.get("answer", "")]),
            hint=data.get("hint", ""),
            explanation=data.get("explanation", ""),
            difficulty=data.get("difficulty", "easy"),
            question_type=data.get("question_type", "multiple_choice"),
        )
    
    async def generate(
        self,
        subject: str,
        topic: str,
        subtopic: str,
        difficulty: "QuestionDifficulty | str" = QuestionDifficulty.EASY,
        question_type: Literal["multiple_choice", "fill_blank", "true_false", "open_ended"] = "multiple_choice",
        grade: int = 1,
        temperature: float = 0.9,
        session_id: str = None,
        validate: bool = True,
    ) -> GeneratedQuestion:
        """
        Generate a question with validation.
        
        Args:
            subject: The subject area
            topic: The topic
            subtopic: The subtopic
            difficulty: Question difficulty
            question_type: Type of question
            grade: Student grade level
            temperature: LLM temperature
            session_id: Session ID for tracking uniqueness
            validate: Whether to validate for uniqueness
        
        Returns:
            GeneratedQuestion that has been validated for uniqueness
        """
        result = await self.run(
            user_input=f"Generate a {difficulty} {question_type} question about {subtopic}",
            session_id=session_id,
            metadata={
                "subject": subject,
                "topic": topic,
                "subtopic": subtopic,
                "difficulty": difficulty,
                "grade": grade,
                "question_type": question_type,
                "temperature": temperature,
                "session_id": session_id or "default",
                "validate": validate,
            }
        )
        
        if result.success:
            return result.output
        else:
            raise Exception(result.error or "Failed to generate question")
    
    async def generate_batch(
        self,
        subject: str,
        topic_distribution: List[Tuple[str, str, int]],  # [(topic, subtopic, count), ...]
        difficulty_distribution: List[str],
        grade: int = 1,
        question_type: str = "multiple_choice",
        session_id: str = None,
    ) -> List[GeneratedQuestion]:
        """
        Generate multiple questions in a single LLM call for better diversity.
        
        This is much more efficient than generating one-at-a-time because:
        1. LLM can ensure variety across all questions in one context
        2. Fewer API calls = lower cost and faster execution  
        3. Avoids retry loops from similar sequential questions
        
        Args:
            subject: The subject area
            topic_distribution: List of (topic, subtopic, count) tuples
            difficulty_distribution: List of difficulties matching total count
            grade: Student grade level
            question_type: Type of questions
            session_id: Session ID for validation tracking
            
        Returns:
            List of Gener

atedQuestion objects
        """
        # Build detailed prompt for batch generation
        total_questions = sum(count for _, _, count in topic_distribution)
        
        # Build topic breakdown string
        topic_breakdown = "\n".join([
            f"  - {topic} ({subtopic}): {count} questions"
            for topic, subtopic, count in topic_distribution
        ])
        
        # Build difficulty breakdown
        diff_counts = {}
        for d in difficulty_distribution:
            diff_counts[d] = diff_counts.get(d, 0) + 1
        difficulty_breakdown = ", ".join([f"{count} {diff}" for diff, count in diff_counts.items()])
        
        batch_prompt = f"""Generate {total_questions} COMPLETELY UNIQUE multiple-choice questions for Grade {grade} {subject}.

TOPIC DISTRIBUTION (must follow exactly):
{topic_breakdown}

DIFFICULTY DISTRIBUTION: {difficulty_breakdown}

CRITICAL REQUIREMENTS FOR DIVERSITY:
1. **Different Concepts**: Each question must test a DIFFERENT concept/skill
2. **Different Numbers**: Use varied numbers/values (avoid similar patterns)
3. **Different Contexts**: Use different real-world scenarios and examples
4. **Different Question Formats**: Vary how questions are asked
5. **Equal Weightage**: Distribute questions evenly across topics as specified above

QUALITY STANDARDS:
- All answers must be mathematically/factually correct
- Options should be plausible but clearly distinct
- Age-appropriate vocabulary for Grade {grade}
- Clear, unambiguous questions

Return a JSON array of {total_questions} questions in this EXACT format:
[
  {{
    "question": "question text here?",
    "answer": "correct answer",
    "options": ["correct answer", "option 2", "option 3", "option 4"],
    "hint": "helpful hint",
    "explanation": "why this answer is correct",
    "difficulty": "easy/medium/hard",
    "topic": "topic name",
    "subtopic": "subtopic name"
  }},
  ... ({total_questions} total)
]"""

        try:
            # Use the LLM to generate batch (returns parsed JSON directly)
            response = await self.llm.generate_json(
                prompt=batch_prompt,
                system_prompt=self.SYSTEM_PROMPT,
                context={"batch_mode": True, "total_questions": total_questions},
                agent_name=self.name,
            )
            
            # Handle response - it might be a list already or need parsing
            import json
            import re
            
            if isinstance(response, list):
                questions_data = response
            elif isinstance(response, dict) and "questions" in response:
                questions_data = response["questions"]
            elif isinstance(response, str):
                # Try to extract JSON array
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    questions_data = json.loads(json_match.group(0))
                else:
                    raise ValueError("Could not find JSON array in response")
            else:
                # Assume it's already a valid structure
                questions_data = [response] if isinstance(response, dict) else []
            
            # Normalize and create GeneratedQuestion objects
            questions = []
            for q_data in questions_data:
                normalized = self._normalize_question(q_data)
                questions.append(normalized)
            
            # Validate batch for duplicates AND answer correctness
            seen_hashes = set()
            unique_questions = []
            
            for q in questions:
                q_hash = hash(q.question.lower().strip())
                if q_hash not in seen_hashes:
                    seen_hashes.add(q_hash)
                    
                    # ============================================================
                    # CRITICAL: Verify answer correctness for math questions
                    # LLMs often make place value and arithmetic errors!
                    # ============================================================
                    try:
                        answer_result = self.validator.verify_answer(
                            q.question, 
                            q.answer, 
                            subject
                        )
                        
                        if not answer_result.is_correct and answer_result.expected_answer:
                            # Fix the wrong answer with the correct one
                            print(f"⚠️ Answer correction: '{q.answer}' → '{answer_result.expected_answer}' for: {q.question[:50]}...")
                            q.answer = answer_result.expected_answer
                            q.correct_answers = [answer_result.expected_answer]
                            
                            # Also fix in options (replace wrong answer with correct)
                            if q.options:
                                try:
                                    wrong_idx = q.options.index(answer_result.provided_answer)
                                    q.options[wrong_idx] = answer_result.expected_answer
                                except ValueError:
                                    # Wrong answer not in options, insert at first position
                                    q.options[0] = answer_result.expected_answer
                    except Exception as vp_err:
                        print(f"Answer verification skipped: {vp_err}")
                    
                    unique_questions.append(q)
            
            return unique_questions
            
        except Exception as e:
            print(f"Batch generation error: {e}")
            raise Exception(f"Failed to generate question batch: {str(e)}")

    
    def clear_session(self, session_id: str) -> None:
        """Clear question history for a session."""
        if self._validator:
            self.validator.clear_session(session_id)


# Singleton instance for backward compatibility
examiner_agent = ExaminerAgent()

# Alias for backward compatibility with old imports
question_generator = examiner_agent

