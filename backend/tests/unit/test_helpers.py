"""Unit tests for src/utils/helpers.py"""

import json
from src.utils.helpers import (
    _extract_audio,
    _extract_diagnosis,
    _extract_doctor_response,
    _extract_questions,
    _extract_review,
    _extract_transcription,
    _format_conversation,
    _format_qa_summary,
)
from src.utils.consts import ConversationTurn


# _extract_questions
class TestExtractQuestions:
    def test_parses_json_array(self):
        result = '["How long have you had this?", "Any fever?", "Any nausea?"]'
        questions = _extract_questions(result)
        assert len(questions) == 3
        assert questions[0] == "How long have you had this?"

    def test_parses_numbered_lines(self):
        result = (
            "1. How long have you had this?\n2. Any fever or chills?\n3. Any vomiting?"
        )
        questions = _extract_questions(result)
        assert len(questions) == 3

    def test_parses_numbered_lines_with_parens(self):
        result = "1) Describe the pain\n2) Any medication taken?\n3) Family history?"
        questions = _extract_questions(result)
        assert len(questions) == 3

    def test_returns_max_three_questions(self):
        items = [f"Question {i}?" for i in range(1, 7)]
        result = json.dumps(items)
        questions = _extract_questions(result)
        assert len(questions) == 3

    def test_returns_fallback_on_empty_input(self):
        questions = _extract_questions("")
        assert len(questions) == 3
        assert all(isinstance(q, str) for q in questions)

    def test_returns_fallback_on_none(self):
        questions = _extract_questions(None)
        assert len(questions) == 3

    def test_ignores_short_lines(self):
        result = (
            "1. Hi\n2. What is the duration of your current symptoms?\n3. Any fever?"
        )
        questions = _extract_questions(result)
        # "Hi" is too short (< 10 chars) so only 2 real questions + fallback fill
        assert len(questions) <= 3

    def test_handles_json_embedded_in_prose(self):
        result = (
            'Here are the questions: ["Any pain?", "Any swelling?", "Any fever?"] end.'
        )
        questions = _extract_questions(result)
        assert "Any pain?" in questions


# _extract_transcription
class TestExtractTranscription:
    def test_extracts_line_after_transcribed(self):
        result = "Processing audio...\nTranscribed text:\nI have a bad headache"
        text = _extract_transcription(result)
        assert text == "I have a bad headache"

    def test_returns_none_on_empty(self):
        assert _extract_transcription("") is None
        assert _extract_transcription(None) is None

    def test_returns_none_when_no_transcription_marker(self):
        result = "Audio processed successfully"
        assert _extract_transcription(result) is None


# _extract_review
class TestExtractReview:
    def test_parses_valid_json(self):
        data = {
            "review_id": "rev-001",
            "doctor_email": "doc@hospital.com",
            "estimated_time_minutes": 30,
        }
        result = f"Review info: {json.dumps(data)}"
        review = _extract_review(result)
        assert review["review_id"] == "rev-001"
        assert review["doctor_email"] == "doc@hospital.com"
        assert review["estimated_time"] == 30

    def test_returns_defaults_on_empty(self):
        review = _extract_review("")
        assert review["review_id"] == "unknown"
        assert "doctor_email" in review
        assert "estimated_time" in review

    def test_returns_defaults_on_invalid_json(self):
        review = _extract_review("not json at all { broken")
        assert review["review_id"] == "unknown"

    def test_returns_defaults_on_none(self):
        review = _extract_review(None)
        assert review["review_id"] == "unknown"


# _extract_doctor_response
class TestExtractDoctorResponse:
    def test_parses_approve_action(self):
        data = {"action": "APPROVED", "review_id": "rev-001"}
        result = json.dumps(data)
        response = _extract_doctor_response(result)
        assert response["action"] == "APPROVED"

    def test_parses_modify_action(self):
        data = {"action": "MODIFIED", "modifications": "Reduce dosage"}
        result = json.dumps(data)
        response = _extract_doctor_response(result)
        assert response["action"] == "MODIFIED"
        assert response["modifications"] == "Reduce dosage"

    def test_returns_default_on_empty(self):
        response = _extract_doctor_response("")
        assert response["action"] == "UNCLEAR"

    def test_returns_error_on_invalid_json(self):
        response = _extract_doctor_response("{ bad json }")
        assert response["action"] == "ERROR"

    def test_returns_default_on_none(self):
        response = _extract_doctor_response(None)
        assert response["action"] == "UNCLEAR"


# _format_conversation
class TestFormatConversation:
    def test_formats_qa_pairs(self):
        turns = [
            ConversationTurn(question="How long?", answer="2 days"),
            ConversationTurn(question="Any fever?", answer="No"),
        ]
        text = _format_conversation(turns)
        assert "How long?" in text
        assert "2 days" in text
        assert "Any fever?" in text
        assert "No" in text

    def test_skips_incomplete_turns(self):
        turns = [
            ConversationTurn(question="How long?", answer=""),
            ConversationTurn(question="", answer="Yes"),
        ]
        text = _format_conversation(turns)
        # Neither turn has both question AND answer non-empty
        assert text.strip() == ""

    def test_empty_conversation_returns_empty_string(self):
        assert _format_conversation([]).strip() == ""


# _format_qa_summary
class TestFormatQaSummary:
    def test_appends_numbered_qa_to_lines(self):
        lines = ["Initial complaint: Headache"]
        turns = [
            ConversationTurn(question="Duration?", answer="2 days"),
            ConversationTurn(question="Fever?", answer="No"),
        ]
        summary = _format_qa_summary(lines, turns)
        assert "Q1: Duration?" in summary
        assert "A1: 2 days" in summary
        assert "Q2: Fever?" in summary

    def test_includes_initial_line(self):
        lines = ["Initial complaint: Chest pain"]
        summary = _format_qa_summary(lines, [])
        assert "Initial complaint: Chest pain" in summary


# _extract_diagnosis
class TestExtractDiagnosis:
    def test_splits_into_three_sections(self):
        result = "Symptom analysis here\n\nDifferential diagnosis here\n\nFinal diagnosis here"
        diagnosis = _extract_diagnosis(result)
        assert diagnosis["symptom_analysis"] == "Symptom analysis here"
        assert diagnosis["differential_diagnosis"] == "Differential diagnosis here"
        assert diagnosis["final_diagnosis"] == "Final diagnosis here"

    def test_returns_empty_strings_on_empty_input(self):
        diagnosis = _extract_diagnosis("")
        assert diagnosis["symptom_analysis"] == ""
        assert diagnosis["differential_diagnosis"] == ""
        assert diagnosis["final_diagnosis"] == ""

    def test_partial_sections(self):
        result = "Only one section here"
        diagnosis = _extract_diagnosis(result)
        assert diagnosis["symptom_analysis"] == "Only one section here"
        assert diagnosis["differential_diagnosis"] == ""


# _extract_audio
class TestExtractAudio:
    def test_extracts_base64_after_marker(self):
        b64 = "A" * 60  # long enough to pass the > 50 char check
        result = f"Audio ready. base64:{b64}"
        extracted = _extract_audio(result)
        assert extracted == b64

    def test_returns_empty_on_short_base64(self):
        result = "base64:short"
        assert _extract_audio(result) == ""

    def test_returns_empty_when_no_marker(self):
        assert _extract_audio("No audio here") == ""

    def test_returns_empty_on_empty_input(self):
        assert _extract_audio("") == ""
