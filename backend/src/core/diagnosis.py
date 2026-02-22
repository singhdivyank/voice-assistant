"""Diagnosis and medication recommendation using LLM"""

import logging
import re
from typing import AsyncIterator

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.callbacks.tracers import LangChainTracer
from langchain.prompts import ChatPromptTemplate

from src.config.settings import get_settings
from src.config.monitoring import (
    telemetry, langsmith, timed_operation
)
from src.utils.exceptions import DiagnosisError, MedicationError
from src.utils.consts import (
    ConversationTurn, DiagnosisSession, PatientInfo,
    MEDICATION_PROMPT, DIAGNOSIS_PROMPT
)

logger = logging.getLogger(__name__)
settings = get_settings()


class DiagnosisEngine:
    """LLM-powered diagnosis and medication recommendation with monitoring"""

    def __init__(self):
        self.configure_api()
        self.create_llm()
        self.create_prompts()

    def configure_api(self) -> None:
        """Configure the Google Generative AI API"""
        settings = get_settings()
        genai.configure(api_key=settings.google_api_key)

    def create_llm(self) -> None:
        """Create LLM instance with LangSmith tracing"""
        
        callbacks = []
        if langsmith.enabled:
            callbacks.append(LangChainTracer(project_name=settings.langsmith_project))

        self.llm = ChatGoogleGenerativeAI(
            name=settings.name,
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_tokens,
            convert_system_message_to_human=True,
            callbacks=callbacks if callbacks else None
        )

    def create_prompts(self) -> None:
        """Create diagnosis and medication prompt instances"""

        self.diagnosis_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are a medical assessment assistant. Be thorough but concise"),
                ("human", DIAGNOSIS_PROMPT),
            ]
        )
        self.medication_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are a medical advisor. Provide clear, actionable guidance"),
                ("human", MEDICATION_PROMPT)
            ]
        )

    @timed_operation("generate_questions")
    def generate_questions(self, complaint: str) -> list[str]:
        """Generate diagnostic follow-up questions based on patient's complaint."""

        try:
            with telemetry.span("llm_diagnosis_questions", {"complaint_length": len(complaint)}):
                chain = self.diagnosis_prompt | self.llm
                response = chain.invoke({"input": complaint})
                questions = self._parse_questions(response.content)
                logger.info("Generated %d diagnostic questions", len(questions))
                return questions
        except Exception as e:
            logger.error("Failed to generate questions: %s", e)
            telemetry.increment_counter("llm_errors", attributes={"type": "questions"})
            raise DiagnosisError(f"Could not generate diagnostic questions: {e}") from e

    @timed_operation("generate_medication")
    def generate_medication(self, session: DiagnosisSession) -> str:
        """Generate medication and lifestyle recommendations."""

        try:
            with telemetry.span("llm_medication", {"session_id": session.session_id}):
                chain = self.medication_prompt | self.llm
                response = chain.invoke({
                    "age": session.patient.age,
                    "gender": session.patient.gender.value,
                    "conversation": session.conversation_summary,
                })
            logger.info("Generated medication recommendations for session %s", session.session_id)
            telemetry.increment_counter("diagnosis_completed")
            return response.content
        except Exception as error:
            logger.error("Failed to generate medication: %s", error)
            telemetry.increment_counter("llm_errors", attributes={"type": "medication"})
            raise MedicationError(f"Could not generate recommendations: {error}") from error
    
    async def generate_medication_stream(self, session: DiagnosisSession) -> AsyncIterator[str]:
        """Stream medication recommendations"""

        telemetry.increment_counter("llm_requests", attributes={"type": "medication_stream"})

        try:
            with telemetry.span("llm_medication_stream", {"session_id": session.session_id}):
                chain = self.medication_prompt | self.llm
                
                async for chunk in chain.astream({
                    "age": session.patient.age,
                    "gender": session.patient.gender.value,
                    "conversation": session.conversation_summary
                }):
                    yield chunk.content if hasattr(chunk, 'content') else str(chunk)

                telemetry.increment_counter("diagnosis_completed")
        except Exception as e:
            logger.error("Failed to stream medication: %s", e)
            telemetry.increment_counter("llm_errors", attributes={"type": "medication_stream"})
            raise MedicationError(f"Coould not generate recommendations: {e}") from e

    def _parse_questions(self, response: str) -> list[str]:
        """Parse questions from LLM resposne."""
        
        questions = []
        
        if not isinstance(response, str):
            logger.error(f"Expected string response, got {type(response)}: {response}")
            return ["Please describe your main symptoms"]
        
        for line in response.split("\n"):
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
            if cleaned and len(cleaned) > 10:
                questions.append(cleaned)
        
        if not questions:
            return ["Please describe your main symptoms"]

        return questions[:3]


class DiagnosisService:
    """High-level service for conducting diagnosis sessions."""

    def __init__(self):
        self.engine = DiagnosisEngine()

    def create_session(
            self, 
            session_id: str, 
            patient: PatientInfo, 
            complaint: str
        ) -> DiagnosisSession:
        """Create a new diagnosis session."""
        
        telemetry.increment_counter("session created")
        
        with telemetry.span("create_session", {"session_id": session_id}):
            session = DiagnosisSession(
                session_id=session_id,
                patient=patient, 
                initial_complaint=complaint
            )
            session.questions = self.engine.generate_questions(complaint=complaint)
            return session

    def add_response(
        self, 
        session: DiagnosisSession, 
        question_idx: int, 
        answer: str
    ) -> None:
        """Add a patient's response to a diagnostic question."""

        if question_idx < len(session.questions):
            session.conversation.append(
                ConversationTurn(
                    question=session.questions[question_idx], 
                    answer=answer
                )
            )
            session.current_question_index = question_idx + 1

    def complete_session(self, session: DiagnosisSession) -> str:
        """Complete the diagnosis and generate recommendations."""
        
        with telemetry.span("complete session", {"session_id": session.session_id}):
            medication = self.engine.generate_medication(session=session)
            session.medication = medication
            session.status = "completed"
            return medication
    
    async def complete_session_stream(self, session: DiagnosisSession) -> AsyncIterator[str]:
        """Complete diagnosis with streaming response."""

        full_response = []
        async for chunk in self.engine.generate_medication_stream(session):
            full_response.append(chunk)
            yield chunk
        
        session.medication = "".join(full_response)
        session.status = "completed"
