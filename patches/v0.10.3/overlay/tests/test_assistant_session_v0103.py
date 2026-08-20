from __future__ import annotations

import unittest

from app.services.assistant_scope import ASSISTANT_SCOPE
from app.services.assistant_session_store import AssistantSessionStore


class AssistantSessionV0103Tests(unittest.TestCase):
    def test_conversations_are_separate_and_memory_is_in_process_only(self):
        store = AssistantSessionStore()
        first = store.create("Stormtroopers")
        second = store.create("Diorama")
        store.add_message(first.id, "user", "Usaremos gris.")
        store.add_message(second.id, "user", "Usaremos barro.")

        self.assertEqual([message.content for message in store.get(first.id).messages], ["Usaremos gris."])
        self.assertEqual([message.content for message in store.get(second.id).messages], ["Usaremos barro."])
        self.assertTrue(store.delete(first.id))
        self.assertIsNone(store.get(first.id))
        self.assertIsNotNone(store.get(second.id))

    def test_clear_removes_all_context(self):
        store = AssistantSessionStore()
        conversation = store.create()
        store.add_message(conversation.id, "assistant", "Respuesta")
        store.clear()
        self.assertEqual(store.list(), [])

    def test_scope_encodes_hobby_and_paint_only_image_rules(self):
        self.assertIn("modelismo", ASSISTANT_SCOPE["allowed_domain"].casefold())
        self.assertIn("pinturas", ASSISTANT_SCOPE["image_scope"].casefold())
        self.assertIn("base de datos", ASSISTANT_SCOPE["database_truth"].casefold())
        self.assertIn("temporales", ASSISTANT_SCOPE["conversation_memory"].casefold())


if __name__ == "__main__":
    unittest.main()
