"""
AI Tutor Platform - Agent Memory Module
Redis-backed conversation and context memory for AI Agents.
"""
import json
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import asyncio

from app.core.config import settings


class AgentMemory:
    """
    Memory management for AI Agents.
    
    Provides:
    - Short-term conversation history
    - Session state management
    - Redis-backed persistence (with in-memory fallback)
    """
    
    def __init__(
        self,
        agent_name: str,
        max_history: int = 10,
        ttl_seconds: int = 3600,  # 1 hour default
    ):
        """
        Initialize agent memory.
        
        Args:
            agent_name: Name of the agent (used as key prefix).
            max_history: Maximum number of messages to retain.
            ttl_seconds: Time-to-live for memory entries.
        """
        self.agent_name = agent_name
        self.max_history = max_history
        self.ttl_seconds = ttl_seconds
        
        self._redis = None
        self._local_store: Dict[str, Dict[str, Any]] = {}
    
    def _key(self, session_id: str, suffix: str = "history") -> str:
        """Generate a Redis key for the session."""
        return f"agent:{self.agent_name}:session:{session_id}:{suffix}"
    
    async def _get_redis(self):
        """Get Redis connection (lazy initialization)."""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = await aioredis.from_url(
                    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                    encoding="utf-8",
                    decode_responses=True,
                )
            except Exception as e:
                print(f"[AgentMemory] Redis unavailable, using local store: {e}")
                self._redis = False  # Mark as unavailable
        return self._redis if self._redis else None
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            session_id: The session identifier.
            role: Message role ('user', 'assistant', 'system').
            content: Message content.
            metadata: Optional additional metadata.
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        
        redis = await self._get_redis()
        key = self._key(session_id)
        
        if redis:
            # Use Redis
            await redis.rpush(key, json.dumps(message))
            await redis.ltrim(key, -self.max_history, -1)
            await redis.expire(key, self.ttl_seconds)
        else:
            # Use local store
            if session_id not in self._local_store:
                self._local_store[session_id] = {"history": [], "state": {}}
            
            history = self._local_store[session_id]["history"]
            history.append(message)
            
            # Trim to max_history
            if len(history) > self.max_history:
                self._local_store[session_id]["history"] = history[-self.max_history:]
    
    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the conversation history for a session.
        
        Returns:
            List of message dictionaries.
        """
        redis = await self._get_redis()
        key = self._key(session_id)
        
        if redis:
            messages = await redis.lrange(key, 0, -1)
            return [json.loads(m) for m in messages]
        else:
            if session_id in self._local_store:
                return self._local_store[session_id].get("history", [])
            return []
    
    async def set_state(
        self,
        session_id: str,
        key: str,
        value: Any,
    ) -> None:
        """
        Set a state variable for the session.
        
        Args:
            session_id: The session identifier.
            key: State key.
            value: State value (must be JSON serializable).
        """
        redis = await self._get_redis()
        state_key = self._key(session_id, "state")
        
        if redis:
            await redis.hset(state_key, key, json.dumps(value))
            await redis.expire(state_key, self.ttl_seconds)
        else:
            if session_id not in self._local_store:
                self._local_store[session_id] = {"history": [], "state": {}}
            self._local_store[session_id]["state"][key] = value
    
    async def get_state(
        self,
        session_id: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Get a state variable for the session.
        """
        redis = await self._get_redis()
        state_key = self._key(session_id, "state")
        
        if redis:
            value = await redis.hget(state_key, key)
            if value:
                return json.loads(value)
            return default
        else:
            if session_id in self._local_store:
                return self._local_store[session_id].get("state", {}).get(key, default)
            return default
    
    async def get_all_state(self, session_id: str) -> Dict[str, Any]:
        """Get all state variables for the session."""
        redis = await self._get_redis()
        state_key = self._key(session_id, "state")
        
        if redis:
            state = await redis.hgetall(state_key)
            return {k: json.loads(v) for k, v in state.items()}
        else:
            if session_id in self._local_store:
                return self._local_store[session_id].get("state", {})
            return {}
    
    async def clear_session(self, session_id: str) -> None:
        """Clear all data for a session."""
        redis = await self._get_redis()
        
        if redis:
            await redis.delete(self._key(session_id))
            await redis.delete(self._key(session_id, "state"))
        else:
            if session_id in self._local_store:
                del self._local_store[session_id]
    
    async def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        redis = await self._get_redis()
        
        if redis:
            return await redis.exists(self._key(session_id)) > 0
        else:
            return session_id in self._local_store
