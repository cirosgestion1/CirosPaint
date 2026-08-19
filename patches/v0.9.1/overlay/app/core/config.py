from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "CirosPaint"
DISPLAY_NAME = "Ciros Paint"
APP_VERSION = "0.9.1"


def app_data_dir() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        root = Path(local_app_data) / APP_NAME
    else:
        root = Path.home() / f".{APP_NAME.lower()}"
    root.mkdir(parents=True, exist_ok=True)
    return root


DATA_DIR = app_data_dir()
DATABASE_PATH = DATA_DIR / "ciros_paint.db"
IMAGES_DIR = DATA_DIR / "images"
BACKUPS_DIR = DATA_DIR / "backups"
IMAGES_DIR.mkdir(exist_ok=True)
BACKUPS_DIR.mkdir(exist_ok=True)
