"""
appdata.py — Platform-aware local storage for per-user Jojo Bot configuration.

Storage locations:
  Windows  → %APPDATA%\\JojoBot\\config.json
  macOS    → ~/Library/Application Support/JojoBot/config.json
  Linux    → ~/.config/JojoBot/config.json

This file is intentionally outside the app install folder so it is never
included when the app package is copied or shared with colleagues.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def get_config_dir() -> Path:
    """Return the platform-appropriate config directory for JojoBot."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else (Path.home() / ".config")
    return Path(base) / "JojoBot"


def get_config_path() -> Path:
    return get_config_dir() / "config.json"


# ---------------------------------------------------------------------------
# Low-level read / write
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    path = get_config_path()
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Could not read AppData config at %s: %s", path, exc)
        return {}


def _save_config(data: dict) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file first, then rename for atomicity
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(path)
    except Exception as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_api_key() -> str | None:
    """Return the stored Anthropic API key, or None if not set."""
    return _load_config().get("anthropic_api_key") or None


def save_api_key(api_key: str) -> None:
    """Persist the API key to the user's local config (never in the app folder)."""
    config = _load_config()
    config["anthropic_api_key"] = api_key.strip()
    _save_config(config)
    logger.info("API key saved to %s", get_config_path())


def get_masked_key() -> str | None:
    """Return a display-safe masked version of the stored key, e.g. sk-ant-api0•••••••••."""
    key = load_api_key()
    if not key:
        return None
    visible = key[:14] if len(key) >= 14 else key
    return f"{visible}{'•' * 8}"


def delete_api_key() -> None:
    """Remove the stored API key (e.g. for a 'sign out' flow)."""
    config = _load_config()
    config.pop("anthropic_api_key", None)
    _save_config(config)
