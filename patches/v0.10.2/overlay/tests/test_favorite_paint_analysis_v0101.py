from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from app.services.favorite_paint_analysis_service import FavoritePaintAnalysisService
from app.services.paint_catalog_service import PaintCatalogService


class FavoritePaintAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        path = Path(self.temp.name) / "paint_catalog.json"
        path.write_text(
            json.dumps(
                [
                    {
                        "brand": "Citadel",
                        "name": "Abaddon Black",
                        "code": "21-25",
                        "range_name": "Base",
                        "paint_type": "Acrílico",
                        "swatch_hex": "#111111",
                        "lab": [5.0, 0.0, 0.0],
                    },
                    {
                        "brand": "Citadel",
                        "name": "Mechanicus Standard Grey",
                        "code": "21-24",
                        "range_name": "Base",
                        "paint_type": "Acrílico",
                        "swatch_hex": "#55565A",
                        "lab": [36.0, 0.0, -2.0],
                    },
                    {
                        "brand": "Citadel",
                        "name": "Evil Sunz Scarlet",
                        "code": "22-05",
                        "range_name": "Layer",
                        "paint_type": "Acrílico",
                        "swatch_hex": "#C21920",
                        "lab": [42.0, 62.0, 43.0],
                    },
                    {
                        "brand": "Citadel",
                        "name": "Nuln Oil",
                        "code": "24-14",
                        "range_name": "Shade",
                        "paint_type": "Wash",
                        "swatch_hex": "#202326",
                        "lab": [13.0, 0.0, -2.0],
                    },
                    {
                        "brand": "Vallejo",
                        "name": "Black",
                        "code": "70.950",
                        "range_name": "Model Color",
                        "paint_type": "Acrílico",
                        "swatch_hex": "#101010",
                        "lab": [4.5, 0.0, 0.0],
                    },
                ]
            ),
            encoding="utf-8",
        )
        self.service = FavoritePaintAnalysisService(PaintCatalogService(path))

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def paint(
        brand: str,
        name: str,
        paint_type: str,
        lab: tuple[float, float, float],
        code: str = "",
        range_name: str = "",
        units: int = 1,
    ):
        return SimpleNamespace(
            brand=brand,
            name=name,
            paint_type=paint_type,
            code=code,
            range_name=range_name,
            color_lab=lab,
            total_units=units,
        )

    def test_exact_inventory_match(self):
        inventory = [self.paint("Citadel", "Abaddon Black", "Acrílico", (5.0, 0.0, 0.0), "21-25", "Base")]
        result = self.service.analyze_description("Paints used:\n- Citadel Abaddon Black 21-25", inventory)
        self.assertEqual(len(result.detected), 1)
        self.assertEqual(len(result.exact_matches), 1)
        self.assertEqual(result.exact_matches[0].inventory_paint.name, "Abaddon Black")
        self.assertEqual(result.author_lines, ("Citadel Abaddon Black 21-25",))

    def test_possible_name_match_is_separate_from_exact(self):
        inventory = [self.paint("Citadel", "Mechanicus Std Grey", "Acrílico", (36.5, 0.0, -2.0), range_name="Base")]
        result = self.service.analyze_description("Colours: Citadel Mechanicus Standard Grey", inventory)
        self.assertEqual(len(result.exact_matches), 0)
        self.assertEqual(len(result.possible_matches), 1)
        self.assertGreaterEqual(result.possible_matches[0].name_similarity, 0.85)

    def test_missing_paint_uses_same_type_delta_e_order_and_85_percent_floor(self):
        inventory = [
            self.paint("AK Interactive", "Deep Red", "Acrílico", (43.0, 60.0, 42.0)),
            self.paint("Vallejo", "Scarlet", "Acrílico", (48.0, 55.0, 38.0)),
            # Deliberately closer in colour, but wrong product type: must never compete.
            self.paint("Citadel", "Red Wash", "Wash", (42.0, 62.0, 43.0)),
        ]
        result = self.service.analyze_description("- Evil Sunz Scarlet", inventory)
        self.assertEqual(len(result.missing), 1)
        alternatives = result.missing[0].alternatives
        self.assertEqual([item.inventory_paint.name for item in alternatives], ["Deep Red"])
        self.assertTrue(all(item.inventory_paint.paint_type == "Acrílico" for item in alternatives))
        self.assertTrue(all(item.similarity >= 85.0 for item in alternatives))

    def test_zero_stock_is_not_an_inventory_match_or_alternative(self):
        inventory = [self.paint("Citadel", "Abaddon Black", "Acrílico", (5.0, 0.0, 0.0), units=0)]
        result = self.service.analyze_description("Citadel Abaddon Black", inventory)
        self.assertEqual(len(result.matches), 0)
        self.assertEqual(len(result.missing), 1)
        self.assertEqual(result.missing[0].alternatives, ())

    def test_generic_colour_word_does_not_identify_a_catalog_product(self):
        result = self.service.analyze_description("Paint the boots black and the armour grey.", [])
        self.assertEqual(result.detected, ())

    def test_brand_plus_generic_product_name_can_still_be_identified(self):
        result = self.service.analyze_description("Basecoat with Vallejo Black 70.950", [])
        names = [item.catalog_paint.name for item in result.detected]
        self.assertIn("Black", names)


if __name__ == "__main__":
    unittest.main()
