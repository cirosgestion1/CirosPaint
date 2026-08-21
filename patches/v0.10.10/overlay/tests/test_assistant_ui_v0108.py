from __future__ import annotations

import time
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from app.services.assistant_local_service import LocalAssistantResult
from app.services.assistant_settings_store import AssistantSettingsStore
from app.ui.pages.assistant_page import AssistantMessageBubble, AssistantPage, AutocompleteDialog, QuantityDialog
from app.ui.pages.settings_page import SettingsPage


class FakeGeminiResolver:
    def __init__(self, _key):
        pass
    def resolve_paint_name(self, raw_name, candidates):
        return "Abaddon Black", {"input_tokens": 4, "output_tokens": 1, "thought_tokens": 0, "tool_tokens": 0, "total_tokens": 5}


class FakeLocalPaintFallback:
    def __init__(self, _session):
        pass
    def try_handle_text(self, text):
        return LocalAssistantResult(
            "needs_resolution",
            "No resuelto localmente",
            "paint_matches",
            {"entity_type": "paint", "candidates": ["Abaddon Black", "Corvus Black"], "raw_name": "Abadon Blak", "operation": "paint_find"},
            requires_ai_resolution=True,
        )
    def find_paint(self, query, allow_ai_fallback=True):
        return LocalAssistantResult("ok", "Coincidencia exacta encontrada.", "paints", {"paints": [{"brand": "Citadel", "name": "Abaddon Black", "total_units": 2, "available_units": 2, "low_units": 0}]})


class FakeMiniLocal:
    captured_owned_only = None
    def __init__(self, _session):
        pass
    def miniature_units(self, game_id="", faction_id="", *, owned_only=False):
        FakeMiniLocal.captured_owned_only = owned_only
        return [SimpleNamespace(unit_name="Stormtroopers")]
    def change_miniature_status(self, value, status, quantity):
        return LocalAssistantResult("ok", f"Se ha cambiado {quantity} {value} al estado {status}.\n\n¿Quieres cambiar otra?", "miniature_counts", {"counts": {}, "actions": [{"label": "Cambiar otra miniatura", "action": "mini_status"}]})


@contextmanager
def fake_session():
    yield object()


def wait_for(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(.01)
    return predicate()


class AssistantUiV0108Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_change_another_button_emits_workflow_action(self):
        bubble = AssistantMessageBubble("assistant", "Hecho", metadata={"data": {"actions": [{"label": "Cambiar otra miniatura", "action": "mini_status"}]}})
        captured = []
        bubble.action_requested.connect(captured.append)
        button = next(btn for btn in bubble.findChildren(QPushButton) if btn.text() == "Cambiar otra miniatura")
        QTest.mouseClick(button, Qt.LeftButton)
        self.assertEqual(captured, ["mini_status"])
        bubble.close()

    def test_status_autocomplete_asks_only_for_owned_units(self):
        FakeMiniLocal.captured_owned_only = None
        with patch("app.ui.pages.assistant_page.get_session", side_effect=lambda: fake_session()), \
             patch("app.ui.pages.assistant_page.AssistantLocalService", FakeMiniLocal), \
             patch.object(AssistantSettingsStore, "gemini_api_key", return_value=""), \
             patch("app.ui.pages.assistant_page.QInputDialog.getItem", return_value=("Pintado", True)), \
             patch.object(QuantityDialog, "get_value", return_value=(1, True)), \
             patch.object(AutocompleteDialog, "get_value", return_value="Stormtroopers"):
            page = AssistantPage()
            page._quick_action("mini_status")
        self.assertTrue(FakeMiniLocal.captured_owned_only)
        page.close()

    def test_paint_typo_automatically_uses_gemini_fallback(self):
        with patch("app.ui.pages.assistant_page.get_session", side_effect=lambda: fake_session()), \
             patch("app.ui.pages.assistant_page.AssistantLocalService", FakeLocalPaintFallback), \
             patch.object(AssistantSettingsStore, "gemini_api_key", return_value="AQ.test"):
            page = AssistantPage(gemini_service_factory=lambda key: FakeGeminiResolver(key))
            page.input.setPlainText("¿Tengo Abadon Blak?")
            QTest.mouseClick(page.send_button, Qt.LeftButton)
            self.assertTrue(wait_for(lambda: not page.busy))
        conversation = page.session_store.get(page.current_conversation_id)
        self.assertEqual(conversation.messages[-1].content, "Coincidencia exacta encontrada.")
        self.assertIn("5 tokens", page.request_status.text())
        page.close()

    def test_settings_shows_daily_request_counter(self):
        with patch.object(AssistantSettingsStore, "gemini_request_count_today", return_value=7), \
             patch.object(AssistantSettingsStore, "gemini_api_key", return_value=""):
            page = SettingsPage()
        self.assertIn("7", page.gemini_request_count.text())
        self.assertIn("00:00", page.gemini_request_count.text())
        page.close()


if __name__ == "__main__":
    unittest.main()


