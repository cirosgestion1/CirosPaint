from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class AssistantMessage:
    role: str
    content: str


@dataclass
class AssistantConversation:
    id: str
    title: str
    messages: list[AssistantMessage] = field(default_factory=list)
    # Exact Interactions API history kept only in RAM. It includes model thought
    # and tool steps required by Gemini stateless conversations (store=False).
    provider_history: list[dict[str, Any]] = field(default_factory=list)


class AssistantSessionStore:
    """In-memory conversation storage only.

    Nothing is written to SQLite, settings or disk. Closing the application or
    deleting a conversation removes both visible messages and Gemini context.
    """

    def __init__(self):
        self._conversations: dict[str, AssistantConversation] = {}

    def create(self, title: str = "Nueva conversación") -> AssistantConversation:
        conversation = AssistantConversation(id=uuid4().hex, title=(title or "Nueva conversación").strip())
        self._conversations[conversation.id] = conversation
        return conversation

    def list(self) -> list[AssistantConversation]:
        return list(self._conversations.values())

    def get(self, conversation_id: str) -> AssistantConversation | None:
        return self._conversations.get(conversation_id)

    def add_message(self, conversation_id: str, role: str, content: str) -> AssistantMessage:
        conversation = self.get(conversation_id)
        if conversation is None:
            raise KeyError("Conversation not found")
        normalized_role = (role or "").strip().casefold()
        if normalized_role not in {"user", "assistant", "tool"}:
            raise ValueError("Unsupported assistant message role")
        message = AssistantMessage(normalized_role, str(content or ""))
        conversation.messages.append(message)
        return message

    def set_provider_history(self, conversation_id: str, history: list[dict[str, Any]]) -> None:
        conversation = self.get(conversation_id)
        if conversation is None:
            raise KeyError("Conversation not found")
        conversation.provider_history = list(history or [])

    def delete(self, conversation_id: str) -> bool:
        return self._conversations.pop(conversation_id, None) is not None

    def clear(self) -> None:
        self._conversations.clear()
