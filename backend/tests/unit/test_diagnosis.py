"""Unit tests for src/core/diagnosis.py"""

import pytest
from unittest.mock import MagicMock, patch

from src.core.diagnosis import DiagnosisEngine, DiagnosisService


# DiagnosisEngine._parse_questions
class TestParseQuestions:
    @pytest.fixture()
    def engine(self):
        with patch("src.core.diagnosis.ChatGoogleGenerativeAI"), patch(
            "src.core.diagnosis.ChatPromptTemplate"
        ):
            eng = DiagnosisEngine.__new__(DiagnosisEngine)
            eng.settings = MagicMock()
            return eng

    def test_parses_numbered_lines(self, engine):
        raw = "1. How long you had this?\n2. Any fever or chills?\n3. Any nausea or vomiting?"
        result = engine._parse_questions(raw)
        assert len(result) == 3
        assert "How long you had this?" in result

    def test_returns_max_three(self, engine):
        raw = "\n".join(f"{i}. Question {i} which is long enough" for i in range(1, 8))
        result = engine._parse_questions(raw)
        assert len(result) == 3

    def test_filters_short_lines(self, engine):
        raw = "1. Short\n2. A properly phrased question about duration?\n3. Another valid question here?"
        result = engine._parse_questions(raw)
        # "Short" is < 10 chars so only 2 real questions
        assert len(result) <= 3
        assert all(len(q) > 10 for q in result)

    def test_returns_fallback_for_non_string(self, engine):
        result = engine._parse_questions(123)
        assert result == ["Please describe your main symptoms"]

    def test_returns_fallback_for_empty_response(self, engine):
        result = engine._parse_questions("")
        assert result == ["Please describe your main symptoms"]


# DiagnosisEngine.generate_questions
class TestGenerateQuestions:
    @pytest.fixture()
    def engine_with_mock_llm(self):
        with patch("src.core.diagnosis.ChatGoogleGenerativeAI"), patch(
            "src.core.diagnosis.ChatPromptTemplate"
        ), patch("src.core.diagnosis.langsmith"):
            eng = DiagnosisEngine()

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = MagicMock(
            content="1. How long have you had this?\n2. Any fever?\n3. Any vomiting?"
        )
        eng.diagnosis_prompt = MagicMock()
        eng.diagnosis_prompt.__or__ = MagicMock(return_value=mock_chain)
        return eng

    def test_returns_list_of_strings(self, engine_with_mock_llm):
        result = engine_with_mock_llm.generate_questions("I have a headache")
        assert isinstance(result, list)
        assert 1 <= len(result) <= 3
        assert all(isinstance(q, str) for q in result)

    def test_returns_up_to_three_questions(self, engine_with_mock_llm):
        result = engine_with_mock_llm.generate_questions("chest pain")
        assert len(result) <= 3

    def test_raises_diagnosis_error_on_llm_failure(self, engine_with_mock_llm):
        from src.utils.exceptions import DiagnosisError

        engine_with_mock_llm.diagnosis_prompt.__or__.return_value.invoke.side_effect = (
            RuntimeError("LLM unavailable")
        )
        with pytest.raises(DiagnosisError):
            engine_with_mock_llm.generate_questions("fever")


# DiagnosisService
class TestDiagnosisService:
    @pytest.fixture()
    def service_with_mock_engine(self):
        with patch("src.core.diagnosis.DiagnosisEngine") as MockEngine:
            svc = DiagnosisService()
            svc.engine = MockEngine.return_value
            svc.engine.generate_questions.return_value = [
                "How long?",
                "Any fever?",
                "Any vomiting?",
            ]
            svc.engine.generate_medication.return_value = "Paracetamol 500mg"
            return svc

    def test_create_session_returns_diagnosis_session(
        self, service_with_mock_engine, patient_info
    ):
        svc = service_with_mock_engine
        session = svc.create_session("s1", patient_info, "Headache")
        assert session.session_id == "s1"
        assert session.initial_complaint == "Headache"
        assert session.questions == ["How long?", "Any fever?", "Any vomiting?"]

    def test_add_response_appends_conversation_turn(
        self, service_with_mock_engine, diagnosis_session
    ):
        svc = service_with_mock_engine
        initial_len = len(diagnosis_session.conversation)
        svc.add_response(diagnosis_session, 0, "2 days")
        assert len(diagnosis_session.conversation) == initial_len + 1
        assert diagnosis_session.conversation[-1].answer == "2 days"

    def test_add_response_increments_question_index(
        self, service_with_mock_engine, diagnosis_session
    ):
        svc = service_with_mock_engine
        svc.add_response(diagnosis_session, 0, "yes")
        assert diagnosis_session.current_question_index == 1

    def test_add_response_ignores_out_of_range_index(
        self, service_with_mock_engine, diagnosis_session
    ):
        svc = service_with_mock_engine
        initial_len = len(diagnosis_session.conversation)
        svc.add_response(diagnosis_session, 999, "answer")
        assert len(diagnosis_session.conversation) == initial_len

    def test_complete_session_sets_status_and_medication(
        self, service_with_mock_engine, diagnosis_session
    ):
        svc = service_with_mock_engine
        med = svc.complete_session(diagnosis_session)
        assert med == "Paracetamol 500mg"
        assert diagnosis_session.status == "completed"
        assert diagnosis_session.medication == "Paracetamol 500mg"

    @pytest.mark.asyncio
    async def test_complete_session_stream_yields_chunks(
        self, service_with_mock_engine, diagnosis_session
    ):
        svc = service_with_mock_engine

        async def fake_stream(session):
            for chunk in ["Paracetamol ", "500mg"]:
                yield chunk

        svc.engine.generate_medication_stream = fake_stream

        chunks = []
        async for chunk in svc.complete_session_stream(diagnosis_session):
            chunks.append(chunk)

        assert chunks == ["Paracetamol ", "500mg"]
        assert diagnosis_session.medication == "Paracetamol 500mg"
        assert diagnosis_session.status == "completed"
