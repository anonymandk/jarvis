"""OpenAI provider stub for JARVIS.

This is a placeholder implementation that will be completed in Phase 8.
Currently raises NotImplementedError for all operations.
"""

from __future__ import annotations

from llm_providers.base import (
    BaseLLM,
    LLMConfig,
    LLMEvent,
    LLMEventType,
    ToolCall,
    ToolResult,
    LLMConnectionError,
)

class OpenAILLM(BaseLLM):
    """OpenAI Realtime API provider (STUB - Phase 8).

    This stub raises NotImplementedError for all operations.
    The functional implementation will be added in Phase 8.
    """

    def __init__(self, api_key: str, **kwargs):
        self._api_key = api_key
        self._connected = False

    async def connect(self, config: LLMConfig) -> None:
        raise NotImplementedError(
            "OpenAI provider not yet implemented. "
            "This will be available in Phase 8. "
            "Please use 'gemini' provider (default) for now."
        )

    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm;rate=16000") -> None:
        raise NotImplementedError("OpenAI provider not yet implemented")

    async def send_text(self, text: str) -> None:
        raise NotImplementedError("OpenAI provider not yet implemented")

    async def send_tool_result(self, result: ToolResult) -> None:
        raise NotImplementedError("OpenAI provider not yet implemented")

    async def receive(self):
        raise NotImplementedError("OpenAI provider not yet implemented")
        yield  # Make this an async generator

    async def close(self) -> None:
        pass

    def is_connected(self) -> bool:
        return self._connected

    def classify_error(self, error: Exception) -> str:
        return "permanent"