from __future__ import annotations

import json
from pathlib import Path

from app.core.config import app_data_dir


class AssistantSettingsStore:
    """Local-only settings used by the assistant UI.

    The Gemini key is never committed to the repository and never embedded in
    the executable. It is stored under the normal Ciros Paint application-data
    directory so changing the key does not require rebuilding the application.
    """

    FILE_NAME = "assistant_settings.json"

    @classmethod
    def _path(cls) -> Path:
        return app_data_dir() / cls.FILE_NAME

    @classmethod
    def _read(cls) -> dict:
        path = cls._path()
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        return data if isinstance(data, dict) else {}

    @classmethod
    def gemini_api_key(cls) -> str:
        return str(cls._read().get("gemini_api_key", "") or "").strip()

    @classmethod
    def set_gemini_api_key(cls, api_key: str) -> None:
        path = cls._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = cls._read()
        normalized = str(api_key or "").strip()
        if normalized:
            data["gemini_api_key"] = normalized
        else:
            data.pop("gemini_api_key", None)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    @classmethod
    def clear_gemini_api_key(cls) -> None:
        cls.set_gemini_api_key("")
