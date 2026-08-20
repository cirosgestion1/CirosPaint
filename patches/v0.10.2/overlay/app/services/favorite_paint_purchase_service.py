from __future__ import annotations

import unicodedata

from sqlalchemy.orm import Session

from app.repositories.paint_repository import PaintRepository
from app.repositories.shopping_repository import ShoppingRepository
from app.services.paint_catalog_service import CatalogPaint, infer_color_tags


class FavoritePaintPurchaseService:
    """Connect a catalog paint detected in a tutorial with Futuras compras."""

    def __init__(self, session: Session):
        self.session = session
        self.paint_repository = PaintRepository(session)
        self.shopping_repository = ShoppingRepository(session)

    def add_to_future(self, source: CatalogPaint) -> str:
        paint = self._find_existing_paint(source)
        if paint is None:
            primary_color, complementary_colors = infer_color_tags(
                source.name,
                source.swatch_hex,
                source.range_name,
            )
            paint = self.paint_repository.add(
                primary_color=primary_color,
                complementary_colors=complementary_colors,
                brand=source.brand,
                name=source.name,
                code=source.code,
                range_name=source.range_name,
                paint_type=source.paint_type,
                swatch_hex=source.swatch_hex,
                available_units=0,
                low_units=0,
            )

        entry = self.shopping_repository.get_for_paint(paint.id)
        if entry is not None and entry.stage == "future":
            return "already"

        quantity = 1
        if entry is not None:
            try:
                quantity = max(1, int(entry.quantity or 1))
            except (TypeError, ValueError):
                quantity = 1
        self.shopping_repository.set_future_quantity(paint.id, quantity)
        return "added"

    def _find_existing_paint(self, source: CatalogPaint):
        source_brand = _normalize(source.brand)
        source_name = _normalize(source.name)
        source_code = _normalize(source.code or "")
        source_range = _normalize(source.range_name or "")

        for paint in self.paint_repository.list():
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


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (value or "").casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).strip()
