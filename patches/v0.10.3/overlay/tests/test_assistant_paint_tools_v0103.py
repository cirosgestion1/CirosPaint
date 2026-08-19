from __future__ import annotations

from types import SimpleNamespace
import unittest

from app.services.assistant_paint_service import AssistantPaintService
from app.services.assistant_tool_registry import PAINT_TOOL_NAMES, get_paint_tool_definitions


class FakeSession:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


class FakePaintRepository:
    def __init__(self, paints=None):
        self.paints = list(paints or [])
        self._next_id = 100

    def list(self):
        return list(self.paints)

    def add(self, **kwargs):
        paint = SimpleNamespace(id=self._next_id, color_lab=kwargs.pop("color_lab", None), **kwargs)
        paint.total_units = paint.available_units + paint.low_units
        self._next_id += 1
        self.paints.append(paint)
        return paint


class FakeShoppingRepository:
    def __init__(self):
        self.entries = {}

    def get_for_paint(self, paint_id):
        return self.entries.get(paint_id)

    def set_future_quantity(self, paint_id, quantity):
        self.entries[paint_id] = SimpleNamespace(paint_id=paint_id, quantity=quantity, stage="future")

    def list_future(self):
        return [item for item in self.entries.values() if item.stage == "future"]


class FakeCatalog:
    def __init__(self, items):
        self._items = list(items)


def catalog_paint(name, code, lab=(50.0, 0.0, 0.0), paint_type="Acrílico", brand="AK Interactive"):
    return SimpleNamespace(
        brand=brand,
        name=name,
        code=code,
        range_name="3rd Generation",
        paint_type=paint_type,
        swatch_hex="#777777",
        lab=lab,
    )


def inventory_paint(
    paint_id,
    name,
    code,
    available=1,
    low=0,
    lab=(50.0, 0.0, 0.0),
    paint_type="Acrílico",
    brand="AK Interactive",
    primary_color="Gris",
):
    paint = SimpleNamespace(
        id=paint_id,
        brand=brand,
        name=name,
        code=code,
        range_name="3rd Generation",
        paint_type=paint_type,
        swatch_hex="#777777",
        primary_color=primary_color,
        complementary_colors=[],
        available_units=available,
        low_units=low,
        color_lab=lab,
    )
    paint.total_units = available + low
    return paint


