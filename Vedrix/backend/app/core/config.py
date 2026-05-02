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

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()

# Bulletproof fix: Ensure SQLite URL uses aiosqlite for async support
if settings.DATABASE_URL.startswith("sqlite://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://", 1)
