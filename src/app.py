"""Main application entry point"""

import logging
from dataclasses import dataclass
from typing import Optional

import gradio as gr

from src.config.settings import (
    AppConfig,
    APP_DESCRIPTION,
    Language,
    Gender
)
from src.core.diagnosis import (
    DiagnosisService, 
    DiagnosisSession, 
    PatientInfo
)
from src.core.prescription import PrescriptionService
from src.services.speech import SpeechService
from src.services.translation import TranslationService
from src.utils.exceptions import NetworkError, DocJarvisError


logging.basicConfig(
    level = logging.INFO,
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    "Context for a consultaion session"
    langauge: Language
    patient: PatientInfo
    translation: TranslationService
    speech: SpeechService
    diagnosis: DiagnosisService
    prescription: PrescriptionService
    session: Optional[DiagnosisSession] = None


class DocJarvis:
    """
    Main application class for medical assistant.

    Orchestrates the consultation flow including speech recognition,
    translation, diagnosis, and prescription generation
    """

    def __init__(self) -> None:
        self.config = AppConfig()
        self.diagnosis_service = DiagnosisService()
        self.prescription_service = PrescriptionService()
    
    def perform_consultation(
            self, 
            language: str, 
            gender: list[str], 
            age: int
        ) -> str:
        """
        Run a complete medical consultation.

        Args:
            language: Selected language name
            gender: Selected gender
            age: Patient age
        
        Returns:
            Path to the generated prescription or error message
        """

        try:
            ctx = self.create_session_context(language, gender, age)
            return self.execute_consultation(ctx)
        except NetworkError as e:
            logger.error(f"Network error: {e}")
            return "Error: Please check you rinternet connection"
        except DocJarvisError as e:
            logger.error(f"Application error: {e}")
            return f"Error: {e}"
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return "An unexpected error occured. Please try again"
    
    def create_session_context(
            self, 
            language: str, 
            gender: list[str], 
            age: int
        ) -> SessionContext:
        """Create the session context with all required services."""

        language = Language.from_sring(name=language)
        gender_enum = Gender.from_string(value=gender[0] if gender else "Undisclosed")
        patient = PatientInfo(age=age, gender=gender_enum)
        paths = self.config.paths
        return SessionContext(
            langauge=language,
            patient=patient,
            translation=TranslationService(target_language=language),
            speech=SpeechService(language=language, paths=paths),
            diagnosis=self.diagnosis_service,
            prescription=self.prescription_service
        )
    
    def execute_consultation(self, context: SessionContext) -> str:
        """Execute the main consultation flow"""
        messages = context.translation.get_msgs()

        context.speech.speak(messages["intro"])
        context.speech.speak(messages["instruction"])
        initial_complaint = context.speech.listen()
        complaint_english = context.translation.to_english(text=initial_complaint)
        logger.info(f"Initial complaint: {complaint_english}")

        context.session = context.diagnosis.create_session(context.patient, initial_complaint)
        self.conduct_qa(context)
        
        medication = context.diagnosis.complete_session(context.session)
        medication_localised = context.translation.to_user_language(text=medication)
        prescription_path = context.prescription.create_prescription(context.session)
        context.speech.speak(medication_localised)

        return str(prescription_path)
    
    def conduct_qa(self, context: SessionContext) -> None:
        """
        Conduct the diagnosis Q&A session.

        Responses are added directly to session conversation
        by the diagnosis service
        """

        for idx, question in enumerate(context.session.questions):
            if not question:
                context
        
            question_localized = context.translation.to_user_language(text=question)
            context.speech.speak(text=question_localized)

            try:
                response = context.speech.listen()
                response_english = context.translation.to_english(response)
                context.diagnosis.add_response(
                    session=context.session,
                    question_idx=idx,
                    answer=response_english
                )
                context.diagnosis.add_response(context.session, idx, response_english)
            except NetworkError:
                logger.warning(f"Network error during Q&A at question {idx}")
                continue

def create_interface(app: DocJarvis) -> gr.Interface:
    """
    Create the Gradio interface.

    Args:
        app: DocJarvis application instance
    
    Returns:
        configured Gradio interface
    """
    return gr.Interface(
        fn=app.perform_consultation,
        inputs=[
            gr.Dropdown(
                choices=Language.choices(),
                multiselect=False,
                label="language selection",
                show_label=True,
                interactive=True
            ),
            gr.CheckboxGroup(
                choices=[g.value for g in Gender],
                label="gender selection",
                show_label=True,
                interactive=True
            ),
            gr.Slider(
                minimum=10,
                maximum=50,
                step=2,
                label="age selection",
                show_label=True,
                interactive=True
            )
        ],
        outputs=gr.TextBox(label="Prescription File Path"),
        title="DocJarvis -- AI Medical Assistant",
        description=APP_DESCRIPTION,
        allow_flagging="never"
    )

def main() -> None:
    """Application entry point"""
    config = AppConfig()
    app = DocJarvis()
    interface = create_interface(app=app)
    interface.launch(
        server_name=config.server.host,
        server_port=config.server.port,
        share=config.server.share
    )


if __name__ == '__main__':
    main()
