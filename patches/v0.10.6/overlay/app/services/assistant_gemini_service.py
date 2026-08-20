from __future__ import annotations

import base64
import copy
import json
import mimetypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from app.db.database import get_session
from app.services.assistant_paint_service import AssistantPaintService
from app.services.assistant_tool_registry import PAINT_TOOL_DEFINITIONS


DEFAULT_GEMINI_MODEL = "gemini-3.7-flash"
MAX_TOOL_ROUNDS = 6


SYSTEM_INSTRUCTION = """Eres Ciros Assistant, el asistente integrado de Ciros Paint.

Ámbito permitido:
- pintura de miniaturas y modelismo;
- aerografía, pincel, imprimación, luces, sombras, degradados y teoría del color aplicada al hobby;
- desgaste, suciedad, óxido, dioramas y escenografía;
- inventario de pinturas y futuras compras gestionados por Ciros Paint.

Reglas obligatorias:
1. Responde en el idioma del usuario.
2. La base de datos local de Ciros Paint es la única fuente de verdad sobre qué pinturas posee el usuario, cantidades, stock y futuras compras.
3. Para afirmar qué pinturas posee el usuario, cuánto stock tiene, qué compras tiene pendientes o para modificar esos datos, utiliza siempre las herramientas de Ciros Paint. Nunca inventes esos datos.
4. Para equivalencias de color utiliza la herramienta de alternativas. No inventes porcentajes ni equivalencias cuando la pregunta dependa del inventario.
5. Nunca afirmes que una modificación se ha realizado hasta recibir un resultado satisfactorio de la herramienta correspondiente.
6. Si una herramienta devuelve ambigüedad o requires_user_input=true, pide al usuario la aclaración necesaria y no des por ejecutado ningún cambio.
7. No menciones nombres internos de herramientas, JSON, SQL, ORM ni detalles técnicos salvo que el usuario pregunte explícitamente por el funcionamiento del programa.
8. No tienes acceso directo a SQLite. Solo puedes solicitar las herramientas declaradas por Ciros Paint.
9. Las imágenes se utilizan únicamente para consultas relacionadas con pinturas de modelismo y el hobby definido.
10. Si una consulta no está relacionada con este ámbito, indica brevemente que Ciros Assistant está especializado en pintura de miniaturas y modelismo.
11. Para recomendaciones comerciales externas, puedes recomendar pinturas concretas; para otros productos del hobby limita la respuesta a características, técnicas y tipos de producto, salvo que el usuario ya haya proporcionado el producto concreto.
12. Sé preciso y práctico. Si faltan datos para realizar una acción con seguridad, pregunta antes de modificar información.
"""


@dataclass
class GeminiReply:
    text: str
    provider_history: list[dict[str, Any]]
    tool_events: list[dict[str, Any]] = field(default_factory=list)


class GeminiAssistantError(RuntimeError):
    def __init__(self, code: str, user_message: str):
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message


