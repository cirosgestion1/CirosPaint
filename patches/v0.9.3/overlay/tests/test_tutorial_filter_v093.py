from __future__ import annotations

import unittest

from app.services.tutorial_query_service import TutorialQueryService


class TutorialFilterV093Tests(unittest.TestCase):
    def test_ambiguous_query_is_contextualized_to_hobby(self):
        decision = TutorialQueryService.contextualize("cómo hacer un árbol")
        self.assertTrue(decision.valid)
        self.assertIn("modelismo", decision.search_query.lower())
        self.assertIn("tree", decision.search_query.lower())

    def test_keeps_model_tree_result(self):
        self.assertTrue(
            TutorialQueryService.result_is_hobby_related(
                "cómo hacer un árbol",
                "How to make realistic model trees for a diorama",
                "Easy scenery tutorial for scale modelling and tabletop terrain.",
            )
        )

    def test_rejects_gardening_tree_result(self):
        self.assertFalse(
            TutorialQueryService.result_is_hobby_related(
                "cómo hacer un árbol",
                "How to grow a bonsai tree at home",
                "Gardening guide: planting, pruning and watering your bonsai.",
            )
        )

    def test_rejects_generic_carpentry_result(self):
        self.assertFalse(
            TutorialQueryService.result_is_hobby_related(
                "madera envejecida",
                "How to age wood for furniture",
                "Carpentry tutorial for a dining table and home furniture.",
            )
        )

    def test_keeps_miniature_painting_result(self):
        self.assertTrue(
            TutorialQueryService.result_is_hobby_related(
                "pintar Darth Vader",
                "STAR WARS LEGION - Cómo pintar Darth Vader",
                "Tutorial de pintura de miniaturas para Star Wars Legion.",
            )
        )

    def test_rejects_programming_tree_result(self):
        self.assertFalse(
            TutorialQueryService.result_is_hobby_related(
                "hacer un árbol",
                "Binary Tree Tutorial in Python",
                "Data structures and programming explained step by step.",
            )
        )


if __name__ == "__main__":
    unittest.main()
