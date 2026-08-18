from __future__ import annotations

import unittest

from app.services.paint_catalog_service import PaintCatalogService, infer_color_tags


class PaintCatalogTests(unittest.TestCase):
    def test_catalog_contains_ice_yellow(self):
        catalog = PaintCatalogService()
        matches = [p for p in catalog.for_brand("Vallejo") if p.name == "Ice Yellow"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].code, "70.858")
        self.assertEqual(matches[0].range_name, "Model Color")
        self.assertEqual(matches[0].paint_type, "Acrílico")

    def test_turquoise_is_blue_with_green_complement(self):
        primary, complements = infer_color_tags("Heretic Turquoise", "#13514B", "Xpress Color")
        self.assertEqual(primary, "Azul")
        self.assertIn("Verde", complements)

    def test_ice_yellow_is_yellow(self):
        primary, complements = infer_color_tags("Ice Yellow", "#EECF72", "Model Color")
        self.assertEqual(primary, "Amarillo")
        self.assertNotIn("Amarillo", complements)

    def test_grey_green_keeps_tint_as_complement(self):
        primary, complements = infer_color_tags("Grey Green", "#787E7A", "Model Air")
        self.assertEqual(primary, "Gris")
        self.assertIn("Verde", complements)


if __name__ == "__main__":
    unittest.main()
