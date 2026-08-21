from __future__ import annotations

import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.repositories.miniature_repository import MiniatureRepository
from app.repositories.paint_repository import PaintRepository
from app.services.assistant_conversation_context import PaintConversationContext
from app.services.assistant_local_service import AssistantLocalService, MiniatureUnit
from app.services.assistant_settings_store import AssistantSettingsStore
from app.ui.pages.assistant_page import AssistantMessageBubble, QuantityDialog


class AssistantPaintRegressionV01010Tests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        repo = PaintRepository(self.session)
        self.paints = [
            repo.add(brand="Citadel", name="Administratum Grey", code="22-50", range_name="Layer", paint_type="Acrílico", swatch_hex="#999999", available_units=2, low_units=0, primary_color="Gris", complementary_colors=[]),
            repo.add(brand="Vallejo", name="Game Color Black", code="72.051", range_name="Game Color", paint_type="Acrílico", swatch_hex="#000000", available_units=3, low_units=0, primary_color="Negro", complementary_colors=[]),
            repo.add(brand="AK", name="Deep Red", code="AK11097", range_name="3rd Gen", paint_type="Acrílico", swatch_hex="#990000", available_units=1, low_units=0, primary_color="Rojo", complementary_colors=[]),
            repo.add(brand="Citadel", name="Abaddon Black", code="21-25", range_name="Base", paint_type="Acrílico", swatch_hex="#111111", available_units=2, low_units=0, primary_color="Negro", complementary_colors=[]),
            repo.add(brand="Citadel", name="Abaddon Black Air", code="28-51", range_name="Air", paint_type="Acrílico", swatch_hex="#111111", available_units=1, low_units=0, primary_color="Negro", complementary_colors=[]),
        ]
        self.context = PaintConversationContext()
        self.local = AssistantLocalService(self.session, context=self.context)
        MiniatureRepository(self.session).upsert_entry(
            "Star Wars: Legion", "Imperio", "Scout Trooper Strike Team",
            unassembled_count=3, assembled_count=4, painted_count=2, finished_count=1,
        )
        self.local._miniatures = [
            MiniatureUnit("legion", "Star Wars: Legion", "empire", "Imperio", "scout-team", "Scout Trooper Strike Team"),
            MiniatureUnit("legion", "Star Wars: Legion", "empire", "Imperio", "death-troopers", "Death Troopers"),
            MiniatureUnit("legion", "Star Wars: Legion", "separatists", "Separatistas", "b1", "B1 Battle Droids"),
        ]

    def tearDown(self): self.session.close(); self.engine.dispose()

    def test_colors_are_data_driven_across_singular_plural_and_brands(self):
        cases = {"tengo pintura gris": "Administratum Grey", "tengo pinturas negras": "Game Color Black", "qué pinturas rojas tengo": "Deep Red", "muéstrame pinturas grises": "Administratum Grey", "buscar pinturas rojas": "Deep Red"}
        with patch.object(AssistantSettingsStore, "gemini_api_key", return_value=""), patch.object(AssistantSettingsStore, "increment_gemini_request_count") as gemini:
            for request, expected in cases.items():
                with self.subTest(request=request):
                    result = self.local.try_handle_text(request)
                    self.assertIsNotNone(result); self.assertFalse(result.requires_ai_resolution)
                    self.assertTrue(any(expected in paint["name"] for paint in result.data["paints"]))
        gemini.assert_not_called()

    def test_ambiguous_candidates_show_again_without_mutation_or_gemini(self):
        first = self.local.try_handle_text("tengo abaddon"); self.assertEqual(first.status, "ambiguous")
        before = [paint.available_units for paint in self.paints[-2:]]
        shown = self.local.try_handle_text("muestra"); blocked = self.local.try_handle_text("añadir otra")
        self.assertEqual(shown.data["paints"], first.data["paints"]); self.assertGreaterEqual(len(shown.data["paints"]), 2); self.assertEqual(blocked.status, "ambiguous")
        self.assertEqual([paint.available_units for paint in self.paints[-2:]], before)

    def test_active_paint_followups_use_id_and_exact_quantities(self):
        found = self.local.try_handle_text("tengo 72.051"); self.assertEqual(found.status, "ok")
        paint_id = self.context.active_paint_id; self.assertEqual(paint_id, self.paints[1].id)
        self.local.try_handle_text("añadir otra"); self.assertEqual(self.local.query_service.paint_units(self.local.query_service.get_inventory_paint(paint_id)), 4)
        self.local.try_handle_text("quita una"); self.assertEqual(self.local.query_service.paint_units(self.local.query_service.get_inventory_paint(paint_id)), 3)
        self.local.try_handle_text("ponla a 4"); self.assertEqual(self.local.query_service.paint_units(self.local.query_service.get_inventory_paint(paint_id)), 4)
        future = self.local.try_handle_text("añádela a futuras compras"); self.assertEqual(future.status, "ok")
        self.assertEqual(self.local.query_service.list_future_paint_purchases()[0].paint_id, paint_id)

    def test_contextual_mutation_without_active_entity_is_blocked(self):
        self.assertEqual(self.local.try_handle_text("añadir otra").status, "ambiguous")


    def test_manual_paint_phrases_are_all_deterministic_and_local(self):
        cases = {
            "cuántas pinturas tengo": 5,
            "cuántas pinturas negras tengo": 3,
            "gris": 1,
            "abaddon": 2,
            "abaddon black": 2,
        }
        with patch.object(AssistantSettingsStore, "increment_gemini_request_count") as gemini:
            for request, expected in cases.items():
                with self.subTest(request=request):
                    result = self.local.try_handle_text(request)
                    self.assertIsNotNone(result)
                    self.assertFalse(result.requires_ai_resolution)
                    self.assertEqual(len(result.data.get("paints", [])), expected)
        gemini.assert_not_called()

    def test_unrelated_short_language_remains_available_for_gemini(self):
        self.assertIsNone(self.local.try_handle_text("qué hora es"))

    def test_global_miniature_count_does_not_resolve_the_word_miniatures(self):
        result = self.local.try_handle_text("cuántas miniaturas tengo")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.data["total"], 10)
        self.assertNotIn("raw_name", result.data)

    def test_conversational_suffix_is_removed_before_miniature_resolution(self):
        result = self.local.try_handle_text("scout trooper strike team tengo?")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.data["unit"]["unit_name"], "Scout Trooper Strike Team")

    def test_miniature_fuzzy_candidates_exclude_lexically_unrelated_units(self):
        _unit, matches, _decision = self.local.resolve_miniature_with_decision("scout troopers", inventory_only=False)
        self.assertTrue(matches)
        self.assertNotIn("B1 Battle Droids", [item.unit_name for item in matches])

    def test_natural_status_phrases_parse_state_quantity_and_entity_locally(self):
        cases = (
            ("hoy terminé un scout trooper strike team", "Terminado", 2),
            ("pinté dos scout trooper strike teams", "Pintado", 3),
            ("monté 3 scout trooper strike teams", "Montado", 5),
        )
        with patch.object(AssistantSettingsStore, "increment_gemini_request_count") as gemini:
            for request, status, expected in cases:
                with self.subTest(request=request):
                    result = self.local.try_handle_text(request)
                    self.assertEqual(result.status, "ok")
                    self.assertEqual(result.data["counts"][status], expected)
        gemini.assert_not_called()


