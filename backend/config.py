"""Application configuration using Pydantic settings."""

import os
from enum import Enum
from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class DeploymentMode(Enum):
    """Deployment mode for document processing."""

    CLOUD = "cloud"
    LOCAL = "local"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = (
        "postgresql://postgres:postgres@localhost:5432/community_resilience"
    )
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "community_resilience"

    # LLM Configuration
    llm_provider: Literal["ollama", "openai", "groq"] = "ollama"
    llm_model: str = "llama3.2"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # JWT Configuration
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION-use-secure-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # OAuth - Google (accepts GOOGLE_CLIENT_ID or GOOGLE_OAUTH_CLIENT_ID)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback/google"

    # OAuth - GitHub (accepts GITHUB_CLIENT_ID or GITHUB_OAUTH_CLIENT_ID)
    github_client_id: str = ""
    github_client_secret: str = ""
    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/auth/callback/github"

    # OAuth - Microsoft (accepts MICROSOFT_CLIENT_ID or MICROSOFT_OAUTH_CLIENT_ID)
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_oauth_client_id: str = ""
    microsoft_oauth_client_secret: str = ""
    microsoft_redirect_uri: str = "http://localhost:8000/auth/callback/microsoft"

    # Frontend URL (for OAuth redirects)
    frontend_url: str = "http://localhost:5173"

    # API Key settings
    api_key_prefix: str = "cr_"

    model_config = SettingsConfigDict(
        env_file=[".env", "../.env"],  # Check both backend and project root
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Deployment configuration
    DEPLOYMENT_MODE: str = "cloud"

    # Document processing feature flags
    DOCLING_ENABLED: bool = True
    FULL_OCR_ENABLED: bool = True
    OFFICE_CONVERSION_ENABLED: bool = True

    # Processing limits
    MAX_UPLOAD_SIZE_MB: int = 50
    PROCESS_TIMEOUT_SECONDS: int = 300

    @property
    def effective_google_client_id(self) -> str:
        """Return Google client ID from either naming convention."""
        return self.google_client_id or self.google_oauth_client_id

    @property
    def effective_google_client_secret(self) -> str:
        """Return Google client secret from either naming convention."""
        return self.google_client_secret or self.google_oauth_client_secret

    @property
    def effective_github_client_id(self) -> str:
        """Return GitHub client ID from either naming convention."""
        return self.github_client_id or self.github_oauth_client_id

    @property
    def effective_github_client_secret(self) -> str:
        """Return GitHub client secret from either naming convention."""
        return self.github_client_secret or self.github_oauth_client_secret

    @property
    def effective_microsoft_client_id(self) -> str:
        """Return Microsoft client ID from either naming convention."""
        return self.microsoft_client_id or self.microsoft_oauth_client_id

    @property
    def effective_microsoft_client_secret(self) -> str:
        """Return Microsoft client secret from either naming convention."""
        return self.microsoft_client_secret or self.microsoft_oauth_client_secret

    @property
    def deployment_mode(self) -> DeploymentMode:
        """Get deployment mode as enum."""
        return DeploymentMode(self.DEPLOYMENT_MODE)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()


# =============================================================================
# Deployment Configuration
# =============================================================================


class DeploymentConfig:
    """
    Central configuration based on deployment mode.

    Cloud mode (Render free tier):
    - Basic PDF text extraction only (PyMuPDF)
    - No OCR, no Office document conversion
    - Documents queued for full processing by local instances

    Local mode:
    - Full Docling processing
    - Tesseract OCR for scanned documents
    - LibreOffice for Office document conversion
    - Structured section extraction
    """

    # Deployment mode from environment
    DEPLOYMENT_MODE: DeploymentMode = DeploymentMode(
        os.getenv("DEPLOYMENT_MODE", "cloud").lower()
    )

    # Feature flags based on deployment mode
    DOCLING_ENABLED: bool = DEPLOYMENT_MODE == DeploymentMode.LOCAL
    FULL_OCR_ENABLED: bool = DEPLOYMENT_MODE == DeploymentMode.LOCAL
    OFFICE_CONVERSION_ENABLED: bool = DEPLOYMENT_MODE == DeploymentMode.LOCAL
    STRUCTURED_EXTRACTION_ENABLED: bool = DEPLOYMENT_MODE == DeploymentMode.LOCAL

    # Processing settings - more generous limits for local deployment
    MAX_UPLOAD_SIZE_MB: int = 50 if DEPLOYMENT_MODE == DeploymentMode.LOCAL else 10
    PROCESS_TIMEOUT_SECONDS: int = (
        300 if DEPLOYMENT_MODE == DeploymentMode.LOCAL else 30
    )

    # Supported file types per mode
    CLOUD_SUPPORTED_EXTENSIONS: set = {".pdf", ".txt", ".md"}
    LOCAL_SUPPORTED_EXTENSIONS: set = {
        ".pdf",
        ".txt",
        ".md",
        ".docx",
        ".doc",
        ".pptx",
        ".ppt",
        ".xlsx",
        ".xls",
        ".html",
        ".htm",
        ".rtf",
        ".odt",
        ".odp",
        ".ods",
    }

    @classmethod
    def get_supported_extensions(cls) -> set:
        """Return supported file extensions for current deployment mode."""
        if cls.DEPLOYMENT_MODE == DeploymentMode.LOCAL:
            return cls.LOCAL_SUPPORTED_EXTENSIONS
        return cls.CLOUD_SUPPORTED_EXTENSIONS

    @classmethod
    def is_file_supported(cls, filename: str) -> bool:
        """Check if file type is supported in current deployment mode."""
        ext = os.path.splitext(filename)[1].lower()
        return ext in cls.get_supported_extensions()

    @classmethod
    def needs_local_processing(cls, filename: str) -> bool:
        """
        Check if file requires local processing.

        Returns True if:
        - We're in cloud mode AND
        - File type is not supported in cloud mode
        """
        if cls.DEPLOYMENT_MODE == DeploymentMode.LOCAL:
            return False

        ext = os.path.splitext(filename)[1].lower()
        return ext not in cls.CLOUD_SUPPORTED_EXTENSIONS

    @classmethod
    def get_config_summary(cls) -> dict:
        """Return configuration summary for debugging/health checks."""
        return {
            "deployment_mode": cls.DEPLOYMENT_MODE.value,
            "docling_enabled": cls.DOCLING_ENABLED,
            "ocr_enabled": cls.FULL_OCR_ENABLED,
            "office_conversion_enabled": cls.OFFICE_CONVERSION_ENABLED,
            "max_upload_size_mb": cls.MAX_UPLOAD_SIZE_MB,
            "process_timeout_seconds": cls.PROCESS_TIMEOUT_SECONDS,
            "supported_extensions": list(cls.get_supported_extensions()),
        }


# =============================================================================
# Sync Configuration
# =============================================================================


class SyncConfig:
    """Configuration for cloud-local synchronization."""

    SYNC_ENABLED: bool = os.getenv("SYNC_ENABLED", "false").lower() == "true"
    SYNC_SERVER_URL: Optional[str] = os.getenv("SYNC_SERVER_URL")
    SYNC_API_KEY: Optional[str] = os.getenv("SYNC_API_KEY")
    SYNC_INTERVAL_MINUTES: int = int(os.getenv("SYNC_INTERVAL_MINUTES", "15"))

    @classmethod
    def is_valid(cls) -> bool:
        """Check if sync configuration is valid."""
        if not cls.SYNC_ENABLED:
            return True  # Sync disabled is valid
        return bool(cls.SYNC_SERVER_URL and cls.SYNC_API_KEY)


# =============================================================================
# Database Configuration
# =============================================================================


class DatabaseConfig:
    """Database connection configuration."""

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/community_resilience",
    )

    # Connection pool settings
    POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))


# =============================================================================
# LLM Configuration
# =============================================================================


class LLMConfig:
    """LLM provider configuration."""

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")  # "groq" or "ollama"

    # Groq settings (cloud)
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # Ollama settings (local)
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")

    @classmethod
    def get_active_provider(cls) -> str:
        """Return the active LLM provider."""
        return cls.LLM_PROVIDER

    @classmethod
    def is_configured(cls) -> bool:
        """Check if LLM is properly configured."""
        if cls.LLM_PROVIDER == "groq":
            return bool(cls.GROQ_API_KEY)
        return True  # Ollama doesn't require API key


# =============================================================================
# Embedding Configuration
# =============================================================================


class EmbeddingConfig:
    """Embedding model configuration."""

    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))
