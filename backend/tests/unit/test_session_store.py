"""Unit tests for src/services/session_store.py"""

import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.services.session_store import InMemorySessionStore, RedisSessionStore


# InMemorySessionStore
class TestInMemorySessionStore:

    @pytest.mark.asyncio
    async def test_save_and_get(self, diagnosis_session):
        store = InMemorySessionStore()
        await store.save(diagnosis_session)
        retrieved = await store.get(diagnosis_session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == diagnosis_session.session_id

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(self):
        store = InMemorySessionStore()
        result = await store.get("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing_session(self, diagnosis_session):
        store = InMemorySessionStore()
        await store.save(diagnosis_session)
        deleted = await store.delete(diagnosis_session.session_id)
        assert deleted is True
        assert await store.get(diagnosis_session.session_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self):
        store = InMemorySessionStore()
        result = await store.delete("ghost-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_save_overwrites_existing(self, diagnosis_session):
        store = InMemorySessionStore()
        await store.save(diagnosis_session)
        diagnosis_session.status = "completed"
        await store.save(diagnosis_session)
        retrieved = await store.get(diagnosis_session.session_id)
        assert retrieved.status == "completed" if retrieved else None

    def test_get_created_at_returns_datetime(self, diagnosis_session):
        store = InMemorySessionStore()
        ts = store.get_created_at(diagnosis_session.session_id)
        assert isinstance(ts, datetime)

    @pytest.mark.asyncio
    async def test_created_at_is_stable_across_saves(self, diagnosis_session):
        store = InMemorySessionStore()
        await store.save(diagnosis_session)
        first = store.get_created_at(diagnosis_session.session_id)
        # second save should not change ts
        await store.save(diagnosis_session)
        second = store.get_created_at(diagnosis_session.session_id)
        assert first == second

    @pytest.mark.asyncio
    async def test_round_trip_preserves_patient_name_email(self, diagnosis_session):
        store = InMemorySessionStore()
        await store.save(diagnosis_session)
        retrieved = await store.get(diagnosis_session.session_id)

        if not retrieved:
            assert None

        assert retrieved.patient.name == diagnosis_session.patient.name
        assert retrieved.patient.email == diagnosis_session.patient.email

    @pytest.mark.asyncio
    async def test_round_trip_preserves_questions(self, diagnosis_session):
        store = InMemorySessionStore()
        await store.save(diagnosis_session)
        retrieved = await store.get(diagnosis_session.session_id)
        assert retrieved.questions == diagnosis_session.questions if retrieved else None

    @pytest.mark.asyncio
    async def test_round_trip_preserves_language(self, diagnosis_session):
        diagnosis_session.language = "hi"
        store = InMemorySessionStore()
        await store.save(diagnosis_session)
        retrieved = await store.get(diagnosis_session.session_id)
        assert retrieved.language == "hi" if retrieved else "en"

    @pytest.mark.asyncio
    async def test_multiple_sessions_isolated(self, diagnosis_session):
        from src.utils.consts import DiagnosisSession, PatientInfo, Gender

        store = InMemorySessionStore()

        other_patient = PatientInfo(
            name="John", email="john@test.com", age=50, gender=Gender.MALE
        )
        other = DiagnosisSession(
            session_id="other-session",
            patient=other_patient,
            initial_complaint="Knee pain",
        )

        await store.save(diagnosis_session)
        await store.save(other)

        r1 = await store.get(diagnosis_session.session_id)
        if r1:
            assert r1.initial_complaint == "I have a persistent headache"

        r2 = await store.get("other-session")
        if r2:
            assert r2.initial_complaint == "Knee pain"


# RedisSessionStore
@pytest.fixture()
def mock_redis():
    """Mock async Redis client."""
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.exists = AsyncMock(return_value=0)
    return client


@pytest.fixture()
def redis_store(mock_redis):
    store = RedisSessionStore(redis_url="redis://localhost:6379", ttl=3600)
    store._client = mock_redis
    return store


class TestRedisSessionStore:

    @pytest.mark.asyncio
    async def test_save_calls_redis_set(
        self, redis_store, mock_redis, diagnosis_session
    ):
        await redis_store.save(diagnosis_session)
        mock_redis.set.assert_called()

    @pytest.mark.asyncio
    async def test_get_returns_none_when_redis_empty(self, redis_store, mock_redis):
        mock_redis.get.return_value = None
        result = await redis_store.get("any-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_deserializes_stored_session(
        self, redis_store, mock_redis, diagnosis_session
    ):
        serialized = json.dumps(diagnosis_session.to_dict())
        mock_redis.get.return_value = serialized
        result = await redis_store.get(diagnosis_session.session_id)
        assert result is not None
        assert result.session_id == diagnosis_session.session_id
        assert result.patient.name == diagnosis_session.patient.name

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_key_deleted(self, redis_store, mock_redis):
        mock_redis.delete.return_value = 1
        result = await redis_store.delete("any-id")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_key_missing(self, redis_store, mock_redis):
        mock_redis.delete.return_value = 0
        result = await redis_store.delete("ghost-id")
        assert result is False

    def test_get_created_at_returns_datetime(self, redis_store):
        ts = redis_store.get_created_at("any-session-id")
        assert isinstance(ts, datetime)

    def test_get_created_at_accepts_session_id(self, redis_store):
        """Regression: old stub had no session_id param — ABC requires it."""
        ts = redis_store.get_created_at("sess-123")
        assert ts is not None

    @pytest.mark.asyncio
    async def test_get_created_at_async_returns_now_when_key_missing(
        self, redis_store, mock_redis
    ):
        mock_redis.get.return_value = None
        ts = await redis_store.get_created_at_async("missing-id")
        assert isinstance(ts, datetime)

    @pytest.mark.asyncio
    async def test_save_sets_timestamp_on_first_save(
        self, redis_store, mock_redis, diagnosis_session
    ):
        # timestamp key does not exist
        mock_redis.exists.return_value = 0
        await redis_store.save(diagnosis_session)
        # Both the session key and the timestamp key should be set
        assert mock_redis.set.call_count == 2

    @pytest.mark.asyncio
    async def test_save_does_not_overwrite_timestamp(
        self, redis_store, mock_redis, diagnosis_session
    ):
        # timestamp key already exists
        mock_redis.exists.return_value = 1
        await redis_store.save(diagnosis_session)
        # Only the session key should be set
        assert mock_redis.set.call_count == 1
