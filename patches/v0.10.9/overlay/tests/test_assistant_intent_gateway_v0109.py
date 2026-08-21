from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from app.services.assistant_confidence_gateway import (
    ConfidenceEscalationGateway,
    ConfidenceLevel,
    EscalationAction,
)
from app.services.assistant_entity_resolver import EntityCandidate, EntityResolution, LocalEntityResolver
from app.services.assistant_intent_router import AssistantLocalIntentRouter, LocalIntent
from app.services.assistant_local_service import AssistantLocalService, LocalAssistantResult, MiniatureUnit
from app.services.assistant_settings_store import AssistantSettingsStore


class RecordingHandler:
    def __init__(self):
        self.calls = []

    def _result(self, operation, *args):
        self.calls.append((operation, *args))
        return LocalAssistantResult("ok", operation)

    def search_paints(self, query): return self._result("search", query)
    def find_paint(self, query): return self._result("stock", query)
    def paints_by_color(self, color): return self._result("color", color)
    def depleted_paints(self): return self._result("depleted")
    def list_future_paints(self): return self._result("future_list")
    def add_future_paint(self, query, quantity=1): return self._result("future_add", query, quantity)
    def mark_paint_purchased(self, query, quantity=1): return self._result("purchased", query, quantity)
    def miniature_counts(self, query): return self._result("mini_counts", query)
    def change_miniature_status(self, query, target_status, quantity):
        return self._result("mini_status", query, target_status, quantity)
    def guided_add_miniature(self): return self._result("mini_add")


class LocalIntentRouterV0109Tests(unittest.TestCase):
    def setUp(self):
        self.handler = RecordingHandler()
        self.router = AssistantLocalIntentRouter(self.handler)

    def test_buscar_pintura_gris_is_resolved_locally(self):
        with patch.object(AssistantSettingsStore, "increment_gemini_request_count") as increment:
            result = self.router.route("Buscar pintura: Gris")
        self.assertEqual(result.status, "ok")
        self.assertEqual(self.handler.calls, [("search", "Gris")])
        increment.assert_not_called()

    def test_existing_deterministic_intents_are_explicit(self):
        examples = {
            "¿Cuántas unidades tengo de Abaddon Black?": LocalIntent.GET_PAINT_STOCK,
            "¿Qué pinturas agotadas tengo?": LocalIntent.LIST_DEPLETED_PAINTS,
            "¿Qué pinturas tengo de color gris?": LocalIntent.LIST_PAINTS_BY_COLOR,
            "Mis futuras compras": LocalIntent.LIST_FUTURE_PURCHASES,
            "Añade 2 Abaddon Black a futuras compras": LocalIntent.ADD_FUTURE_PURCHASE,
            "He comprado 2 Abaddon Black": LocalIntent.COMPLETE_PURCHASE,
            "¿Cuántos Stormtroopers tengo?": LocalIntent.GET_MINIATURE_COUNTS,
            "Añade miniaturas": LocalIntent.ADD_MINIATURE,
            "He terminado 2 Stormtroopers": LocalIntent.CHANGE_MINIATURE_STATUS,
        }
        for text, expected in examples.items():
            with self.subTest(text=text):
                self.assertEqual(self.router.classify(text).intent, expected)

    def test_deterministic_operation_works_without_api_key_or_gemini_request(self):
        with patch.object(AssistantSettingsStore, "gemini_api_key", return_value=""), \
             patch.object(AssistantSettingsStore, "increment_gemini_request_count") as increment:
            self.assertEqual(self.router.route("Buscar pintura: Gris").status, "ok")
        increment.assert_not_called()


class ConfidenceEscalationGatewayV0109Tests(unittest.TestCase):
    def setUp(self):
        self.resolver = LocalEntityResolver()
        self.gateway = ConfidenceEscalationGateway()
        self.paint = EntityCandidate("abaddon-black", "Abaddon Black", ("Citadel Abaddon Black",))

    def test_exact_match_stays_local(self):
        decision = self.gateway.evaluate("Abaddon Black", self.resolver.resolve("Abaddon Black", [self.paint]))
        self.assertEqual(decision.level, ConfidenceLevel.EXACT)
        self.assertEqual(decision.action, EscalationAction.ACCEPT_LOCAL)

    def test_normalized_match_stays_local(self):
        paint = EntityCandidate("gris-frio", "Grís Frío")
        decision = self.gateway.evaluate("gris frio", self.resolver.resolve("gris frio", [paint]))
        self.assertEqual(decision.level, ConfidenceLevel.NORMALIZED)
        self.assertEqual(decision.action, EscalationAction.ACCEPT_LOCAL)

    def test_safe_fuzzy_match_stays_local(self):
        resolution = self.resolver.resolve("Abadon Black", [self.paint])
        decision = self.gateway.evaluate("Abadon Black", resolution)
        self.assertEqual(decision.level, ConfidenceLevel.FUZZY_HIGH)
        self.assertEqual(decision.action, EscalationAction.ACCEPT_LOCAL)

    def test_ambiguous_candidates_require_selection(self):
        candidates = [EntityCandidate("grey-a", "Grey Knights Alpha"), EntityCandidate("grey-b", "Grey Knights Beta")]
        resolution = self.resolver.resolve("Grey Knights", candidates)
        decision = self.gateway.evaluate("Grey Knights", resolution)
        self.assertEqual(decision.action, EscalationAction.REQUEST_SELECTION)
        self.assertFalse(decision.should_escalate)

    def test_truly_unresolved_case_can_escalate(self):
        resolution = EntityResolution(
            "ambiguous", matches=[self.paint], confidence=0.51, margin=0.01
        )
        decision = self.gateway.evaluate("Aba desconocida", resolution)
        self.assertEqual(decision.action, EscalationAction.USE_GEMINI)
        self.assertTrue(decision.should_escalate)


class AmbiguousMutationV0109Tests(unittest.TestCase):
    def test_ambiguous_miniature_does_not_mutate(self):
        service = AssistantLocalService.__new__(AssistantLocalService)
        units = [
            MiniatureUnit("game", "Game", "faction", "Faction", "grey-a", "Grey Knights Alpha"),
            MiniatureUnit("game", "Game", "faction", "Faction", "grey-b", "Grey Knights Beta"),
        ]
        decision = ConfidenceEscalationGateway().evaluate(
            "Grey Knights",
            LocalEntityResolver().resolve(
                "Grey Knights", [EntityCandidate(unit.unit_id, unit.unit_name, payload=unit) for unit in units]
            ),
        )
        service.resolve_miniature_with_decision = Mock(return_value=(None, units, decision))
        service._move_status = Mock()

        result = service.change_miniature_status("Grey Knights", "Pintado", 1)

        self.assertEqual(result.status, "ambiguous")
        self.assertFalse(result.requires_ai_resolution)
        service._move_status.assert_not_called()


if __name__ == "__main__":
    unittest.main()
