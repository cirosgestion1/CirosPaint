from __future__ import annotations

import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.services.favorite_category_service import FavoriteCategoryService
from app.services.favorite_paint_analysis_service import PaintAnalysisResult
from app.ui.dialogs.paint_analysis_dialog import PaintAnalysisDialog
from app.ui.pages.favorites_page import FavoriteCard


class FavoritePaintAnalysisUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def favorite():
        return SimpleNamespace(
            video_id="dQw4w9WgXcQ",
            title="Darth Vader painting guide",
            channel_title="Test Channel",
            description="",
            thumbnail_url="",
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            duration_text="10:00",
            published_at="2026-01-01T00:00:00Z",
            view_count=100,
            like_count=10,
        )

    def test_analysis_buttons_only_exist_for_miniatures(self):
        miniature = FavoriteCard(self.favorite(), FavoriteCategoryService.MINIATURES, lambda: None, lambda: None)
        general = FavoriteCard(self.favorite(), FavoriteCategoryService.GENERAL, lambda: None, lambda: None)
        try:
            self.assertIsNotNone(miniature.analyze_paints_button)
            self.assertEqual(miniature.analyze_paints_button.text(), "Analizar pinturas")
            self.assertIsNotNone(miniature.view_paints_button)
            self.assertTrue(miniature.view_paints_button.isHidden())
            self.assertIsNone(general.analyze_paints_button)
            self.assertIsNone(general.view_paints_button)
        finally:
            miniature.close()
            general.close()

    def test_results_dialog_has_three_visual_sections(self):
        result = PaintAnalysisResult(author_lines=(), detected=(), matches=(), missing=())
        dialog = PaintAnalysisDialog("Test", result)
        try:
            texts = [label.text() for label in dialog.findChildren(type(dialog.findChildren.__self__) if False else __import__('PySide6.QtWidgets', fromlist=['QLabel']).QLabel)]
            joined = " | ".join(texts)
            self.assertIn("1. Lo escrito por el autor", joined)
            self.assertIn("2. Coincidencias con tu inventario", joined)
            self.assertIn("3. Alternativas", joined)
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main()
