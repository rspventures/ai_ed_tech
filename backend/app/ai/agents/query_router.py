from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState

class Route(BaseModel):
    """Routing decision for a user query."""
    type: Literal["META", "DETAIL", "HYBRID"] = Field(
        ..., 
        description="The type of query. 'META' for high-level summaries/syllabi/topics. 'DETAIL' for specific facts/questions. 'HYBRID' if unsure."
    )
    rewritten_query: Optional[str] = Field(
        None, 
        description="An optional rewritten version of the query to improve retrieval (e.g. expanding keywords)."
    )
    reasoning: str = Field(
        default="No reasoning provided",
        description="Brief explanation of the routing decision."
    )

class QueryRouterAgent(BaseAgent):
    """
    Agent responsible for analyzing user queries and routing them 
    to the appropriate retrieval strategy (Meta-Chunk vs Content-Chunk).
    """
    
    name = "QueryRouter"
    description = "Routes queries to appropriate retrieval strategies"
    version = "1.0.0"
    
    def __init__(self):
        super().__init__()

    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """Simple pass-through plan - routing happens in execute."""
        return {"action": "route", "query": context.user_input}

    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """
        Analyze the query and decide on a routing strategy.
        """
        query = plan.get("query", context.user_input)
        
        router_prompt = f"""Analyze the following user query for an educational RAG system.

Classify the query into one of three types:
1. META: High-level questions about document structure, syllabus, topics, main ideas, or summaries.
   Examples: "What is this document about?", "What is the syllabus?", "List the chapters", "Summarize the text".
   
2. DETAIL: Specific questions asking for facts, definitions, or explanations of specific concepts.
   Examples: "What is the formula for gravity?", "Who is the main character?", "Explain photosynthesis".
   
3. HYBRID: Queries that might require both high-level context and specific details, or are ambiguous.

User Query: "{query}"

Respond with a JSON object containing these EXACT fields:
{{
  "type": "META" or "DETAIL" or "HYBRID",
  "reasoning": "Brief explanation of why you chose this type",
  "rewritten_query": "Optional improved search query or null"
}}"""
        
        try:
            # Use generate_json for structured output
            response_data = await self.llm.generate_json(
                prompt=router_prompt,
                system_prompt="You are a query routing assistant. Always respond with valid JSON containing 'type', 'reasoning', and 'rewritten_query' fields.",
                agent_name=self.name,
            )
            
            # Ensure reasoning has a default if missing
            if "reasoning" not in response_data or not response_data.get("reasoning"):
                response_data["reasoning"] = "Query classification based on content analysis"
            
            # Parse into Route model
            route = Route.model_validate(response_data)
            
            return AgentResult(
                success=True,
                output=route,
                state=AgentState.COMPLETED
            )
            
        except Exception as e:
            print(f"[QueryRouter] Routing failed: {e}")
            # Fallback to HYBRID if routing fails
            return AgentResult(
                success=True,
                output=Route(type="HYBRID", reasoning=f"Fallback due to error: {str(e)}", rewritten_query=query),
                state=AgentState.COMPLETED
            )
