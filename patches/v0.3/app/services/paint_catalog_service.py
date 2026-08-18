from __future__ import annotations

import colorsys
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CatalogPaint:
    brand: str
    name: str
    code: str | None
    range_name: str | None
    paint_type: str
    swatch_hex: str | None

    @property
    def display_name(self) -> str:
        bits = [self.name]
        if self.range_name:
            bits.append(self.range_name)
        if self.code:
            bits.append(self.code)
        return " — ".join(bits)


class PaintCatalogService:
    def __init__(self, catalog_path: Path | None = None):
        self.catalog_path = catalog_path or (Path(__file__).resolve().parents[1] / "data" / "paint_catalog.json")
        self._items = self._load()

    def _load(self) -> list[CatalogPaint]:
        try:
            raw = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        items: list[CatalogPaint] = []
        for row in raw:
            try:
                items.append(
                    CatalogPaint(
                        brand=str(row["brand"]),
                        name=str(row["name"]),
                        code=(str(row["code"]) if row.get("code") else None),
                        range_name=(str(row["range_name"]) if row.get("range_name") else None),
                        paint_type=str(row.get("paint_type") or "Acrílico"),
                        swatch_hex=(str(row["swatch_hex"]) if row.get("swatch_hex") else None),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return items

    def for_brand(self, brand: str) -> list[CatalogPaint]:
        return [item for item in self._items if item.brand == brand]

    def find_exact(self, brand: str, name: str, display_name: str | None = None) -> CatalogPaint | None:
        needle = name.strip().casefold()
        candidates = [item for item in self._items if item.brand == brand and item.name.casefold() == needle]
        if not candidates:
            return None
        if display_name:
            for item in candidates:
                if item.display_name == display_name:
                    return item
        return candidates[0] if len(candidates) == 1 else None

    @property
    def count(self) -> int:
        return len(self._items)


def infer_color_tags(name: str, swatch_hex: str | None, range_name: str | None = None) -> tuple[str, list[str]]:
    """Return a deterministic color-family suggestion from product metadata."""
    text = f"{name} {range_name or ''}".casefold()

    metallic_words = (
        "metal", "metallic", "gold", "silver", "steel", "aluminium", "aluminum",
        "copper", "bronze", "brass", "gunmetal", "iron", "chrome",
    )
    if any(word in text for word in metallic_words):
        return "Metálico", []

    keyword_rules: list[tuple[tuple[str, ...], str]] = [
        (("black", "negro"), "Negro"),
        (("white", "blanco"), "Blanco"),
        (("grey", "gray", "gris"), "Gris"),
        (("turquoise", "turquesa", "teal", "aqua"), "Azul"),
        (("yellow", "amarillo"), "Amarillo"),
        (("orange", "naranja"), "Naranja"),
        (("brown", "marrón", "marron", "umber", "sienna", "earth"), "Marrón"),
        (("green", "verde"), "Verde"),
        (("blue", "azul"), "Azul"),
        (("purple", "violet", "morado", "lilac"), "Morado"),
        (("pink", "rose", "rosa", "magenta"), "Rosa"),
        (("beige", "ivory", "khaki", "sand", "flesh", "skin", "hueso", "bone"), "Beige"),
        (("red", "rojo", "carmine", "scarlet", "crimson"), "Rojo"),
    ]

    keyword_primary = None
    for words, family in keyword_rules:
        if any(word in text for word in words):
            keyword_primary = family
            break

    if any(word in text for word in ("turquoise", "turquesa", "teal", "aqua")):
        return "Azul", ["Verde"]

    compound_tint = None
    if re.search(r"\b(grey|gray|gris)\b", text):
        for words, family in keyword_rules:
            if family in {"Gris", "Negro", "Blanco"}:
                continue
            if any(word in text for word in words):
                compound_tint = family
                break

    rgb = _hex_to_rgb(swatch_hex)
    if rgb is None:
        if compound_tint:
            return "Gris", [compound_tint]
        return keyword_primary or "Otro", []

    r, g, b = [channel / 255 for channel in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    hue = h * 360

    if s < 0.13:
        primary = keyword_primary or ("Blanco" if v >= 0.88 else "Negro" if v <= 0.18 else "Gris")
        complements: list[str] = []
        if compound_tint and compound_tint != primary:
            complements.append(compound_tint)
        elif primary == "Gris" and s >= 0.055:
            tint = _hue_family(hue, v, s)
            if tint not in {"Gris", primary, "Otro"}:
                complements.append(tint)
        return primary, complements

    primary = keyword_primary or _hue_family(hue, v, s)
    complements: list[str] = []

    if primary == "Azul" and 160 <= hue <= 195:
        complements.append("Verde")
    elif primary == "Verde" and 145 <= hue < 170:
        complements.append("Azul")
    elif primary == "Amarillo" and 38 <= hue <= 48:
        complements.append("Naranja")
    elif primary == "Naranja" and 42 <= hue <= 52:
        complements.append("Amarillo")
    elif primary == "Rojo" and hue >= 335:
        complements.append("Rosa")
    elif primary == "Rosa" and hue <= 340:
        complements.append("Rojo")

    if compound_tint:
        return "Gris", [compound_tint]

    return primary, [c for c in dict.fromkeys(complements) if c != primary]


def _hex_to_rgb(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    match = re.fullmatch(r"#?([0-9a-fA-F]{6})", value.strip())
    if not match:
        return None
    raw = match.group(1)
    return tuple(int(raw[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _hue_family(hue: float, value: float, saturation: float) -> str:
    if value < 0.17:
        return "Negro"
    if value > 0.9 and saturation < 0.18:
        return "Blanco"
    if 15 <= hue < 45:
        if value < 0.55:
            return "Marrón"
        if saturation < 0.45 and value > 0.68:
            return "Beige"
        return "Naranja"
    if 45 <= hue < 72:
        if saturation < 0.35 and value > 0.65:
            return "Beige"
        return "Amarillo"
    if 72 <= hue < 165:
        return "Verde"
    if 165 <= hue < 250:
        return "Azul"
    if 250 <= hue < 315:
        return "Morado"
    if 315 <= hue < 345:
        return "Rosa"
    return "Rojo"