class AssistantUiRegressionV01010Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def test_long_user_assistant_and_multiline_bubbles_expand_for_width(self):
        contents = ["Mensaje de usuario " * 80, "Respuesta del asistente\n" + "\n".join(f"Línea {index}" for index in range(12)), "\n".join(f"Pintura {index}: cantidad completa" for index in range(8))]
        for role, content in (("user", contents[0]), ("assistant", contents[1]), ("assistant", contents[2])):
            bubble = AssistantMessageBubble(role, content); bubble.resize(360, 10); QApplication.processEvents()
            self.assertTrue(bubble.hasHeightForWidth()); self.assertGreater(bubble.heightForWidth(360), 40)
            self.assertIn(content.splitlines()[-1].split()[-1], bubble.text_label.text()); bubble.close()

    def test_structured_miniature_lists_and_confirmation_have_dynamic_height(self):
        items = [{"unit": {"unit_name": f"Unidad {index}"}, "counts": {"Sin montar": 2, "Montado": 1, "Pintado": 3, "Terminado": 4}} for index in range(10)]
        bubble = AssistantMessageBubble("assistant", "Listado completo", metadata={"kind": "miniature_list", "data": {"items": items}})
        bubble.resize(420, 10); QApplication.processEvents(); self.assertGreater(bubble.heightForWidth(420), 100); bubble.close()

    def test_wrapped_label_geometry_is_applied_to_the_real_bubble(self):
        bubble = AssistantMessageBubble("assistant", "Texto largo con saltos y palabras " * 70)
        bubble.show(); bubble.set_available_width(390); QApplication.processEvents()
        content_width = bubble.text_label.width()
        self.assertEqual(bubble.width(), min(800, int(390 * 0.92)))
        self.assertGreaterEqual(bubble.text_label.height(), bubble.text_label.heightForWidth(content_width))
        self.assertGreaterEqual(bubble.height(), bubble.layout().sizeHint().height())
        bubble.close()

    def test_quantity_spinbox_step_buttons_and_manual_value_are_consistent(self):
        dialog = QuantityDialog("Cantidad", "Cantidad", 1, 1, 5)
        dialog.spin.stepUp(); dialog.spin.stepUp(); dialog.spin.stepUp(); dialog.spin.stepUp(); self.assertEqual(dialog.spin.value(), 5)
        dialog.spin.stepDown(); self.assertEqual(dialog.spin.value(), 4)
        dialog.spin.lineEdit().setText("3"); dialog.spin.interpretText(); self.assertEqual(dialog.spin.value(), 3)
        dialog.spin.setValue(99); self.assertEqual(dialog.spin.value(), 5); dialog.close()


if __name__ == "__main__": unittest.main()