class AssistantPaintToolsV0103Tests(unittest.TestCase):
    def make_service(self, paints=None, catalog=None):
        session = FakeSession()
        paint_repo = FakePaintRepository(paints)
        shopping_repo = FakeShoppingRepository()
        service = AssistantPaintService(
            session,
            catalog_service=FakeCatalog(catalog or []),
            paint_repository=paint_repo,
            shopping_repository=shopping_repo,
        )
        return service, session, paint_repo, shopping_repo

    def test_registry_exposes_exactly_the_seven_initial_paint_tools(self):
        self.assertEqual(
            PAINT_TOOL_NAMES,
            (
                "search_paints",
                "get_paint_stock",
                "find_paint_alternatives",
                "add_paint_to_inventory",
                "set_paint_quantity",
                "add_paint_to_future_purchases",
                "list_future_paint_purchases",
            ),
        )
        definitions = get_paint_tool_definitions()
        self.assertEqual(len(definitions), 7)
        self.assertTrue(next(item for item in definitions if item["name"] == "add_paint_to_inventory")["mutates_data"])
        self.assertFalse(next(item for item in definitions if item["name"] == "get_paint_stock")["mutates_data"])

    def test_search_filters_by_brand_color_type_and_stock(self):
        paints = [
            inventory_paint(1, "Black Grey", "AK11018", available=1, primary_color="Gris"),
            inventory_paint(2, "Deep Red", "AK11097", available=0, primary_color="Rojo"),
            inventory_paint(3, "Grey Primer", "AK-P", available=1, primary_color="Gris", paint_type="Imprimación"),
        ]
        service, *_ = self.make_service(paints=paints)
        result = service.search_paints(brand="AK", color="gris", paint_type="Acrílico", only_in_stock=True)
        self.assertEqual(result.status, "ok")
        self.assertEqual([item["code"] for item in result.data["paints"]], ["AK11018"])

    def test_stock_returns_database_quantity(self):
        service, *_ = self.make_service(paints=[inventory_paint(1, "Black Grey", "AK11018", available=2, low=1)])
        result = service.get_paint_stock(code="AK11018")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.data["paint"]["total_units"], 3)

    def test_ambiguous_write_requests_user_input_and_does_not_mutate(self):
        source_a = catalog_paint("Grey", "A1")
        source_b = catalog_paint("Grey Blue", "A2")
        service, _, paint_repo, _ = self.make_service(catalog=[source_a, source_b])
        result = service.add_paint_to_inventory(query="grey", quantity=1)
        self.assertEqual(result.status, "ambiguous")
        self.assertTrue(result.requires_user_input)
        self.assertEqual(paint_repo.list(), [])

    def test_buying_existing_paint_adds_units_instead_of_setting_total(self):
        source = catalog_paint("Black Grey", "AK11018")
        existing = inventory_paint(1, "Black Grey", "AK11018", available=1, low=1)
        service, session, _, _ = self.make_service(paints=[existing], catalog=[source])
        result = service.add_paint_to_inventory(code="AK11018", quantity=2)
        self.assertEqual(result.status, "ok")
        self.assertEqual(existing.available_units, 3)
        self.assertEqual(existing.low_units, 1)
        self.assertGreaterEqual(session.commits, 1)

    def test_setting_total_preserves_low_units_when_possible(self):
        existing = inventory_paint(1, "Black Grey", "AK11018", available=2, low=1)
        service, _, _, _ = self.make_service(paints=[existing])
        result = service.set_paint_quantity(code="AK11018", quantity=2)
        self.assertEqual(result.status, "ok")
        self.assertEqual(existing.low_units, 1)
        self.assertEqual(existing.available_units, 1)

    def test_future_purchase_reuses_existing_entry_without_duplicate(self):
        source = catalog_paint("Black Grey", "AK11018")
        existing = inventory_paint(1, "Black Grey", "AK11018", available=0)
        service, _, _, shopping = self.make_service(paints=[existing], catalog=[source])
        first = service.add_paint_to_future_purchases(code="AK11018", quantity=2)
        second = service.add_paint_to_future_purchases(code="AK11018", quantity=2)
        self.assertEqual(first.status, "ok")
        self.assertFalse(first.data["already_present"])
        self.assertTrue(second.data["already_present"])
        self.assertEqual(len(shopping.list_future()), 1)

    def test_alternatives_use_same_type_stock_and_85_percent_threshold(self):
        source = catalog_paint("Target", "T1", lab=(50.0, 0.0, 0.0))
        close = inventory_paint(1, "Close", "C1", available=1, lab=(51.0, 0.0, 0.0))
        empty = inventory_paint(2, "Empty", "E1", available=0, lab=(50.0, 0.0, 0.0))
        wrong_type = inventory_paint(3, "Wrong Type", "W1", available=1, lab=(50.0, 0.0, 0.0), paint_type="Lavado")
        far = inventory_paint(4, "Far", "F1", available=1, lab=(100.0, 100.0, 100.0))
        service, *_ = self.make_service(paints=[close, empty, wrong_type, far], catalog=[source])
        result = service.find_paint_alternatives(code="T1")
        self.assertEqual(result.status, "ok")
        self.assertEqual([row["paint"]["code"] for row in result.data["alternatives"]], ["C1"])
        self.assertGreaterEqual(result.data["alternatives"][0]["similarity_percent"], 85.0)

    def test_unknown_catalog_paint_is_never_created(self):
        service, _, paint_repo, _ = self.make_service()
        result = service.add_paint_to_inventory(query="Invented Paint", quantity=1)
        self.assertEqual(result.status, "not_found")
        self.assertEqual(paint_repo.list(), [])

    def test_dispatcher_rejects_unknown_tool(self):
        service, *_ = self.make_service()
        result = service.execute("delete_everything", {})
        self.assertEqual(result.status, "invalid")


if __name__ == "__main__":
    unittest.main()
