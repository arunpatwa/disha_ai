"""Application configuration."""
# Using Pydantic for settings - auto loads from .env file
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """App config - everything loaded from .env file"""
    
    # Database - using SQLite by default (works everywhere, no setup needed)
    DATABASE_URL: str = "sqlite:///./disha_ai.db"
    
    # Redis - not using yet but might need for caching later
    REDIS_URL: Optional[str] = None
    
    # LLM config - add your API key to .env
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "openai"  # can be: openai, anthropic, or demo
    
    # Token limits - GPT-4 has 8k context window, keeping 1k for response
    MAX_CONTEXT_TOKENS: int = 8000
    MAX_RESPONSE_TOKENS: int = 1000
    MESSAGES_PER_PAGE: int = 50
    
    # App settings
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True  # OPENAI_API_KEY != openai_api_key


settings = Settings()
