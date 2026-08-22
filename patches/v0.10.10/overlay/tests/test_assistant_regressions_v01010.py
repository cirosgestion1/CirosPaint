from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.repositories.miniature_repository import MiniatureRepository
from app.repositories.material_repository import MaterialRepository
from app.repositories.paint_repository import PaintRepository
from app.repositories.shopping_repository import ShoppingRepository
from app.services.assistant_conversation_context import PaintConversationContext
from app.services.assistant_local_service import AssistantLocalService, MiniatureUnit
from app.services.assistant_settings_store import AssistantSettingsStore
from app.ui.pages.assistant_page import AssistantMessageBubble, QuantityDialog
from app.ui.styles import APP_STYLE


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
        self.local.catalog_service._items = [
            SimpleNamespace(brand=paint.brand, name=paint.name, code=paint.code,
                            range_name=paint.range_name, paint_type=paint.paint_type,
                            swatch_hex=paint.swatch_hex, source_name=paint.name)
            for paint in self.paints
        ]
        MiniatureRepository(self.session).upsert_entry(
            "Star Wars: Legion", "Imperio", "Scout Trooper Strike Team",
            unassembled_count=3, assembled_count=4, painted_count=2, finished_count=1,
        )
        self.local._miniatures = [
            MiniatureUnit("legion", "Star Wars: Legion", "empire", "Imperio Galáctico", "scout-team", "Scout Trooper Strike Team"),
            MiniatureUnit("legion", "Star Wars: Legion", "empire", "Imperio Galáctico", "death-troopers", "Death Troopers"),
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

    def test_each_paint_card_action_keeps_its_canonical_id(self):
        first = self.local.find_paint("72.051")
        second = self.local.find_paint("AK11097")
        first_actions = first.data["actions"]
        second_actions = second.data["actions"]
        self.assertEqual({item["paint_id"] for item in first_actions}, {self.paints[1].id})
        self.assertEqual({item["paint_id"] for item in second_actions}, {self.paints[2].id})

        # The second result is now the global conversation context, but an action
        # belonging to the first card must still mutate the first paint only.
        before_first = self.local.query_service.paint_units(self.paints[1])
        before_second = self.local.query_service.paint_units(self.paints[2])
        result = self.local.change_paint_quantity_by_id(first_actions[0]["paint_id"], "add")
        self.assertEqual(result.status, "ok")
        self.assertEqual(self.local.query_service.paint_units(self.paints[1]), before_first + 1)
        self.assertEqual(self.local.query_service.paint_units(self.paints[2]), before_second)

    def test_all_id_bound_paint_actions_use_the_card_entity(self):
        paint_id = self.paints[2].id
        self.assertEqual(self.local.change_paint_quantity_by_id(paint_id, "add").data["paint"]["id"], paint_id)
        self.assertEqual(self.local.change_paint_quantity_by_id(paint_id, "remove").data["paint"]["id"], paint_id)
        self.assertEqual(self.local.change_paint_quantity_by_id(paint_id, "set", 4).data["paint"]["id"], paint_id)
        future = self.local.add_paint_id_to_future(paint_id)
        self.assertEqual(future.data["paint"]["id"], paint_id)
        self.assertEqual(ShoppingRepository(self.session).get_for_paint(paint_id).paint_id, paint_id)

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

    def test_same_paint_id_always_uses_the_canonical_swatch(self):
        for color_query, partial, full, paint_id in (
            ("rojo", "deep", "deep red", self.paints[2].id),
            ("gris", "administratum", "administratum grey", self.paints[0].id),
        ):
            results = [self.local.try_handle_text(value) for value in (color_query, partial, full)]
            payloads = [next(item for item in result.data["paints"] if item["id"] == paint_id) for result in results]
            self.assertEqual({item["swatch_hex"] for item in payloads}, {self.local.query_service.get_inventory_paint(paint_id).swatch_hex})
            for field in ("id", "brand", "name", "code", "range_name", "primary_color", "swatch_hex"):
                self.assertEqual({item[field] for item in payloads}, {getattr(self.local.query_service.get_inventory_paint(paint_id), field)})

    def test_completed_purchase_reuses_repository_and_canonical_identity(self):
        paint = self.paints[3]
        initial_units = self.local.query_service.paint_units(paint)
        self.local.add_paint_id_to_future(paint.id, 2)
        self.assertIsNotNone(ShoppingRepository(self.session).get_for_paint(paint.id))
        completed = self.local.mark_paint_purchased("Citadel Abaddon Black", 2)
        self.assertEqual(completed.status, "ok")
        payload = completed.data["paints"][0]
        self.assertEqual(payload["id"], paint.id)
        self.assertEqual(payload["range_name"], paint.range_name)
        self.assertEqual(payload["swatch_hex"], paint.swatch_hex)
        self.assertEqual(self.local.query_service.paint_units(paint), initial_units + 2)
        self.assertIsNone(ShoppingRepository(self.session).get_for_paint(paint.id))
        matching = [item for item in self.local.query_service.list_inventory_paints()
                    if item.brand == paint.brand and item.name == paint.name]
        self.assertEqual([item.id for item in matching], [paint.id])

    def test_faction_queries_are_owned_only_strict_and_data_driven(self):
        cases = ("cuántas miniaturas imperiales tengo", "cuántas miniaturas imperial tengo",
                 "cuántas miniaturas del imperio tengo", "qué miniaturas del imperio galáctico tengo",
                 "qué miniaturas imperiales tengo", "cuántos imperiales tengo",
                 "muéstrame mis miniaturas imperiales")
        with patch.object(AssistantSettingsStore, "increment_gemini_request_count") as gemini:
            for request in cases:
                result = self.local.try_handle_text(request)
                self.assertEqual(result.status, "ok", request)
                self.assertEqual(result.data["total"], 10, request)
                self.assertEqual([item["unit"]["unit_name"] for item in result.data["items"]], ["Scout Trooper Strike Team"])
        gemini.assert_not_called()

    def test_isolated_faction_aliases_work_for_multiple_real_factions(self):
        MiniatureRepository(self.session).upsert_entry(
            "Star Wars: Legion", "Alianza Rebelde", "Rebel Troopers",
            unassembled_count=2, assembled_count=0, painted_count=0, finished_count=0,
        )
        self.local._miniatures.append(
            MiniatureUnit("legion", "Star Wars: Legion", "rebels", "Alianza Rebelde", "rebel-troopers", "Rebel Troopers")
        )
        with patch.object(AssistantSettingsStore, "increment_gemini_request_count") as gemini:
            for request, expected_label, expected_total in (
                ("imperial", "Imperio Galáctico", 10),
                ("imperiales", "Imperio Galáctico", 10),
                ("imperio", "Imperio Galáctico", 10),
                ("rebelde", "Alianza Rebelde", 2),
                ("rebeldes", "Alianza Rebelde", 2),
            ):
                result = self.local.try_handle_text(request)
                self.assertEqual(result.status, "ok", request)
                self.assertEqual(result.data["label"], expected_label, request)
                self.assertEqual(result.data["total"], expected_total, request)
                self.assertFalse(result.requires_ai_resolution)
        gemini.assert_not_called()

    def test_isolated_unit_and_safe_unit_typo_are_local(self):
        MiniatureRepository(self.session).upsert_entry(
            "Star Wars: Legion", "Imperio", "Stormtroopers",
            unassembled_count=2, assembled_count=1, painted_count=0, finished_count=0,
        )
        self.local._miniatures.append(
            MiniatureUnit("legion", "Star Wars: Legion", "empire", "Imperio Galáctico", "stormtroopers", "Stormtroopers")
        )
        with patch.object(AssistantSettingsStore, "increment_gemini_request_count") as gemini:
            for request in ("Stormtroopers", "Stormtrooper", "Stormtruper", "Stormtroper"):
                result = self.local.try_handle_text(request)
                self.assertIsNotNone(result, request)
                self.assertEqual(result.status, "ok", request)
                names = [item["unit"]["unit_name"] for item in result.data.get("items", [])]
                if result.data.get("unit"):
                    names.append(result.data["unit"]["unit_name"])
                self.assertEqual(names, ["Stormtroopers"], request)
                self.assertFalse(result.requires_ai_resolution)
        gemini.assert_not_called()

    def test_permissive_unit_typo_matching_is_limited_to_legion(self):
        MiniatureRepository(self.session).upsert_entry(
            "Warhammer Age of Sigmar", "Stormcast Eternals", "Liberators",
            unassembled_count=1, assembled_count=0, painted_count=0, finished_count=0,
        )
        self.local._miniatures.append(
            MiniatureUnit("aos", "Warhammer Age of Sigmar", "stormcast", "Stormcast Eternals", "liberators", "Liberators")
        )
        exact = self.local.try_handle_text("Liberators")
        typo = self.local.try_handle_text("Liberatros")
        self.assertEqual(exact.status, "ok")
        self.assertIsNone(typo)

    def test_unfinished_queries_work_globally_for_unit_and_faction(self):
        cases = {
            "cuántas miniaturas tengo por terminar": 9,
            "cuántos scout trooper strike teams tengo por terminar": 9,
            "cuántas miniaturas imperiales tengo por terminar": 9,
        }
        for request, expected in cases.items():
            result = self.local.try_handle_text(request)
            self.assertEqual(result.status, "ok", request)
            self.assertEqual(result.data["total"], expected, request)
            self.assertTrue(result.data["unfinished"])

    def test_controlled_temporal_state_variants_are_local(self):
        cases = ("acabo de terminar 1 scout trooper strike team", "he terminado un scout trooper strike team",
                 "ahora terminé un scout trooper strike team")
        with patch.object(AssistantSettingsStore, "increment_gemini_request_count") as gemini:
            for request in cases:
                result = self.local.try_handle_text(request)
                self.assertEqual(result.status, "ok", request)
        gemini.assert_not_called()

    def test_text_paint_operations_reuse_existing_mutations_and_clarify(self):
        initial = self.paints[2].available_units
        added = self.local.try_handle_text("añade Deep Red")
        self.assertEqual(added.status, "ok")
        self.assertEqual(self.paints[2].available_units, initial + 1)
        incomplete = self.local.try_handle_text("añade pintura")
        self.assertEqual(incomplete.status, "needs_input")
        future = self.local.try_handle_text("quiero comprar Deep Red")
        self.assertEqual(future.status, "ok")
        self.assertIsNotNone(ShoppingRepository(self.session).get_for_paint(self.paints[2].id))
        completed = self.local.try_handle_text("ya compré Deep Red")
        self.assertEqual(completed.status, "ok")
        self.assertIsNone(ShoppingRepository(self.session).get_for_paint(self.paints[2].id))
        clarify = self.local.try_handle_text("compra Deep Red")
        self.assertEqual(clarify.status, "needs_input")

    def test_inventory_future_and_completed_purchase_wording_variants_are_local(self):
        cases = (
            "agrega Administratum Grey", "mete Administratum Grey en el inventario",
            "añade Administratum Grey al inventario", "añade Administratum Grey a futura compra",
            "mete Administratum Grey en futuras compras", "apunta Administratum Grey para comprar",
            "compré una nueva pintura Administratum Grey", "he comprado Administratum Grey",
            "marca Administratum Grey como comprada",
        )
        with patch.object(AssistantSettingsStore, "increment_gemini_request_count") as gemini:
            for request in cases:
                with self.subTest(request=request):
                    result = self.local.try_handle_text(request)
                    self.assertIsNotNone(result)
                    self.assertFalse(result.requires_ai_resolution)
                    self.assertEqual(result.status, "ok")
        gemini.assert_not_called()

    def test_generic_future_purchases_matches_paints_and_materials(self):
        shopping = ShoppingRepository(self.session)
        shopping.set_future_quantity(self.paints[1].id, 2)
        material = MaterialRepository(self.session).add(brand="Tamiya", name="Masking Tape", category="Otros", quantity=0)
        shopping.set_material_future_quantity(material.id, 1)
        generic = self.local.try_handle_text("qué tengo en futuras compras")
        paints = self.local.try_handle_text("qué pinturas tengo en futuras compras")
        materials = self.local.try_handle_text("qué materiales tengo en futuras compras")
        repository_rows = self.local.query_service.list_future_purchase_rows(include_restock=True)
        self.assertEqual(generic.data["total"], len(repository_rows))
        self.assertEqual(generic.data["paint_count"], len([row for row in repository_rows if row["kind"] == "paint"]))
        self.assertEqual(generic.data["material_count"], 1)
        self.assertTrue(all(item["kind"] == "paint" for item in paints.data["items"]))
        self.assertTrue(all(item["kind"] == "material" for item in materials.data["items"]))

    def test_spanish_text_is_utf8_without_mojibake(self):
        result = self.local.try_handle_text("cuántas miniaturas tengo")
        combined = result.message + " colección pinturas miniaturas ¿Qué quieres hacer? áéíóúñ¡"
        self.assertNotIn("Ã", combined)
        self.assertNotIn("Â", combined)

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
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(APP_STYLE)

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

    def test_spanish_utf8_is_preserved_in_rendered_rich_text(self):
        content = "colección pinturas miniaturas ¿Qué quieres hacer? áéíóúñ¡"
        bubble = AssistantMessageBubble("assistant", content)
        self.assertNotIn("Ã", bubble.text_label.text())
        self.assertNotIn("Â", bubble.text_label.text())
        for expected in ("colección", "¿Qué quieres hacer?", "áéíóúñ¡"):
            self.assertIn(expected, bubble.text_label.text())
        bubble.close()

    def test_quantity_spinbox_step_buttons_and_manual_value_are_consistent(self):
        dialog = QuantityDialog("Cantidad", "Cantidad", 1, 1, 5)
        dialog.spin.stepUp(); dialog.spin.stepUp(); dialog.spin.stepUp(); dialog.spin.stepUp(); self.assertEqual(dialog.spin.value(), 5)
        dialog.spin.stepDown(); self.assertEqual(dialog.spin.value(), 4)
        dialog.spin.lineEdit().setText("3"); dialog.spin.interpretText(); self.assertEqual(dialog.spin.value(), 3)
        dialog.spin.setValue(99); self.assertEqual(dialog.spin.value(), 5); dialog.close()

    def test_quantity_spinbox_arrows_are_visible_and_mouse_functional(self):
        dialog = QuantityDialog("Cantidad", "Cantidad", 1, 1, 5)
        dialog.show(); QApplication.processEvents()
        up, down = dialog.spin.arrow_rects()
        self.assertFalse(up.isEmpty()); self.assertFalse(down.isEmpty())
        image = dialog.spin.grab().toImage()
        for rect in (up, down):
            bright = 0
            for x in range(max(0, rect.left()), min(image.width(), rect.right() + 1)):
                for y in range(max(0, rect.top()), min(image.height(), rect.bottom() + 1)):
                    color = image.pixelColor(x, y)
                    bright += int(color.lightness() > 180)
            self.assertGreater(bright, 3)
        QTest.mouseClick(dialog.spin, Qt.LeftButton, pos=up.center()); self.assertEqual(dialog.spin.value(), 2)
        QTest.mouseClick(dialog.spin, Qt.LeftButton, pos=up.center()); self.assertEqual(dialog.spin.value(), 3)
        QTest.mouseClick(dialog.spin, Qt.LeftButton, pos=down.center()); self.assertEqual(dialog.spin.value(), 2)
        dialog.close()

    def test_paint_action_button_emits_bound_paint_id(self):
        action = {"label": "+1 unidad", "action": "paint_active_add", "paint_id": 42}
        bubble = AssistantMessageBubble("assistant", "Pintura", metadata={"data": {"actions": [action]}})
        captured = []
        bubble.action_requested.connect(captured.append)
        button = next(item for item in bubble.findChildren(QPushButton) if item.text() == "+1 unidad")
        QTest.mouseClick(button, Qt.LeftButton)
        self.assertEqual(captured, [action])
        bubble.close()

    def test_canonical_paint_card_keeps_range_and_swatch(self):
        paint = {
            "id": 42, "brand": "Citadel", "name": "Abaddon Black", "range_name": "Base",
            "swatch_hex": "#111111", "available_units": 2, "low_units": 0, "total_units": 2,
        }
        bubble = AssistantMessageBubble("assistant", "Pintura", metadata={"kind": "paints", "data": {"paints": [paint]}})
        labels = [item.text() for item in bubble.findChildren(QLabel)]
        self.assertTrue(any("Citadel Abaddon Black — Base" in value for value in labels))
        swatches = [item for item in bubble.findChildren(QLabel) if "#111111" in item.styleSheet()]
        self.assertEqual(len(swatches), 1)
        bubble.close()


if __name__ == "__main__": unittest.main()
