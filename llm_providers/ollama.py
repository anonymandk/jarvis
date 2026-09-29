"""Ollama provider stub for JARVIS.

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

class OllamaLLM(BaseLLM):
    """Ollama local LLM provider (STUB - Phase 8).

    This stub raises NotImplementedError for all operations.
    The functional implementation will be added in Phase 8.
    Note: Ollama doesn't have native real-time audio API, so Phase 8
    will implement a STT -> Ollama -> TTS pipeline.
    """

    def __init__(self, host: str = "http://localhost:11434", model: str = None, **kwargs):
        self._host = host
        self._model = model
        self._connected = False

    async def connect(self, config: LLMConfig) -> None:
        raise NotImplementedError(
            "Ollama provider not yet implemented. "
            "This will be available in Phase 8. "
            "Note: Ollama requires a STT -> LLM -> TTS pipeline "
            "since it doesn't have native real-time audio API. "
            "Please use 'gemini' provider (default) for now."
        )

    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm;rate=16000") -> None:
        raise NotImplementedError("Ollama provider not yet implemented")

    async def send_text(self, text: str) -> None:
        raise NotImplementedError("Ollama provider not yet implemented")

    async def send_tool_result(self, result: ToolResult) -> None:
        raise NotImplementedError("Ollama provider not yet implemented")

    async def receive(self):
        raise NotImplementedError("Ollama provider not yet implemented")
        yield  # Make this an async generator

    async def close(self) -> None:
        pass

    def is_connected(self) -> bool:
        return self._connected

    def classify_error(self, error: Exception) -> str:
        return "permanent"