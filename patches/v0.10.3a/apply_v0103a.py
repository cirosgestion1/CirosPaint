from __future__ import annotations

import shutil
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply_v0103a.py <build_source>")

    root = Path(sys.argv[1]).resolve()
    patch_root = Path(__file__).resolve().parent

    config_path = root / "app" / "core" / "config.py"
    text = config_path.read_text(encoding="utf-8")
    old = 'APP_VERSION = "0.10.3"'
    new = 'APP_VERSION = "0.10.3a"'
    if old not in text:
        raise RuntimeError("Expected Ciros Paint 0.10.3 version marker was not found")
    config_path.write_text(text.replace(old, new, 1), encoding="utf-8")

    for name in ("CirosPaint.cmd", "CirosPaint_DEBUG.cmd", "LEEME_0.10.3a.txt"):
        source = patch_root / "launcher" / name
        if not source.exists():
            raise RuntimeError(f"Missing 0.10.3a launcher file: {source}")
        shutil.copy2(source, root / name)


if __name__ == "__main__":
    main()
