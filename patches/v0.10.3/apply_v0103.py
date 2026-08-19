from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply_v0103.py <build_source>")

    root = Path(sys.argv[1]).resolve()
    config_path = root / "app" / "core" / "config.py"
    text = config_path.read_text(encoding="utf-8")
    old = 'APP_VERSION = "0.10.2"'
    new = 'APP_VERSION = "0.10.3"'
    if old not in text:
        raise RuntimeError("Expected Ciros Paint 0.10.2 version marker was not found")
    config_path.write_text(text.replace(old, new, 1), encoding="utf-8")


if __name__ == "__main__":
    main()
