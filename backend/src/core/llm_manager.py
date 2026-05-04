"""Manage LLM calls and API limits"""

import logging
from typing import Any, AsyncIterator, Dict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tracers.langchain import LangChainTracer

from src.config.settings import get_settings
from src.config.monitoring import langsmith, timed_operation, telemetry
from src.utils.exceptions import LLMError
from src.utils.singleton import Singleton

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMManager(Singleton):
    """Centralized LLM management for all agents"""

    _initialized: bool = False

    def __init__(self):
        if self._initialized:
            return

        self.create_llm()
        self._initialized = True
        logger.info("LLM Manager initialized")

    def get_llm_configs(self, callbacks=None):
        """LLM hyperparameters"""
        return {
            "model": settings.gemini_model,
            "google_api_key": settings.google_api_key,
            "temperature": settings.llm_temperature,
            "max_output_tokens": settings.llm_max_tokens,
            "convert_system_message_to_human": True,
            "callbacks": callbacks if callbacks else None,
        }

    def create_llm(self) -> None:
        """Create LLM instance with monitoring"""
        callbacks = []
        if langsmith.enabled:
            tracer = LangChainTracer(project_name=settings.langsmith_project)
            callbacks.append(tracer)

        self.llm = ChatGoogleGenerativeAI(**self.get_llm_configs(callbacks=callbacks))

    @timed_operation("llm_call")
    async def call_llm(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Centralzed LLM calling with monitoring"""

        telemetry.increment_counter("llm_requests")

        try:
            with telemetry.span("llm_generation", context or {}):
                result = await self.llm.ainvoke(prompt)
                return result.content
        except Exception as e:
            telemetry.increment_counter("llm_errors")
            logger.error("LLM call failed: %s", e)
            raise LLMError(f"LLM generation failed: {e}") from e

    @timed_operation("llm_stream")
    async def stream_llm(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """Streaming LLM calls"""

        telemetry.increment_counter("llm_requests", attributes={"type": "stream"})

        try:
            with telemetry.span("llm_stream_generation", context or {}):
                async for chunk in self.llm.astream(prompt):
                    yield chunk.content if hasattr(chunk, "content") else str(chunk)
        except Exception as e:
            telemetry.increment_counter("llm_errors", attributes={"type": "stream"})
            logger.error("LLM stream failed: %s", e)
            raise LLMError(f"LLM streaming failed: {e}") from e


llm_manager = LLMManager()
