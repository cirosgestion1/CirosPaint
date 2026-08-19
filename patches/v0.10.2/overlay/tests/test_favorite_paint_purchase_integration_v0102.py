from __future__ import annotations

from types import SimpleNamespace
import unittest

from app.db.database import get_session, init_database
from app.repositories.paint_repository import PaintRepository
from app.repositories.shopping_repository import ShoppingRepository
from app.services.favorite_paint_purchase_service import FavoritePaintPurchaseService


class FavoritePaintPurchaseIntegrationV0102Tests(unittest.TestCase):
    def test_original_catalog_paint_reaches_real_future_purchase_repository(self):
        # Mirror the normal application startup so the real SQLite schema exists.
        init_database()

        source = SimpleNamespace(
            brand="Ciros Paint Test",
            name="Integration Scarlet 0102",
            code="CIROS-0102-TEST",
            range_name="Integration",
            paint_type="Acrílico",
            swatch_hex="#C21920",
        )

        with get_session() as session:
            paint_repo = PaintRepository(session)
            shopping_repo = ShoppingRepository(session)

            # Defensive cleanup in case a runner reuses a local database.
            for paint in paint_repo.list():
                if getattr(paint, "code", None) == source.code:
                    entry = shopping_repo.get_for_paint(paint.id)
                    if entry is not None:
                        session.delete(entry)
                    session.delete(paint)
            session.commit()

            status = FavoritePaintPurchaseService(session).add_to_future(source)
            self.assertEqual(status, "added")

            paint = next(p for p in paint_repo.list() if getattr(p, "code", None) == source.code)
            self.assertEqual(paint.total_units, 0)
            self.assertEqual(paint.paint_type, "Acrílico")

            entry = shopping_repo.get_for_paint(paint.id)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.stage, "future")
            self.assertEqual(entry.quantity, 1)

            # A second click must not duplicate or alter the existing future entry.
            self.assertEqual(FavoritePaintPurchaseService(session).add_to_future(source), "already")
            entries = [item for item in shopping_repo.list_future() if item.paint_id == paint.id]
            self.assertEqual(len(entries), 1)

            session.delete(entry)
            session.delete(paint)
            session.commit()


if __name__ == "__main__":
    unittest.main()
