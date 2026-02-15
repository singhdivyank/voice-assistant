"""Unit tests for translation service"""

from unittest.mock import patch, MagicMock

from src.services.translation import TranslationService
from src.config.settings import Language


class TestTranslationService:
    def test_is_english(self):
        """Test English language detection"""
        service = TranslationService(Language.ENGLISH)
        assert service.is_english
        
        service = TranslationService(Language.HINDI)
        assert not service.is_english

    def test_translate_empty_text(self):
        """Test handling of empty text"""
        service = TranslationService(Language.SPANISH)
        
        assert service.translate("") == ""
        assert service.translate("  ") == "  "

    def test_translate_english_passthrough(self):
        """Test that English text passes through unchanged"""
        service = TranslationService(Language.ENGLISH)
        
        text = "Hello, how are you?"
        assert service.translate(text) == text
        assert service.to_english(text) == text

    @patch('src.services.translation.GoogleTranslator')
    def test_translate_to_user_language(self, mock_translator_class):
        """Test translation to user language"""
        mock_translator = MagicMock()
        mock_translator.translate.return_value = "Hola, cómo estás?"
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService(Language.SPANISH)
        result = service.to_user_language("Hello, how are you?")
        
        mock_translator_class.assert_called_with(source="en", target="es")
        assert result == "Hola, cómo estás?"