from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.repositories.miniature_repository import MiniatureRepository
from app.repositories.paint_repository import PaintRepository
from app.repositories.shopping_repository import ShoppingRepository
from app.services.assistant_local_service import AssistantLocalService
from app.services.assistant_settings_store import AssistantSettingsStore
from app.services.query_service import CentralizedQueryService


class FakePaintCatalog:
    def __init__(self):
        self._items = [
            SimpleNamespace(brand="Citadel", name="Administratum Grey", code="22-50", range_name="Layer",
                            paint_type="Acrílico", primary_color="Gris", source_name="Administratum Grey Layer"),
            SimpleNamespace(brand="Vallejo", name="Black", code="72.051", range_name="Game Color",
                            paint_type="Acrílico", primary_color="Negro", source_name="Game Color Black"),
        ]


class FakeMiniatureCatalog:
    @classmethod
    def games(cls):
        return [{
            "id": "sw-legion", "name": "Star Wars: Legion", "factions": [{
                "id": "empire", "name": "Imperio", "units": [
                    {"id": "stormtroopers", "name": "Stormtroopers"},
                    {"id": "darth-vader", "name": "Darth Vader"},
                ],
            }],
        }]


class CentralizedQueryServiceV01010Tests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.paint_repository = PaintRepository(self.session)
        self.shopping_repository = ShoppingRepository(self.session)
        self.miniature_repository = MiniatureRepository(self.session)
        self.grey = self.paint_repository.add(
            brand="Citadel", name="Administratum Grey", code="22-50", range_name="Layer",
            paint_type="Acrílico", swatch_hex="#999999", available_units=2, low_units=1,
            primary_color="Gris", complementary_colors=[],
        )
        self.black = self.paint_repository.add(
            brand="Vallejo", name="Black", code="72.051", range_name="Game Color",
            paint_type="Acrílico", swatch_hex="#000000", available_units=0, low_units=0,
            primary_color="Negro", complementary_colors=[],
        )
        self.shopping_repository.set_future_quantity(self.black.id, 2)
        self.miniature_repository.add_faction("Star Wars: Legion", "Imperio")
        self.miniature_repository.upsert_entry(
            "Star Wars: Legion", "Imperio", "Stormtroopers",
            unassembled_count=2, assembled_count=1, painted_count=0, finished_count=0,
        )
        self.queries = CentralizedQueryService(
            self.session,
            paint_repository=self.paint_repository,
            shopping_repository=self.shopping_repository,
            miniature_repository=self.miniature_repository,
            paint_catalog_service=FakePaintCatalog(),
            miniature_catalog_service=FakeMiniatureCatalog,
        )

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_inventory_and_catalog_paint_searches(self):
        inventory = self.queries.filter_inventory_paints(query="Grey")
        catalog = self.queries.list_catalog_paints(code="72.051")
        self.assertEqual([paint.id for paint in inventory], [self.grey.id])
        self.assertEqual([paint.name for paint in catalog], ["Black"])

    def test_stock_comes_from_existing_inventory_entity(self):
        paint = self.queries.get_inventory_paint(self.grey.id)
        self.assertEqual(self.queries.paint_units(paint), 3)
        self.assertEqual([item.id for item in self.queries.list_inventory_paints(only_in_stock=True)], [self.grey.id])

    def test_future_purchases_reuse_eager_loaded_repository_result(self):
        entries = self.queries.list_future_paint_purchases()
        rows = self.queries.list_future_paint_rows()
        self.assertEqual([(entry.paint.name, entry.quantity) for entry in entries], [("Black", 2)])
        self.assertEqual([(row["paint"].name, row["quantity"]) for row in rows], [("Black", 2)])

    def test_miniature_collection_and_state_filter(self):
        all_entries = self.queries.list_miniature_collection("Star Wars: Legion", "Imperio")
        assembled = self.queries.list_miniature_collection("Star Wars: Legion", "Imperio", state="Montado")
        finished = self.queries.list_miniature_collection("Star Wars: Legion", "Imperio", state="Terminado")
        self.assertEqual([entry.unit_name for entry in all_entries], ["Stormtroopers"])
        self.assertEqual([entry.unit_name for entry in assembled], ["Stormtroopers"])
        self.assertEqual(finished, [])

    def test_full_miniature_catalog_and_owned_only(self):
        catalog = self.queries.list_miniature_catalog_units()
        owned = self.queries.list_miniature_catalog_units(owned_only=True)
        self.assertEqual({unit.unit_name for unit in catalog}, {"Stormtroopers", "Darth Vader"})
        self.assertEqual([unit.unit_name for unit in owned], ["Stormtroopers"])

    def test_query_results_are_equivalent_to_repositories(self):
        self.assertEqual(
            [paint.id for paint in self.queries.list_inventory_paints()],
            [paint.id for paint in self.paint_repository.list()],
        )
        self.assertEqual(
            [entry.id for entry in self.queries.list_miniature_collection("Star Wars: Legion", "Imperio")],
            [entry.id for entry in self.miniature_repository.list_entries("Star Wars: Legion", "Imperio")],
        )

    def test_local_operation_does_not_use_gemini(self):
        local = AssistantLocalService(self.session)
        with patch.object(AssistantSettingsStore, "gemini_api_key", return_value=""), \
             patch.object(AssistantSettingsStore, "increment_gemini_request_count") as increment:
            result = local.try_handle_text("Buscar pintura: Gris")
        self.assertEqual(result.status, "ok")
        self.assertFalse(result.requires_ai_resolution)
        increment.assert_not_called()


if __name__ == "__main__":
    unittest.main()
