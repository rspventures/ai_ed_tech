"""
AI Tutor Platform - Entity Extractor Agent
Extracts entities and relationships from document chunks for Graph RAG.
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json

from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.services.graph_store import Entity, Relationship, get_graph_store


@dataclass
class ExtractionResult:
    """Result of entity extraction."""
    entities: List[Entity]
    relationships: List[Relationship]
    source_document_id: str
    chunks_processed: int


class EntityExtractorAgent(BaseAgent):
    """
    Entity Extraction Agent for Graph RAG.
    
    Extracts named entities and relationships from document chunks
    to build a knowledge graph that enhances retrieval.
    
    Entity Types:
    - CONCEPT: Core ideas or topics (e.g., "photosynthesis", "democracy")
    - TERM: Technical or domain-specific terms
    - PERSON: Named individuals
    - TOPIC: Broader categories or subjects
    - PREREQUISITE: Required prior knowledge
    """
    
    name = "EntityExtractorAgent"
    description = "Extracts entities and relationships for Graph RAG"
    version = "1.0.0"
    
    EXTRACTION_PROMPT = """Extract key educational concepts, terms, and their relationships from this text.

TEXT:
{text}

Return a JSON object with:
1. "entities": Array of objects with:
   - "name": The entity name (lowercase, canonical form)
   - "type": One of CONCEPT, TERM, PERSON, TOPIC, PREREQUISITE
   
2. "relationships": Array of objects with:
   - "source": Source entity name
   - "target": Target entity name  
   - "type": One of RELATED_TO, PART_OF, CAUSES, PREREQUISITE_FOR, EXAMPLE_OF, DEFINED_AS

Extract 3-8 key entities and 2-5 relationships. Focus on educational value.
Only return the JSON, no other text.

Example output:
{{
  "entities": [
    {{"name": "photosynthesis", "type": "CONCEPT"}},
    {{"name": "chlorophyll", "type": "TERM"}},
    {{"name": "sunlight", "type": "CONCEPT"}}
  ],
  "relationships": [
    {{"source": "photosynthesis", "target": "chlorophyll", "type": "PART_OF"}},
    {{"source": "sunlight", "target": "photosynthesis", "type": "PREREQUISITE_FOR"}}
  ]
}}"""

    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """Plan entity extraction."""
        chunks = context.metadata.get("chunks", [])
        document_id = context.metadata.get("document_id")
        
        if not chunks:
            return {"action": "error", "error": "No chunks provided for extraction"}
        
        if not document_id:
            return {"action": "error", "error": "document_id is required"}
        
        return {
            "action": "extract",
            "params": {
                "chunks": chunks,
                "document_id": document_id,
                "batch_size": context.metadata.get("batch_size", 3),
            }
        }
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """Execute entity extraction."""
        if plan["action"] == "error":
            return AgentResult(
                success=False,
                output=None,
                state=AgentState.ERROR,
                error=plan["error"]
            )
        
        params = plan["params"]
        chunks = params["chunks"]
        document_id = params["document_id"]
        batch_size = params["batch_size"]
        
        all_entities = []
        all_relationships = []
        
        # Process chunks in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            combined_text = "\n\n---\n\n".join(batch[:3])  # Limit context size
            
            try:
                # Extract entities and relationships
                extraction = await self._extract_from_text(
                    text=combined_text,
                    document_id=document_id,
                    chunk_index=i,
                )
                
                if extraction:
                    all_entities.extend(extraction[0])
                    all_relationships.extend(extraction[1])
                    
            except Exception as e:
                print(f"[EntityExtractor] Batch {i} extraction failed: {e}")
                continue
        
        # Store in graph database
        graph_store = get_graph_store()
        if await graph_store.is_available():
            entities_added, rels_added = await graph_store.add_entities_batch(
                entities=all_entities,
                relationships=all_relationships,
            )
            print(f"[EntityExtractor] Stored {entities_added} entities, {rels_added} relationships")
        
        result = ExtractionResult(
            entities=all_entities,
            relationships=all_relationships,
            source_document_id=document_id,
            chunks_processed=len(chunks),
        )
        
        return AgentResult(
            success=True,
            output=result,
            state=AgentState.COMPLETED,
            metadata={
                "entity_count": len(all_entities),
                "relationship_count": len(all_relationships),
            }
        )
    
    async def _extract_from_text(
        self,
        text: str,
        document_id: str,
        chunk_index: int,
    ) -> Optional[Tuple[List[Entity], List[Relationship]]]:
        """Extract entities and relationships from text using LLM."""
        try:
            response = await self.llm.generate_json(
                prompt=self.EXTRACTION_PROMPT.format(text=text[:2000]),
                system_prompt="You are an entity extraction system. Return only valid JSON.",
                agent_name=self.name,
            )
            
            if not isinstance(response, dict):
                return None
            
            # Parse entities
            entities = []
            for e in response.get("entities", []):
                if isinstance(e, dict) and "name" in e:
                    entities.append(Entity(
                        name=e.get("name", "").lower().strip(),
                        entity_type=e.get("type", "CONCEPT"),
                        document_id=document_id,
                        chunk_id=f"{document_id}:{chunk_index}",
                    ))
            
            # Parse relationships
            relationships = []
            for r in response.get("relationships", []):
                if isinstance(r, dict) and "source" in r and "target" in r:
                    relationships.append(Relationship(
                        source_name=r.get("source", "").lower().strip(),
                        target_name=r.get("target", "").lower().strip(),
                        relationship_type=r.get("type", "RELATED_TO"),
                    ))
            
            return entities, relationships
            
        except Exception as e:
            print(f"[EntityExtractor] Extraction failed: {e}")
            return None
    
    async def extract(
        self,
        chunks: List[str],
        document_id: str,
    ) -> ExtractionResult:
        """
        Convenience method to extract entities from chunks.
        
        Args:
            chunks: List of text chunks
            document_id: Document ID for linking
            
        Returns:
            ExtractionResult with entities and relationships
        """
        result = await self.run(
            user_input="Extract entities",
            metadata={
                "chunks": chunks,
                "document_id": document_id,
            }
        )
        
        if result.success:
            return result.output
        else:
            return ExtractionResult(
                entities=[],
                relationships=[],
                source_document_id=document_id,
                chunks_processed=0,
            )


# Singleton instance
entity_extractor_agent = EntityExtractorAgent()
