from __future__ import annotations

import unittest

from app.services.favorite_category_service import FavoriteCategoryService


class FavoriteCategoryServiceTests(unittest.TestCase):
    def test_identifies_miniature_tutorials(self):
        samples = (
            "Cómo pintar miniaturas de Warhammer",
            "Painting a Stormtrooper for Star Wars Legion",
            "28mm figure painting tutorial",
            "Peanas para miniaturas con barro",
        )
        for text in samples:
            with self.subTest(text=text):
                self.assertEqual(
                    FavoriteCategoryService.classify_text(text),
                    FavoriteCategoryService.MINIATURES,
                )

    def test_identifies_general_modeling_tutorials(self):
        samples = (
            "Cómo construir un diorama de bosque con nieve",
            "Aerógrafo y weathering para una maqueta de tanque",
            "Terrain trees and water effects tutorial",
            "Escenografía con espuma, corcho y vegetación",
        )
        for text in samples:
            with self.subTest(text=text):
                self.assertEqual(
                    FavoriteCategoryService.classify_text(text),
                    FavoriteCategoryService.GENERAL,
                )

    def test_general_is_safe_fallback_for_ambiguous_hobby_content(self):
        self.assertEqual(
            FavoriteCategoryService.classify_text("Técnica rápida de pincel y pigmentos"),
            FavoriteCategoryService.GENERAL,
        )


if __name__ == "__main__":
    unittest.main()
