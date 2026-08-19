from __future__ import annotations

import sys
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected text not found in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply_v094.py <build_source>")
    root = Path(sys.argv[1]).resolve()

    config = root / "app/core/config.py"
    replace_once(config, 'APP_VERSION = "0.9.3"', 'APP_VERSION = "0.9.4"')

    print("Ciros Paint 0.9.4 integration patches applied")


if __name__ == "__main__":
    main()
