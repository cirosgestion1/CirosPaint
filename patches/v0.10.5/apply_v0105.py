from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply_v0105.py <build_source>")

    root = Path(sys.argv[1]).resolve()
    config_path = root / "app" / "core" / "config.py"
    text = config_path.read_text(encoding="utf-8")
    old = 'APP_VERSION = "0.10.4"'
    new = 'APP_VERSION = "0.10.5"'
    if old not in text:
        raise RuntimeError("Expected Ciros Paint 0.10.4 version marker was not found")
    config_path.write_text(text.replace(old, new, 1), encoding="utf-8")

    required = (
        root / "app" / "ui" / "pages" / "assistant_page.py",
        root / "app" / "ui" / "pages" / "settings_page.py",
        root / "app" / "ui" / "dialogs" / "assistant_info_dialog.py",
    )
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"0.10.5 overlay file was not copied: {path}")

    print("Ciros Paint 0.10.5 assistant/settings overlay applied")


if __name__ == "__main__":
    main()
