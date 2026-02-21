"""Application configurations and settings."""

from pathlib import Path
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings

from src.utils.consts import Environment


class Settings(BaseSettings):
    """Main application settings"""

    # Application
    app_name: str = "DocJarvis"
    app_version: str = "2.0.0"
    environment: Environment = Environment.DEV
    debug: bool = Field(default=True)

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent
    output_dir: Path = Field(default_factory=lambda: Path("outputs"))
    audio_dir: Path = Field(default_factory=lambda: Path("outputs/audio"))
    prescription_dir: Path = Field(default_factory=lambda: Path("outputs/prescriptions"))

    # LLM Configurations
    name: str = "DocJarvis-llm"
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_model: str = "gemini-pro"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048

    # LangSmith monitoring
    langsmith_api_key: Optional[str] = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = "docjarvis"
    langsmith_tracing: bool = True

    # OpenTelemetry
    otel_service_name: str = "docjarvis-backend"
    otel_exporter_endpoint: str = "http://localhost:4317"
    otel_enabled: bool = True

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    session_ttl: int = 3600

    
    class Config:
        """Pydantic configuration"""

        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def setup_dir(self) -> None:
        """Create necessary dictionaries"""
        for dir_path in [self.output_dir, self.audio_dir, self.prescription_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""

    settings = Settings()
    settings.setup_dir()
    return settings
