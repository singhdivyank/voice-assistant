"""
Integration tests for V2 workflow routes: /api/v2/workflow/*

medical_crew is fully mocked so no LLM, speech, or Gmail calls are made.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def mock_crew():
    """Patch medical_crew at the route module level for all tests in this file."""
    crew = MagicMock()
    crew._initialised = True
    crew.initialise = AsyncMock()
    crew.generate_welcome_audio = AsyncMock(
        return_value={
            "status": "success",
            "audio_base64": "A" * 60,
            "message": "Welcome to DocJarvis",
        }
    )
    crew.process_initial_symptom = AsyncMock(
        return_value={
            "status": "success",
            "questions": ["Q1?", "Q2?", "Q3?"],
            "questions_english": ["Q1?", "Q2?", "Q3?"],
            "session_id": "test-session",
        }
    )
    crew.process_qa_answer = AsyncMock(
        return_value={
            "status": "success",
            "answered_questions": 1,
            "total_questions": 3,
            "all_questions_answered": False,
            "next_step": "continue_qa",
        }
    )
    crew.generate_recommednations = AsyncMock(
        return_value={
            "status": "success",
            "recommendations": "Paracetamol 500mg",
            "step": "recommendations_generated",
        }
    )
    crew.generate_recommendations_audio = AsyncMock(
        return_value={
            "status": "success",
            "audio_base64": "B" * 60,
        }
    )
    crew.generate_and_review_prescriptions = AsyncMock(
        return_value={
            "status": "success",
            "prescription_generated": True,
            "review_id": "rev-001",
        }
    )
    crew.process_doctor_response = AsyncMock(
        return_value={
            "status": "success",
            "doctor_action": "APPROVED",
        }
    )

    with patch("src.api.routes.workflow_routes.medical_crew", crew):
        yield crew


# POST /api/v2/workflow/welcome-audio
class TestWelcomeAudio:
    def test_returns_audio_base64(self, client):
        resp = client.post("/api/v2/workflow/welcome-audio", data={"language": "en"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "audio_base64" in data

    def test_default_language_is_en(self, client):
        resp = client.post("/api/v2/workflow/welcome-audio", data={})
        assert resp.status_code == 200


# POST /api/v2/workflow/process-initial-symptom
class TestProcessInitialSymptom:
    def test_processes_text_complaint(self, client):
        resp = client.post(
            "/api/v2/workflow/process-initial-symptom",
            data={
                "patient_age": 30,
                "patient_gender": "female",
                "language": "en",
                "initial_complaint": "Persistent headache",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "questions" in data
        assert len(data["questions"]) == 3

    def test_auto_generates_session_id_when_not_provided(self, client):
        resp = client.post(
            "/api/v2/workflow/process-initial-symptom",
            data={"patient_age": 25, "patient_gender": "male", "language": "en"},
        )
        assert resp.status_code == 200

    def test_uses_provided_session_id(self, client):
        resp = client.post(
            "/api/v2/workflow/process-initial-symptom",
            data={
                "session_id": "my-session-001",
                "patient_age": 45,
                "patient_gender": "male",
                "language": "en",
                "initial_complaint": "Back pain",
            },
        )
        assert resp.status_code == 200

    def test_rejects_missing_age(self, client):
        resp = client.post(
            "/api/v2/workflow/process-initial-symptom",
            data={"patient_gender": "female"},
        )
        assert resp.status_code == 422


# POST /api/v2/workflow/answer-question/{session_id}
class TestAnswerQuestion:
    def test_records_answer(self, client, mock_crew):
        # Pre-populate active_sessions
        from src.api.routes.workflow_routes import active_sessions
        from src.api.schemas import SessionState

        session_state = SessionState(
            session_id="sess-qa",
            status="active",
            patient_name="Jane",
            patient_email="j@test.com",
            patient_age=30,
            patient_gender="female",
            language="en",
            initial_complaint="Headache",
            questions=["Q1?", "Q2?", "Q3?"],
            conversation=[],
            current_question_index=0,
        )
        active_sessions["sess-qa"] = session_state

        resp = client.post(
            "/api/v2/workflow/answer-question/sess-qa",
            data={"question_index": 0, "answer": "Two days"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

        # Cleanup
        active_sessions.pop("sess-qa", None)

    def test_returns_404_for_unknown_session(self, client):
        resp = client.post(
            "/api/v2/workflow/answer-question/ghost-session",
            data={"question_index": 0, "answer": "Yes"},
        )
        assert resp.status_code == 404


# POST /api/v2/workflow/generate-recommendations/{session_id}
class TestGenerateRecommendations:
    def test_generates_recommendations(self, client):
        from src.api.routes.workflow_routes import active_sessions
        from src.api.schemas import SessionState

        session_state = SessionState(
            session_id="sess-rec",
            status="active",
            patient_name="Jane",
            patient_email="j@test.com",
            patient_age=30,
            patient_gender="female",
            language="en",
            initial_complaint="Headache",
            questions=["Q1?"],
            conversation=[],
            current_question_index=1,
        )
        active_sessions["sess-rec"] = session_state

        resp = client.post("/api/v2/workflow/generate-recommendations/sess-rec")
        assert resp.status_code == 200
        assert "recommendations" in resp.json()

        active_sessions.pop("sess-rec", None)

    def test_returns_404_for_unknown_session(self, client):
        resp = client.post("/api/v2/workflow/generate-recommendations/ghost")
        assert resp.status_code == 404


# POST /api/v2/workflow/recommendations-audio
class TestRecommendationsAudio:
    def test_generates_audio(self, client):
        resp = client.post(
            "/api/v2/workflow/recommendations-audio",
            data={"recommendations": "Take paracetamol", "language": "en"},
        )
        assert resp.status_code == 200
        assert "audio_base64" in resp.json()


# GET /api/v2/workflow/session/{session_id}/status
class TestSessionStatus:
    def test_returns_session_status(self, client):
        from src.api.routes.workflow_routes import active_sessions
        from src.api.schemas import SessionState

        session_state = SessionState(
            session_id="sess-status",
            status="active",
            patient_name="Bob",
            patient_email="bob@test.com",
            patient_age=40,
            patient_gender="male",
            language="en",
            initial_complaint="Chest pain",
            questions=["Q1?", "Q2?"],
            conversation=[],
            current_question_index=0,
        )
        active_sessions["sess-status"] = session_state

        resp = client.get("/api/v2/workflow/session/sess-status/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "sess-status"
        assert "progress" in data
        assert "questions" in data

        active_sessions.pop("sess-status", None)

    def test_returns_404_for_missing_session(self, client):
        resp = client.get("/api/v2/workflow/session/ghost/status")
        assert resp.status_code == 404


# GET /api/v2/workflow/sessions/active
class TestActiveSessions:
    def test_returns_active_sessions_dict(self, client):
        resp = client.get("/api/v2/workflow/sessions/active")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_active_sessions" in data
        assert "sessions" in data


# DELETE /api/v2/workflow/session/{session_id}
class TestDeleteWorkflowSession:
    def test_deletes_existing_session(self, client):
        from src.api.routes.workflow_routes import active_sessions
        from src.api.schemas import SessionState

        session_state = SessionState(
            session_id="to-delete",
            status="active",
            patient_name="Del",
            patient_email="del@test.com",
            patient_age=30,
            patient_gender="female",
            language="en",
            initial_complaint="Pain",
            questions=[],
            conversation=[],
            current_question_index=0,
        )
        active_sessions["to-delete"] = session_state

        resp = client.delete("/api/v2/workflow/session/to-delete")
        assert resp.status_code == 200
        assert "deleted successfully" in resp.json()["message"]

    def test_returns_404_for_missing_session(self, client):
        resp = client.delete("/api/v2/workflow/session/ghost")
        assert resp.status_code == 404


# GET /api/v2/workflow/health
class TestWorkflowHealth:
    def test_returns_healthy_status(self, client):
        resp = client.get("/api/v2/workflow/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "crew_initialized" in data
