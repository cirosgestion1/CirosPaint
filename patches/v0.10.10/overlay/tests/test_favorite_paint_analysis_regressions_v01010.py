from __future__ import annotations

import unittest

from app.services.favorite_paint_analysis_service import FavoritePaintAnalysisService


DESCRIPTION = """Paints used:

Dark Sea Blue (VMC)
Black (VMC)
Blue Grey Pale (VMC)
White (VMC)
Mephiston Red
Kantor Blue
Sybarite Green
Orange Fluo (VMC)
Bloodletter
Stormvermin Fur
Drakenhof Nightshade (For the base)
Agrax Earthshade (For the base)
Biel-Tan Green (For the base)
Athonian Camoshade (For the base)

Brown Earth basing paste (Vallejo)
Testors Dullcote matte varnish
Javis fine turf (...)
Army Painter Black and Brown Battleground
"""


class FavoritePaintAnalysisRegressionV01010Tests(unittest.TestCase):
    def setUp(self):
        self.service = FavoritePaintAnalysisService()

    def test_complete_author_list_resolves_against_real_catalog(self):
        detected = self.service.detect_catalog_paints(DESCRIPTION)

        self.assertEqual(len(detected), 14)
        self.assertEqual(
            [item.source_text for item in detected],
            [
                "Dark Sea Blue",
                "Black",
                "Blue Grey Pale",
                "White",
                "Mephiston Red",
                "Kantor Blue",
                "Sybarite Green",
                "Orange Fluo",
                "Bloodletter",
                "Stormvermin Fur",
                "Drakenhof Nightshade",
                "Agrax Earthshade",
                "Biel-Tan Green",
                "Athonian Camoshade",
            ],
        )
        self.assertTrue(all(item.catalog_paint in self.service._catalog_items for item in detected))

    def test_range_abbreviation_is_context_not_part_of_name(self):
        detected = self.service.detect_catalog_paints("Black (VMC)\nOrange Fluo (VMC)")

        self.assertEqual([item.catalog_paint.brand for item in detected], ["Vallejo", "Vallejo"])
        self.assertEqual([item.catalog_paint.range_name for item in detected], ["Model Color", "Model Color"])
        self.assertEqual([item.source_text for item in detected], ["Black", "Orange Fluo"])

    def test_parenthesized_comments_are_removed_without_losing_paints(self):
        detected = self.service.detect_catalog_paints(
            "Drakenhof Nightshade (For the base)\nAgrax Earthshade (For the base)"
        )

        self.assertEqual(len(detected), 2)
        self.assertEqual(
            [item.source_text for item in detected],
            ["Drakenhof Nightshade", "Agrax Earthshade"],
        )

    def test_material_lines_do_not_create_catalog_entities(self):
        materials = """Brown Earth basing paste (Vallejo)
Testors Dullcote matte varnish
Javis fine turf (...)
Army Painter Black and Brown Battleground"""
        self.assertEqual(self.service.detect_catalog_paints(materials), [])

    def test_identification_is_independent_from_alternative_threshold(self):
        result = self.service.analyze_description("Mephiston Red", [])

        self.assertEqual(len(result.detected), 1)
        self.assertEqual(result.detected[0].catalog_paint.name, "Mephiston Red")
        self.assertEqual(len(result.missing), 1)
        self.assertEqual(result.missing[0].alternatives, ())

    def test_every_candidate_line_is_processed(self):
        detected = self.service.detect_catalog_paints(
            "Agrax Earthshade\nStormvermin Fur\nBloodletter"
        )
        self.assertEqual(
            [item.catalog_paint.name for item in detected],
            ["Agrax Earth", "Stormvermin Fur", "Bloodletter"],
        )


if __name__ == "__main__":
    unittest.main()
