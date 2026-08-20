from __future__ import annotations

import time
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit

from app.services.assistant_gemini_service import GeminiAssistantError, GeminiReply
from app.services.assistant_settings_store import AssistantSettingsStore
from app.ui.dialogs.assistant_info_dialog import AssistantInfoDialog
from app.ui.pages.assistant_page import AssistantPage
from app.ui.pages.settings_page import SettingsPage


class FakeGeminiService:
    def __init__(self, api_key, *, fail=False):
        self.api_key = api_key
        self.fail = fail

    def check_connection(self):
        if self.fail:
            raise GeminiAssistantError("authentication", "API Key no válida.")
        return "Conexión correcta con Gemini (gemini-3.7-flash)."

    def reply(self, provider_history, user_text, image_path=None):
        if self.fail:
            raise GeminiAssistantError("quota", "Se ha alcanzado un límite de uso de Gemini.")
        history = list(provider_history or [])
        history.append({"type": "user_input", "content": [{"type": "text", "text": user_text or "imagen"}]})
        history.append({"type": "model_output", "content": [{"type": "text", "text": "Respuesta Gemini"}]})
        return GeminiReply("Respuesta Gemini", history, [])


def wait_for(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    QApplication.processEvents()
    return predicate()


class AssistantUiV0106Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_send_button_runs_real_async_flow_and_stores_provider_history(self):
        factory = lambda key: FakeGeminiService(key)
        with patch.object(AssistantSettingsStore, "gemini_api_key", return_value="AQ.test"):
            page = AssistantPage(gemini_service_factory=factory)
            QApplication.processEvents()
            page.input.setPlainText("¿Cómo pinto una armadura negra?")
            QTest.mouseClick(page.send_button, Qt.LeftButton)
            self.assertTrue(page.busy)
            self.assertFalse(page.send_button.isEnabled())
            self.assertTrue(wait_for(lambda: not page.busy))

        conversation = page.session_store.get(page.current_conversation_id)
        self.assertIsNotNone(conversation)
        self.assertEqual([message.role for message in conversation.messages], ["user", "assistant"])
        self.assertEqual(conversation.messages[-1].content, "Respuesta Gemini")
        self.assertEqual(len(conversation.provider_history), 2)
        self.assertTrue(page.send_button.isEnabled())
        page.close()

    def test_missing_key_does_not_consume_message(self):
        with patch.object(AssistantSettingsStore, "gemini_api_key", return_value=""):
            page = AssistantPage(gemini_service_factory=lambda key: FakeGeminiService(key))
            page.input.setPlainText("Hola")
            QTest.mouseClick(page.send_button, Qt.LeftButton)
            QApplication.processEvents()
        conversation = page.session_store.get(page.current_conversation_id)
        self.assertEqual(conversation.messages, [])
        self.assertIn("Ajustes", page.request_status.text())
        self.assertEqual(page.input.toPlainText(), "Hola")
        page.close()

    def test_gemini_error_is_rendered_without_crashing_chat(self):
        factory = lambda key: FakeGeminiService(key, fail=True)
        with patch.object(AssistantSettingsStore, "gemini_api_key", return_value="AQ.test"):
            page = AssistantPage(gemini_service_factory=factory)
            page.input.setPlainText("Consulta")
            QTest.mouseClick(page.send_button, Qt.LeftButton)
            self.assertTrue(wait_for(lambda: not page.busy))
        conversation = page.session_store.get(page.current_conversation_id)
        self.assertIn("límite de uso", conversation.messages[-1].content)
        page.close()

    def test_connection_button_checks_gemini_asynchronously(self):
        page = SettingsPage(gemini_service_factory=lambda key: FakeGeminiService(key))
        page.gemini_api_key_input.setText("AQ.test")
        QTest.mouseClick(page.gemini_test_button, Qt.LeftButton)
        self.assertFalse(page.gemini_test_button.isEnabled())
        self.assertTrue(wait_for(lambda: page.gemini_test_button.isEnabled()))
        self.assertIn("Conexión correcta", page.gemini_status.text())
        page.close()

    def test_settings_and_info_reflect_functional_assistant(self):
        page = SettingsPage(gemini_service_factory=lambda key: FakeGeminiService(key))
        self.assertEqual(page.gemini_api_key_input.echoMode(), QLineEdit.Password)
        self.assertIsNotNone(page.open_data_button)
        texts = [label.text() for label in page.findChildren(QLabel)]
        self.assertIn("Gemini API", texts)
        page.close()

        dialog = AssistantInfoDialog()
        text = " | ".join(label.text() for label in dialog.findChildren(QLabel))
        self.assertIn("Analizar imágenes", text)
        self.assertIn("Puedes adjuntar imágenes", text)
        self.assertIn("Cómo utiliza tus datos", text)
        dialog.close()


if __name__ == "__main__":
    unittest.main()
