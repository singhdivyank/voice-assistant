"""Tools for diagnosis and q&a agents"""

from langchain_core.tools import tool

@tool
async def analyze_symptoms_and_diagnose(
    age: int, 
    gender: str, 
    complaint: str, 
    qa_history: str
) -> str:
    """Provides formal differential diagnosis. Call this only after Q&A"""

    from src.utils.consts import AGENT_DIAGNOSIS_PROMPT
    from src.core.multi_agent.llm_manager import LLMManager

    llm_manager = LLMManager().llm
    
    prompt = AGENT_DIAGNOSIS_PROMPT.format(
        age=age,
        gender=gender,
        complaint=complaint,
        qa_summary=qa_history
    )
    response = await llm_manager.ainvoke(prompt)
    return response.content

@tool
async def recommend_medications(
    diagnosis: str, 
    symptoms: str, 
    age: int, 
    gender: str
) -> str:
    """generates medication recommendation based on diagnosis"""

    from src.utils.consts import AGENT_MEDICATION_PROMPT
    from src.core.multi_agent.llm_manager import LLMManager

    llm_ob = LLMManager().llm

    prompt = AGENT_MEDICATION_PROMPT.format(
        age=age,
        gender=gender,
        qa_summary=diagnosis,
        complaint=symptoms
    )

    response = await llm_ob.ainvoke(prompt)
    return response.content
