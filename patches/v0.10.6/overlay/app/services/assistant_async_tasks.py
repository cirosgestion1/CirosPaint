from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.services.assistant_gemini_service import GeminiAssistantError, GeminiAssistantService


class AssistantRequestSignals(QObject):
    success = Signal(str, str, object, object)
    failure = Signal(str, str, str)
    finished = Signal()


class AssistantRequestTask(QRunnable):
    def __init__(
        self,
        conversation_id: str,
        api_key: str,
        provider_history: list[dict[str, Any]],
        user_text: str,
        image_path: str | None,
        service_factory: Callable[[str], Any] | None = None,
    ):
        super().__init__()
        self.conversation_id = conversation_id
        self.api_key = api_key
        self.provider_history = list(provider_history or [])
        self.user_text = user_text
        self.image_path = image_path
        self.service_factory = service_factory or (lambda key: GeminiAssistantService(key))
        self.signals = AssistantRequestSignals()

    @Slot()
    def run(self):
        try:
            service = self.service_factory(self.api_key)
            reply = service.reply(self.provider_history, self.user_text, self.image_path)
            self.signals.success.emit(
                self.conversation_id,
                reply.text,
                reply.provider_history,
                reply.tool_events,
            )
        except GeminiAssistantError as exc:
            self.signals.failure.emit(self.conversation_id, exc.code, exc.user_message)
        except Exception as exc:
            self.signals.failure.emit(
                self.conversation_id,
                "unexpected",
                f"Se ha producido un error inesperado en Ciros Assistant: {exc}",
            )
        finally:
            self.signals.finished.emit()


class GeminiConnectionSignals(QObject):
    success = Signal(str)
    failure = Signal(str, str)
    finished = Signal()


class GeminiConnectionTask(QRunnable):
    def __init__(self, api_key: str, service_factory: Callable[[str], Any] | None = None):
        super().__init__()
        self.api_key = api_key
        self.service_factory = service_factory or (lambda key: GeminiAssistantService(key))
        self.signals = GeminiConnectionSignals()

    @Slot()
    def run(self):
        try:
            service = self.service_factory(self.api_key)
            message = service.check_connection()
            self.signals.success.emit(message)
        except GeminiAssistantError as exc:
            self.signals.failure.emit(exc.code, exc.user_message)
        except Exception as exc:
            self.signals.failure.emit("unexpected", f"No se ha podido comprobar la conexión con Gemini: {exc}")
        finally:
            self.signals.finished.emit()
