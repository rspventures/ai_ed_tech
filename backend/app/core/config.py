"""
AI Tutor Platform - Core Configuration
Pydantic Settings for application configuration with environment variable support
"""
from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Sentinel default that must never be used in a deployed environment.
INSECURE_SECRET_KEY_DEFAULT = "your-super-secret-key-change-in-production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "AI Tutor Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ai_tutor"
    
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # LLM Configuration
    LLM_PROVIDER: Literal["openai", "anthropic"] = "openai"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # OpenAI specific
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Anthropic specific
    # NOTE: claude-3-sonnet-20240229 was retired and 404s. Current, cost-effective
    # default; the LiteLLM model router (Phase 2) supersedes this per-workload.
    ANTHROPIC_MODEL: str = "claude-haiku-4-5"
    
    # LLM Performance
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_MAX_RETRIES: int = 3
    
    # Hybrid Search
    COHERE_API_KEY: str = ""  # For reranking - optional

    # NOTE (Phase 2 subtraction): Neo4j/Graph RAG, Arize Phoenix, Sarvam and the
    # OpenAI-TTS fallback were removed. Their settings blocks are gone; ElevenLabs
    # is the voice provider. Sarvam/Bhashini may return in Phase 5 for Indic voice.

    # ElevenLabs TTS (Primary - High Quality)
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE: str = "rachel"  # Warm, friendly female voice
    ELEVENLABS_MODEL: str = "turbo"  # eleven_turbo_v2_5 for low latency
    ELEVENLABS_STABILITY: float = 0.5  # Lower = more expressive
    ELEVENLABS_SIMILARITY: float = 0.75  # Higher = more consistent
    
    # CORS - stored as comma-separated string
    CORS_ORIGINS_STR: str = "http://localhost:3000,http://localhost:5173"

    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS_STR.split(",") if origin.strip()]

    @property
    def CORS_ALLOW_CREDENTIALS(self) -> bool:
        """
        Credentials MUST NOT be sent with a wildcard origin — browsers reject the
        combination and it is a security anti-pattern. Only allow credentials when
        explicit origins are configured.
        """
        return "*" not in self.CORS_ORIGINS

    # Rate limiting (slowapi) — defense against brute-force and paid-endpoint abuse.
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "200/minute"          # global fallback per client IP
    RATE_LIMIT_AUTH: str = "10/minute"              # login/register/refresh per IP
    RATE_LIMIT_AI: str = "30/minute"                # LLM/image/TTS endpoints per IP
    RATE_LIMIT_STORAGE_URI: str = ""                # e.g. redis://... ; empty = in-memory

    @model_validator(mode="after")
    def _enforce_secure_production(self) -> "Settings":
        """Fail fast on insecure configuration in deployed (non-dev) environments."""
        if self.ENVIRONMENT != "development":
            problems: list[str] = []
            if self.SECRET_KEY == INSECURE_SECRET_KEY_DEFAULT or len(self.SECRET_KEY) < 32:
                problems.append(
                    "SECRET_KEY must be set to a strong random value "
                    "(>=32 chars, not the built-in default)"
                )
            if self.DEBUG:
                problems.append("DEBUG must be false outside development")
            if "*" in self.CORS_ORIGINS:
                problems.append(
                    "CORS_ORIGINS_STR must list explicit origins (no '*') outside development"
                )
            if problems:
                raise ValueError(
                    f"Insecure configuration for ENVIRONMENT={self.ENVIRONMENT}: "
                    + "; ".join(problems)
                )
        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
