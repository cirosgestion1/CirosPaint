from __future__ import annotations

import sys
from pathlib import Path


def _patch_gemini_runtime(root: Path) -> None:
    path = root / "app" / "services" / "assistant_gemini_service.py"
    text = path.read_text(encoding="utf-8")

    status_check = '''            if getattr(interaction, "status", "completed") not in {None, "completed"}:
                raise GeminiAssistantError("unexpected_status", "Gemini respondió, pero la comprobación no terminó correctamente.")
'''
    text = text.replace(status_check, "")

    text = text.replace(
        'if mime_type not in accepted or len(raw) > 15 * 1024 * 1024:',
        'if mime_type not in accepted or len(raw) > 14 * 1024 * 1024:',
    )
    text = text.replace(
        'if len(raw) > 19 * 1024 * 1024:',
        'if len(raw) > 14 * 1024 * 1024:',
    )
    text = text.replace(
        'return dumper(mode="json", exclude_none=True)',
        'return dumper(mode="json")',
    )
    text = text.replace(
        'return dumper(exclude_none=True)',
        'return dumper()',
    )
    path.write_text(text, encoding="utf-8")


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
        requirements += "google-genai>=2.3,<3\n"
        requirements_path.write_text(requirements, encoding="utf-8")

    notices_path = root / "THIRD_PARTY_NOTICES.txt"
    if notices_path.is_file():
        notices = notices_path.read_text(encoding="utf-8")
        marker = "Google Gen AI Python SDK"
        if marker not in notices:
            if notices and not notices.endswith("\n"):
                notices += "\n"
            notices += (
                "\nGoogle Gen AI Python SDK (google-genai)\n"
                "Copyright Google LLC\n"
                "Licensed under the Apache License, Version 2.0.\n"
                "Source: https://github.com/googleapis/python-genai\n"
            )
            notices_path.write_text(notices, encoding="utf-8")

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

    _patch_gemini_runtime(root)

    runtime = (root / "app" / "services" / "assistant_gemini_service.py").read_text(encoding="utf-8")
    if 'len(raw) > 14 * 1024 * 1024' not in runtime:
        raise RuntimeError("0.10.6 Gemini inline image safety patch was not applied")
    if 'getattr(interaction, "status"' in runtime:
        raise RuntimeError("0.10.6 obsolete Gemini interaction status check is still present")

    print("Ciros Paint 0.10.6 functional Gemini assistant overlay applied")


if __name__ == "__main__":
    main()
