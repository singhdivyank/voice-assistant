"""Agents for mutli-agent system"""

from crewai import Agent

from .backstories import *
from src.core.crew_ai.tools.medical_tools import *
from src.core.crew_ai.tools.gmail_mcp_tools import GMailMCPReadTool, GMailMCPSendTool
from src.utils.consts import PRESCRIPTION_TEMPLATE

stt_tool = SpeechToTextTool()
tts_tool = TextToSpeechTool()
translate_tool = TranslationTool()
qna_tool = QuestionGenerationTool()
medication_tool = MedicationTool()
prescription_tool = PrescriptionTool()
gmail_mcp_read = GMailMCPReadTool()
gmail_mcp_send = GMailMCPSendTool()

speech_processor = Agent(
    role='Speech Processing Specialist',
    goal='Accurately convert speech to text and text to speech for medical consultations',
    backstory=SPEECH_BACKSTORY,
    tools=[stt_tool, tts_tool],
    verbose=True
)

translator = Agent(
    role='Language Translation',
    goal='Provide accurate language translations while preserving meaning and cultural sensitivity',
    backstory=TRANSLATION_BACKSTORY,
    tools=[translate_tool],
    verbose=True    
)

qna_generator = Agent(
    role='Diagnosis Qusetion Generator',
    goal='Generate exactly 3 focused diagnostic questions based on the symptoms to help narrow down diagnosis',
    backstory=QNA_BACKSTORY,
    tools=[qna_tool],
    verbose=True
)

medication = Agent(
    role='Clinical Pharmacist and Therapeutics Specialist',
    goal='Provide evidence-based medication recommendations with comprehensive safety guidelines',
    backstory=RECOMMENDATION_BACKSTORY,
    tools=[medication_tool],
    verbose=True
)

prescription_specialist = Agent(
    role='Prescription Verification Specialist with Gmail MCP',
    goal = 'Generate prescriptions and coordinate human review via Gmail MCP server',
    backstory=PRESCRIPTION_BACKSTORY.format(format=PRESCRIPTION_TEMPLATE),
    tools=[prescription_tool, gmail_mcp_send, gmail_mcp_read],
    verbose=True,
    max_retries=2
)
