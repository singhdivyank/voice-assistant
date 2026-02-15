"""Unit tests for diagnosis service"""

from unittest.mock import patch, MagicMock

from src.core.diagnosis import (
    DiagnosisEngine, DiagnosisService, DiagnosisSession,
    PatientInfo, ConversationTurn
)
from src.config.settings import Gender
from src.utils.exceptions import DiagnosisError


class TestDiagnosisSession:
    def test_conversation_summary(self, sample_session):
        """Test conversation summary generation"""
        sample_session.conversation = [
            ConversationTurn(question="How severe is the pain?", answer="Moderate"),
            ConversationTurn(question="Any nausea?", answer="No"),
        ]
        
        summary = sample_session.conversation_summary
        
        assert "Initial complaint:" in summary
        assert "headache" in summary
        assert "How severe" in summary
        assert "Moderate" in summary

    def test_is_complete(self, sample_session):
        """Test session completion check"""
        sample_session.questions = ["Q1", "Q2", "Q3"]
        sample_session.current_question_index = 2
        
        assert not sample_session.is_complete
        
        sample_session.current_question_index = 3
        assert sample_session.is_complete

    def test_to_dict_and_from_dict(self, sample_session):
        """Test serialization/deserialization"""
        sample_session.questions = ["Q1", "Q2"]
        sample_session.medication = "Take rest"
        
        data = sample_session.to_dict()
        restored = DiagnosisSession.from_dict(data)
        
        assert restored.session_id == sample_session.session_id
        assert restored.patient.age == sample_session.patient.age
        assert restored.questions == sample_session.questions
        assert restored.medication == sample_session.medication


class TestDiagnosisEngine:
    @patch('src.core.diagnosis.genai')
    @patch('src.core.diagnosis.ChatGoogleGenerativeAI')
    def test_generate_questions(self, mock_llm_class, mock_genai):
        """Test question generation"""
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm
        
        mock_response = MagicMock()
        mock_response.content = "1. How long have you had headaches?\n2. What is the pain level?\n3. Any other symptoms?"
        
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response
        mock_llm.__or__ = MagicMock(return_value=mock_chain)
        
        engine = DiagnosisEngine()
        questions = engine.generate_questions("I have a headache")
        
        assert len(questions) <= 3
        assert all(isinstance(q, str) for q in questions)

    def test_parse_questions(self):
        """Test question parsing from LLM response"""
        engine = DiagnosisEngine.__new__(DiagnosisEngine)
        
        response = """1. How long have you experienced this?
        2. Is the pain constant or intermittent?
        3. Have you taken any medication?"""
        
        questions = engine._parse_questions(response)
        
        assert len(questions) == 3
        assert not any(q.startswith("1.") for q in questions)
