"""
Shared pytest fixtures for unit and integration tests.

Fixture hierarchy:
  - Raw domain objects  : patient_info, diagnosis_session, completed_session
  - Schema objects      : session_create_payload, session_state
  - Store               : in_memory_store (async)
  - Mocks               : mock_llm, mock_diagnosis_service, mock_store,
                          mock_gmail_client, mock_speech_service
  - FastAPI test client : client (uses mock_store + mock_diagnosis_service)
"""

import os
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-real")


@pytest.fixture()
def patient_info():
    """Minimal PatientInfo dataclass instance."""
    from src.utils.consts import Gender, PatientInfo

    return PatientInfo(
        name="Jane Doe",
        email="jane@example.com",
        age=30,
        gender=Gender.FEMALE,
    )


@pytest.fixture()
def diagnosis_session(patient_info):
    """Active DiagnosisSession with one question ready."""
    from src.utils.consts import DiagnosisSession

    session = DiagnosisSession(
        session_id=str(uuid.uuid4()),
        patient=patient_info,
        initial_complaint="I have a persistent headache",
    )
    session.questions = [
        "How long have you had this headache?",
        "Is the pain throbbing or constant?",
        "Do you have any fever or nausea?",
    ]
    session.language = "en"
    return session


@pytest.fixture()
def completed_session(diagnosis_session):
    """DiagnosisSession with all questions answered and medication set."""
    from src.utils.consts import ConversationTurn

    diagnosis_session.conversation = [
        ConversationTurn(question=diagnosis_session.questions[0], answer="Two days"),
        ConversationTurn(question=diagnosis_session.questions[1], answer="Throbbing"),
        ConversationTurn(question=diagnosis_session.questions[2], answer="Mild nausea"),
    ]
    diagnosis_session.current_question_index = 3
    diagnosis_session.medication = "Paracetamol 500mg every 6 hours"
    diagnosis_session.status = "completed"
    return diagnosis_session


# Schema / API payload fixtures
@pytest.fixture()
def session_create_payload():
    """Valid SessionCreate request body dict."""
    return {
        "patient_name": "Jane Doe",
        "patient_email": "jane@example.com",
        "patient_age": 30,
        "patient_gender": "female",
        "language": "en",
        "initial_complaint": "I have a persistent headache",
    }


@pytest.fixture()
def session_state(diagnosis_session):
    """SessionState Pydantic model built from a DiagnosisSession."""
    from src.api.schemas import SessionState, ConversationTurnSchema

    return SessionState(
        session_id=diagnosis_session.session_id,
        status=diagnosis_session.status,
        patient_name=diagnosis_session.patient.name,
        patient_email=diagnosis_session.patient.email,
        patient_age=diagnosis_session.patient.age,
        patient_gender=diagnosis_session.patient.gender.value,
        language=diagnosis_session.language,
        initial_complaint=diagnosis_session.initial_complaint,
        questions=diagnosis_session.questions,
        conversation=[
            ConversationTurnSchema(question=t.question, answer=t.answer)
            for t in diagnosis_session.conversation
        ],
        current_question_index=diagnosis_session.current_question_index,
        medication=diagnosis_session.medication,
    )


# In-memory session store (real implementation, no mocks)
@pytest_asyncio.fixture()
async def in_memory_store():
    """Real InMemorySessionStore, fresh for each test."""
    from src.services.session_store import InMemorySessionStore

    return InMemorySessionStore()


# Lightweight mocks
@pytest.fixture()
def mock_llm():
    """Mock ChatGoogleGenerativeAI that returns a fixed string."""
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(
        content="1. How long have you had this?\n2. Any fever?\n3. Any vomiting?"
    )
    llm.ainvoke = AsyncMock(
        return_value=MagicMock(content="Paracetamol 500mg every 6 hours.")
    )
    llm.astream = AsyncMock(return_value=_async_iter(["Paracetamol ", "500mg"]))
    return llm


@pytest.fixture()
def mock_diagnosis_service(diagnosis_session):
    """Mock DiagnosisService with pre-set return values."""
    svc = MagicMock()
    svc.create_session.return_value = diagnosis_session
    svc.add_response.return_value = None
    svc.complete_session.return_value = "Paracetamol 500mg every 6 hours"
    svc.complete_session_stream = _async_iter_fn(["Paracetamol ", "500mg"])
    svc.engine = MagicMock()
    svc.engine.generate_questions.return_value = diagnosis_session.questions
    return svc


@pytest.fixture()
def mock_store(diagnosis_session):
    """Mock SessionStore with get/save/delete wired up."""
    store = MagicMock()
    store.get = AsyncMock(return_value=diagnosis_session)
    store.save = AsyncMock(return_value=None)
    store.delete = AsyncMock(return_value=True)
    store.get_created_at.return_value = datetime.now()
    return store


@pytest.fixture()
def mock_gmail_client():
    """Mock GMailMCPClient."""
    client = MagicMock()
    client.connected = True
    client.connect = AsyncMock()
    client.send_email = AsyncMock(
        return_value={
            "success": True,
            "message_id": "msg_abc123",
            "timestamp": datetime.now().isoformat(),
        }
    )
    client.read_emails = AsyncMock(return_value=[])
    return client


@pytest.fixture()
def mock_speech_service():
    """Mock SpeechService."""
    svc = MagicMock()
    svc.listen_from_file.return_value = "I have a headache"
    svc.synthesize_base64 = AsyncMock(return_value="base64audiodata==")
    return svc


# # FastAPI TestClient
# @pytest.fixture()
# def client(mock_store, mock_diagnosis_service):
#     """
#     Sync TestClient with session store and diagnosis service both mocked.
#     Patches are applied at the dependency-injection and module level so the
#     actual LLM / Redis / speech APIs are never touched.
#     """
#     from src.api.main import app
#     from src.services.session_store import get_session_store

#     app.dependency_overrides[get_session_store] = lambda: mock_store

#     with (
#         patch(
#             "src.api.routes.sessions.diagnosis_service",
#             return_value=mock_diagnosis_service,
#         ),
#         patch("src.core.crew_ai.medical_crew.MedicalCrew", MagicMock()),
#     ):
#         with TestClient(app, raise_server_exceptions=True) as c:
#             yield c

#     app.dependency_overrides.clear()


# @pytest_asyncio.fixture()
# async def async_client(mock_store, mock_diagnosis_service):
#     """Async HTTPX client for endpoints that need async assertions."""
#     from src.api.main import app
#     from src.services.session_store import get_session_store

#     app.dependency_overrides[get_session_store] = lambda: mock_store

#     with (
#         patch(
#             "src.api.routes.sessions.diagnosis_service",
#             return_value=mock_diagnosis_service,
#         ),
#         patch("src.core.crew_ai.medical_crew.MedicalCrew", MagicMock()),
#     ):
#         async with AsyncClient(app=app, base_url="http://test") as ac:
#             yield ac

#     app.dependency_overrides.clear()


# Private helpers
async def _async_gen(items):
    for item in items:
        yield item


def _async_iter(items):
    """Return an async iterator over items (for astream mocking)."""
    return _async_gen(items)


def _async_iter_fn(items):
    """Return a callable that yields items as an async generator."""

    async def _inner(*args, **kwargs):
        for item in items:
            yield item

    return _inner
