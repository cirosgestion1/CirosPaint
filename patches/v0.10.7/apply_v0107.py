from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply_v0107.py <build_source>")
    root = Path(sys.argv[1]).resolve()

    config_path = root / "app" / "core" / "config.py"
    text = config_path.read_text(encoding="utf-8")
    old = 'APP_VERSION = "0.10.6"'
    new = 'APP_VERSION = "0.10.7"'
    if old not in text:
        raise RuntimeError("Expected Ciros Paint 0.10.6 version marker was not found")
    config_path.write_text(text.replace(old, new, 1), encoding="utf-8")

    for obsolete in (
        root / "tests" / "test_assistant_gemini_v0106.py",
        root / "tests" / "test_assistant_ui_v0106.py",
    ):
        if obsolete.exists():
            obsolete.unlink()

    required = (
        root / "app" / "services" / "assistant_local_service.py",
        root / "app" / "services" / "assistant_gemini_service.py",
        root / "app" / "services" / "assistant_async_tasks.py",
        root / "app" / "services" / "assistant_session_store.py",
        root / "app" / "ui" / "pages" / "assistant_page.py",
        root / "app" / "ui" / "dialogs" / "assistant_info_dialog.py",
        root / "tests" / "test_assistant_local_v0107.py",
        root / "tests" / "test_assistant_gemini_v0107.py",
        root / "tests" / "test_assistant_ui_v0107.py",
    )
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"0.10.7 overlay file was not copied: {path}")

    local = (root / "app" / "services" / "assistant_local_service.py").read_text(encoding="utf-8")
    gemini = (root / "app" / "services" / "assistant_gemini_service.py").read_text(encoding="utf-8")
    page = (root / "app" / "ui" / "pages" / "assistant_page.py").read_text(encoding="utf-8")
    checks = (
        ("AssistantLocalService", local),
        ('"thinking_level": "low"', gemini),
        ("total_input_tokens", gemini),
        ("resolve_miniature_name", gemini),
        ("Consulta local · 0 tokens Gemini", page),
        ("QCompleter", page),
        ("setMarkdown", page),
    )
    for marker, source in checks:
        if marker not in source:
            raise RuntimeError(f"0.10.7 verification marker missing: {marker}")

    print("Ciros Paint 0.10.7 local-first assistant overlay applied")


if __name__ == "__main__":
    main()
