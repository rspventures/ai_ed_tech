"""
AI Tutor Platform - Flashcard Agent
Generates flashcard decks for subtopics using the Plan-Execute pattern.

Per INSTRUCTIONS.md, this agent:
- Extends BaseAgent for automatic Safety Pipeline and Observability
- Uses Plan-Execute pattern
- Outputs structured JSON matching FlashcardDeckContent schema
"""
from typing import Any, Dict

from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.ai.core.telemetry import get_tracer


class FlashcardAgent(BaseAgent):
    """
    The Flashcard Generator Agent 🃏
    
    Generates comprehensive flashcard decks for any subtopic with:
    - 10-15 flashcards per deck
    - Grade-appropriate language
    - Difficulty levels (easy, medium, hard)
    
    Uses the Plan-Execute pattern per INSTRUCTIONS.md.
    Safety and Observability are automatically applied via BaseAgent.
    """
    
    name = "FlashcardAgent"
    description = "Generates flashcard decks with 10-15 cards per subtopic"
    version = "1.0.0"
    
    # Age ranges by grade
    AGE_RANGES = {
        1: "6-7", 2: "7-8", 3: "8-9", 4: "9-10",
        5: "10-11", 6: "11-12", 7: "12-13",
        8: "13-14", 9: "14-15", 10: "15-16",
    }
    
    SYSTEM_PROMPT = """You are an expert flashcard creator for students.
Your goal is to create COMPREHENSIVE flashcard decks that help students memorize key concepts.

Create flashcards about:
- Subject: {subject}
- Topic: {topic}
- Subtopic: {subtopic}
- Grade Level: {grade} (ages {age_range})

FLASHCARD RULES:
1. Create EXACTLY 10-15 flashcards
2. Cover ALL key terms, definitions, and concepts
3. Use grade-appropriate language
4. Front side: Question or term (keep SHORT)
5. Back side: Answer or definition (clear and concise)
6. Assign difficulty: "easy", "medium", or "hard"

DIFFICULTY GUIDELINES:
- easy: Basic definitions, simple facts
- medium: Application, examples, cause-effect
- hard: Complex relationships, comparisons, synthesis

OUTPUT FORMAT (JSON only, no markdown):
{{
    "title": "Flashcards: [Subtopic Name]",
    "description": "Master key concepts about [topic description]",
    "cards": [
        {{"front": "What is X?", "back": "X is...", "difficulty": "easy"}},
        {{"front": "How does Y work?", "back": "Y works by...", "difficulty": "medium"}},
        {{"front": "Compare A and B", "back": "A differs from B in...", "difficulty": "hard"}},
        ... (10-15 cards total)
    ]
}}

Generate the flashcard deck now. Output ONLY valid JSON."""

    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """
        Plan the flashcard generation based on context.
        """
        metadata = context.metadata
        grade = metadata.get("grade", 5)
        
        return {
            "action": "generate_flashcards",
            "params": {
                "subject": metadata.get("subject", "General"),
                "topic": metadata.get("topic", ""),
                "subtopic": metadata.get("subtopic", ""),
                "grade": grade,
                "age_range": self.AGE_RANGES.get(grade, "6-16"),
            }
        }
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """
        Execute the flashcard generation with structured output.
        """
        tracer = get_tracer()
        
        with tracer.start_as_current_span("generate_flashcards") as span:
            try:
                params = plan["params"]
                
                span.set_attribute("flashcard.subject", params["subject"])
                span.set_attribute("flashcard.topic", params["topic"])
                span.set_attribute("flashcard.subtopic", params["subtopic"])
                span.set_attribute("flashcard.grade", params["grade"])
                
                # Generate flashcards via LLM
                response = await self.llm.generate_json(
                    prompt="Generate the flashcard deck now.",
                    system_prompt=self.SYSTEM_PROMPT,
                    context=params,
                    agent_name=self.name,
                )
                
                # Validate and normalize response
                if "cards" not in response:
                    response["cards"] = []
                
                if "title" not in response:
                    response["title"] = f"Flashcards: {params['subtopic']}"
                
                if "description" not in response:
                    response["description"] = f"Master key concepts about {params['subtopic']}"
                
                # Ensure all cards have difficulty
                for card in response.get("cards", []):
                    if "difficulty" not in card:
                        card["difficulty"] = "medium"
                
                # Log observability
                span.set_attribute("flashcard.card_count", len(response["cards"]))
                
                return AgentResult(
                    success=True,
                    output=response,
                    state=AgentState.COMPLETED,
                    metadata={"params": params, "card_count": len(response["cards"])},
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
        Convenience method for generating a flashcard deck.
        
        Returns the raw flashcard content dict matching FlashcardDeckContent schema.
        """
        result = await self.run(
            user_input=f"Generate flashcards about {subtopic}",
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
            raise Exception(result.error or "Failed to generate flashcards")


# Singleton instance
flashcard_agent = FlashcardAgent()
