"""Diagnosis and medication recommendation using LLM"""

import logging
import re

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate

from src.config.settings import LLMConfig, DIAGNOSIS_PROMPT, MEDICATION_PROMPT
from src.utils.exceptions import DiagnosisError, MedicationError
from utils.classConsts import ConversationTurn, DiagnosisSession, PatientInfo

logger = logging.getLogger(__name__)


class DiagnosisEngine:
    """
    LLM-powered diagnosis and medication recommendation.

    Uses Google's Gemini model for generating diagnostic questions
    and medication recommendation based on the conversation
    """

    def __init__(self):
        self.config = LLMConfig()
        self.configure_api()
        self.create_llm()
        self.create_prompts()

    def configure_api(self) -> None:
        """Configure the Google Generative AI API"""
        genai.configure(api_key=self.config.api_key)

    def create_llm(self) -> None:
        """Create LLM instance"""
        self.llm = ChatGoogleGenerativeAI(
            name=self.config.model_name,
            temperature=self.config.temperature,
            model=self.config.gemini_model,
            convert_system_message_to_human=True,
        )

    def create_prompts(self) -> None:
        """Create diagnosis and medication prompt instances"""
        self.diagnosis_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "you are a medical assessment assistant"),
                ("human", DIAGNOSIS_PROMPT),
            ]
        )
        self.medication_prompt = ChatPromptTemplate.from_messages(
            [("human", MEDICATION_PROMPT)]
        )

    def generate_questions(self, complaint: str) -> list[str]:
        """
        Generate diagnostic follow-up questions based on patient's complaint.

        Params:
            complaint (str): Patient's initial complaint

        Returns:
            List of diagnostic questions

        Raises:
            DiagnosisError: if question generation fails
        """

        try:
            chain = self.diagnosis_prompt | self.llm
            response = chain.invoke({"input": complaint})
            questions = self._parse_questions(response.content)
            logger.info("Generated %s diagnostic questions", len(questions))
            return questions
        except Exception as e:
            logger.error("Failed to generate questions: %s", e)
            raise DiagnosisError(f"Could not generate diagnostic questions: {e}") from e

    def generate_medication(self, session: DiagnosisSession) -> str:
        """
        Generate medication and lifestyle recommendations.

        Args:
            session: Complete diagnosis session with conversation

        Returns:
            Medication and lifestyle recommendations

        Raises:
            MedicationError: If recommendation generation fails
        """

        try:
            chain = self.medication_prompt | self.llm
            response = chain.invoke(
                {
                    "age": session.patient.age,
                    "gender": session.patient.gender.value,
                    "conversation": session.conversation_summary,
                }
            )
            logger.info("Generated medication recommendations")
            return response.content
        except Exception as error:
            logger.error("Failed to generate medication: %s", error)
            raise MedicationError(f"Could not generate recommendations: {error}") from error

    def _parse_questions(self, response: str) -> list[str]:
        """
        Parse questions from LLM resposne.

        Args:
            response: Raw LLM response.

        Return:
            List of cleaned questions
        """
        lines = response.strip().split("\n")
        questions = []

        for line in lines:
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
            if cleaned and len(cleaned) > 5:
                questions.append(cleaned)

        return questions[:3]


class DiagnosisService:
    """
    High-level service for conducting diagnosis sessions.

    Orchestrates the diagnosis flow from initial complaint
    through questions to final recommendations
    """

    def __init__(self):
        self.engine = DiagnosisEngine()

    def create_session(self, patient: PatientInfo, complaint: str) -> DiagnosisSession:
        """
        Create a new diagnosis session.

        Args:
            patient: Patient information
            complaint: Initial complaint

        Returns:
            New Diagnosis session with generated questions
        """
        session = DiagnosisSession(patient=patient, initial_complaint=complaint)
        session.questions = self.engine.generate_questions(complaint=complaint)
        return session

    def add_response(
        self, session: DiagnosisSession, question_idx: int, answer: str
    ) -> None:
        """
        Add a patient's response to a diagnostic question.

        Args:
            session: Current diagnosis session
            question_idx: Index of the question being answered
            answer: Patient's answer
        """

        if question_idx < len(session.questions):
            session.conversation.append(
                ConversationTurn(
                    question=session.questions[question_idx], answer=answer
                )
            )

    def complete_session(self, session: DiagnosisSession) -> str:
        """
        Complete the diagnosis and generate recommendations.

        Args:
            session: Complete diagnosis session

        Returns:
            Medication and lifestyle recommendations
        """
        return self.engine.generate_medication(session=session)
