"""Unit tests for src/monitoring/cache_manager.py"""

import pytest
from src.monitoring.cache_manager import CacheManager


@pytest.fixture()
def cache():
    """Fresh CacheManager with small max_size for eviction testing."""
    return CacheManager(max_size=5, ttl_seconds=60)


# Basic get / set
class TestCacheGetSet:
    def test_cache_miss_returns_none(self, cache):
        result = cache.get("translation", "hello world")
        assert result is None

    def test_set_and_get_enabled_agent(self, cache):
        cache.set("translation", "hello", "hola")
        result = cache.get("translation", "hello")
        assert result == "hola"

    def test_disabled_agent_always_misses(self, cache):
        """diagnosis caching is disabled in agent_cache_config."""
        cache.set("diagnosis", "input", "output")
        assert cache.get("diagnosis", "input") is None

    def test_different_inputs_produce_different_keys(self, cache):
        cache.set("translation", "hello", "hola")
        cache.set("translation", "goodbye", "adios")
        assert cache.get("translation", "hello") == "hola"
        assert cache.get("translation", "goodbye") == "adios"

    def test_overwrite_same_key(self, cache):
        cache.set("translation", "hello", "hola")
        cache.set("translation", "hello", "salut")
        assert cache.get("translation", "hello") == "salut"


# TTL expiry
class TestCacheTTL:
    def test_expired_entry_returns_none(self, cache):
        cache.set("translation", "hi", "hola")
        # Manually back-date the cache entry
        key = list(cache._cache.keys())[0]
        value, _, access_count = cache._cache[key]
        from datetime import datetime, timedelta

        cache._cache[key] = (
            value,
            datetime.now() - timedelta(seconds=7300),
            access_count,
        )

        result = cache.get("translation", "hi")
        assert result is None

    def test_fresh_entry_is_returned(self, cache):
        cache.set("tts", "speak this", b"audio_bytes")
        result = cache.get("tts", "speak this")
        assert result == b"audio_bytes"


# Stats
class TestCacheStats:
    def test_initial_stats(self, cache):
        stats = cache.get_stats()
        assert stats["total_entries"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0

    def test_hit_increments_counter(self, cache):
        cache.set("translation", "data", "result")
        cache.get("translation", "data")
        stats = cache.get_stats()
        assert stats["hits"] == 1

    def test_miss_increments_counter(self, cache):
        cache.get("translation", "non_existent")
        stats = cache.get_stats()
        assert stats["misses"] == 1

    def test_hit_rate_calculation(self, cache):
        cache.set("translation", "a", "1")
        cache.get("translation", "a")  # hit
        cache.get("translation", "b")  # miss
        stats = cache.get_stats()
        assert stats["hit_rate"] == pytest.approx(0.5, abs=0.01)

    def test_memory_utilization_in_stats(self, cache):
        cache.set("translation", "x", "y")
        stats = cache.get_stats()
        assert "memory_usage" in stats
        assert stats["memory_usage"]["utilization"] == pytest.approx(1 / 5)


# Clear agent cache
class TestClearAgentCache:
    def test_clears_only_target_agent_entries(self, cache):
        cache.set("translation", "a", "1")
        cache.set("translation", "b", "2")
        cache.set("tts", "c", "3")
        cache.clear_agent_cache("translation")
        assert cache.get("translation", "a") is None
        assert cache.get("translation", "b") is None
        # tts entry must survive
        assert cache.get("tts", "c") == "3"

    def test_clear_nonexistent_agent_does_not_raise(self, cache):
        cache.clear_agent_cache("nonexistent_agent")  # should not raise


# LRU eviction
class TestLRUEviction:
    def test_evicts_lru_when_full(self, cache):
        """With max_size=5 and translation TTL=7200s, fill 5 entries then add a 6th."""
        for i in range(5):
            cache.set("translation", f"key_{i}", f"val_{i}")

        # All 5 should be cached
        assert cache.get_stats()["total_entries"] == 5

        # Adding a 6th triggers eviction of the LRU entry (key_0)
        cache.set("translation", "key_5", "val_5")
        assert cache.get_stats()["total_entries"] == 5
        assert cache.evictions == 1

    def test_recently_accessed_entry_survives_eviction(self, cache):
        for i in range(4):
            cache.set("translation", f"key_{i}", f"val_{i}")

        # Access key_0 to make it recently used
        cache.get("translation", "key_0")

        # Fill remaining slot then force eviction
        cache.set("translation", "key_4", "val_4")
        cache.set("translation", "key_5", "val_5")  # evicts LRU (key_1)

        # key_0 was accessed recently so it should still be there
        assert cache.get("translation", "key_0") is not None
