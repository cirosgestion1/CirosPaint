from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply_v0108.py <build_source>")
    root = Path(sys.argv[1]).resolve()

    config_path = root / "app" / "core" / "config.py"
    text = config_path.read_text(encoding="utf-8")
    old = 'APP_VERSION = "0.10.7"'
    new = 'APP_VERSION = "0.10.8"'
    if old not in text:
        raise RuntimeError("Expected Ciros Paint 0.10.7 version marker was not found")
    config_path.write_text(text.replace(old, new, 1), encoding="utf-8")

    required = (
        root / "app" / "services" / "assistant_entity_resolver.py",
        root / "app" / "services" / "assistant_workflow_service.py",
        root / "app" / "services" / "assistant_local_service.py",
        root / "app" / "services" / "assistant_gemini_service.py",
        root / "app" / "services" / "assistant_settings_store.py",
        root / "app" / "services" / "assistant_async_tasks.py",
        root / "app" / "ui" / "pages" / "assistant_page.py",
        root / "app" / "ui" / "pages" / "settings_page.py",
        root / "app" / "ui" / "dialogs" / "assistant_info_dialog.py",
        root / "tests" / "test_assistant_architecture_v0108.py",
        root / "tests" / "test_assistant_gemini_v0108.py",
        root / "tests" / "test_assistant_ui_v0108.py",
    )
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"0.10.8 overlay file was not copied: {path}")

    resolver = (root / "app" / "services" / "assistant_entity_resolver.py").read_text(encoding="utf-8")
    workflow = (root / "app" / "services" / "assistant_workflow_service.py").read_text(encoding="utf-8")
    local = (root / "app" / "services" / "assistant_local_service.py").read_text(encoding="utf-8")
    gemini = (root / "app" / "services" / "assistant_gemini_service.py").read_text(encoding="utf-8")
    settings = (root / "app" / "services" / "assistant_settings_store.py").read_text(encoding="utf-8")
    page = (root / "app" / "ui" / "pages" / "assistant_page.py").read_text(encoding="utf-8")
    settings_page = (root / "app" / "ui" / "pages" / "settings_page.py").read_text(encoding="utf-8")

    checks = (
        ("class LocalEntityResolver", resolver),
        ("class AssistantWorkflowEngine", workflow),
        ("owned_only=True", page),
        ("action_requested", page),
        ("Cambiar otra miniatura", local),
        ("PaintResolveTask", page),
        ("resolve_paint_name", gemini),
        ("increment_gemini_request_count", gemini),
        ("gemini_request_count_today", settings),
        ("unassembled_count", local),
        ("finished_count", local),
        ("Requests Gemini del día", settings_page),
    )
    for marker, source in checks:
        if marker not in source:
            raise RuntimeError(f"0.10.8 verification marker missing: {marker}")

    print("Ciros Paint 0.10.8 entity resolver/workflow overlay applied")


if __name__ == "__main__":
    main()
