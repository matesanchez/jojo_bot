"""
config.py — Load and validate all environment variables for Jojo Bot.
"""
import os
from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

VALID_INSTRUMENTS = {
    "pure", "go", "avant", "start", "pilot_600",
    "basic", "prime", "process", "fplc", "explorer", "purifier", "unicorn", "general",
}


class Settings(BaseSettings):
    # Claude API
    anthropic_api_key: SecretStr

    # ChromaDB
    chroma_db_path: str = "./chroma_db"

    # Manuals directory
    manuals_dir: str = "./data/manuals"

    # SQLite database
    database_url: str = "sqlite+aiosqlite:///./jojobot.db"

    # CORS — comma-separated list of allowed origins
    cors_origins: str = "http://localhost:3000"

    # Logging
    log_level: str = "info"

    # Claude model — centralised here so both generator & protocol_generator import it
    claude_model: str = "claude-sonnet-4-20250514"

    # Environment flag
    environment: str = "development"  # "development" | "production"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        upper = v.upper()
        if upper not in VALID_LOG_LEVELS:
            raise ValueError(f"Invalid log_level '{v}'. Must be one of: {VALID_LOG_LEVELS}")
        return upper

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
