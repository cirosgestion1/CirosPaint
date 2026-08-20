from __future__ import annotations

import re
import unicodedata
from typing import Any

from sqlalchemy.orm import Session

from app.core.color_math import delta_e_cie76, similarity_percent
from app.repositories.paint_repository import PaintRepository
from app.repositories.shopping_repository import ShoppingRepository
from app.services.assistant_contracts import AssistantToolResult
from app.services.favorite_paint_analysis_service import MIN_VISIBLE_SIMILARITY_PERCENT
from app.services.paint_catalog_service import PaintCatalogService, infer_color_tags


class AssistantPaintService:
    """Deterministic paint tools exposed to the future Ciros Assistant provider.

    This class deliberately contains no AI/provider code. The model will only
    be allowed to request these operations; Ciros Paint remains responsible
    for catalog validation, inventory truth, colour maths and database writes.
    """

    def __init__(
        self,
        session: Session,
        catalog_service: PaintCatalogService | None = None,
        paint_repository: PaintRepository | None = None,
        shopping_repository: ShoppingRepository | None = None,
    ):
        self.session = session
        self.catalog_service = catalog_service or PaintCatalogService()
        self.paint_repository = paint_repository or PaintRepository(session)
        self.shopping_repository = shopping_repository or ShoppingRepository(session)

    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> AssistantToolResult:
        args = dict(arguments or {})
        handlers = {
            "search_paints": self.search_paints,
            "get_paint_stock": self.get_paint_stock,
            "find_paint_alternatives": self.find_paint_alternatives,
            "add_paint_to_inventory": self.add_paint_to_inventory,
            "set_paint_quantity": self.set_paint_quantity,
            "add_paint_to_future_purchases": self.add_paint_to_future_purchases,
            "list_future_paint_purchases": self.list_future_paint_purchases,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            return AssistantToolResult("invalid", f"Herramienta desconocida: {tool_name}.")
        try:
            return handler(**args)
        except TypeError:
            return AssistantToolResult("invalid", "Los datos recibidos para la herramienta no son válidos.")

    def search_paints(
        self,
        query: str = "",
        brand: str = "",
        name: str = "",
        code: str = "",
        range_name: str = "",
        color: str = "",
        paint_type: str = "",
        only_in_stock: bool = False,
    ) -> AssistantToolResult:
        paints = [
            paint
            for paint in self.paint_repository.list()
            if self._matches_inventory_filters(
                paint,
                query=query,
                brand=brand,
                name=name,
                code=code,
                range_name=range_name,
                color=color,
                paint_type=paint_type,
            )
        ]
        if only_in_stock:
            paints = [paint for paint in paints if self._inventory_units(paint) > 0]
        paints.sort(key=lambda item: (_normalize(getattr(item, "brand", "")), _normalize(getattr(item, "name", ""))))
        data = [self._paint_payload(paint) for paint in paints]
        if not data:
            return AssistantToolResult("not_found", "No hay pinturas del inventario que coincidan con la búsqueda.", {"paints": []})
        return AssistantToolResult("ok", f"Se han encontrado {len(data)} pinturas.", {"paints": data})

    def get_paint_stock(
        self,
        query: str = "",
        brand: str = "",
        name: str = "",
        code: str = "",
        range_name: str = "",
    ) -> AssistantToolResult:
        resolved = self._resolve_inventory_paint(query=query, brand=brand, name=name, code=code, range_name=range_name)
        if isinstance(resolved, AssistantToolResult):
            return resolved
        payload = self._paint_payload(resolved)
        units = payload["total_units"]
        message = f"Tienes {units} unidad{'es' if units != 1 else ''} de {payload['brand']} {payload['name']}."
        return AssistantToolResult("ok", message, {"paint": payload})

    def find_paint_alternatives(
        self,
        query: str = "",
        brand: str = "",
        name: str = "",
        code: str = "",
        range_name: str = "",
        limit: int = 3,
    ) -> AssistantToolResult:
        source = self._resolve_catalog_paint(query=query, brand=brand, name=name, code=code, range_name=range_name)
        if isinstance(source, AssistantToolResult):
            return source
        source_lab = getattr(source, "lab", None)
        if source_lab is None:
            return AssistantToolResult(
                "not_found",
                "La pintura existe en el catálogo, pero no tiene datos de color suficientes para calcular alternativas.",
                {"source": self._catalog_payload(source), "alternatives": []},
            )

        source_type = _normalize(getattr(source, "paint_type", ""))
        ranked: list[tuple[float, float, object]] = []
        for paint in self.paint_repository.list():
            if self._inventory_units(paint) <= 0:
                continue
            if _normalize(getattr(paint, "paint_type", "")) != source_type:
                continue
            if self._same_identity(paint, source):
                continue
            delta = delta_e_cie76(source_lab, getattr(paint, "color_lab", None))
            if delta is None:
                continue
            similarity = similarity_percent(delta)
            if similarity is None or float(similarity) < MIN_VISIBLE_SIMILARITY_PERCENT:
                continue
            ranked.append((float(delta), float(similarity), paint))

        ranked.sort(key=lambda item: (item[0], -item[1]))
        safe_limit = max(1, min(10, int(limit or 3)))
        alternatives = [
            {
                "paint": self._paint_payload(paint),
                "delta_e": round(delta, 3),
                "similarity_percent": round(similarity, 2),
            }
            for delta, similarity, paint in ranked[:safe_limit]
        ]
        source_payload = self._catalog_payload(source)
        if not alternatives:
            return AssistantToolResult(
                "not_found",
                f"No tienes alternativas compatibles de al menos un {MIN_VISIBLE_SIMILARITY_PERCENT:.0f} % para {source_payload['name']}.",
                {"source": source_payload, "alternatives": []},
            )
        return AssistantToolResult(
            "ok",
            f"Se han encontrado {len(alternatives)} alternativas en tu inventario.",
            {"source": source_payload, "alternatives": alternatives},
        )

    def add_paint_to_inventory(
        self,
        quantity: int,
        query: str = "",
        brand: str = "",
        name: str = "",
        code: str = "",
        range_name: str = "",
    ) -> AssistantToolResult:
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return AssistantToolResult("invalid", "La cantidad debe ser un número entero.")
        if quantity < 1:
            return AssistantToolResult("invalid", "La cantidad a añadir debe ser al menos 1.")

        source = self._resolve_catalog_paint(query=query, brand=brand, name=name, code=code, range_name=range_name)
        if isinstance(source, AssistantToolResult):
            return source

        paint = self._find_inventory_by_catalog(source)
        if paint is None:
            primary_color, complementary_colors = infer_color_tags(
                getattr(source, "name", ""),
                getattr(source, "swatch_hex", None),
                getattr(source, "range_name", None),
            )
            paint = self.paint_repository.add(
                primary_color=primary_color,
                complementary_colors=complementary_colors,
                brand=getattr(source, "brand", ""),
                name=getattr(source, "name", ""),
                code=getattr(source, "code", None),
                range_name=getattr(source, "range_name", None),
                paint_type=getattr(source, "paint_type", "Acrílico"),
                swatch_hex=getattr(source, "swatch_hex", None),
                available_units=quantity,
                low_units=0,
            )
        else:
            paint.available_units = self._safe_int(getattr(paint, "available_units", 0)) + quantity
            self.session.commit()

        payload = self._paint_payload(paint)
        return AssistantToolResult(
            "ok",
            f"Se han añadido {quantity} unidad{'es' if quantity != 1 else ''} de {payload['brand']} {payload['name']} al inventario.",
            {"paint": payload, "added_units": quantity},
        )

    def set_paint_quantity(
        self,
        quantity: int,
        query: str = "",
        brand: str = "",
        name: str = "",
        code: str = "",
        range_name: str = "",
    ) -> AssistantToolResult:
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return AssistantToolResult("invalid", "La cantidad debe ser un número entero.")
        if quantity < 0:
            return AssistantToolResult("invalid", "La cantidad total no puede ser negativa.")

        paint = self._resolve_inventory_paint(query=query, brand=brand, name=name, code=code, range_name=range_name)
        if isinstance(paint, AssistantToolResult):
            return paint

        current_low = max(0, self._safe_int(getattr(paint, "low_units", 0)))
        new_low = min(current_low, quantity)
        paint.low_units = new_low
        paint.available_units = quantity - new_low
        self.session.commit()
        payload = self._paint_payload(paint)
        return AssistantToolResult(
            "ok",
            f"La cantidad total de {payload['brand']} {payload['name']} se ha establecido en {quantity}.",
            {"paint": payload, "total_units": quantity},
        )

    def add_paint_to_future_purchases(
        self,
        query: str = "",
        brand: str = "",
        name: str = "",
        code: str = "",
        range_name: str = "",
        quantity: int = 1,
    ) -> AssistantToolResult:
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return AssistantToolResult("invalid", "La cantidad debe ser un número entero.")
        if quantity < 1:
            return AssistantToolResult("invalid", "La cantidad de Futuras compras debe ser al menos 1.")

        source = self._resolve_catalog_paint(query=query, brand=brand, name=name, code=code, range_name=range_name)
        if isinstance(source, AssistantToolResult):
            return source
        paint = self._find_inventory_by_catalog(source)
        if paint is None:
            primary_color, complementary_colors = infer_color_tags(
                getattr(source, "name", ""),
                getattr(source, "swatch_hex", None),
                getattr(source, "range_name", None),
            )
            paint = self.paint_repository.add(
                primary_color=primary_color,
                complementary_colors=complementary_colors,
                brand=getattr(source, "brand", ""),
                name=getattr(source, "name", ""),
                code=getattr(source, "code", None),
                range_name=getattr(source, "range_name", None),
                paint_type=getattr(source, "paint_type", "Acrílico"),
                swatch_hex=getattr(source, "swatch_hex", None),
                available_units=0,
                low_units=0,
            )

        existing = self.shopping_repository.get_for_paint(paint.id)
        if existing is not None and getattr(existing, "stage", None) == "future" and self._safe_int(getattr(existing, "quantity", 0)) == quantity:
            return AssistantToolResult(
                "ok",
                "La pintura ya estaba en Futuras compras con esa cantidad.",
                {"paint": self._paint_payload(paint), "quantity": quantity, "already_present": True},
            )
        self.shopping_repository.set_future_quantity(paint.id, quantity)
        return AssistantToolResult(
            "ok",
            f"{getattr(paint, 'brand', '')} {getattr(paint, 'name', '')} se ha añadido a Futuras compras.",
            {"paint": self._paint_payload(paint), "quantity": quantity, "already_present": False},
        )

    def list_future_paint_purchases(self) -> AssistantToolResult:
        paints_by_id = {getattr(paint, "id", None): paint for paint in self.paint_repository.list()}
        rows: list[dict[str, Any]] = []
        for entry in self.shopping_repository.list_future():
            paint = paints_by_id.get(getattr(entry, "paint_id", None))
            if paint is None:
                continue
            rows.append({"paint": self._paint_payload(paint), "quantity": self._safe_int(getattr(entry, "quantity", 0))})
        rows.sort(key=lambda item: (_normalize(item["paint"]["brand"]), _normalize(item["paint"]["name"])))
        if not rows:
            return AssistantToolResult("not_found", "No tienes pinturas en Futuras compras.", {"purchases": []})
        return AssistantToolResult("ok", f"Tienes {len(rows)} pinturas en Futuras compras.", {"purchases": rows})

    def _resolve_inventory_paint(self, **filters: str):
        candidates = [
            paint
            for paint in self.paint_repository.list()
            if self._matches_inventory_filters(paint, **filters)
        ]
        if not candidates:
            return AssistantToolResult("not_found", "No encuentro esa pintura en tu inventario.")
        exact = self._prefer_exact_inventory(candidates, **filters)
        if exact is not None:
            return exact
        if len(candidates) > 1:
            return AssistantToolResult(
                "ambiguous",
                "Hay varias pinturas que coinciden. Necesito que indiques cuál quieres usar.",
                {"matches": [self._paint_payload(item) for item in candidates[:10]]},
                requires_user_input=True,
            )
        return candidates[0]

    def _resolve_catalog_paint(self, **filters: str):
        items = list(getattr(self.catalog_service, "_items", ()))
        query = _normalize(filters.get("query", ""))
        brand = _normalize(filters.get("brand", ""))
        name = _normalize(filters.get("name", ""))
        code = _normalize(filters.get("code", ""))
        range_name = _normalize(filters.get("range_name", ""))

        candidates = []
        for item in items:
            item_brand = _normalize(getattr(item, "brand", ""))
            item_name = _normalize(getattr(item, "name", ""))
            item_code = _normalize(getattr(item, "code", "") or "")
            item_range = _normalize(getattr(item, "range_name", "") or "")
            if brand and brand not in item_brand:
                continue
            if name and name not in item_name:
                continue
            if code and code != item_code:
                continue
            if range_name and range_name not in item_range:
                continue
            if query:
                haystack = " ".join(value for value in (item_brand, item_name, item_code, item_range) if value)
                if query not in haystack and query != item_code and query != item_name:
                    continue
            candidates.append(item)

        if not candidates:
            return AssistantToolResult(
                "not_found",
                "No encuentro esa pintura en el catálogo de Ciros Paint. No se realizará ninguna modificación.",
            )
        exact = self._prefer_exact_catalog(candidates, query=query, brand=brand, name=name, code=code, range_name=range_name)
        if exact is not None:
            return exact
        if len(candidates) > 1:
            return AssistantToolResult(
                "ambiguous",
                "El catálogo contiene varias pinturas que coinciden. Necesito más datos antes de continuar.",
                {"matches": [self._catalog_payload(item) for item in candidates[:10]]},
                requires_user_input=True,
            )
        return candidates[0]

    def _prefer_exact_inventory(self, candidates: list[object], **filters: str):
        code = _normalize(filters.get("code", ""))
        name = _normalize(filters.get("name", ""))
        query = _normalize(filters.get("query", ""))
        brand = _normalize(filters.get("brand", ""))
        if code:
            exact = [item for item in candidates if _normalize(getattr(item, "code", "") or "") == code]
            if len(exact) == 1:
                return exact[0]
        if name:
            exact = [item for item in candidates if _normalize(getattr(item, "name", "")) == name and (not brand or _normalize(getattr(item, "brand", "")) == brand)]
            if len(exact) == 1:
                return exact[0]
        if query:
            exact = [item for item in candidates if query in {_normalize(getattr(item, "name", "")), _normalize(getattr(item, "code", "") or ""), _normalize(f"{getattr(item, 'brand', '')} {getattr(item, 'name', '')}")}]
            if len(exact) == 1:
                return exact[0]
        return None

    @staticmethod
    def _prefer_exact_catalog(candidates: list[object], *, query: str, brand: str, name: str, code: str, range_name: str):
        if code:
            exact = [item for item in candidates if _normalize(getattr(item, "code", "") or "") == code]
            if len(exact) == 1:
                return exact[0]
        if name:
            exact = [item for item in candidates if _normalize(getattr(item, "name", "")) == name and (not brand or _normalize(getattr(item, "brand", "")) == brand) and (not range_name or _normalize(getattr(item, "range_name", "") or "") == range_name)]
            if len(exact) == 1:
                return exact[0]
        if query:
            exact = [item for item in candidates if query in {_normalize(getattr(item, "name", "")), _normalize(getattr(item, "code", "") or ""), _normalize(f"{getattr(item, 'brand', '')} {getattr(item, 'name', '')}")}]
            if len(exact) == 1:
                return exact[0]
        return None

    def _find_inventory_by_catalog(self, source: object):
        for paint in self.paint_repository.list():
            if self._same_identity(paint, source):
                return paint
        return None

    @staticmethod
    def _same_identity(first: object, second: object) -> bool:
        if _normalize(getattr(first, "brand", "")) != _normalize(getattr(second, "brand", "")):
            return False
        first_code = _normalize(getattr(first, "code", "") or "")
        second_code = _normalize(getattr(second, "code", "") or "")
        if first_code and second_code:
            return first_code == second_code
        if _normalize(getattr(first, "name", "")) != _normalize(getattr(second, "name", "")):
            return False
        first_range = _normalize(getattr(first, "range_name", "") or "")
        second_range = _normalize(getattr(second, "range_name", "") or "")
        return not (first_range and second_range and first_range != second_range)

    def _matches_inventory_filters(
        self,
        paint: object,
        query: str = "",
        brand: str = "",
        name: str = "",
        code: str = "",
        range_name: str = "",
        color: str = "",
        paint_type: str = "",
        **_: str,
    ) -> bool:
        item_brand = _normalize(getattr(paint, "brand", ""))
        item_name = _normalize(getattr(paint, "name", ""))
        item_code = _normalize(getattr(paint, "code", "") or "")
        item_range = _normalize(getattr(paint, "range_name", "") or "")
        item_type = _normalize(getattr(paint, "paint_type", ""))
        item_colors = [getattr(paint, "primary_color", "")]
        complementary = getattr(paint, "complementary_colors", ()) or ()
        if isinstance(complementary, str):
            complementary = [complementary]
        item_colors.extend(complementary)
        normalized_colors = {_normalize(value) for value in item_colors if value}

        query_n = _normalize(query)
        brand_n = _normalize(brand)
        name_n = _normalize(name)
        code_n = _normalize(code)
        range_n = _normalize(range_name)
        color_n = _normalize(color)
        type_n = _normalize(paint_type)

        if brand_n and brand_n not in item_brand:
            return False
        if name_n and name_n not in item_name:
            return False
        if code_n and code_n != item_code:
            return False
        if range_n and range_n not in item_range:
            return False
        if type_n and type_n != item_type:
            return False
        if color_n and not any(color_n in value for value in normalized_colors):
            return False
        if query_n:
            haystack = " ".join(value for value in (item_brand, item_name, item_code, item_range, item_type, *sorted(normalized_colors)) if value)
            if query_n not in haystack:
                return False
        return True

    def _paint_payload(self, paint: object) -> dict[str, Any]:
        return {
            "id": getattr(paint, "id", None),
            "brand": str(getattr(paint, "brand", "") or ""),
            "name": str(getattr(paint, "name", "") or ""),
            "code": getattr(paint, "code", None),
            "range_name": getattr(paint, "range_name", None),
            "paint_type": str(getattr(paint, "paint_type", "") or ""),
            "primary_color": getattr(paint, "primary_color", None),
            "complementary_colors": list(getattr(paint, "complementary_colors", ()) or ()),
            "available_units": max(0, self._safe_int(getattr(paint, "available_units", 0))),
            "low_units": max(0, self._safe_int(getattr(paint, "low_units", 0))),
            "total_units": self._inventory_units(paint),
        }

    @staticmethod
    def _catalog_payload(paint: object) -> dict[str, Any]:
        return {
            "brand": str(getattr(paint, "brand", "") or ""),
            "name": str(getattr(paint, "name", "") or ""),
            "code": getattr(paint, "code", None),
            "range_name": getattr(paint, "range_name", None),
            "paint_type": str(getattr(paint, "paint_type", "") or ""),
            "swatch_hex": getattr(paint, "swatch_hex", None),
        }

    @classmethod
    def _inventory_units(cls, paint: object) -> int:
        total = getattr(paint, "total_units", None)
        if total is not None:
            try:
                return max(0, int(total))
            except (TypeError, ValueError):
                pass
        return max(0, cls._safe_int(getattr(paint, "available_units", 0))) + max(0, cls._safe_int(getattr(paint, "low_units", 0)))

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", without_marks).split())
