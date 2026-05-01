from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Vedrix"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-for-dev")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/vedrix")
    
    # AI API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    APIFREE_API_KEY: str = os.getenv("APIFREE_API_KEY", "")
    
    # OpenRouter Base URLs
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    class Config:
        case_sensitive = True

settings = Settings()
