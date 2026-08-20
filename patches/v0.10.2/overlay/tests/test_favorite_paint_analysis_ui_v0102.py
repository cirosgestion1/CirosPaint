from __future__ import annotations

import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from app.services.favorite_paint_analysis_service import (
    DetectedPaint,
    MissingPaintAlternatives,
    PaintAnalysisResult,
)
from app.ui.dialogs.paint_analysis_dialog import PaintAnalysisDialog


class FavoritePaintAnalysisUiV0102Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def catalog_paint():
        return SimpleNamespace(
            brand="Citadel",
            name="Evil Sunz Scarlet",
            range_name="Layer",
            code="22-05",
            paint_type="Acrílico",
        )

    def test_empty_analysis_shows_clear_message(self):
        result = PaintAnalysisResult(author_lines=(), detected=(), matches=(), missing=())
        dialog = PaintAnalysisDialog("Test", result)
        try:
            joined = " | ".join(label.text() for label in dialog.findChildren(QLabel))
            self.assertIn("No se han encontrado pinturas en la descripción del vídeo.", joined)
            self.assertNotIn("1. Lo escrito por el autor", joined)
        finally:
            dialog.close()

    def test_missing_paint_without_85_percent_match_has_cart_button(self):
        source = self.catalog_paint()
        detected = DetectedPaint("Evil Sunz Scarlet", source)
        result = PaintAnalysisResult(
            author_lines=("Evil Sunz Scarlet",),
            detected=(detected,),
            matches=(),
            missing=(MissingPaintAlternatives(detected, ()),),
        )
        added = []

        def add_to_future(paint):
            added.append(paint.name)
            return "added"

        dialog = PaintAnalysisDialog("Test", result, on_add_to_future_purchases=add_to_future)
        try:
            labels = " | ".join(label.text() for label in dialog.findChildren(QLabel))
            self.assertIn("No hay coincidencias de al menos un 85 %", labels)
            buttons = [button for button in dialog.findChildren(QPushButton) if "Añadir a futuras compras" in button.text()]
            self.assertEqual(len(buttons), 1)
            buttons[0].click()
            self.assertEqual(added, ["Evil Sunz Scarlet"])
            self.assertFalse(buttons[0].isEnabled())
            self.assertIn("Añadida", buttons[0].text())
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main()
