"""Unit tests for src/utils/consts.py"""

from typing import Optional

from src.utils.consts import (
    AgentPerformanceMetrics,
    ConversationTurn,
    DiagnosisSession,
    Gender,
    Language,
    PatientInfo,
    WorkflowStep,
)


# Gender
class TestGender:
    def test_from_string_known_values(self):
        assert Gender.from_string("male") == Gender.MALE
        assert Gender.from_string("Female") == Gender.FEMALE
        assert Gender.from_string("FEMALE") == Gender.FEMALE

    def test_from_string_unknown_falls_back_to_undisclosed(self):
        assert Gender.from_string("alien") == Gender.UNDISCLOSED
        assert Gender.from_string("") == Gender.UNDISCLOSED


# Language
class TestLanguage:
    def test_from_code_known(self):
        assert Language.from_code("en") == Language.ENGLISH
        assert Language.from_code("hi") == Language.HINDI
        assert Language.from_code("ES") == Language.SPANISH  # case-insensitive

    def test_from_code_unknown_returns_english(self):
        assert Language.from_code("xx") == Language.ENGLISH

    def test_from_code_empty_returns_english(self):
        assert Language.from_code("") == Language.ENGLISH
        assert Language.from_code(None) == Language.ENGLISH

    def test_from_string_name(self):
        assert Language.from_string("hindi") == Language.HINDI
        assert Language.from_string("ENGLISH") == Language.ENGLISH

    def test_from_string_unknown_returns_english(self):
        assert Language.from_string("klingon") == Language.ENGLISH

    def test_choices_returns_all_names_lowercase(self):
        choices = Language.choices()
        assert "english" in choices
        assert "hindi" in choices
        assert len(choices) == len(Language)


# PatientInfo
class TestPatientInfo:
    def test_str_representation(self):
        p = PatientInfo(name="Alice", email="a@b.com", age=25, gender=Gender.FEMALE)
        s = str(p)
        assert "Alice" in s
        assert "25" in s
        assert "female" in s

    def test_fields_stored_correctly(self):
        p = PatientInfo(name="Bob", email="b@c.com", age=40, gender=Gender.MALE)
        assert p.name == "Bob"
        assert p.email == "b@c.com"
        assert p.age == 40
        assert p.gender == Gender.MALE


