"""
app/core/config.py

Central configuration module for EduSync ERP.
All settings are loaded from environment variables via Pydantic BaseSettings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Pydantic automatically reads values from the .env file.
    """

    # ──────────────────────────────────────────────
    # Project Information
    # ──────────────────────────────────────────────
    PROJECT_NAME: str = "EduSync — Smart Campus ERP"
    API_VERSION: str = "v1"

    # ──────────────────────────────────────────────
    # MongoDB Configuration
    # ──────────────────────────────────────────────
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "edusync_db"

    # ──────────────────────────────────────────────
    # JWT Authentication Configuration
    # ──────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ──────────────────────────────────────────────
    # College Domain Restriction
    # ──────────────────────────────────────────────
    COLLEGE_EMAIL_DOMAIN: str = "college.edu"  # Change to your college domain

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings object.
    Using lru_cache ensures the .env file is read only once,
    improving performance on repeated calls.
    """
    return Settings()


# A module-level settings instance for convenient direct imports.
settings = get_settings()
