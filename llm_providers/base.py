"""Provider-neutral interfaces and data models for ARGUS LLM integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator


class LLMEventType(Enum):
    """Normalized event types emitted by LLM providers."""

    AUDIO = "audio"
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TURN_COMPLETE = "turn_complete"
    INTERRUPTION = "interruption"
    ERROR = "error"
    CLOSE = "close"


@dataclass
class LLMEvent:
    """Normalized event emitted by an LLM provider."""

    type: LLMEventType
    data: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    """Normalized tool call request."""

    id: str
    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Normalized tool result sent back to a provider."""

    id: str
    name: str
    result: Any
    error: str | None = None


class BaseLLM(ABC):
    """Abstract interface for real-time, bidirectional LLM providers."""

    @abstractmethod
    async def connect(self, config: LLMConfig) -> None:
        """Establish a provider session."""

    @abstractmethod
    async def send_audio(
        self,
        audio_data: bytes,
        mime_type: str = "audio/pcm;rate=16000",
    ) -> None:
        """Send raw audio to the model."""

    @abstractmethod
    async def send_text(self, text: str) -> None:
        """Send text to the model."""

    @abstractmethod
    async def send_tool_result(self, result: ToolResult) -> None:
        """Send a tool execution result back to the model."""

    @abstractmethod
    def receive(self) -> AsyncIterator[LLMEvent]:
        """Yield normalized events received from the model."""

    @abstractmethod
    async def close(self) -> None:
        """Close the provider session."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the provider session is active."""

    @abstractmethod
    def classify_error(self, error: Exception) -> str:
        """Classify errors for retry policy decisions."""


@dataclass
class LLMConfig:
    """Provider-neutral configuration for a live LLM session."""

    model: str
    system_instruction: str
    voice_name: str
    input_sample_rate: int = 16000
    output_sample_rate: int = 24000
    vad_silence_ms: int = 200
    tools: list[dict[str, Any]] = field(default_factory=list)
    provider_options: dict[str, Any] = field(default_factory=dict)


class LLMProviderError(Exception):
    """Base exception for provider errors."""


class LLMConnectionError(LLMProviderError):
    """Raised when a provider connection fails."""


class LLMAuthenticationError(LLMProviderError):
    """Raised when provider credentials are rejected."""


class LLMUnsupportedVoiceError(LLMProviderError):
    """Raised when a voice is not supported by the provider."""


class LLMTransientError(LLMProviderError):
    """Raised when a provider error may succeed on retry."""
