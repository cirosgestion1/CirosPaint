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
        raise SystemExit("Usage: apply_v0101.py <build_source>")
    root = Path(sys.argv[1]).resolve()
    replace_once(root / "app/core/config.py", 'APP_VERSION = "0.9"', 'APP_VERSION = "0.10.1"')
    print("Ciros Paint 0.10.1 integration patches applied")


if __name__ == "__main__":
    main()
