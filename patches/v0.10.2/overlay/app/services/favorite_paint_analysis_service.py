from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import html
import re
import unicodedata
from urllib.parse import urlencode

from app.core.color_math import delta_e_cie76, similarity_percent
from app.services.paint_catalog_service import CatalogPaint, PaintCatalogService
from app.services.youtube_service import VIDEOS_ENDPOINT, YouTubeApiError, _request_json


MIN_VISIBLE_SIMILARITY_PERCENT = 85.0
MIN_POSSIBLE_NAME_SIMILARITY = MIN_VISIBLE_SIMILARITY_PERCENT / 100.0

_GENERIC_SINGLE_NAMES = {
    "black", "white", "grey", "gray", "red", "green", "blue", "yellow", "orange",
    "brown", "purple", "violet", "pink", "beige", "flesh", "skin", "gold", "silver",
    "steel", "metal", "metallic", "wash", "ink", "oil", "primer", "varnish", "varnish",
    "negro", "blanco", "gris", "rojo", "verde", "azul", "amarillo", "naranja", "marron",
    "morado", "rosa", "carne", "piel", "dorado", "plata", "metalico", "tinta", "oleo",
}

_BRAND_VARIANTS = {
    "ak interactive": ("ak interactive", "ak"),
    "citadel": ("citadel", "citadel colour"),
    "vallejo": ("vallejo",),
}

_BULLET_PREFIX_RE = re.compile(r"^\s*(?:(?:[-*•▪◦–—]+)|(?:\d+[.)]))\s*")


@dataclass(frozen=True)
class DetectedPaint:
    source_text: str
    catalog_paint: CatalogPaint


@dataclass(frozen=True)
class InventoryPaintMatch:
    detected: DetectedPaint
    inventory_paint: object
    kind: str  # exact | possible
    name_similarity: float = 1.0


@dataclass(frozen=True)
class PaintAlternative:
    inventory_paint: object
    delta_e: float
    similarity: float


@dataclass(frozen=True)
class MissingPaintAlternatives:
    detected: DetectedPaint
    alternatives: tuple[PaintAlternative, ...]


@dataclass(frozen=True)
class PaintAnalysisResult:
    author_lines: tuple[str, ...]
    detected: tuple[DetectedPaint, ...]
    matches: tuple[InventoryPaintMatch, ...]
    missing: tuple[MissingPaintAlternatives, ...]

    @property
    def exact_matches(self) -> tuple[InventoryPaintMatch, ...]:
        return tuple(item for item in self.matches if item.kind == "exact")

    @property
    def possible_matches(self) -> tuple[InventoryPaintMatch, ...]:
        return tuple(item for item in self.matches if item.kind == "possible")

    @property
    def has_detected_paints(self) -> bool:
        return bool(self.detected)


