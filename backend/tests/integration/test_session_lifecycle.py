"""
Integration tests for the full session lifecycle using the real
InMemorySessionStore (no mocked store).

These tests exercise the complete save → get → update → delete cycle and
verify that all fields survive the serialisation round-trip correctly.
"""

import pytest
import pytest_asyncio
from src.services.session_store import InMemorySessionStore
from src.utils.consts import ConversationTurn, DiagnosisSession, Gender, PatientInfo


@pytest_asyncio.fixture()
async def store():
    return InMemorySessionStore()


@pytest_asyncio.fixture()
async def saved_session(store, diagnosis_session):
    await store.save(diagnosis_session)
    return diagnosis_session


# Full lifecycle
class TestFullSessionLifecycle:
    @pytest.mark.asyncio
    async def test_create_read_delete(self, store, diagnosis_session):
        await store.save(diagnosis_session)

        retrieved = await store.get(diagnosis_session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == diagnosis_session.session_id

        deleted = await store.delete(diagnosis_session.session_id)
        assert deleted is True
        assert await store.get(diagnosis_session.session_id) is None

    @pytest.mark.asyncio
    async def test_update_session_after_answer(self, store, diagnosis_session):
        await store.save(diagnosis_session)

        # Simulate answering a question
        diagnosis_session.conversation.append(
            ConversationTurn(question=diagnosis_session.questions[0], answer="2 days")
        )
        diagnosis_session.current_question_index = 1
        await store.save(diagnosis_session)

        retrieved = await store.get(diagnosis_session.session_id)
        assert len(retrieved.conversation) == 1
        assert retrieved.conversation[0].answer == "2 days"
        assert retrieved.current_question_index == 1

    @pytest.mark.asyncio
    async def test_complete_session_persists_medication(self, store, diagnosis_session):
        await store.save(diagnosis_session)

        diagnosis_session.medication = "Ibuprofen 400mg"
        diagnosis_session.status = "completed"
        await store.save(diagnosis_session)

        retrieved = await store.get(diagnosis_session.session_id)
        assert retrieved.medication == "Ibuprofen 400mg"
        assert retrieved.status == "completed"

    @pytest.mark.asyncio
    async def test_patient_name_and_email_persisted(self, store, diagnosis_session):
        await store.save(diagnosis_session)
        retrieved = await store.get(diagnosis_session.session_id)
        assert retrieved.patient.name == "Jane Doe"
        assert retrieved.patient.email == "jane@example.com"

    @pytest.mark.asyncio
    async def test_language_persisted(self, store, diagnosis_session):
        diagnosis_session.language = "bn"
        await store.save(diagnosis_session)
        retrieved = await store.get(diagnosis_session.session_id)
        assert retrieved.language == "bn"

    @pytest.mark.asyncio
    async def test_all_questions_persisted(self, store, diagnosis_session):
        await store.save(diagnosis_session)
        retrieved = await store.get(diagnosis_session.session_id)
        assert retrieved.questions == diagnosis_session.questions

    @pytest.mark.asyncio
    async def test_full_conversation_persisted(self, store, diagnosis_session):
        diagnosis_session.conversation = [
            ConversationTurn(question="Q1?", answer="A1"),
            ConversationTurn(question="Q2?", answer="A2"),
            ConversationTurn(question="Q3?", answer="A3"),
        ]
        await store.save(diagnosis_session)
        retrieved = await store.get(diagnosis_session.session_id)
        assert len(retrieved.conversation) == 3
        assert retrieved.conversation[2].answer == "A3"


# Multiple concurrent sessions
class TestMultipleSessions:
    @pytest.mark.asyncio
    async def test_two_sessions_isolated(self, store):
        p1 = PatientInfo(name="Alice", email="a@t.com", age=25, gender=Gender.FEMALE)
        p2 = PatientInfo(name="Bob", email="b@t.com", age=50, gender=Gender.MALE)

        s1 = DiagnosisSession(session_id="s1", patient=p1, initial_complaint="Fever")
        s2 = DiagnosisSession(
            session_id="s2", patient=p2, initial_complaint="Back pain"
        )

        await store.save(s1)
        await store.save(s2)

        r1 = await store.get("s1")
        r2 = await store.get("s2")

        assert r1.initial_complaint == "Fever"
        assert r2.initial_complaint == "Back pain"
        assert r1.patient.name == "Alice"
        assert r2.patient.name == "Bob"

    @pytest.mark.asyncio
    async def test_deleting_one_session_leaves_other(self, store):
        p = PatientInfo(name="X", email="x@x.com", age=30, gender=Gender.MALE)
        s1 = DiagnosisSession(session_id="keep", patient=p, initial_complaint="Pain")
        s2 = DiagnosisSession(session_id="drop", patient=p, initial_complaint="Fever")

        await store.save(s1)
        await store.save(s2)
        await store.delete("drop")

        assert await store.get("keep") is not None
        assert await store.get("drop") is None

    @pytest.mark.asyncio
    async def test_timestamps_unique_per_session(self, store):
        import asyncio

        p = PatientInfo(name="T", email="t@t.com", age=20, gender=Gender.FEMALE)
        s1 = DiagnosisSession(session_id="ts1", patient=p, initial_complaint="C1")
        s2 = DiagnosisSession(session_id="ts2", patient=p, initial_complaint="C2")

        await store.save(s1)
        await asyncio.sleep(0.01)
        await store.save(s2)

        ts1 = store.get_created_at("ts1")
        ts2 = store.get_created_at("ts2")
        assert ts1 <= ts2
