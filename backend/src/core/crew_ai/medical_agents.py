"""Agents for mutli-agent system"""

from crewai import Agent, LLM

from src.config.settings import get_settings
from src.core.crew_ai.tools.medical_tools import (
    MedicationTool,
    PrescriptionTool,
    QuestionGenerationTool,
    TextToSpeechTool,
    TranslationTool,
)
from src.core.crew_ai.tools.gmail_mcp_tools import GMailMCPReadTool, GMailMCPSendTool
from src.utils.backstories import (
    PRESCRIPTION_BACKSTORY,
    QNA_BACKSTORY,
    RECOMMENDATION_BACKSTORY,
    SPEECH_BACKSTORY,
    TRANSLATION_BACKSTORY,
)
from src.utils.consts import PRESCRIPTION_TEMPLATE

settings = get_settings()

gemini_llm = LLM(
    model=f"gemini/{settings.gemini_model}",
    api_key=settings.google_api_key,
    temperature=settings.llm_temperature,
)

speech_processor = Agent(
    role="Speech Processing Specialist",
    goal="Accurately convert text to speech for medical consultations",
    backstory=SPEECH_BACKSTORY,
    tools=[TextToSpeechTool()],
    llm=gemini_llm,
    verbose=True,
)

translator = Agent(
    role="Language Translation",
    goal="Provide accurate language translations while preserving \
        meaning and cultural sensitivity",
    backstory=TRANSLATION_BACKSTORY,
    tools=[TranslationTool()],
    llm=gemini_llm,
    verbose=True,
)

qna_generator = Agent(
    role="Diagnosis Qusetion Generator",
    goal="Generate exactly 3 focused diagnostic questions based on \
        the symptoms to help narrow down diagnosis",
    backstory=QNA_BACKSTORY,
    tools=[QuestionGenerationTool()],
    llm=gemini_llm,
    verbose=True,
)

medication = Agent(
    role="Clinical Pharmacist and Therapeutics Specialist",
    goal="Provide evidence-based medication recommendations with \
        comprehensive safety guidelines",
    backstory=RECOMMENDATION_BACKSTORY,
    tools=[MedicationTool()],
    llm=gemini_llm,
    verbose=True,
)

prescription_specialist = Agent(
    role="Prescription Verification Specialist with Gmail MCP",
    goal="Generate prescriptions and coordinate human review via Gmail MCP server",
    backstory=PRESCRIPTION_BACKSTORY.format(format=PRESCRIPTION_TEMPLATE),
    tools=[PrescriptionTool(), GMailMCPSendTool(), GMailMCPReadTool()],
    llm=gemini_llm,
    verbose=True,
    max_retries=2,
)
