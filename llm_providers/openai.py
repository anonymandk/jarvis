"""OpenAI Realtime provider placeholder."""

from __future__ import annotations

from collections.abc import AsyncIterator

from llm_providers.base import BaseLLM, LLMConfig, LLMEvent, ToolResult


class OpenAILLM(BaseLLM):
    """OpenAI Realtime provider, not implemented yet."""

    def __init__(self, api_key: str | None = None, **kwargs: object) -> None:
        self._api_key = api_key
        self._connected = False

    async def connect(self, config: LLMConfig) -> None:
        raise NotImplementedError("OpenAI Realtime provider is not implemented.")

    async def send_audio(
        self,
        audio_data: bytes,
        mime_type: str = "audio/pcm;rate=16000",
    ) -> None:
        raise NotImplementedError("OpenAI Realtime provider is not implemented.")

    async def send_text(self, text: str) -> None:
        raise NotImplementedError("OpenAI Realtime provider is not implemented.")

    async def send_tool_result(self, result: ToolResult) -> None:
        raise NotImplementedError("OpenAI Realtime provider is not implemented.")

    def receive(self) -> AsyncIterator[LLMEvent]:
        raise NotImplementedError("OpenAI Realtime provider is not implemented.")

    async def close(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def classify_error(self, error: Exception) -> str:
        return "permanent"
