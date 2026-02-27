"""Translation service for multilingual support"""

import logging
import asyncio
from functools import lru_cache
from typing import Optional

from deep_translator import GoogleTranslator
from deep_translator.exceptions import (
    TranslationNotFound,
    NotValidPayload,
    RequestError
)

from src.config.settings import get_settings
from src.config.monitoring import telemetry, timed_operation
from src.utils.consts import Language, MESSAGES
from src.utils.exceptions import TranslationError, NetworkError


logger = logging.getLogger(__name__)
settings = get_settings()


class TranslationService:
    """Service for translating text between languages with caching and monitoring."""

    def __init__(self, target_language: Language):
        self.target_language = target_language
        self._message_cache: dict[str, str] = {}
        self._translation_cache: dict[str, str] = {}
        self.cache_size = 1000

    @property
    def is_english(self) -> bool:
        """Check if target language is English."""
        return self.target_language == Language.ENGLISH
    
    @property
    def language_code(self) -> str:
        """Get the language code"""
        return self.target_language.value
    
    @property
    def language_name(self) -> str:
        """Get the language name"""
        return self.target_language.name.title()
    
    def _get_cache_key(self, text: str, to_english: bool) -> str:
        """Generate cache key for translation"""
        direction = "to_en" if to_english else f"to_{self.language_code}"
        return f"{direction}:{hash(text)}"
    
    def _get_cache(self, text: str, to_english: bool) -> Optional[str]:
        """Get cached translation if available"""
        key = self._get_cache_key(text, to_english)
        return self._translation_cache.get(key)
    
    def _set_cache(self, text: str, to_english: bool, result: str) -> None:
        """Cache a translation result"""
        if len(self._translation_cache) >= self.cache_size:
            keys = list(self._translation_cache.keys())
            for key in keys[:len(keys)//2]:
                del self._translation_cache[key]
        
        key = self._get_cache_key(text, to_english)
        self._translation_cache[key] = result

    @timed_operation("translation")
    def translate(self, text: str, to_english: bool = False) -> str:
        """Translate text to target language or to English"""
        if not text or not text.strip():
            return text

        if self.is_english:
            return text
        
        cached = self._get_cache(text, to_english)
        if cached:
            logger.debug("Translation cache hit")
            return cached
        
        telemetry.increment_counter(
            "translation_requests",
            attributes={"direction": "to_english" if to_english else "to_user"}
        )

        source_lang = "en" if not to_english else self.language_code
        dest_language = self.language_code if not to_english else "en"

        try:
            translator = GoogleTranslator(source=source_lang, target=dest_language)
            result = translator.translate(text=text)
            logger.debug(
                "Translated '%s...' from %s to %s",
                result[:30],
                source_lang,
                dest_language,
            )
            self._set_cache(text, to_english, result)
            return result
        except RequestError as e:
            logger.error("Network error during translation: %s", e)
            telemetry.increment_counter("translation_errors", attributes={"type": "network"})
            raise NetworkError(f"Translation service unavailable: {e}") from e
        except NotValidPayload as e:
            logger.error("Invalid text for translation: %s", e)
            telemetry.increment_counter("translation_errors", attributes={"type": "invalid"})
            raise TranslationError(f"Invalid text for translation: {e}") from e
        except TranslationNotFound as e:
            logger.error("Translation not found: %s", e)
            telemetry.increment_counter("translation_errors", attributes={"type": "not_found"})
            raise TranslationError(f"Translation not available: {e}") from e
        except (ValueError, RuntimeError) as e:
            logger.error("Translation failed: %s", e)
            telemetry.increment_counter("translation_errors", attributes={"type": "unknown"})
            raise TranslationError(f"Failed to translate text: {e}") from e

    async def translate_async(self, text: str, to_english: bool = False) -> str:
        """Translate text asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.translate(text, to_english)
        )
    
    def to_english(self, text: str) -> str:
        """Convinience method to translate to English for LLM"""
        return self.translate(text=text, to_english=True)
    
    async def to_english_async(self, text: str) -> str:
        """Async convinience method to translate to English for LLM"""
        return await self.translate(text=text, to_english=True)

    def to_user_language(self, text: str) -> str:
        """Convinience method to translate to user's language"""
        return self.translate(text=text, to_english=False)
    
    async def to_user_language_async(self, text: str) -> str:
        """Async convinience method to translate to user's language"""
        return await self.translate(text=text, to_english=False)

    def translate_batch(self, texts: list[str], to_english: bool = False) -> list[str]:
        """Translate multiple texts"""
        return [self.translate(text, to_english) for text in texts]
    
    async def translate_batch_async(
        self, texts: list[str], to_english: bool = False
    ) -> list[str]:
        """translate multiple texts asynchronously"""
        tasks = [self.translate_async(text, to_english) for text in texts]
        return await asyncio.gather(*tasks)

    def get_messages(self) -> dict[str, str]:
        """Get all static messages translated to the target language"""
        if self._message_cache:
            return self._message_cache
        
        for key, message in MESSAGES.items():
            try:
                self._message_cache[key] = self.to_user_language(message)
            except TranslationError:
                self._message_cache[key] = message
                logger.warning("Failed to translate message '%s', using English", key)
        
        return self._message_cache
    
    def get_message(self, key: str) -> str:
        """Get a specific translated message"""
        messages = self.get_messages()
        return messages.get(key, MESSAGES.get(key, ""))
    
    def clear_cache(self) -> None:
        """Clear all caches"""
        self._message_cache.clear()
        self._translation_cache.clear()
        logger.debug("Translation caches cleared")


class TranslationServiceFactory:
    """Factory for creating and caching translation service instances"""

    _instances: dict[Language, TranslationService] = {}

    @classmethod
    def get_service(cls, language: Language) -> TranslationService:
        """Get or create translation service for given language"""
        if language not in cls._instances:
            cls._instances[language] = TranslationService(language)
            logger.info("Created TranslationService for %s", language.name)
        return cls._instances[language]
    
    @classmethod
    def clear_all(cls) -> None:
        """Clear all cached instances"""
        for service in cls._instances.values():
            service.clear_cache()
        cls._instances.clear()


def get_translation_service(language: Language) -> TranslationService:
    """Factory function to get translation service"""
    return TranslationServiceFactory.get_service(language)

@lru_cache
def detect_language(text: str) -> Optional[str]:
    """Detect the language of a text (cached)"""
    try:
        from langdetect import detect
        return detect(text)
    except Exception as e:
        logger.warning("Language detection failed: %s", e)
        return None

def is_supported_language(lang_code: str) -> bool:
    """Check if a language code is supported"""
    supported = {lang.value for lang in Language}
    return lang_code.lower() in supported
