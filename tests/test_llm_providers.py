import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from google.genai import types

from llm_providers import (
    GeminiLLM,
    LLMConfig,
    LLMEventType,
    OllamaLLM,
    OpenAILLM,
    ToolResult,
    create_llm_provider,
)


def make_config():
    return LLMConfig(
        model="models/gemini-live-test",
        system_instruction="Test instructions",
        voice_name="Puck",
        vad_silence_ms=250,
        tools=[
            {
                "name": "test_tool",
                "description": "A test tool",
                "parameters": {"type": "OBJECT", "properties": {}},
            }
        ],
    )


class GeminiProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_connect_send_and_close_use_live_context_manager(self):
        session = SimpleNamespace(
            send_realtime_input=AsyncMock(),
            send_client_content=AsyncMock(),
            send_tool_response=AsyncMock(),
        )
        connection = SimpleNamespace(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock(return_value=False),
        )
        live = SimpleNamespace(connect=Mock(return_value=connection))
        client = SimpleNamespace(aio=SimpleNamespace(live=live))

        with patch("llm_providers.gemini.genai.Client", return_value=client) as factory:
            provider = GeminiLLM("test-key")
            await provider.connect(make_config())

        self.assertTrue(provider.is_connected())
        factory.assert_called_once()
        live.connect.assert_called_once()
        live_config = live.connect.call_args.kwargs["config"]
        self.assertEqual(live_config.response_modalities, [types.Modality.AUDIO])
        self.assertEqual(
            live_config.tools[0].function_declarations[0].name,
            "test_tool",
        )

        await provider.send_audio(b"\x00\x01")
        await provider.send_text("hello")
        await provider.send_tool_result(
            ToolResult(id="call-1", name="test_tool", result={"ok": True})
        )
        session.send_realtime_input.assert_awaited_once()
        session.send_client_content.assert_awaited_once()
        session.send_tool_response.assert_awaited_once()

        await provider.close()
        connection.__aexit__.assert_awaited_once_with(None, None, None)
        self.assertFalse(provider.is_connected())

    async def test_receive_normalizes_audio_text_tool_and_turn_events(self):
        response = SimpleNamespace(
            server_content=SimpleNamespace(
                model_turn=SimpleNamespace(
                    parts=[
                        SimpleNamespace(
                            inline_data=SimpleNamespace(data=b"\x00\x01"),
                            text=None,
                        ),
                        SimpleNamespace(inline_data=None, text="spoken words"),
                    ]
                ),
                output_transcription=SimpleNamespace(text="output transcript"),
                input_transcription=SimpleNamespace(text="input transcript"),
                turn_complete=True,
                interrupted=True,
            ),
            tool_call=SimpleNamespace(
                function_calls=[
                    SimpleNamespace(id="tool-1", name="test_tool", args={"x": 1})
                ]
            ),
        )

        async def receive():
            yield response

        provider = GeminiLLM("test-key")
        provider._session = SimpleNamespace(receive=receive)
        provider._connected = True

        events = [event async for event in provider.receive()]

        self.assertEqual(
            [event.type for event in events],
            [
                LLMEventType.AUDIO,
                LLMEventType.TEXT,
                LLMEventType.TEXT,
                LLMEventType.TEXT,
                LLMEventType.TURN_COMPLETE,
                LLMEventType.INTERRUPTION,
                LLMEventType.TOOL_CALL,
            ],
        )
        self.assertEqual(events[0].data, b"\x00\x01")
        self.assertEqual(events[2].metadata, {"is_output": True})
        self.assertEqual(events[3].metadata, {"is_input": True})
        self.assertEqual(events[-1].data.args, {"x": 1})

    def test_provider_config_defaults_are_independent(self):
        first = LLMConfig(model="m", system_instruction="", voice_name="Puck")
        second = LLMConfig(model="m", system_instruction="", voice_name="Puck")

        first.tools.append({"name": "only_first"})
        first.provider_options["key"] = "value"

        self.assertEqual(second.tools, [])
        self.assertEqual(second.provider_options, {})


class ProviderFactoryTests(unittest.TestCase):
    def test_factory_constructs_gemini_from_explicit_api_key(self):
        settings = SimpleNamespace(llm=SimpleNamespace(provider="gemini"))
        with patch("llm_providers.factory.get_settings", return_value=settings):
            provider = create_llm_provider(api_key="test-key")

        self.assertIsInstance(provider, GeminiLLM)

    def test_unimplemented_providers_fail_explicitly(self):
        settings = SimpleNamespace(llm=SimpleNamespace(provider="gemini"))
        with patch("llm_providers.factory.get_settings", return_value=settings):
            with self.assertRaisesRegex(NotImplementedError, "OpenAI"):
                create_llm_provider(provider="openai")
            with self.assertRaisesRegex(NotImplementedError, "Ollama"):
                create_llm_provider(provider="ollama")

    def test_provider_placeholders_are_instantiable(self):
        self.assertIsInstance(OpenAILLM(), OpenAILLM)
        self.assertIsInstance(OllamaLLM(), OllamaLLM)


if __name__ == "__main__":
    unittest.main()
