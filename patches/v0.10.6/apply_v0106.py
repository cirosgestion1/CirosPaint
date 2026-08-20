from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply_v0106.py <build_source>")

    root = Path(sys.argv[1]).resolve()
    config_path = root / "app" / "core" / "config.py"
    text = config_path.read_text(encoding="utf-8")
    old = 'APP_VERSION = "0.10.5"'
    new = 'APP_VERSION = "0.10.6"'
    if old not in text:
        raise RuntimeError("Expected Ciros Paint 0.10.5 version marker was not found")
    config_path.write_text(text.replace(old, new, 1), encoding="utf-8")

    requirements_path = root / "requirements.txt"
    requirements = requirements_path.read_text(encoding="utf-8") if requirements_path.is_file() else ""
    if "google-genai" not in requirements.casefold():
        if requirements and not requirements.endswith("\n"):
            requirements += "\n"
        requirements += "google-genai>=1,<2\n"
        requirements_path.write_text(requirements, encoding="utf-8")

    obsolete_test = root / "tests" / "test_assistant_ui_v0105.py"
    if obsolete_test.exists():
        obsolete_test.unlink()

    required = (
        root / "app" / "services" / "assistant_gemini_service.py",
        root / "app" / "services" / "assistant_async_tasks.py",
        root / "app" / "services" / "assistant_session_store.py",
        root / "app" / "ui" / "pages" / "assistant_page.py",
        root / "app" / "ui" / "pages" / "settings_page.py",
        root / "app" / "ui" / "dialogs" / "assistant_info_dialog.py",
        root / "tests" / "test_assistant_gemini_v0106.py",
        root / "tests" / "test_assistant_ui_v0106.py",
    )
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"0.10.6 overlay file was not copied: {path}")

    print("Ciros Paint 0.10.6 functional Gemini assistant overlay applied")


if __name__ == "__main__":
    main()
