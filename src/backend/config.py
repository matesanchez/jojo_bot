"""
config.py — Load and validate all environment variables for Jojo Bot.

API key priority order:
  1. %APPDATA%/JojoBot/config.json   (set via the in-app Settings panel)
  2. ANTHROPIC_API_KEY env var / .env file
  3. None — backend starts fine, returns a helpful error on first chat
"""
from __future__ import annotations

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
    # Claude API — optional at startup; can be supplied later via Settings panel
    anthropic_api_key: SecretStr | None = None

    # ChromaDB
    chroma_db_path: str = "./chroma_db"

    # Manuals directory (base knowledge base)
    manuals_dir: str = "./data/manuals"

    # User-uploaded documents directory
    user_documents_dir: str = "./data/user_documents"

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


def get_api_key() -> str | None:
    """
    Return the active Anthropic API key, checking AppData first then .env.

    This is intentionally NOT cached — the user can update the key at runtime
    via the Settings panel without restarting the server.
    """
    # 1. Check user's local AppData config (set via Settings panel)
    try:
        from appdata import load_api_key
        key = load_api_key()
        if key:
            return key
    except Exception:
        pass

    # 2. Fall back to .env / environment variable
    s = get_settings()
    if s.anthropic_api_key:
        return s.anthropic_api_key.get_secret_value()

    return None