class GeminiAssistantService:
    """Gemini orchestration for Ciros Assistant.

    Gemini receives provider-neutral tool declarations and can request a tool,
    but every database operation remains inside Ciros Paint. Interactions are
    sent with store=False; the provider history is kept only in RAM by the app.
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_GEMINI_MODEL,
        client_factory: Callable[[str], Any] | None = None,
        paint_service_factory: Callable[[Any], Any] | None = None,
    ):
        self.api_key = str(api_key or "").strip()
        self.model = str(model or DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
        self.client_factory = client_factory
        self.paint_service_factory = paint_service_factory or (lambda session: AssistantPaintService(session))

    def check_connection(self) -> str:
        if not self.api_key:
            raise GeminiAssistantError("missing_key", "No hay una API Key de Gemini configurada.")
        client = self._create_client()
        try:
            interaction = client.interactions.create(
                model=self.model,
                input="Responde únicamente con: CIROS_OK",
                system_instruction="Esta es una comprobación técnica de conexión. Responde únicamente con CIROS_OK.",
                store=False,
                timeout=30,
            )
            if getattr(interaction, "status", "completed") not in {None, "completed"}:
                raise GeminiAssistantError("unexpected_status", "Gemini respondió, pero la comprobación no terminó correctamente.")
            return f"Conexión correcta con Gemini ({self.model})."
        except GeminiAssistantError:
            raise
        except Exception as exc:
            raise self._map_exception(exc) from exc
        finally:
            self._close_client(client)

    def reply(
        self,
        provider_history: list[dict[str, Any]] | None,
        user_text: str,
        image_path: str | None = None,
    ) -> GeminiReply:
        if not self.api_key:
            raise GeminiAssistantError("missing_key", "Configura primero una API Key de Gemini en Ajustes.")

        history = copy.deepcopy(list(provider_history or []))
        history.append(self._build_user_input(user_text, image_path))
        tools = self._gemini_tool_declarations()
        tool_events: list[dict[str, Any]] = []
        client = self._create_client()

        try:
            for _round in range(MAX_TOOL_ROUNDS):
                interaction = client.interactions.create(
                    model=self.model,
                    input=history,
                    tools=tools,
                    system_instruction=SYSTEM_INSTRUCTION,
                    store=False,
                    timeout=45,
                )

                steps = list(getattr(interaction, "steps", None) or [])
                history.extend(self._dump_step(step) for step in steps)
                function_calls = [step for step in steps if getattr(step, "type", None) == "function_call"]

                if not function_calls:
                    answer = str(getattr(interaction, "output_text", "") or "").strip()
                    if not answer:
                        answer = self._extract_text_from_steps(steps)
                    if not answer:
                        raise GeminiAssistantError("empty_response", "Gemini no devolvió una respuesta de texto utilizable.")
                    return GeminiReply(answer, history, tool_events)

                function_results: list[dict[str, Any]] = []
                with get_session() as session:
                    paint_service = self.paint_service_factory(session)
                    for call in function_calls:
                        name = str(getattr(call, "name", "") or "")
                        arguments = dict(getattr(call, "arguments", None) or {})
                        result = paint_service.execute(name, arguments).as_dict()
                        tool_events.append({"name": name, "arguments": arguments, "result": result})
                        function_results.append(
                            {
                                "type": "function_result",
                                "name": name,
                                "call_id": str(getattr(call, "id", "") or ""),
                                "result": [
                                    {
                                        "type": "text",
                                        "text": json.dumps(result, ensure_ascii=False, default=str),
                                    }
                                ],
                            }
                        )
                history.extend(function_results)

            raise GeminiAssistantError(
                "tool_loop",
                "Gemini ha solicitado demasiadas operaciones seguidas. Reformula la petición de una forma más concreta.",
            )
        except GeminiAssistantError:
            raise
        except Exception as exc:
            raise self._map_exception(exc) from exc
        finally:
            self._close_client(client)

    def _create_client(self):
        if self.client_factory is not None:
            return self.client_factory(self.api_key)
        try:
            from google import genai
        except ImportError as exc:
            raise GeminiAssistantError(
                "sdk_missing",
                "El componente de Gemini no está instalado en esta versión de Ciros Paint.",
            ) from exc
        return genai.Client(api_key=self.api_key)

    @staticmethod
    def _close_client(client) -> None:
        close = getattr(client, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass

    @staticmethod
    def _gemini_tool_declarations() -> list[dict[str, Any]]:
        declarations: list[dict[str, Any]] = []
        for definition in PAINT_TOOL_DEFINITIONS:
            parameters = copy.deepcopy(definition.input_schema)
            parameters.pop("additionalProperties", None)
            declarations.append(
                {
                    "type": "function",
                    "name": definition.name,
                    "description": definition.description,
                    "parameters": parameters,
                }
            )
        return declarations

    def _build_user_input(self, user_text: str, image_path: str | None) -> dict[str, Any]:
        text = str(user_text or "").strip()
        content: list[dict[str, Any]] = []
        if text:
            content.append({"type": "text", "text": text})
        elif image_path:
            content.append({"type": "text", "text": "Analiza esta imagen dentro del ámbito de Ciros Assistant."})

        if image_path:
            content.append(self._image_block(image_path))
        if not content:
            raise GeminiAssistantError("empty_input", "Escribe un mensaje o adjunta una imagen.")
        return {"type": "user_input", "content": content}

    @staticmethod
    def _image_block(image_path: str) -> dict[str, Any]:
        path = Path(image_path)
        if not path.is_file():
            raise GeminiAssistantError("image_missing", "La imagen adjunta ya no existe o no se puede leer.")

        mime_type = (mimetypes.guess_type(path.name)[0] or "").casefold()
        accepted = {"image/jpeg", "image/png", "image/webp"}
        raw = path.read_bytes()

        if mime_type not in accepted or len(raw) > 15 * 1024 * 1024:
            raw, mime_type = GeminiAssistantService._convert_image_for_inline(path)
        if len(raw) > 19 * 1024 * 1024:
            raise GeminiAssistantError(
                "image_too_large",
                "La imagen sigue siendo demasiado grande para enviarla a Gemini. Utiliza una imagen de menor resolución.",
            )
        return {
            "type": "image",
            "data": base64.b64encode(raw).decode("ascii"),
            "mime_type": mime_type,
        }

    @staticmethod
    def _convert_image_for_inline(path: Path) -> tuple[bytes, str]:
        try:
            from PySide6.QtCore import QBuffer, QIODevice, Qt
            from PySide6.QtGui import QImage
        except ImportError as exc:
            raise GeminiAssistantError("image_format", "No se ha podido preparar la imagen para Gemini.") from exc

        image = QImage(str(path))
        if image.isNull():
            raise GeminiAssistantError("image_format", "El formato de la imagen adjunta no se ha podido leer.")
        if max(image.width(), image.height()) > 2048:
            image = image.scaled(2048, 2048, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        buffer = QBuffer()
        if not buffer.open(QIODevice.WriteOnly):
            raise GeminiAssistantError("image_format", "No se ha podido preparar la imagen para Gemini.")
        if not image.save(buffer, "JPEG", 85):
            raise GeminiAssistantError("image_format", "No se ha podido convertir la imagen para Gemini.")
        return bytes(buffer.data()), "image/jpeg"

    @staticmethod
    def _dump_step(step: Any) -> dict[str, Any]:
        dumper = getattr(step, "model_dump", None)
        if callable(dumper):
            try:
                return dumper(mode="json", exclude_none=True)
            except TypeError:
                return dumper(exclude_none=True)
        if isinstance(step, dict):
            return copy.deepcopy(step)
        data = dict(getattr(step, "__dict__", {}) or {})
        if not data:
            raise GeminiAssistantError("invalid_step", "Gemini devolvió un paso de conversación no reconocido.")
        return data

    @staticmethod
    def _extract_text_from_steps(steps: list[Any]) -> str:
        pieces: list[str] = []
        for step in steps:
            if getattr(step, "type", None) != "model_output":
                continue
            for block in list(getattr(step, "content", None) or []):
                if getattr(block, "type", None) == "text":
                    text = str(getattr(block, "text", "") or "").strip()
                    if text:
                        pieces.append(text)
        return "\n".join(pieces).strip()

    @staticmethod
    def _map_exception(exc: Exception) -> GeminiAssistantError:
        code = getattr(exc, "code", None)
        if code is None:
            code = getattr(exc, "status_code", None)
        try:
            numeric_code = int(code) if code is not None else None
        except (TypeError, ValueError):
            numeric_code = None
        text = str(exc or "").casefold()

        if numeric_code in {401, 403} or "unauthenticated" in text or "permission_denied" in text:
            return GeminiAssistantError(
                "authentication",
                "Gemini ha rechazado la autenticación. Comprueba la API Key y que tenga acceso a Gemini API.",
            )
        if numeric_code == 429 or "resource_exhausted" in text or "quota" in text:
            return GeminiAssistantError(
                "quota",
                "Se ha alcanzado un límite de uso de Gemini. Inténtalo cuando se restablezca la cuota disponible.",
            )
        if numeric_code == 503 or "unavailable" in text or "overloaded" in text:
            return GeminiAssistantError(
                "unavailable",
                "Gemini está temporalmente saturado o no disponible. Inténtalo de nuevo más tarde.",
            )
        if numeric_code == 400 or "invalid_argument" in text:
            return GeminiAssistantError(
                "invalid_request",
                "Gemini ha rechazado la solicitud. Comprueba la configuración o reformula el mensaje.",
            )
        if "timeout" in text or "timed out" in text:
            return GeminiAssistantError("timeout", "La conexión con Gemini ha tardado demasiado en responder.")
        if any(token in text for token in ("connection", "network", "dns", "name resolution")):
            return GeminiAssistantError("network", "No se ha podido conectar con Gemini. Comprueba tu conexión a Internet.")
        return GeminiAssistantError("unknown", f"No se ha podido completar la petición a Gemini: {exc}")
