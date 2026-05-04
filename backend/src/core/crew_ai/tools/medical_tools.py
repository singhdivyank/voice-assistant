"""classes for crewai tools and agents"""

import asyncio
import base64
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from crewai_tools import BaseTool

from src.config.settings import get_settings
from src.services.speech import SpeechRecognizer, TextToSpeech
from src.services.translation import TranslationService
from src.core.llm_manager import llm_manager
from src.utils.consts import (
    DIAGNOSIS_PROMPT,
    Language,
    MEDICATION_PROMPT,
    PRESCRIPTION_TEMPLATE,
)
from src.utils.file_handler import FileHandler
from src.utils.helpers import run_async

settings = get_settings()


class SpeechToTextTool(BaseTool):
    name: str = "transcribe_audio"
    description: str = "Convert audio files to text"

    def _run(self, audio_file_path: str, language_code: str = "en") -> str:
        """Transcribe audio file to text"""

        try:
            language = Language.from_code(language_code)
            recognizer = SpeechRecognizer(language)
            text = recognizer.transcribe_from_file(Path(audio_file_path))
            return text
        except Exception as e:
            return f"Transcription failed: {str(e)}"


class TextToSpeechTool(BaseTool):
    name: str = "generate_audio"
    description: str = "Converting text to speech audio"

    def _run(
        self, text: str, language_code: str = "en", filename: Optional[str] = None
    ) -> str:
        """Generate audio from text"""

        try:
            language = Language.from_code(language_code)
            tts = TextToSpeech(language)
            audio_bytes = run_async(tts.synthesize(text))

            if not filename:
                file_id = uuid.uuid4().hex[:8]
                filename = f"audio_{file_id}.wav"

            audio_path = settings.audio_dir / filename
            audio_path.write_bytes(audio_bytes)
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            return f"Audio saved to {audio_path}\nBase64: {audio_b64}"
        except Exception as e:
            return f"Audio generation failed: {str(e)}"


class TranslationTool(BaseTool):
    name: str = "translate_text"
    description: str = "Translate text between languages"

    def _run(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text"""

        try:
            given_lang = Language.from_code(code=source_lang)
            translator = TranslationService(given_lang)
            if target_lang.lower() in ["en", "english"]:
                return translator.to_english(text)

            return translator.to_user_language(text)
        except Exception as e:
            return f"Translation failed: {str(e)}"


class QuestionGenerationTool(BaseTool):
    name: str = "generate_medical_questions"
    description: str = "Generate follow-up medical questions based on patient complaint"

    def _run(self, complaint: str) -> str:
        """Generate diagnosis questions"""

        questions = []

        try:
            prompt = DIAGNOSIS_PROMPT.format(input=complaint)
            response = run_async(llm_manager.call_llm(prompt, {"agent": "qa"}))

            for line in response.split("\n"):
                cleaned_text = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
                if cleaned_text and len(cleaned_text) > 10:
                    questions.append(cleaned_text)

            return json.dumps(questions[:3])
        except Exception as e:
            return f"Question generation failed: {str(e)}"


class MedicationTool(BaseTool):
    name: str = "medical_recommendation"
    description: str = "Generate medication recommendations"

    def _run(self, patient_age: int, patient_gender: str, diagnosis: str) -> str:
        """Generate medication recommendations"""

        try:
            prompt = MEDICATION_PROMPT.format(
                age=patient_age, gender=patient_gender, conversation=diagnosis
            )
            response = asyncio.run(
                llm_manager.call_llm(prompt, {"agent": "medication"})
            )
            return response
        except Exception as e:
            return f"Medication recommendation failed: {str(e)}"


class PrescriptionTool(BaseTool):
    name: str = "generate_prescription"
    description: str = "Generate formatted prescription document"

    def _run(
        self,
        session_id: str,
        patient_age: int,
        patient_gender: str,
        complaint: str,
        conversation: str,
        medication: str,
    ) -> str:
        """Generate prescription document"""

        try:
            file_handler = FileHandler()
            # TODO- instead of session id use patient name
            prescription_path = (
                settings.prescription_dir / f"prescription_{session_id}.txt"
            )
            now = datetime.now()

            content = PRESCRIPTION_TEMPLATE.format(
                date=now.strftime("%Y-%m-%d"),
                time=now.strftime("%H:%M"),
                age=patient_age,
                gender=patient_gender,
                initial_complaint=complaint,
                conversation=conversation,
                medication=medication,
            )

            file_handler.safe_write(prescription_path, content)
            return f"Prescription saved to: {prescription_path}"
        except Exception as e:
            return f"Prescription generation failed: {str(e)}"
