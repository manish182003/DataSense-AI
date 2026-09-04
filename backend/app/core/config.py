"""
DataSense Configuration Settings
Handles environment variables and core application settings using Pydantic BaseSettings.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "DataSense"
    DEBUG: bool = True
    
    # Storage settings
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
    DUCKDB_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "datasense.duckdb")
    
    # LLM Settings (Groq API)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "groq/compound-mini")
    LARGE_LLM_MODEL: str = os.getenv("LARGE_LLM_MODEL", "qwen/qwen3.6-27b")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
