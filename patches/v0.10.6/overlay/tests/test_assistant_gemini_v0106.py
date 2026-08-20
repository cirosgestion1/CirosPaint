from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest

from app.services.assistant_contracts import AssistantToolResult
from app.services.assistant_gemini_service import GeminiAssistantError, GeminiAssistantService


class FakeStep:
    def __init__(self, step_type, **kwargs):
        self.type = step_type
        for key, value in kwargs.items():
            setattr(self, key, value)

    def model_dump(self, mode="json", exclude_none=True):
        data = {"type": self.type}
        for key, value in self.__dict__.items():
            if key == "type":
                continue
            if value is not None or not exclude_none:
                data[key] = value
        return data


class FakeInteraction:
    def __init__(self, steps=None, output_text="", status="completed"):
        self.steps = list(steps or [])
        self.output_text = output_text
        self.status = status


class FakeInteractions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClient:
    def __init__(self, responses):
        self.interactions = FakeInteractions(responses)
        self.closed = False

    def close(self):
        self.closed = True


class FakePaintService:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or AssistantToolResult(
            "ok",
            "Tienes 2 unidades.",
            {"paint": {"brand": "AK", "name": "Black Grey", "total_units": 2}},
        )

    def execute(self, name, arguments):
        self.calls.append((name, arguments))
        return self.result


class FakeHttpError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class GeminiAssistantV0106Tests(unittest.TestCase):
    def test_plain_text_uses_stateless_interactions_and_system_instruction(self):
        final_step = FakeStep("model_output", content=[])
        client = FakeClient([FakeInteraction([final_step], "Usa una capa base negra y luces grises.")])
        service = GeminiAssistantService("AQ.test", client_factory=lambda _key: client)

        reply = service.reply([], "¿Cómo pintarías una armadura negra?")

        self.assertIn("luces grises", reply.text)
        self.assertTrue(client.closed)
        call = client.interactions.calls[0]
        self.assertEqual(call["model"], "gemini-3.7-flash")
        self.assertFalse(call["store"])
        self.assertIn("base de datos local", call["system_instruction"])
        self.assertEqual(call["input"][0]["type"], "user_input")
        self.assertGreaterEqual(len(call["tools"]), 7)
        self.assertTrue(all(tool["type"] == "function" for tool in call["tools"]))
        self.assertTrue(all("additionalProperties" not in tool["parameters"] for tool in call["tools"]))
        self.assertEqual(reply.provider_history[0]["type"], "user_input")
        self.assertEqual(reply.provider_history[-1]["type"], "model_output")

    def test_function_call_is_executed_locally_and_result_returns_to_gemini(self):
        function_call = FakeStep(
            "function_call",
            id="call_1",
            name="get_paint_stock",
            arguments={"query": "Black Grey"},
        )
        final_step = FakeStep("model_output", content=[])
        client = FakeClient(
            [
                FakeInteraction([function_call], ""),
                FakeInteraction([final_step], "Tienes 2 unidades de AK Black Grey."),
            ]
        )
        paint_service = FakePaintService()
        service = GeminiAssistantService(
            "AQ.test",
            client_factory=lambda _key: client,
            paint_service_factory=lambda _session: paint_service,
        )

        reply = service.reply([], "¿Cuánto Black Grey tengo?")

        self.assertEqual(paint_service.calls, [("get_paint_stock", {"query": "Black Grey"})])
        self.assertEqual(len(client.interactions.calls), 2)
        second_input = client.interactions.calls[1]["input"]
        function_results = [step for step in second_input if step.get("type") == "function_result"]
        self.assertEqual(len(function_results), 1)
        self.assertEqual(function_results[0]["call_id"], "call_1")
        self.assertIn("Tienes 2 unidades", function_results[0]["result"][0]["text"])
        self.assertEqual(reply.text, "Tienes 2 unidades de AK Black Grey.")
        self.assertEqual(reply.tool_events[0]["name"], "get_paint_stock")

    def test_provider_history_is_reused_between_turns_without_server_storage(self):
        old_history = [
            {"type": "user_input", "content": [{"type": "text", "text": "Primera pregunta"}]},
            {"type": "model_output", "content": [{"type": "text", "text": "Primera respuesta"}]},
        ]
        client = FakeClient([FakeInteraction([FakeStep("model_output", content=[])], "Segunda respuesta")])
        service = GeminiAssistantService("AQ.test", client_factory=lambda _key: client)

        reply = service.reply(old_history, "Segunda pregunta")

        sent = client.interactions.calls[0]["input"]
        self.assertEqual(sent[0], old_history[0])
        self.assertEqual(sent[1], old_history[1])
        self.assertEqual(sent[2]["type"], "user_input")
        self.assertFalse(client.interactions.calls[0]["store"])
        self.assertEqual(reply.text, "Segunda respuesta")

    def test_image_is_sent_inline_with_text(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "paint.png"
            image.write_bytes(b"not-a-real-image-but-small-enough-for-inline-test")
            client = FakeClient([FakeInteraction([FakeStep("model_output", content=[])], "Imagen recibida")])
            service = GeminiAssistantService("AQ.test", client_factory=lambda _key: client)

            reply = service.reply([], "¿Qué pintura ves?", str(image))

        content = client.interactions.calls[0]["input"][0]["content"]
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[1]["type"], "image")
        self.assertEqual(content[1]["mime_type"], "image/png")
        self.assertTrue(content[1]["data"])
        self.assertEqual(reply.text, "Imagen recibida")

    def test_429_has_clear_quota_message(self):
        client = FakeClient([FakeHttpError(429, "RESOURCE_EXHAUSTED quota")])
        service = GeminiAssistantService("AQ.test", client_factory=lambda _key: client)
        with self.assertRaises(GeminiAssistantError) as captured:
            service.reply([], "Hola")
        self.assertEqual(captured.exception.code, "quota")
        self.assertIn("límite de uso", captured.exception.user_message)

    def test_connection_check_is_a_real_minimal_interaction(self):
        client = FakeClient([FakeInteraction([], "CIROS_OK")])
        service = GeminiAssistantService("AQ.test", client_factory=lambda _key: client)
        message = service.check_connection()
        self.assertIn("Conexión correcta", message)
        call = client.interactions.calls[0]
        self.assertFalse(call["store"])
        self.assertIn("CIROS_OK", call["input"])


if __name__ == "__main__":
    unittest.main()
