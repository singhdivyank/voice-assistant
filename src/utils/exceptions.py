"""Custom Exceptions for the applications"""


class DocJarvisError(Exception):
    """Base exception for DocJarvis application"""
    pass


class AudioError(DocJarvisError):
    """Exception raised for audio-related errors"""
    pass


class TranscriptionError(AudioError):
    """Exception raised when speech-to-text fails"""
    pass


class TextToSpeechError(AudioError):
    """Exception raised when text-to-speech fails"""
    pass


class NetworkError(DocJarvisError):
    """Exception raised for network connectivity issues"""
    pass


class TranslationError(DocJarvisError):
    """Exception raised when translation fails"""
    pass


class LLMError(DocJarvisError):
    """Exception raised for LLM-related errors"""
    pass


class DiagnosisError(LLMError):
    """Exception raised when diagnosis generation fails"""
    pass


class MedicationError(LLMError):
    """Exception raised when medication recommendation fails"""
    pass


class FileOperationError(DocJarvisError):
    """Exception raised for file operations failure"""
    pass


class ConfigurationError(DocJarvisError):
    """Exception raised for configuration issues"""
    pass