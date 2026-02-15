"""Session storage servis with Redis support."""

import json
import logging
from datetime import datetime
from typing import Optional

from src.core.diagnosis import DiagnosisSession
from src.config.settings import get_settings
from src.utils.consts import SessionStore

logger = logging.getLogger(__name__)
settings = get_settings()


class InMemorySessionStore(SessionStore):
    """In-memory session storage (for development)"""

    def __init__(self):
        self._sessions: dict[str, dict] = {}
        self._timestamps: dict[str, datetime] = {}
        
    async def save(self, session: DiagnosisSession) -> None:
        """Save session to memory"""
        
        if session.session_id not in self._timestamps:
            self._timestamps[session.session_id] = datetime.now()
        self._sessions[session.session_id] = session.to_dict()
        logger.debug("Saved session %s to memory", session.session_id)
    
    async def get(self, session_id: str) -> Optional[DiagnosisSession]:
        """Get session from memory"""
        
        data = self._sessions.get(session_id)
        if not data:
            return None
        return DiagnosisSession.from_dict(data)
    
    async def delete(self, session_id: str) -> bool:
        """Delete session from memory"""

        if session_id in self._sessions:
            del self._sessions[session_id]
            if session_id in self._timestamps:
                del self._timestamps[session_id]
            return True
        return False
    
    def get_created_at(self, session_id: str) -> datetime:
        """Get session creation time"""

        return self._timestamps.get(session_id, datetime.now())


class RedisSessionStore(SessionStore):
    """Redis-based session storage (for production)."""

    def __init__(self, redis_url: str, ttl: int = 3600):
        self.redis_url = redis_url
        self.ttl = ttl
        self._client = None
    
    async def _get_client(self):
        """Get Redis client"""

        if self._client is None:
            import redis.asyncio as redis
            self._client = redis.from_url(self.redis_url)
        return self._client
    
    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session"""
        return f"docjarvis:session:{session_id}"
    
    def _timestamp_key(self, session_id: str) -> str:
        """Generate Redis key for session timestamp"""
        return f"docjarvis:session:{session_id}:created"
    
    async def save(self, session: DiagnosisSession) -> None:
        """Save session to Redis"""

        client = await self._get_client()
        key = self._session_key(session.session_id)
        ts_key = self._timestamp_key(session.session_id)

        exists = await client.exists(ts_key)
        if not exists:
            await client.set(ts_key, datetime.now().isoformat(), ex=self.ttl)
        
        await client.set(key, json.dumps(session.to_dict()), ex=self.ttl)
        logger.debug("Saved session %s to Redis", session.session_id)
    
    async def get(self, session_id: str) -> Optional[DiagnosisSession]:
        """Get session from Redis"""

        client = await self._get_client()
        key = self._session_key(session_id)
        data = await client.get(key)

        if not data:
            return None
        return DiagnosisSession.from_dict(json.loads(data))
    
    async def delete(self, session_id: str) -> bool:
        """Delete session from Redis"""

        client = await self._get_client()
        key = self._session_key(session_id)
        ts_key = self._timestamp_key(session_id)
        result = await client.delete(key, ts_key)
        return result > 0
    
    def get_created_at(self) -> datetime:
        """Get session creation time"""
        return datetime.now()
    
    async def get_created_at_async(self, session_id: str) -> datetime:
        """Get session creation time (async version)"""

        client = await self._get_client()
        ts_key = self._timestamp_key(session_id)
        data = await client.get(ts_key)

        if not data:
            return datetime.now()
        return datetime.fromisoformat(data.decode('utf-8'))


_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """Get the session store instance"""

    global _store

    if _store is None:
        if settings.environment.value == 'production':
            _store = RedisSessionStore(settings.redis_url, settings.session_ttl)
        else:
            _store = InMemorySessionStore()
        logger.info("Initialized %s session store", _store.__class__.__name__)
    
    return _store
