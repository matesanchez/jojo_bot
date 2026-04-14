"""
config.py — Load and validate all environment variables for Jojo Bot.
"""
import os
from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()


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

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Convenience export
settings = get_settings()
