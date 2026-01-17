"""
AI Tutor Platform - Graph Store Service
Manages Neo4j graph database for entity relationships and Graph RAG.
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio

from app.core.config import settings


@dataclass
class Entity:
    """An entity extracted from document content."""
    name: str
    entity_type: str  # CONCEPT, TOPIC, PERSON, TERM, etc.
    document_id: str
    chunk_id: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


@dataclass
class Relationship:
    """A relationship between two entities."""
    source_name: str
    target_name: str
    relationship_type: str  # RELATED_TO, PART_OF, CAUSES, PREREQUISITE, etc.
    weight: float = 1.0
    properties: Optional[Dict[str, Any]] = None


class GraphStore:
    """
    Neo4j Graph Store for Graph RAG.
    
    Stores entities and relationships extracted from documents,
    enabling multi-hop reasoning and knowledge graph queries.
    """
    
    def __init__(self):
        self._driver = None
        self._available = False
    
    async def _get_driver(self):
        """Lazy initialization of Neo4j driver with timeout."""
        if self._driver is None:
            try:
                from neo4j import AsyncGraphDatabase
                
                self._driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                )
                # Test connection with timeout to prevent hanging
                async def test_connection():
                    async with self._driver.session() as session:
                        await session.run("RETURN 1")
                
                await asyncio.wait_for(test_connection(), timeout=5.0)
                self._available = True
                print("[GraphStore] Connected to Neo4j")
            except asyncio.TimeoutError:
                print("[GraphStore] Neo4j connection timed out (5s)")
                self._available = False
                if self._driver:
                    await self._driver.close()
                self._driver = None
            except Exception as e:
                print(f"[GraphStore] Neo4j connection failed: {e}")
                self._available = False
                self._driver = None
        
        return self._driver
    
    async def is_available(self) -> bool:
        """Check if Neo4j is available."""
        await self._get_driver()
        return self._available
    
    async def close(self):
        """Close the Neo4j driver."""
        if self._driver:
            await self._driver.close()
            self._driver = None
    
    async def add_entity(self, entity: Entity) -> bool:
        """
        Add an entity to the graph.
        
        Creates or merges an entity node with its properties.
        """
        driver = await self._get_driver()
        if not driver:
            return False
        
        try:
            async with driver.session() as session:
                query = """
                MERGE (e:Entity {name: $name})
                ON CREATE SET 
                    e.entity_type = $entity_type,
                    e.document_id = $document_id,
                    e.chunk_id = $chunk_id,
                    e.created_at = datetime(),
                    e.properties = $properties
                ON MATCH SET
                    e.document_ids = CASE 
                        WHEN $document_id IN coalesce(e.document_ids, [e.document_id]) 
                        THEN coalesce(e.document_ids, [e.document_id])
                        ELSE coalesce(e.document_ids, [e.document_id]) + $document_id
                    END
                RETURN e
                """
                await session.run(
                    query,
                    name=entity.name.lower(),
                    entity_type=entity.entity_type,
                    document_id=entity.document_id,
                    chunk_id=entity.chunk_id,
                    properties=entity.properties or {},
                )
                return True
        except Exception as e:
            print(f"[GraphStore] Failed to add entity: {e}")
            return False
    
    async def add_relationship(self, relationship: Relationship) -> bool:
        """
        Add a relationship between two entities.
        
        Creates entities if they don't exist, then adds the relationship.
        """
        driver = await self._get_driver()
        if not driver:
            return False
        
        try:
            async with driver.session() as session:
                query = """
                MERGE (source:Entity {name: $source_name})
                MERGE (target:Entity {name: $target_name})
                MERGE (source)-[r:RELATES_TO {type: $rel_type}]->(target)
                ON CREATE SET 
                    r.weight = $weight,
                    r.created_at = datetime()
                ON MATCH SET
                    r.weight = r.weight + $weight
                RETURN r
                """
                await session.run(
                    query,
                    source_name=relationship.source_name.lower(),
                    target_name=relationship.target_name.lower(),
                    rel_type=relationship.relationship_type,
                    weight=relationship.weight,
                )
                return True
        except Exception as e:
            print(f"[GraphStore] Failed to add relationship: {e}")
            return False
    
    async def add_entities_batch(
        self, 
        entities: List[Entity],
        relationships: List[Relationship],
    ) -> Tuple[int, int]:
        """
        Add multiple entities and relationships in a batch.
        
        Returns:
            Tuple of (entities_added, relationships_added)
        """
        entities_added = 0
        relationships_added = 0
        
        for entity in entities:
            if await self.add_entity(entity):
                entities_added += 1
        
        for rel in relationships:
            if await self.add_relationship(rel):
                relationships_added += 1
        
        return entities_added, relationships_added
    
    async def find_related_entities(
        self,
        entity_names: List[str],
        max_hops: int = 2,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Find entities related to the given entities within max_hops.
        
        Args:
            entity_names: Starting entity names
            max_hops: Maximum relationship hops to traverse
            limit: Maximum results to return
            
        Returns:
            List of related entities with relationship path
        """
        driver = await self._get_driver()
        if not driver:
            return []
        
        try:
            async with driver.session() as session:
                # Normalize names
                names = [n.lower() for n in entity_names]
                
                query = f"""
                MATCH (start:Entity)
                WHERE start.name IN $names
                MATCH path = (start)-[*1..{max_hops}]-(related:Entity)
                WHERE NOT related.name IN $names
                WITH related, 
                     min(length(path)) as distance,
                     collect(DISTINCT start.name) as connected_to
                RETURN related.name as name,
                       related.entity_type as entity_type,
                       related.document_id as document_id,
                       distance,
                       connected_to
                ORDER BY distance, related.name
                LIMIT $limit
                """
                result = await session.run(query, names=names, limit=limit)
                records = await result.data()
                
                return [
                    {
                        "name": r["name"],
                        "entity_type": r.get("entity_type"),
                        "document_id": r.get("document_id"),
                        "distance": r["distance"],
                        "connected_to": r["connected_to"],
                    }
                    for r in records
                ]
        except Exception as e:
            print(f"[GraphStore] Failed to find related entities: {e}")
            return []
    
    async def get_document_entities(
        self,
        document_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all entities from a specific document."""
        driver = await self._get_driver()
        if not driver:
            return []
        
        try:
            async with driver.session() as session:
                query = """
                MATCH (e:Entity)
                WHERE e.document_id = $document_id 
                   OR $document_id IN coalesce(e.document_ids, [])
                RETURN e.name as name, 
                       e.entity_type as entity_type,
                       e.chunk_id as chunk_id
                ORDER BY e.name
                """
                result = await session.run(query, document_id=document_id)
                records = await result.data()
                return records
        except Exception as e:
            print(f"[GraphStore] Failed to get document entities: {e}")
            return []
    
    async def delete_document_entities(self, document_id: str) -> bool:
        """Delete all entities associated with a document."""
        driver = await self._get_driver()
        if not driver:
            return False
        
        try:
            async with driver.session() as session:
                # Remove document from entity's document_ids or delete if only source
                query = """
                MATCH (e:Entity)
                WHERE e.document_id = $document_id
                DETACH DELETE e
                """
                await session.run(query, document_id=document_id)
                return True
        except Exception as e:
            print(f"[GraphStore] Failed to delete document entities: {e}")
            return False


# Singleton instance
_graph_store: Optional[GraphStore] = None


def get_graph_store() -> GraphStore:
    """Get or create the graph store singleton."""
    global _graph_store
    if _graph_store is None:
        _graph_store = GraphStore()
    return _graph_store
