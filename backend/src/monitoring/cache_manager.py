"""Monitoring cache ttl"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.config.monitoring import telemetry

logger = logging.getLogger(__name__)


class CacheManager:
    """Intelligent caching system for agent results"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, datetime, int]] = {}
        self._access_order: List[str] = []
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.agent_cache_config = {
            "translation": {"ttl": 7200, "enabled": True},
            "qa": {"ttl": 3600, "enabled": True},
            "diagnosis": {"ttl": 1800, "enabled": False},
            "prescription": {"ttl": 900, "enabled": False},
            "tts": {"ttl": 3600, "enabled": True},
            "stt": {"ttl": 1800, "enabled": True},
        }

    def get(self, agent_name: str, input_data: Any) -> Optional[Any]:
        """Get cached result for agent execution"""

        config = self.agent_cache_config.get(agent_name, {})
        if not config.get("enabled", False):
            return None

        cache_key = self._generate_cache_key(agent_name, input_data)
        if cache_key in self._cache:
            value, timestamp, access_control = self._cache[cache_key]
            ttl = config.get("ttl", self.ttl_seconds)
            if (datetime.now() - timestamp).total_seconds() < ttl:
                self._cache[cache_key] = (value, timestamp, access_control + 1)
                self._update_access_order(cache_key)
                self.hits += 1
                telemetry.increment_counter(
                    "cache_operations",
                    attributes={"agent": agent_name, "operation": "hit"},
                )

                logger.debug("Cache hit for agent %s", agent_name)
                return value

            del self._cache[cache_key]
            if cache_key in self._access_order:
                self._access_order.remove(cache_key)

        self.misses += 1
        telemetry.increment_counter(
            "cache_operations", attributes={"agent": agent_name, "operation": "miss"}
        )

        return None

    def set(self, agent_name: str, input_data: Any, result: Any) -> None:
        """Cache result for agent execution"""

        config = self.agent_cache_config.get(agent_name, {})
        if not config.get("enabled", False):
            return

        cache_key = self._generate_cache_key(agent_name, input_data)

        if len(self._cache) >= self.max_size:
            self._evict_lru()

        self._cache[cache_key] = (result, datetime.now(), 1)
        self._update_access_order(cache_key)
        telemetry.increment_counter(
            "cache_operations", attributes={"agent": agent_name, "operation": "set"}
        )
        logger.debug("Cached result for agent %s", agent_name)

    def clear_agent_cache(self, agent_name: str) -> None:
        """Clear all cache entries for a specific agent"""

        keys_to_remove = [
            key for key, _ in self._cache.items() if key.startswith(f"{agent_name}:")
        ]
        for key in keys_to_remove:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)

        logger.info(
            "Cleared %d cache entries for agent %s", len(keys_to_remove), agent_name
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""

        total_requests = self.hits + self.misses
        hit_rate = self.hits / max(1, total_requests)
        return {
            "total_entries": len(self._cache),
            "total_requests": total_requests,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 4),
            "evictions": self.evictions,
            "memory_usage": {
                "cache_size": len(self._cache),
                "max_size": self.max_size,
                "utilization": len(self._cache) / self.max_size,
            },
        }

    def _generate_cache_key(self, agent_name: str, input_data: Any) -> str:
        """Generate cache key from agent name and input"""

        input_str = (
            json.dumps(input_data, sort_keys=True)
            if isinstance(input_data, dict)
            else str(input_data)
        )
        hash_obj = hashlib.md5(f"{agent_name}:{input_str}".encode())
        return f"{agent_name}:{hash_obj.hexdigest()[:16]}"

    def _update_access_order(self, cache_key: str) -> None:
        """Update LRU access order"""

        if cache_key in self._access_order:
            self._access_order.remove(cache_key)
        self._access_order.append(cache_key)

    def _evict_lru(self) -> None:
        """Evict least recently used cache entry"""

        if not self._access_order:
            return

        lru_key = self._access_order.pop(0)
        if lru_key in self._cache:
            del self._cache[lru_key]
            self.evictions += 1
            telemetry.increment_counter("cache_evictions")


cache_manager = CacheManager()
