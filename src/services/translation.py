"""Translation service for multilingual support"""

import logging

from googletrans import Translator

from src.config.settings import Language    
from src.utils.dataclasses import TranslatorProtocol
from src.utils.exceptions import TranslationError


logger = logging.getLogger(__name__)

MESSAGES = {
    "intro": "Send message from microphone. To stop, say 'thanks' ",
    "instruction": "Please begin",
    "diagnosis": "Performing diagnosis"
}


class TranslationService:
    """
    Service for translating text between languages.

    Supports translation to/from English for LLM processing
    and user-facing content.
    """
    
    def __init__(self, target_language: Language, translator: TranslatorProtocol | None = None):
        self.target_language = target_language
        self._translator = translator or Translator()
        self.message_cache: dict[str, str] = {}
    
    @property
    def is_english(self) -> bool:
        """Check if target language is English."""
        return self.target_language == Language.ENGLISH

    def translate(self, text: str, to_english: bool = False) -> str:
        """
        Translate text to target language or to English
        
        Args:
            text: Text to translate
            to_english: If True, translate to English; otherwise to target language
        
        Returns:
            translated text
        
        Raises:
            TranslationError: If translation fails
        """
        if not text or text.strip():
            return text
        
        dest_langauage = 'en' if to_english else self.target_language.value
        if (to_english and self.is_english) or (not to_english and self.is_english):
            return text
        
        try:
            result = self._translator.translate(text=text, dest=dest_langauage)
            logger.debug(f"Translated '{text[:50]}...' to {dest_langauage}")
            return result.text
        except Exception as e:
            logger.error(f"Translation failed: {e}")    
            raise TranslationError(f"Failed to translate text: {e}")
    
    def to_english(self, text: str) -> str:
        """Convinience method to translate to English for LLM"""
        return self.translate(text=text, to_english=True)
    
    def to_user_language(self, text: str) -> str:
        """Convinience method to translate to user's language"""
        return self.translate(text=text, to_english=False)
    
    def get_msgs(self) -> None:
        """
        Get all static messages translated to the target langauge.
        
        Returns:
            Dictionary of message keys to translated strings
        """
        if self.message_cache:
            return self.message_cache
        
        for key, message in MESSAGES.items():
            self.message_cache[key] = self.to_user_language(message)
