from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"Expected one {label}; found {text.count(old)}")
    return text.replace(old, new, 1)


def replace_section(text: str, start: str, end: str, new: str, label: str) -> str:
    first = text.find(start)
    last = text.find(end, first)
    if first < 0 or last < 0:
        raise RuntimeError(f"Could not locate {label}")
    return text[:first] + new + text[last:]


def update(root: Path, relative: str, transform) -> None:
    path = root / relative
    path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")


def main(root: Path) -> None:
    update(root, "app/core/config.py", lambda text: replace_once(
        text, 'APP_VERSION = "0.10.9"', 'APP_VERSION = "0.10.10"', "0.10.9 version marker"
    ))

    def miniature_repository(text: str) -> str:
        anchor = "    def upsert_entry(\n"
        method = '''    def list_all_entries(self, game: str = "", faction: str = "") -> list[MiniatureCollectionEntry]:
        stmt = select(MiniatureCollectionEntry)
        if game:
            stmt = stmt.where(MiniatureCollectionEntry.game == game)
        if faction:
            stmt = stmt.where(MiniatureCollectionEntry.faction == faction)
        stmt = stmt.order_by(MiniatureCollectionEntry.unit_name.asc())
        return list(self.session.scalars(stmt).all())

'''
        return replace_once(text, anchor, method + anchor, "miniature repository read method")
    update(root, "app/repositories/miniature_repository.py", miniature_repository)

    def paint_service(text: str) -> str:
        if "def set_paint_quantity_by_id(" in text:
            return text
        text = replace_once(text, "from app.services.paint_catalog_service import PaintCatalogService, infer_color_tags\n",
                            "from app.services.paint_catalog_service import PaintCatalogService, infer_color_tags\nfrom app.services.query_service import CentralizedQueryService\n",
                            "paint query import")
        text = replace_once(text, "        shopping_repository: ShoppingRepository | None = None,\n    ):",
                            "        shopping_repository: ShoppingRepository | None = None,\n        query_service: CentralizedQueryService | None = None,\n    ):",
                            "paint constructor signature")
        text = replace_once(text, "        self.shopping_repository = shopping_repository or ShoppingRepository(session)\n",
                            "        self.shopping_repository = shopping_repository or ShoppingRepository(session)\n"
                            "        self.query_service = query_service or CentralizedQueryService(\n"
                            "            session, paint_repository=self.paint_repository, shopping_repository=self.shopping_repository,\n"
                            "            paint_catalog_service=self.catalog_service,\n        )\n",
                            "paint query initialization")
        text = text.replace("self.paint_repository.list()", "self.query_service.list_inventory_paints()")
        text = replace_once(text, 'items = list(getattr(self.catalog_service, "_items", ()))',
                            "items = self.query_service.list_catalog_paints()", "catalog read")
        old = '''        paints_by_id = {getattr(paint, "id", None): paint for paint in self.query_service.list_inventory_paints()}
        rows: list[dict[str, Any]] = []
        for entry in self.shopping_repository.list_future():
            paint = paints_by_id.get(getattr(entry, "paint_id", None))
            if paint is None:
                continue
            rows.append({"paint": self._paint_payload(paint), "quantity": self._safe_int(getattr(entry, "quantity", 0))})
'''
        new = '''        rows: list[dict[str, Any]] = []
        for entry in self.query_service.list_future_paint_purchases():
            paint = getattr(entry, "paint", None)
            if paint is not None:
                rows.append({"paint": self._paint_payload(paint), "quantity": self._safe_int(getattr(entry, "quantity", 0))})
'''
        return replace_once(text, old, new, "future purchases read")
    update(root, "app/services/assistant_paint_service.py", paint_service)

    def local_service(text: str) -> str:
        if "PaintConversationContext" in text:
            return text
        text = replace_once(text, "from app.services.paint_catalog_service import PaintCatalogService\n",
                            "from app.services.paint_catalog_service import PaintCatalogService\n"
                            "from app.services.query_service import CentralizedQueryService, MiniatureCatalogUnit\n",
                            "local query import")
        text = replace_section(text, "@dataclass(frozen=True)\nclass MiniatureUnit:", "\n\nclass AssistantLocalService:",
                               "MiniatureUnit = MiniatureCatalogUnit", "miniature unit data class")
        text = replace_once(text, "        self.catalog_service = PaintCatalogService()\n",
                            "        self.catalog_service = self.paint_service.catalog_service\n"
                            "        self.query_service = CentralizedQueryService(\n"
                            "            session, paint_repository=self.paint_service.paint_repository,\n"
                            "            shopping_repository=self.paint_service.shopping_repository,\n"
                            "            paint_catalog_service=self.catalog_service,\n        )\n"
                            "        self.paint_service.query_service = self.query_service\n", "local query initialization")
        text = replace_once(text, "        self._miniatures = self._load_miniature_catalog()\n",
                            "        self._miniatures = self.query_service.list_miniature_catalog_units()\n", "miniature catalog load")
        text = text.replace("self.paint_service.paint_repository.list()", "self.query_service.list_inventory_paints()")
        games = '''    def miniature_games(self, *, owned_only: bool = False) -> list[tuple[str, str]]:
        keys = self._owned_collection_keys() if owned_only else None
        return self.query_service.list_miniature_games(owned_only=owned_only, units=self._miniatures, owned_keys=keys)

    def miniature_factions(self, game_id: str, *, owned_only: bool = False) -> list[tuple[str, str]]:
        keys = self._owned_collection_keys() if owned_only else None
        return self.query_service.list_miniature_factions(
            game_id, owned_only=owned_only, units=self._miniatures, owned_keys=keys
        )

    def miniature_units(self, game_id: str = "", faction_id: str = "", *, owned_only: bool = False) -> list[MiniatureUnit]:
        keys = self._owned_collection_keys() if owned_only else None
        return self.query_service.list_miniature_catalog_units(
            game_id, faction_id, owned_only=owned_only, units=self._miniatures, owned_keys=keys
        )

    def owned_miniature_units(self) -> list[MiniatureUnit]:
        return self.miniature_units(owned_only=True)

'''
        return replace_section(text, "    def miniature_games(", "    def _owned_collection_keys(", games,
                               "local miniature query facade")
    update(root, "app/services/assistant_local_service.py", local_service)

    def paints_page(text: str) -> str:
        text = replace_once(text, "from app.repositories.shopping_repository import ShoppingRepository\n",
                            "from app.repositories.shopping_repository import ShoppingRepository\nfrom app.services.query_service import CentralizedQueryService\n",
                            "paints page query import")
        return replace_once(text, "            items = PaintRepository(session).list(self.search.text(), colors, types)",
                            "            items = CentralizedQueryService(session).list_inventory_paints(self.search.text(), colors, types)",
                            "paints page list")
    update(root, "app/ui/pages/paints_page.py", paints_page)

    def shopping_page(text: str) -> str:
        text = replace_once(text, "from app.repositories.shopping_repository import ShoppingRepository\n",
                            "from app.repositories.shopping_repository import ShoppingRepository\nfrom app.services.query_service import CentralizedQueryService\n",
                            "shopping query import")
        start = "            shopping_repo = ShoppingRepository(session)\n            entries = shopping_repo.list_entries()"
        end = "\n        rows = [(\"paint\", row) for row in paint_rows] + [(\"material\", row) for row in material_rows]"
        new = '''            shopping_repo = ShoppingRepository(session)
            purchase_rows = CentralizedQueryService(
                session, shopping_repository=shopping_repo
            ).list_future_purchase_rows(include_restock=True)
            paint_rows = [row for row in purchase_rows if row["kind"] == "paint"]
            material_rows = [row for row in purchase_rows if row["kind"] == "material"]
'''
        return replace_section(text, start, end, new, "shopping purchase reads")
    update(root, "app/ui/pages/shopping_page.py", shopping_page)

    def miniatures_page(text: str) -> str:
        text = replace_once(text, "from app.services.miniature_catalog_service import MiniatureCatalogService\n",
                            "from app.services.miniature_catalog_service import MiniatureCatalogService\nfrom app.services.query_service import CentralizedQueryService\n",
                            "miniature page query import")
        text = replace_once(text, "            stored = MiniatureRepository(session).list_factions(self.current_game)",
                            "            stored = CentralizedQueryService(session).list_collection_factions(self.current_game)",
                            "faction list read")
        text = replace_once(text, "            entries = repo.list_entries(self.current_game, self.current_faction)\n            summary = repo.summary(self.current_game, self.current_faction)",
                            "            queries = CentralizedQueryService(session, miniature_repository=repo)\n"
                            "            entries = queries.list_miniature_collection(self.current_game, self.current_faction)\n"
                            "            summary = queries.miniature_collection_summary(self.current_game, self.current_faction)",
                            "collection reads")
        return text
    update(root, "app/ui/pages/miniatures_page.py", miniatures_page)

    required = [
        root / "app/services/query_service.py",
        root / "app/services/assistant_conversation_context.py",
        root / "tests/test_query_service_v01010.py",
        root / "tests/test_assistant_regressions_v01010.py",
        root / "tests/test_favorite_paint_analysis_regressions_v01010.py",
        root / "tests/test_runtime_assets_v01010.py",
        root / "app/assets/runtime_assets_manifest.json",
    ]
    if not all(path.is_file() for path in required):
        raise RuntimeError("Missing 0.10.10 overlay files")
    print("Applied Ciros Paint 0.10.10 centralized query service")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve())
