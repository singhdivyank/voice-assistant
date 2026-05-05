import asyncio
import concurrent.futures
import json
import re
from typing import Any, Dict, List, Optional


def run_async(coro):
    """Run an async coroutine safely from a synchronous context."""

    # to run async code safely
    _THREAD_POOL = concurrent.futures.ThreadPoolExecutor(
        max_workers=4, thread_name_prefix="crewai_tools"
    )
    future = _THREAD_POOL.submit(asyncio.run, coro)
    return future.result()


def _extract_questions(result: Optional[str] = None) -> List[str]:
    "Extract questions from crew result"

    fallback = [
        "Please describe your main symptoms in more detail",
        "When did these symptoms first start?",
        "Have you experienced anything like this before?",
    ]

    if not result:
        return fallback

    start, end = result.find("["), result.find("]")
    if start in range(0, end):
        try:
            questions = json.loads(result[start : end + 1])
            if isinstance(questions, list):
                cleaned = [
                    question.strip()
                    for question in questions
                    if isinstance(question, str) and question.strip()
                ]
                if cleaned:
                    return cleaned[:3]
        except json.JSONDecodeError:
            pass

    questions = []
    for line in result.splitlines():
        _match = re.compile(r"^\s*\d+[\.\)]\s+(.*\S)\s*$").match(line)
        if _match:
            question = _match.group(1).strip()
            if len(question) > 10:
                questions.append(question)
                if len(questions) == 3:
                    return questions

    return fallback


def _extract_transcription(result: Optional[str] = None) -> Optional[str]:
    """Extract transcribed text from result"""

    if not result:
        return None

    lines = [line.strip() for line in result.splitlines()]

    for idx, line in enumerate(lines):
        if "transcribed" in line.lower():
            for next_line in lines[idx + 1 :]:
                if next_line:
                    return next_line

            return None

    return None


def _extract_doctor_response(result: Optional[str] = None) -> Dict[str, Any]:
    default_response = {"action": "UNCLEAR"}

    if not result:
        return default_response

    start, end = result.find("{"), result.rfind("}")
    if start == -1 or end == -1 or start > end:
        return default_response

    try:
        data = json.loads(result[start : end + 1])
        return data if isinstance(data, dict) else default_response
    except json.JSONDecodeError:
        return {"action": "ERROR"}


def _format_qa_summary(lines: list, conversation: list) -> str:

    for idx, turn in enumerate(conversation, 1):
        if turn.question and turn.answer:
            lines.append(f"Q{idx}: {turn.question}")
            lines.append(f"A{idx}: {turn.answer}")

    return "\n".join(lines)


def _format_conversation(conversation: list) -> str:

    lines = []

    for turn in conversation:
        if turn.question and turn.answer:
            lines.append(f"Q: {turn.question}")
            lines.append(f"A: {turn.answer}")
            lines.append("")

    return "\n".join(lines)


def _extract_diagnosis(result: str) -> Dict[str, str]:
    diagnosis_info = {
        "symptom_analysis": "",
        "differential_diagnosis": "",
        "final_diagnosis": "",
    }

    if not result:
        return diagnosis_info

    sections = [section.strip() for section in result.split("\n\n", 2)]
    keys = ("symptom_analysis", "differential_diagnosis", "final_diagnosis")

    for key, section in zip(keys, sections):
        diagnosis_info[key] = section

    return diagnosis_info


def _extract_audio(result: str) -> str:
    if not result:
        return ""

    marker = "base64:"
    idx = result.lower().find(marker)
    if idx == -1:
        return ""

    audio_part = result[idx + len(marker) :].strip()
    audio_part = audio_part.split("\n", 1)[0].strip()
    return audio_part if len(audio_part) > 50 else ""
