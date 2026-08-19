from __future__ import annotations

import json
import os
from pathlib import Path

from app.core.config import DATA_DIR

SETTINGS_PATH = DATA_DIR / "settings.json"
YOUTUBE_ENV_KEY = "CIROS_YOUTUBE_API_KEY"


class SettingsStore:
    """Small local settings store for credentials and UI preferences."""

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
    def favorite_category(cls, video_id: str) -> tuple[str | None, bool]:
        records = cls._load().get("favorite_categories", {})
        if not isinstance(records, dict):
            return None, False
        record = records.get(video_id)
        if isinstance(record, str):
            return record.strip() or None, True
        if not isinstance(record, dict):
            return None, False
        category = str(record.get("category", "")).strip() or None
        return category, bool(record.get("manual", False))

    @classmethod
    def set_favorite_category(cls, video_id: str, category: str, *, manual: bool) -> None:
        data = cls._load()
        records = data.get("favorite_categories")
        if not isinstance(records, dict):
            records = {}
            data["favorite_categories"] = records
        records[video_id] = {"category": category.strip(), "manual": bool(manual)}
        cls._save(data)

    @classmethod
    def remove_favorite_category(cls, video_id: str) -> None:
        data = cls._load()
        records = data.get("favorite_categories")
        if not isinstance(records, dict) or video_id not in records:
            return
        records.pop(video_id, None)
        if not records:
            data.pop("favorite_categories", None)
        cls._save(data)

    @classmethod
    def settings_path(cls) -> Path:
        return SETTINGS_PATH
