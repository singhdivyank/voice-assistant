"""Helper methods for routes module"""

from datetime import datetime
from typing import Any, Dict
from src.config.settings import get_settings
from src.utils.consts import Language
from src.services.translation import TranslationService

settings = get_settings()


def _base_status(service: str) -> dict:
    """helper function for liveness check"""

    return {
        "service": service,
        "version": settings.app_version,
        "timestep": datetime.now().isoformat(),
    }


def _component_ok(name: str, **extra) -> tuple[dict, bool]:
    return {name: {"status": "ready", **extra}}, True


def _component_fail(name: str, exc: Exception) -> tuple[dict, bool]:
    return {name: {"status": "not_ready", "error": str(exc)}}, False


def get_health_status(agent_perf: Dict[str, Any], agent_load: Dict[str, Any]) -> str:
    """initialise health status from obtained performance stats"""

    health_status = "healthy"

    success_rate = agent_perf.get("success_rate", 1.0)
    p95_latency = agent_perf.get("p95_ms", 0)
    current_load = agent_load.get("current_load", 0)
    max_load = agent_load.get("max_concurrent", 1)

    if success_rate < 0.9 or p95_latency > 10000 or current_load >= max_load:
        health_status = "unhealthy"
    elif success_rate < 0.95 or p95_latency > 5000 or current_load / max_load > 0.8:
        health_status = "degraded"

    return health_status


def _translate_questions(questions: list[str], usr_lang: Language) -> list[str]:
    """Translate question list to user language if not English."""
    if not questions or usr_lang == Language.ENGLISH:
        return questions

    try:
        svc = TranslationService(target_language=usr_lang)
        return [svc.to_user_language(q) for q in questions]
    except Exception:
        return questions


def _translate_text_to_user(text: str, lang_code: str) -> str:
    """Translate text to user language if not English."""
    if not text or lang_code == "en":
        return text
    try:
        lang = Language.from_code(lang_code)
        svc = TranslationService(target_language=lang)
        return svc.to_user_language(text)
    except Exception:
        return text


def _translate_text_to_english(text: str, usr_lang: Language) -> str:
    """Translate text from user language to English for LLM."""
    if not text or usr_lang == Language.ENGLISH:
        return text
    try:
        svc = TranslationService(target_language=usr_lang)
        return svc.to_english(text)
    except Exception:
        return text
