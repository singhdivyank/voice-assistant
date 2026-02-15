"""Integration tests for API endpoints"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestSessionsAPI:
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_readiness_check(self, client):
        """Test readiness check endpoint"""
        response = client.get("/ready")
        assert response.status_code == 200
        assert "status" in response.json()

    @patch('src.api.routes.sessions.diagnosis_service')
    def test_create_session(self, mock_service, client, sample_session):
        """Test session creation"""
        mock_service.create_session.return_value = sample_session
        sample_session.questions = ["Q1", "Q2", "Q3"]
        
        response = client.post("/api/v1/sessions/", json={
            "patient_age": 35,
            "patient_gender": "male",
            "language": "en",
            "initial_complaint": "I have a headache"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["patient_age"] == 35

    def test_create_session_validation_error(self, client):
        """Test session creation with invalid data"""
        response = client.post("/api/v1/sessions/", json={
            "patient_age": 150,  # Invalid age
            "patient_gender": "male",
            "language": "en",
            "initial_complaint": "test"
        })
        
        assert response.status_code == 422

    def test_get_nonexistent_session(self, client):
        """Test getting non-existent session"""
        response = client.get("/api/v1/sessions/nonexistent-id")
        assert response.status_code == 404


class TestDiagnosisAPI: