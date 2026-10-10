"""Ollama provider placeholder."""

from __future__ import annotations

from collections.abc import AsyncIterator

from llm_providers.base import BaseLLM, LLMConfig, LLMEvent, ToolResult


class OllamaLLM(BaseLLM):
    """Ollama provider, not implemented yet."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str | None = None,
        **kwargs: object,
    ) -> None:
        self._host = host
        self._model = model
        self._connected = False

    async def connect(self, config: LLMConfig) -> None:
        raise NotImplementedError("Ollama provider is not implemented.")

    async def send_audio(
        self,
        audio_data: bytes,
        mime_type: str = "audio/pcm;rate=16000",
    ) -> None:
        raise NotImplementedError("Ollama provider is not implemented.")

    async def send_text(self, text: str) -> None:
        raise NotImplementedError("Ollama provider is not implemented.")

    async def send_tool_result(self, result: ToolResult) -> None:
        raise NotImplementedError("Ollama provider is not implemented.")

    def receive(self) -> AsyncIterator[LLMEvent]:
        raise NotImplementedError("Ollama provider is not implemented.")

    async def close(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def classify_error(self, error: Exception) -> str:
        return "permanent"
