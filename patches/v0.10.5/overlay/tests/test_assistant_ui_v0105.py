from __future__ import annotations

import unittest

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit

from app.ui.dialogs.assistant_info_dialog import AssistantInfoDialog
from app.ui.pages.assistant_page import AssistantPage
from app.ui.pages.settings_page import SettingsPage


class AssistantUiV0105Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_real_send_button_click_survives_event_loop_and_sends_text(self):
        page = AssistantPage()
        QApplication.processEvents()
        page.input.setPlainText("¿Qué grises oscuros tengo?")
        QTest.mouseClick(page.send_button, Qt.LeftButton)
        QApplication.processEvents()

        conversation = page.session_store.get(page.current_conversation_id)
        self.assertIsNotNone(conversation)
        self.assertEqual([message.role for message in conversation.messages], ["user", "assistant"])
        self.assertIn("¿Qué grises oscuros tengo?", conversation.messages[0].content)
        self.assertIn("0.10.5", conversation.messages[1].content)
        page.close()

    def test_real_send_button_click_can_send_image_only(self):
        page = AssistantPage()
        QApplication.processEvents()
        page.attached_image_path = "C:/temp/pintura_prueba.png"
        page.attachment_label.setText("📷 pintura_prueba.png")
        page.attachment_label.setVisible(True)
        page.remove_attachment_button.setVisible(True)
        QTest.mouseClick(page.send_button, Qt.LeftButton)
        QApplication.processEvents()

        conversation = page.session_store.get(page.current_conversation_id)
        self.assertIsNotNone(conversation)
        self.assertIn("pintura_prueba.png", conversation.messages[0].content)
        self.assertIsNone(page.attached_image_path)
        page.close()

    def test_assistant_has_info_button_but_no_gemini_settings_or_old_capability_list(self):
        page = AssistantPage()
        self.assertIsNotNone(page.info_button)
        self.assertFalse(hasattr(page, "settings_button"))
        self.assertFalse(hasattr(page, "connection_badge"))
        texts = [label.text() for label in page.findChildren(QLabel)]
        self.assertNotIn("Puede trabajar con", texts)
        self.assertNotIn("Imágenes: solo pinturas de modelismo", texts)
        page.close()

    def test_info_dialog_contains_summary_and_detailed_sections(self):
        dialog = AssistantInfoDialog()
        text = " | ".join(label.text() for label in dialog.findChildren(QLabel))
        self.assertIn("¿Qué puede hacer?", text)
        self.assertIn("Consultar tu inventario de pinturas", text)
        self.assertIn("Buscar alternativas", text)
        self.assertIn("Gestionar pinturas y cantidades", text)
        self.assertIn("Futuras compras", text)
        self.assertIn("Ayuda con pintura y modelismo", text)
        self.assertIn("Analizar imágenes", text)
        self.assertIn("Cómo utiliza tus datos", text)
        dialog.close()

    def test_gemini_configuration_lives_in_settings(self):
        page = SettingsPage()
        self.assertEqual(page.gemini_api_key_input.echoMode(), QLineEdit.Password)
        self.assertIsNotNone(page.open_data_button)
        texts = [label.text() for label in page.findChildren(QLabel)]
        self.assertIn("Base de datos local", texts)
        self.assertIn("YouTube Data API", texts)
        self.assertIn("Gemini API", texts)
        page.close()


if __name__ == "__main__":
    unittest.main()
