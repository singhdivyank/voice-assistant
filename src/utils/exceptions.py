"""Custom Exceptions for the applications"""


class DocJarvisError(Exception):
    """Base exception for DocJarvis application"""


class AudioError(DocJarvisError):
    """Exception raised for audio-related errors"""


class TranscriptionError(AudioError):
    """Exception raised when speech-to-text fails"""


class TextToSpeechError(AudioError):
    """Exception raised when text-to-speech fails"""


class NetworkError(DocJarvisError):
    """Exception raised for network connectivity issues"""


class TranslationError(DocJarvisError):
    """Exception raised when translation fails"""


class LLMError(DocJarvisError):
    """Exception raised for LLM-related errors"""


class DiagnosisError(LLMError):
    """Exception raised when diagnosis generation fails"""


class MedicationError(LLMError):
    """Exception raised when medication recommendation fails"""


class FileOperationError(DocJarvisError):
    """Exception raised for file operations failure"""


class ConfigurationError(DocJarvisError):
    """Exception raised for configuration issues"""
