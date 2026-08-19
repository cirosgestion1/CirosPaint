from __future__ import annotations

from types import SimpleNamespace
import unittest

from app.db.database import get_session, init_database
from app.repositories.paint_repository import PaintRepository
from app.repositories.shopping_repository import ShoppingRepository
from app.services.assistant_paint_service import AssistantPaintService


class FakeCatalog:
    def __init__(self, items):
        self._items = list(items)


class AssistantPaintToolsIntegrationV0103Tests(unittest.TestCase):
    def test_assistant_paint_writes_use_real_ciros_paint_repositories(self):
        init_database()
        code = "CIROS-ASSISTANT-0103"
        source = SimpleNamespace(
            brand="Ciros Paint Test",
            name="Assistant Grey 0103",
            code=code,
            range_name="Integration",
            paint_type="Acrílico",
            swatch_hex="#777777",
            lab=(50.0, 0.0, 0.0),
        )

        with get_session() as session:
            paint_repo = PaintRepository(session)
            shopping_repo = ShoppingRepository(session)

            for paint in paint_repo.list():
                if getattr(paint, "code", None) == code:
                    entry = shopping_repo.get_for_paint(paint.id)
                    if entry is not None:
                        session.delete(entry)
                    session.delete(paint)
            session.commit()

            service = AssistantPaintService(session, catalog_service=FakeCatalog([source]))

            added = service.add_paint_to_inventory(code=code, quantity=2)
            self.assertEqual(added.status, "ok")
            paint = next(item for item in paint_repo.list() if getattr(item, "code", None) == code)
            self.assertEqual(paint.total_units, 2)

            stock = service.get_paint_stock(code=code)
            self.assertEqual(stock.status, "ok")
            self.assertEqual(stock.data["paint"]["total_units"], 2)

            changed = service.set_paint_quantity(code=code, quantity=1)
            self.assertEqual(changed.status, "ok")
            session.refresh(paint)
            self.assertEqual(paint.total_units, 1)

            future = service.add_paint_to_future_purchases(code=code, quantity=2)
            self.assertEqual(future.status, "ok")
            entry = shopping_repo.get_for_paint(paint.id)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.stage, "future")
            self.assertEqual(entry.quantity, 2)

            listed = service.list_future_paint_purchases()
            self.assertEqual(listed.status, "ok")
            found = [row for row in listed.data["purchases"] if row["paint"]["code"] == code]
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["quantity"], 2)

            session.delete(entry)
            session.delete(paint)
            session.commit()


if __name__ == "__main__":
    unittest.main()
