from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from app.services.favorite_paint_analysis_service import (
    MIN_POSSIBLE_NAME_SIMILARITY,
    MIN_VISIBLE_SIMILARITY_PERCENT,
    FavoritePaintAnalysisService,
)
from app.services.paint_catalog_service import PaintCatalogService


class FavoritePaintAnalysisV0102Tests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        path = Path(self.temp.name) / "paint_catalog.json"
        path.write_text(
            json.dumps(
                [
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
                        "name": "Mechanicus Standard Grey",
                        "code": "21-24",
                        "range_name": "Base",
                        "paint_type": "Acrílico",
                        "swatch_hex": "#55565A",
                        "lab": [36.0, 0.0, -2.0],
                    },
                ]
            ),
            encoding="utf-8",
        )
        self.service = FavoritePaintAnalysisService(PaintCatalogService(path))

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def paint(brand: str, name: str, paint_type: str, lab, units: int = 1):
        return SimpleNamespace(
            brand=brand,
            name=name,
            paint_type=paint_type,
            code="",
            range_name="",
            color_lab=lab,
            total_units=units,
        )

    def test_threshold_is_exactly_85_percent(self):
        self.assertEqual(MIN_VISIBLE_SIMILARITY_PERCENT, 85.0)
        self.assertEqual(MIN_POSSIBLE_NAME_SIMILARITY, 0.85)

    def test_possible_name_match_below_85_is_not_returned(self):
        source = self.service.detect_catalog_paints("Citadel Mechanicus Standard Grey")[0].catalog_paint
        candidate = self.paint("Citadel", "Mechanicus Grey", "Acrílico", (36.0, 0.0, -2.0))
        possible = self.service._find_possible_inventory_match(source, [candidate])
        self.assertIsNone(possible)

    def test_colour_alternatives_below_85_are_hidden(self):
        inventory = [
            self.paint("AK Interactive", "Near Scarlet", "Acrílico", (42.2, 61.8, 43.1)),
            self.paint("Vallejo", "Very Distant Red", "Acrílico", (95.0, -50.0, -50.0)),
            self.paint("Citadel", "Perfect Red Wash", "Wash", (42.0, 62.0, 43.0)),
        ]
        result = self.service.analyze_description("Evil Sunz Scarlet", inventory)
        self.assertEqual(len(result.missing), 1)
        alternatives = result.missing[0].alternatives
        self.assertEqual([item.inventory_paint.name for item in alternatives], ["Near Scarlet"])
        self.assertTrue(all(item.similarity >= 85.0 for item in alternatives))
        self.assertTrue(all(item.inventory_paint.paint_type == "Acrílico" for item in alternatives))

    def test_no_detected_paints_sets_empty_analysis_state(self):
        result = self.service.analyze_description("No paint list is provided here.", [])
        self.assertFalse(result.has_detected_paints)
        self.assertEqual(result.detected, ())


if __name__ == "__main__":
    unittest.main()