# DiagnosisSession
class TestDiagnosisSession:
    def _make_session(
        self,
        session_id: str = "sess-001",
        patient: Optional[PatientInfo] = None,
        initial_complaint: str = "Headache",
    ):
        if patient is None:
            patient = PatientInfo(
                name="Jane", email="jane@test.com", age=30, gender=Gender.FEMALE
            )
        return DiagnosisSession(
            session_id=session_id, patient=patient, initial_complaint=initial_complaint
        )

    # conversation_summary
    def test_conversation_summary_includes_complaint(self):
        session = self._make_session()
        assert "Headache" in session.conversation_summary

    def test_conversation_summary_includes_qa(self):
        session = self._make_session()
        session.conversation = [ConversationTurn(question="Duration?", answer="2 days")]
        summary = session.conversation_summary
        assert "Duration?" in summary
        assert "2 days" in summary

    # is_complete
    def test_is_complete_false_when_questions_remain(self):
        session = self._make_session()
        session.questions = ["Q1", "Q2", "Q3"]
        session.current_question_index = 1
        assert not session.is_complete

    def test_is_complete_true_when_all_answered(self):
        session = self._make_session()
        session.questions = ["Q1", "Q2"]
        session.current_question_index = 2
        assert session.is_complete

    def test_is_complete_true_with_no_questions(self):
        session = self._make_session()
        session.questions = []
        session.current_question_index = 0
        assert session.is_complete

    # to_dict / from_dict round-trip
    def test_to_dict_includes_patient_name_and_email(self):
        session = self._make_session()
        d = session.to_dict()
        assert d["patient_name"] == "Jane"
        assert d["patient_email"] == "jane@test.com"

    def test_to_dict_includes_core_fields(self):
        session = self._make_session()
        session.questions = ["Q1"]
        session.medication = "Aspirin"
        d = session.to_dict()
        assert d["session_id"] == "sess-001"
        assert d["initial_complaint"] == "Headache"
        assert d["questions"] == ["Q1"]
        assert d["medication"] == "Aspirin"
        assert d["status"] == "active"
        assert d["language"] == "en"

    def test_round_trip_preserves_all_fields(self):
        session = self._make_session()
        session.questions = ["Q1", "Q2"]
        session.conversation = [ConversationTurn(question="Q1", answer="Yes")]
        session.medication = "Ibuprofen"
        session.current_question_index = 1
        session.status = "completed"
        session.language = "hi"

        restored = DiagnosisSession.from_dict(session.to_dict())

        assert restored.session_id == session.session_id
        assert restored.patient.name == "Jane"
        assert restored.patient.email == "jane@test.com"
        assert restored.patient.age == 30
        assert restored.patient.gender == Gender.FEMALE
        assert restored.initial_complaint == "Headache"
        assert restored.questions == ["Q1", "Q2"]
        assert restored.medication == "Ibuprofen"
        assert restored.current_question_index == 1
        assert restored.status == "completed"
        assert restored.language == "hi"

    def test_from_dict_defaults_for_missing_name_email(self):
        """Older stored sessions without patient_name/patient_email get safe defaults."""
        data = {
            "session_id": "s1",
            "patient_age": 25,
            "patient_gender": "male",
            "initial_complaint": "Fever",
            "questions": [],
            "conversation": [],
            "medication": None,
            "current_question_index": 0,
            "status": "active",
            "language": "en",
        }
        session = DiagnosisSession.from_dict(data)
        assert session.patient.name == "Unknown"
        assert session.patient.email == ""


# AgentPerformanceMetrics
class TestAgentPerformanceMetrics:
    def test_initial_state(self):
        m = AgentPerformanceMetrics("qa")
        assert m.total_executions == 0
        assert m.success_rate == 1.0
        assert m.error_count == 0

    def test_update_successful_execution(self):
        m = AgentPerformanceMetrics("qa")
        m.update(duration_ms=200.0, success=True)
        assert m.total_executions == 1
        assert m.error_count == 0
        assert m.average_duration_ms == 200.0
        assert m.success_rate == 1.0

    def test_update_failed_execution(self):
        m = AgentPerformanceMetrics("qa")
        m.update(duration_ms=100.0, success=True)
        m.update(duration_ms=0.0, success=False)
        assert m.total_executions == 2
        assert m.error_count == 1
        assert m.success_rate == 0.5

    def test_percentiles_calculated_after_updates(self):
        m = AgentPerformanceMetrics("qa")
        for i in range(1, 11):  # 10 successful executions
            m.update(duration_ms=float(i * 100), success=True)
        assert m.p50_ms > 0
        assert m.p95_ms >= m.p50_ms
        assert m.p99_ms >= m.p95_ms

    def test_to_dict_keys(self):
        m = AgentPerformanceMetrics("stt")
        m.update(150.0)
        d = m.to_dict()
        for key in (
            "agent_name",
            "total_executions",
            "average_duration_ms",
            "success_rate",
            "p50_ms",
            "p95_ms",
            "p99_ms",
        ):
            assert key in d

    def test_min_max_tracked(self):
        m = AgentPerformanceMetrics("tts")
        m.update(500.0)
        m.update(100.0)
        m.update(300.0)
        assert m.min_duration_ms == 100.0
        assert m.max_duration_ms == 500.0


# WorkflowStep ordering sanity
class TestWorkflowStep:
    def test_all_steps_have_string_values(self):
        for step in WorkflowStep:
            assert isinstance(step.value, str)

    def test_error_step_exists(self):
        assert WorkflowStep.ERROR is not None

    def test_completed_step_exists(self):
        assert WorkflowStep.COMPLETED is not None
