from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from app.repositories.miniature_repository import MiniatureRepository
from app.repositories.paint_repository import PaintRepository
from app.repositories.shopping_repository import ShoppingRepository
from app.services.miniature_catalog_service import MiniatureCatalogService
from app.services.paint_catalog_service import PaintCatalogService


@dataclass(frozen=True)
class MiniatureCatalogUnit:
    game_id: str
    game_name: str
    faction_id: str
    faction_name: str
    unit_id: str
    unit_name: str

    def as_dict(self) -> dict[str, str]:
        return {
            "game_id": self.game_id, "game_name": self.game_name,
            "faction_id": self.faction_id, "faction_name": self.faction_name,
            "unit_id": self.unit_id, "unit_name": self.unit_name,
        }


class CentralizedQueryService:
    """Application read facade backed by the existing repositories and catalogs."""

    def __init__(self, session: Session, *, paint_repository=None, shopping_repository=None,
                 miniature_repository=None, paint_catalog_service=None,
                 miniature_catalog_service=MiniatureCatalogService):
        self.session = session
        self.paint_repository = paint_repository or PaintRepository(session)
        self.shopping_repository = shopping_repository or ShoppingRepository(session)
        self.miniature_repository = miniature_repository or MiniatureRepository(session)
        self.paint_catalog_service = paint_catalog_service or PaintCatalogService()
        self.miniature_catalog_service = miniature_catalog_service
        self._miniature_units: tuple[MiniatureCatalogUnit, ...] | None = None

    def list_inventory_paints(self, search: str = "", colors: list[str] | None = None,
                              paint_types: list[str] | None = None, *, only_in_stock: bool = False) -> list[object]:
        if search or colors or paint_types:
            paints = self.paint_repository.list(search, colors, paint_types)
        else:
            paints = self.paint_repository.list()
        return [paint for paint in paints if self.paint_units(paint) > 0] if only_in_stock else paints

    def get_inventory_paint(self, paint_id: int):
        return self.paint_repository.get(paint_id)

    def filter_inventory_paints(self, **filters: str) -> list[object]:
        return [paint for paint in self.list_inventory_paints() if self._matches_paint(paint, **filters)]

    def list_catalog_paints(self, **filters: str) -> list[object]:
        return [item for item in getattr(self.paint_catalog_service, "_items", ()) if self._matches_paint(item, **filters)]

    def list_future_paint_purchases(self) -> list[object]:
        return self.shopping_repository.list_future()

    def list_future_paint_rows(self, *, include_restock: bool = False) -> list[dict]:
        entries = self.shopping_repository.list_entries()
        entries_by_paint = {entry.paint_id: entry for entry in entries}
        rows = [
            {"paint_id": entry.paint_id, "paint": entry.paint, "quantity": max(1, _safe_int(entry.quantity))}
            for entry in self.list_future_paint_purchases()
        ]
        if include_restock:
            future_ids = {row["paint_id"] for row in rows}
            for paint in self.list_inventory_paints():
                if getattr(paint, "needs_restock", False) and paint.id not in future_ids and entries_by_paint.get(paint.id) is None:
                    rows.append({"paint_id": paint.id, "paint": paint, "quantity": 1})
        return sorted(rows, key=lambda row: (_normalize(row["paint"].name), _normalize(row["paint"].brand)))

    @staticmethod
    def paint_units(paint: object) -> int:
        return _safe_int(getattr(paint, "available_units", 0)) + _safe_int(getattr(paint, "low_units", 0))

    def list_miniature_catalog_units(self, game_id: str = "", faction_id: str = "", *,
                                     owned_only: bool = False, units: Iterable[MiniatureCatalogUnit] | None = None,
                                     owned_keys: set[str] | None = None) -> list[MiniatureCatalogUnit]:
        source = list(units) if units is not None else list(self._catalog_units())
        if owned_only:
            keys = owned_keys if owned_keys is not None else self.owned_miniature_keys()
            source = [unit for unit in source if _normalize(unit.unit_id) in keys or _normalize(unit.unit_name) in keys]
        rows = [unit for unit in source if (not game_id or unit.game_id == game_id)
                and (not faction_id or unit.faction_id == faction_id)]
        return sorted(rows, key=lambda unit: _normalize(unit.unit_name))

    def list_miniature_games(self, *, owned_only: bool = False, units=None,
                             owned_keys: set[str] | None = None) -> list[tuple[str, str]]:
        values: dict[str, str] = {}
        for unit in self.list_miniature_catalog_units(owned_only=owned_only, units=units, owned_keys=owned_keys):
            values.setdefault(unit.game_id, unit.game_name)
        return sorted(values.items(), key=lambda item: _normalize(item[1]))

    def list_miniature_factions(self, game_id: str, *, owned_only: bool = False, units=None,
                                owned_keys: set[str] | None = None) -> list[tuple[str, str]]:
        values: dict[str, str] = {}
        for unit in self.list_miniature_catalog_units(game_id, owned_only=owned_only, units=units, owned_keys=owned_keys):
            values.setdefault(unit.faction_id, unit.faction_name)
        return sorted(values.items(), key=lambda item: _normalize(item[1]))

    def list_collection_factions(self, game: str) -> list[object]:
        return self.miniature_repository.list_factions(game)

    def list_miniature_collection(self, game: str = "", faction: str = "", *, state: str = "") -> list[object]:
        entries = self.miniature_repository.list_all_entries(game=game, faction=faction)
        column = {"Sin montar": "unassembled_count", "Montado": "assembled_count",
                  "Pintado": "painted_count", "Terminado": "finished_count"}.get(state)
        return [entry for entry in entries if _safe_int(getattr(entry, column, 0)) > 0] if column else entries

    def miniature_collection_summary(self, game: str, faction: str) -> dict[str, int]:
        return self.miniature_repository.summary(game, faction)

    def owned_miniature_keys(self) -> set[str]:
        keys = set()
        for entry in self.list_miniature_collection():
            total = sum(_safe_int(getattr(entry, name, 0)) for name in
                        ("unassembled_count", "assembled_count", "painted_count", "finished_count"))
            if total > 0:
                keys.add(_normalize(getattr(entry, "unit_name", "")))
        return keys

    def _catalog_units(self) -> tuple[MiniatureCatalogUnit, ...]:
        if self._miniature_units is None:
            rows = []
            for game_index, game in enumerate(self.miniature_catalog_service.games()):
                game_name = str(game.get("name") or f"Juego {game_index + 1}")
                game_id = str(game.get("id") or game.get("key") or game.get("slug") or _slug(game_name))
                for faction_index, faction in enumerate(game.get("factions") or []):
                    faction_name = str(faction.get("name") or f"Facción {faction_index + 1}")
                    faction_id = str(faction.get("id") or faction.get("key") or faction.get("slug") or _slug(faction_name))
                    for unit in faction.get("units") or []:
                        unit_name = str(unit.get("name") or unit.get("title") or "").strip()
                        if unit_name:
                            unit_id = str(unit.get("id") or unit.get("key") or unit.get("slug") or _slug(unit_name))
                            rows.append(MiniatureCatalogUnit(game_id, game_name, faction_id, faction_name, unit_id, unit_name))
            self._miniature_units = tuple(rows)
        return self._miniature_units

    @staticmethod
    def _matches_paint(paint: object, **filters: str) -> bool:
        values = [getattr(paint, name, "") for name in
                  ("brand", "name", "code", "range_name", "paint_type", "primary_color", "source_name")]
        query = _normalize(filters.get("query", ""))
        if query and query not in " ".join(_normalize(value) for value in values if value):
            return False
        named = (("brand", 0), ("name", 1), ("code", 2), ("range_name", 3), ("paint_type", 4))
        if any(_normalize(filters.get(key, "")) and _normalize(filters[key]) not in _normalize(values[index])
               for key, index in named):
            return False
        color = _normalize(filters.get("color", ""))
        if color:
            colors = {_normalize(getattr(paint, "primary_color", ""))}
            colors.update(_normalize(getattr(tag, "color_name", "")) for tag in getattr(paint, "color_tags", ()))
            if color not in colors:
                return False
        return True


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join("".join(char for char in text if not unicodedata.combining(char)).casefold().strip().split())


def _slug(value: str) -> str:
    return "-".join(_normalize(value).replace(":", " ").split())


def _safe_int(value: object) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
