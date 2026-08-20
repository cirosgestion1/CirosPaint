from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from app.services.favorite_paint_purchase_service import FavoritePaintPurchaseService


class FavoritePaintPurchaseV0102Tests(unittest.TestCase):
    @staticmethod
    def source():
        return SimpleNamespace(
            brand="Citadel",
            name="Evil Sunz Scarlet",
            code="22-05",
            range_name="Layer",
            paint_type="Acrílico",
            swatch_hex="#C21920",
        )

    @patch("app.services.favorite_paint_purchase_service.ShoppingRepository")
    @patch("app.services.favorite_paint_purchase_service.PaintRepository")
    def test_existing_future_entry_is_not_duplicated(self, paint_repo_cls, shopping_repo_cls):
        existing = SimpleNamespace(id=7, brand="Citadel", name="Evil Sunz Scarlet", code="22-05", range_name="Layer")
        paint_repo_cls.return_value.list.return_value = [existing]
        shopping_repo_cls.return_value.get_for_paint.return_value = SimpleNamespace(stage="future", quantity=2)

        service = FavoritePaintPurchaseService(MagicMock())
        status = service.add_to_future(self.source())

        self.assertEqual(status, "already")
        shopping_repo_cls.return_value.set_future_quantity.assert_not_called()
        paint_repo_cls.return_value.add.assert_not_called()

    @patch("app.services.favorite_paint_purchase_service.ShoppingRepository")
    @patch("app.services.favorite_paint_purchase_service.PaintRepository")
    def test_existing_non_future_entry_is_promoted_directly_to_future(self, paint_repo_cls, shopping_repo_cls):
        existing = SimpleNamespace(id=8, brand="Citadel", name="Evil Sunz Scarlet", code="22-05", range_name="Layer")
        paint_repo_cls.return_value.list.return_value = [existing]
        shopping_repo_cls.return_value.get_for_paint.return_value = SimpleNamespace(stage="basket", quantity=3)

        service = FavoritePaintPurchaseService(MagicMock())
        status = service.add_to_future(self.source())

        self.assertEqual(status, "added")
        shopping_repo_cls.return_value.set_future_quantity.assert_called_once_with(8, 3)

    @patch("app.services.favorite_paint_purchase_service.infer_color_tags", return_value=("Rojo", []))
    @patch("app.services.favorite_paint_purchase_service.ShoppingRepository")
    @patch("app.services.favorite_paint_purchase_service.PaintRepository")
    def test_missing_catalog_paint_is_created_at_zero_and_added_to_future(
        self, paint_repo_cls, shopping_repo_cls, infer_tags
    ):
        paint_repo_cls.return_value.list.return_value = []
        created = SimpleNamespace(id=9)
        paint_repo_cls.return_value.add.return_value = created
        shopping_repo_cls.return_value.get_for_paint.return_value = None

        service = FavoritePaintPurchaseService(MagicMock())
        status = service.add_to_future(self.source())

        self.assertEqual(status, "added")
        infer_tags.assert_called_once_with("Evil Sunz Scarlet", "#C21920", "Layer")
        kwargs = paint_repo_cls.return_value.add.call_args.kwargs
        self.assertEqual(kwargs["brand"], "Citadel")
        self.assertEqual(kwargs["name"], "Evil Sunz Scarlet")
        self.assertEqual(kwargs["available_units"], 0)
        self.assertEqual(kwargs["low_units"], 0)
        shopping_repo_cls.return_value.set_future_quantity.assert_called_once_with(9, 1)


if __name__ == "__main__":
    unittest.main()
