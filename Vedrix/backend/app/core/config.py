from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Vedrix"
    
    # Security
    SECRET_KEY: str = "change-me-in-production-use-env-file"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./vedrix.db"
    DB_SSL_MODE: str = "require"  # PostgreSQL SSL mode: "disable", "require", "verify-full"
    
    # AI API Keys
    GROQ_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    APIFREE_API_KEY: str = ""
    
    # OpenRouter Base URLs
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    APIFREE_BASE_URL: str = "https://apifreellm.com/api/v1"

    # Email
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM_NAME: str = "Vedrix AI"
    FRONTEND_URL: str = "http://localhost:5173"

    # Judge0 Code Execution
    JUDGE0_URL: str = "https://judge0-ce.p.rapidapi.com"
    JUDGE0_API_KEY: str = ""

    # Supabase (optional — mirrors data to Postgres when configured)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""   # use the publishable/anon key or service key

    # Redis for caching
    REDIS_URL: str = "redis://localhost:6379/0"

    # Environment
    ENVIRONMENT: str = "development"  # "development" or "production"

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()

# Bulletproof fix: Ensure SQLite URL uses aiosqlite for async support
if settings.DATABASE_URL.startswith("sqlite://"):
    import logging
    logging.warning(
        f"config.py: Detected 'sqlite://' in DATABASE_URL. "
        f"Auto-fixing to 'sqlite+aiosqlite://' for async support. "
        f"Use 'sqlite+aiosqlite://' in your .env to silence this warning."
    )
    settings.DATABASE_URL = settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://", 1)
