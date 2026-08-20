from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication, QLineEdit

from app.ui.pages.assistant_page import AssistantPage


class AssistantUiV0104Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_visual_shell_is_ready(self):
        page = AssistantPage()
        self.assertEqual(page.connection_badge.text() in {"Gemini · Sin configurar", "Gemini · Clave guardada"}, True)
        self.assertEqual(page.api_key_input.echoMode(), QLineEdit.Password)
        self.assertEqual(page.conversation_list.count(), 1)
        self.assertIsNotNone(page.current_conversation_id)
        self.assertFalse(page.settings_panel.isVisible())
        self.assertIn("pintura", page.input.placeholderText().casefold())
        page.close()

    def test_conversations_are_in_memory_and_chat_can_render_placeholder(self):
        page = AssistantPage()
        first_id = page.current_conversation_id
        page.input.setPlainText("¿Qué grises oscuros tengo?")
        page.send_message()
        conversation = page.session_store.get(first_id)
        self.assertIsNotNone(conversation)
        self.assertEqual([message.role for message in conversation.messages], ["user", "assistant"])
        self.assertIn("0.10.4", conversation.messages[-1].content)

        page.new_conversation()
        self.assertEqual(page.conversation_list.count(), 2)
        self.assertNotEqual(page.current_conversation_id, first_id)
        page.delete_current_conversation()
        self.assertEqual(page.conversation_list.count(), 1)
        page.close()


if __name__ == "__main__":
    unittest.main()
