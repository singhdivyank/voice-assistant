"""Test configuration and fixtures"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from src.api.main import app
from src.core.diagnosis import DiagnosisSession, PatientInfo
from src.config.settings import Gender
from src.services.session_store import InMemorySessionStore


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_session_store():
    """Create mock session store"""
    return InMemorySessionStore()


@pytest.fixture
def sample_patient():
    """Create sample patient"""
    return PatientInfo(age=35, gender=Gender.MALE)


@pytest.fixture
def sample_session(sample_patient):
    """Create sample diagnosis session"""
    return DiagnosisSession(
        session_id="test-session-123",
        patient=sample_patient,
        initial_complaint="I have a headache for 3 days"
    )