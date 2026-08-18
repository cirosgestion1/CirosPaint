from __future__ import annotations

import argparse
import json
from pathlib import Path


def map_type(brand: str, range_name: str, name: str, code: str | None) -> str:
    value = f"{range_name} {name} {code or ''}".casefold()
    if "contrast" in value or "xpress color" in value or "quick gen" in value:
        return "Contrast"
    if "wash" in value or "shade" in value:
        return "Wash"
    if "ink" in value:
        return "Ink"
    if "pigment" in value:
        return "Pigment"
    if "oil" in value or (brand == "AK Interactive" and (code or "").upper().startswith("AKABT")):
        return "Oil"
    if brand == "AK Interactive" and any(word in value for word in ("streak", "filter", "enamel", "weathering")):
        return "Enamel"
    return "Acrílico"


def parse_markdown(path: Path, brand: str, has_code: bool) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or cells[0].casefold() == "name":
            continue
        try:
            if has_code:
                name, code, range_name, r, g, b = cells[:6]
            else:
                name, range_name, r, g, b = cells[:5]
                code = ""
            if "discontinued" in range_name.casefold():
                continue
            rgb = (int(r), int(g), int(b))
        except (ValueError, IndexError):
            continue
        swatch = "#%02X%02X%02X" % rgb
        rows.append({
            "brand": brand,
            "name": name.strip("'\" "),
            "code": code or None,
            "range_name": range_name or None,
            "paint_type": map_type(brand, range_name, name, code),
            "swatch_hex": swatch,
        })
    return rows


def dedupe(rows: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for row in rows:
        key = (row["brand"], row["name"].casefold(), row.get("code"), row.get("range_name"))
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    paints_dir = args.source_dir / "paints"
    rows = []
    rows += parse_markdown(paints_dir / "Vallejo.md", "Vallejo", has_code=True)
    rows += parse_markdown(paints_dir / "AK.md", "AK Interactive", has_code=True)
    rows += parse_markdown(paints_dir / "Citadel_Colour.md", "Citadel", has_code=False)
    rows = dedupe(rows)
    rows.sort(key=lambda row: (row["brand"], row["name"].casefold(), row.get("range_name") or ""))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(rows)} catalog paints to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