class FavoritePaintAnalysisService:
    """Deterministic description -> catalog -> inventory analysis.

    0.10.2 keeps the 0.10.1 deterministic behaviour and adds one explicit
    visibility rule: possible name matches and colour alternatives must reach
    at least 85% similarity. Anything below that threshold is not presented as
    a useful match to the user.
    """

    def __init__(self, catalog_service: PaintCatalogService | None = None):
        self.catalog_service = catalog_service or PaintCatalogService()
        self._catalog_items: tuple[CatalogPaint, ...] = tuple(getattr(self.catalog_service, "_items", ()))
        self._aliases = self._build_alias_index(self._catalog_items)

    @staticmethod
    def fetch_video_description(api_key: str, video_id: str) -> str:
        key = (api_key or "").strip()
        video = (video_id or "").strip()
        if not key:
            raise YouTubeApiError("Falta la clave de YouTube Data API.")
        if not video:
            raise YouTubeApiError("El vídeo no tiene un identificador válido.")
        params = {"part": "snippet", "id": video, "key": key}
        payload = _request_json(f"{VIDEOS_ENDPOINT}?{urlencode(params)}")
        items = payload.get("items") or []
        if not items:
            raise YouTubeApiError("YouTube no ha devuelto información para este vídeo.")
        snippet = items[0].get("snippet") or {}
        return html.unescape(str(snippet.get("description") or ""))

    def analyze_description(self, description: str, inventory_paints: list[object]) -> PaintAnalysisResult:
        detected = self.detect_catalog_paints(description)
        available_inventory = [paint for paint in inventory_paints if self._inventory_units(paint) > 0]

        matches: list[InventoryPaintMatch] = []
        missing: list[MissingPaintAlternatives] = []
        author_lines: list[str] = []

        for item in detected:
            if item.source_text not in author_lines:
                author_lines.append(item.source_text)

            exact = self._find_exact_inventory_match(item.catalog_paint, available_inventory)
            if exact is not None:
                matches.append(InventoryPaintMatch(item, exact, "exact", 1.0))
                continue

            possible = self._find_possible_inventory_match(item.catalog_paint, available_inventory)
            if possible is not None:
                paint, score = possible
                matches.append(InventoryPaintMatch(item, paint, "possible", score))
                continue

            alternatives = self._find_alternatives(item.catalog_paint, available_inventory)
            missing.append(MissingPaintAlternatives(item, tuple(alternatives)))

        return PaintAnalysisResult(
            author_lines=tuple(author_lines),
            detected=tuple(detected),
            matches=tuple(matches),
            missing=tuple(missing),
        )

    def detect_catalog_paints(self, description: str) -> list[DetectedPaint]:
        if not (description or "").strip() or not self._aliases:
            return []

        found: list[DetectedPaint] = []
        seen: set[tuple[str, str, str, str]] = set()

        for raw_line in (description or "").splitlines():
            source_text = _clean_source_line(raw_line)
            if not source_text:
                continue
            normalized_line = _normalize(source_text)
            if not normalized_line:
                continue
            padded_line = f" {normalized_line} "

            line_candidates: dict[tuple[str, str, str, str], tuple[CatalogPaint, int, int]] = {}
            for alias, paint, strength in self._aliases:
                if f" {alias} " not in padded_line:
                    continue
                identity = _catalog_identity(paint)
                previous = line_candidates.get(identity)
                rank = (strength, len(alias))
                if previous is None or rank > (previous[1], previous[2]):
                    line_candidates[identity] = (paint, strength, len(alias))

            for identity, (paint, _strength, _length) in sorted(
                line_candidates.items(), key=lambda pair: (pair[1][1], pair[1][2]), reverse=True
            ):
                if identity in seen:
                    continue
                seen.add(identity)
                found.append(DetectedPaint(source_text=source_text, catalog_paint=paint))

        return found

    @classmethod
    def _build_alias_index(cls, items: tuple[CatalogPaint, ...]) -> tuple[tuple[str, CatalogPaint, int], ...]:
        alias_map: dict[str, list[tuple[CatalogPaint, int]]] = {}
        for item in items:
            for alias, strength in cls._aliases_for_item(item):
                alias_map.setdefault(alias, []).append((item, strength))

        usable: list[tuple[str, CatalogPaint, int]] = []
        for alias, candidates in alias_map.items():
            identities = {_catalog_identity(item) for item, _strength in candidates}
            if len(identities) != 1:
                continue
            item, strength = max(candidates, key=lambda pair: pair[1])
            usable.append((alias, item, strength))

        usable.sort(key=lambda row: (row[2], len(row[0])), reverse=True)
        return tuple(usable)

    @classmethod
    def _aliases_for_item(cls, item: CatalogPaint) -> tuple[tuple[str, int], ...]:
        values: dict[str, int] = {}

        def add(value: str | None, strength: int, allow_generic: bool = False) -> None:
            alias = _normalize(value or "")
            if not alias:
                return
            tokens = alias.split()
            if len(alias) < 4 and strength < 100:
                return
            if len(tokens) == 1 and alias in _GENERIC_SINGLE_NAMES and not allow_generic:
                return
            values[alias] = max(values.get(alias, 0), strength)

        brand_key = _normalize(item.brand)
        brands = _BRAND_VARIANTS.get(brand_key, (brand_key,))
        name = item.name or ""
        range_name = item.range_name or ""

        if item.code:
            code_norm = _normalize(item.code)
            if len(code_norm.replace(" ", "")) >= 3 and (any(ch.isdigit() for ch in code_norm) or len(code_norm) >= 5):
                add(item.code, 100, allow_generic=True)

        for brand in brands:
            add(f"{brand} {name}", 98)
            if range_name:
                add(f"{brand} {range_name} {name}", 99)
                add(f"{brand} {name} {range_name}", 99)

        if range_name:
            add(f"{name} {range_name}", 94)
            add(f"{range_name} {name}", 94)
        if item.source_name:
            add(item.source_name, 92)
        add(name, 88)
        return tuple(values.items())

    @staticmethod
    def _find_exact_inventory_match(source: CatalogPaint, inventory: list[object]) -> object | None:
        source_brand = _normalize(source.brand)
        source_name = _normalize(source.name)
        source_code = _normalize(source.code or "")
        source_range = _normalize(source.range_name or "")

        for paint in inventory:
            if _normalize(getattr(paint, "brand", "")) != source_brand:
                continue
            paint_code = _normalize(getattr(paint, "code", "") or "")
            if source_code and paint_code and source_code == paint_code:
                return paint

            if _normalize(getattr(paint, "name", "")) != source_name:
                continue
            paint_range = _normalize(getattr(paint, "range_name", "") or "")
            if source_range and paint_range and source_range != paint_range:
                continue
            return paint
        return None

    @classmethod
    def _find_possible_inventory_match(cls, source: CatalogPaint, inventory: list[object]) -> tuple[object, float] | None:
        source_brand = _normalize(source.brand)
        source_type = _normalize(source.paint_type)
        source_name = _normalize(source.name)
        candidates: list[tuple[float, object]] = []

        for paint in inventory:
            if _normalize(getattr(paint, "brand", "")) != source_brand:
                continue
            if _normalize(getattr(paint, "paint_type", "")) != source_type:
                continue
            candidate_name = _normalize(getattr(paint, "name", ""))
            score = _name_similarity(source_name, candidate_name)
            if score >= MIN_POSSIBLE_NAME_SIMILARITY:
                candidates.append((score, paint))

        if not candidates:
            return None
        candidates.sort(key=lambda row: row[0], reverse=True)
        return candidates[0][1], candidates[0][0]

    @staticmethod
    def _find_alternatives(source: CatalogPaint, inventory: list[object], limit: int = 3) -> list[PaintAlternative]:
        if source.lab is None:
            return []
        source_type = _normalize(source.paint_type)
        ranked: list[PaintAlternative] = []
        for paint in inventory:
            if _normalize(getattr(paint, "paint_type", "")) != source_type:
                continue
            lab = getattr(paint, "color_lab", None)
            delta = delta_e_cie76(source.lab, lab)
            if delta is None:
                continue
            similarity = similarity_percent(delta)
            if similarity is None or float(similarity) < MIN_VISIBLE_SIMILARITY_PERCENT:
                continue
            ranked.append(PaintAlternative(paint, float(delta), float(similarity)))
        ranked.sort(key=lambda item: (item.delta_e, -item.similarity))
        return ranked[: max(1, int(limit))]

    @staticmethod
    def _inventory_units(paint: object) -> int:
        total = getattr(paint, "total_units", None)
        if total is not None:
            try:
                return max(0, int(total))
            except (TypeError, ValueError):
                pass
        try:
            return max(0, int(getattr(paint, "available_units", 0))) + max(0, int(getattr(paint, "low_units", 0)))
        except (TypeError, ValueError):
            return 0


def _catalog_identity(item: CatalogPaint) -> tuple[str, str, str, str]:
    return (
        _normalize(item.brand),
        _normalize(item.name),
        _normalize(item.code or ""),
        _normalize(item.range_name or ""),
    )


def _clean_source_line(value: str) -> str:
    cleaned = _BULLET_PREFIX_RE.sub("", (value or "").strip())
    return " ".join(cleaned.split())


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (value or "").casefold())
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", without_marks).split())


def _name_similarity(first: str, second: str) -> float:
    if not first or not second:
        return 0.0
    if first == second:
        return 1.0
    sequence = SequenceMatcher(None, first, second).ratio()
    first_tokens = set(first.split())
    second_tokens = set(second.split())
    union = first_tokens | second_tokens
    token_score = (len(first_tokens & second_tokens) / len(union)) if union else 0.0
    containment = 0.0
    shorter, longer = (first, second) if len(first) <= len(second) else (second, first)
    if len(shorter) >= 6 and f" {shorter} " in f" {longer} ":
        containment = 0.90
    return max(sequence, token_score, containment)
