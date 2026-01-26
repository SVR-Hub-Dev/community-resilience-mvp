"""Application configuration using Pydantic settings."""

from pydantic_settings import BaseSettings
from typing import Literal
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/community_resilience"

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

    # OAuth - Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback/google"

    # OAuth - GitHub
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/auth/callback/github"

    # Frontend URL (for OAuth redirects)
    frontend_url: str = "http://localhost:5173"

    # API Key settings
    api_key_prefix: str = "cr_"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
