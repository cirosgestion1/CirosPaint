from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_sha256(root: Path) -> tuple[int, str]:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256(path)))
    return len(files), digest.hexdigest()


def verify_runtime_assets(source_root: Path) -> dict[str, object]:
    root = source_root.resolve()
    manifest_path = root / "app" / "assets" / "runtime_assets_manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"Runtime asset manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    catalog = manifest["paint_catalog"]
    catalog_path = root / catalog["path"]
    if not catalog_path.is_file():
        raise RuntimeError(f"Paint catalog is missing: {catalog_path}")
    actual_catalog_hash = _sha256(catalog_path)
    if actual_catalog_hash != catalog["sha256"]:
        raise RuntimeError(f"Paint catalog hash mismatch: {actual_catalog_hash}")
    entries = len(json.loads(catalog_path.read_text(encoding="utf-8")))
    if entries != catalog["entries"]:
        raise RuntimeError(f"Paint catalog entry count mismatch: {entries}")

    for relative, expected_hash in manifest["brand_assets"].items():
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"Required brand asset is missing: {relative}")
        actual_hash = _sha256(path)
        if actual_hash != expected_hash:
            raise RuntimeError(f"Brand asset hash mismatch for {relative}: {actual_hash}")

    miniature = manifest["miniature_assets"]
    miniature_root = root / miniature["root"]
    count, tree_hash = _tree_sha256(miniature_root)
    if count != miniature["file_count"]:
        raise RuntimeError(f"Miniature asset count mismatch: {count}")
    if tree_hash != miniature["tree_sha256"]:
        raise RuntimeError(f"Miniature asset tree hash mismatch: {tree_hash}")

    return {
        "catalog_entries": entries,
        "brand_assets": len(manifest["brand_assets"]),
        "miniature_assets": count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Ciros Paint runtime assets.")
    parser.add_argument("source_root", nargs="?", default=".")
    result = verify_runtime_assets(Path(parser.parse_args().source_root))
    print(
        "Runtime assets verified: "
        f"{result['catalog_entries']} paints, "
        f"{result['brand_assets']} brand logos, "
        f"{result['miniature_assets']} miniature assets"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
