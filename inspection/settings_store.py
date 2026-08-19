from __future__ import annotations

import json
import os
from pathlib import Path

from app.core.config import DATA_DIR

SETTINGS_PATH = DATA_DIR / "settings.json"
YOUTUBE_ENV_KEY = "CIROS_YOUTUBE_API_KEY"


class SettingsStore:
    """Very small local settings store.

    API credentials are never bundled in the executable. 0.9.0 stores the
    YouTube Data API key in the user's local Ciros Paint data directory; a
    Windows credential-backed secret store can replace this implementation
    later without changing the tutorial-search API.
    """

    @staticmethod
    def _load() -> dict:
        if not SETTINGS_PATH.exists():
            return {}
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _save(data: dict) -> None:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        temp = SETTINGS_PATH.with_suffix(".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(SETTINGS_PATH)

    @classmethod
    def youtube_api_key(cls) -> str:
        env_key = os.getenv(YOUTUBE_ENV_KEY, "").strip()
        if env_key:
            return env_key
        return str(cls._load().get("youtube_api_key", "")).strip()

    @classmethod
    def set_youtube_api_key(cls, api_key: str) -> None:
        data = cls._load()
        value = api_key.strip()
        if value:
            data["youtube_api_key"] = value
        else:
            data.pop("youtube_api_key", None)
        cls._save(data)

    @classmethod
    def settings_path(cls) -> Path:
        return SETTINGS_PATH
