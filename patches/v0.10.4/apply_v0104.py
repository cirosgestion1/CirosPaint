from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply_v0104.py <build_source>")

    root = Path(sys.argv[1]).resolve()
    config_path = root / "app" / "core" / "config.py"
    text = config_path.read_text(encoding="utf-8")
    old = 'APP_VERSION = "0.10.3"'
    new = 'APP_VERSION = "0.10.4"'
    if old not in text:
        raise RuntimeError("Expected Ciros Paint 0.10.3 version marker was not found")
    config_path.write_text(text.replace(old, new, 1), encoding="utf-8")

    assistant_page = root / "app" / "ui" / "pages" / "assistant_page.py"
    if not assistant_page.is_file():
        raise RuntimeError("0.10.4 assistant page overlay was not copied")

    settings_store = root / "app" / "services" / "assistant_settings_store.py"
    if not settings_store.is_file():
        raise RuntimeError("0.10.4 assistant settings store overlay was not copied")

    print("Ciros Paint 0.10.4 visual assistant overlay applied")


if __name__ == "__main__":
    main()
