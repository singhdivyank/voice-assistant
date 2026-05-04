"""
Integration tests for V1 session routes: /api/v1/sessions/*

Uses the `client` fixture from conftest (real FastAPI app with mock store +
mock diagnosis service, no LLM/Redis/speech calls).
"""

from unittest.mock import AsyncMock


# POST /api/v1/sessions/  — create_session
class TestCreateSession:
    def test_creates_session_with_complaint(self, client, session_create_payload):
        resp = client.post("/api/v1/sessions/", json=session_create_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["patient_name"] == "Jane Doe"
        assert data["patient_email"] == "jane@example.com"
        assert data["patient_age"] == 30
        assert data["initial_complaint"] == "I have a persistent headache"

    def test_creates_session_without_complaint(self, client, session_create_payload):
        session_create_payload["initial_complaint"] = ""
        resp = client.post("/api/v1/sessions/", json=session_create_payload)
        assert resp.status_code == 200

    def test_returns_questions_list(self, client, session_create_payload):
        resp = client.post("/api/v1/sessions/", json=session_create_payload)
        assert resp.status_code == 200
        assert isinstance(resp.json()["questions"], list)

    def test_rejects_invalid_age(self, client, session_create_payload):
        session_create_payload["patient_age"] = 200
        resp = client.post("/api/v1/sessions/", json=session_create_payload)
        assert resp.status_code == 422

    def test_rejects_missing_age(self, client, session_create_payload):
        del session_create_payload["patient_age"]
        resp = client.post("/api/v1/sessions/", json=session_create_payload)
        assert resp.status_code == 422

    def test_default_language_is_en(self, client, session_create_payload):
        del session_create_payload["language"]
        resp = client.post("/api/v1/sessions/", json=session_create_payload)
        assert resp.status_code == 200

    def test_created_at_is_present(self, client, session_create_payload):
        resp = client.post("/api/v1/sessions/", json=session_create_payload)
        assert "created_at" in resp.json()


# GET /api/v1/sessions/{session_id}  — get_session
class TestGetSession:
    def test_returns_full_session_state(self, client, diagnosis_session):
        resp = client.get(f"/api/v1/sessions/{diagnosis_session.session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == diagnosis_session.session_id
        assert data["patient_name"] == diagnosis_session.patient.name
        assert data["patient_email"] == diagnosis_session.patient.email
        assert data["patient_age"] == diagnosis_session.patient.age
        assert isinstance(data["questions"], list)
        assert isinstance(data["conversation"], list)

    def test_returns_404_for_missing_session(self, client, mock_store):
        mock_store.get = AsyncMock(return_value=None)
        resp = client.get("/api/v1/sessions/nonexistent-id")
        assert resp.status_code == 404

    def test_returns_medication_when_completed(
        self, client, mock_store, completed_session
    ):
        mock_store.get = AsyncMock(return_value=completed_session)
        resp = client.get(f"/api/v1/sessions/{completed_session.session_id}")
        assert resp.status_code == 200
        assert resp.json()["medication"] is not None


# POST /api/v1/sessions/{session_id}/answer  — submit_answer
class TestSubmitAnswer:
    def test_accepts_alid_answer(self, client, diagnosis_session):
        payload = {"question_index": 0, "answer": "Two days"}
        resp = client.post(
            f"/api/v1/sessions/{diagnosis_session.session_id}/answer", json=payload
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert "current_index" in data
        assert "is_complete" in data

    def test_returns_next_question(self, client, diagnosis_session):
        payload = {"question_index": 0, "answer": "Yes"}
        resp = client.post(
            f"/api/v1/sessions/{diagnosis_session.session_id}/answer", json=payload
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "next_question" in data

    def test_returns_404_for_missing_session(self, client, mock_store):
        mock_store.get = AsyncMock(return_value=None)
        payload = {"question_index": 0, "answer": "Yes"}
        resp = client.post("/api/v1/sessions/ghost/answer", json=payload)
        assert resp.status_code == 404

    def test_returns_400_for_completed_session(
        self, client, mock_store, completed_session
    ):
        mock_store.get = AsyncMock(return_value=completed_session)
        payload = {"question_index": 0, "answer": "Yes"}
        resp = client.post(
            f"/api/v1/sessions/{completed_session.session_id}/answer", json=payload
        )
        assert resp.status_code == 400

    def test_rejects_negative_question_index(self, client, diagnosis_session):
        payload = {"question_index": -1, "answer": "Yes"}
        resp = client.post(
            f"/api/v1/sessions/{diagnosis_session.session_id}/answer", json=payload
        )
        assert resp.status_code == 422

    def test_rejects_empty_answer(self, client, diagnosis_session):
        payload = {"question_index": 0, "answer": ""}
        resp = client.post(
            f"/api/v1/sessions/{diagnosis_session.session_id}/answer", json=payload
        )
        assert resp.status_code == 422


# POST /api/v1/sessions/{session_id}/complete  — complete_session
class TestCompleteSession:
    def test_completes_session_and_returns_medication(self, client, diagnosis_session):
        resp = client.post(f"/api/v1/sessions/{diagnosis_session.session_id}/complete")
        assert resp.status_code == 200
        data = resp.json()
        assert "medication" in data
        assert data["session_id"] == diagnosis_session.session_id

    def test_returns_cached_medication_if_already_completed(
        self, client, mock_store, completed_session
    ):
        mock_store.get = AsyncMock(return_value=completed_session)
        resp = client.post(f"/api/v1/sessions/{completed_session.session_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["medication"] == completed_session.medication

    def test_returns_404_for_missing_session(self, client, mock_store):
        mock_store.get = AsyncMock(return_value=None)
        resp = client.post("/api/v1/sessions/ghost/complete")
        assert resp.status_code == 404

    def test_non_english_session_includes_medication_english(
        self, client, mock_store, diagnosis_session
    ):
        diagnosis_session.language = "hi"
        mock_store.get = AsyncMock(return_value=diagnosis_session)
        resp = client.post(f"/api/v1/sessions/{diagnosis_session.session_id}/complete")
        assert resp.status_code == 200
        data = resp.json()
        assert "medication_english" in data


# DELETE /api/v1/sessions/{session_id}
class TestDeleteSession:
    def test_deletes_existing_session(self, client, diagnosis_session):
        resp = client.delete(f"/api/v1/sessions/{diagnosis_session.session_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_returns_404_for_missing_session(self, client, mock_store):
        mock_store.delete = AsyncMock(return_value=False)
        resp = client.delete("/api/v1/sessions/ghost")
        assert resp.status_code == 404
