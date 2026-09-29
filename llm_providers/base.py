"""Base LLM Provider interface for JARVIS.

Defines the abstract interface for real-time LLM providers with normalized events.
This is NOT a copy of the Gemini API - it's a normalized interface that all
providers must implement.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional
from enum import Enum


class LLMEventType(Enum):
    """Normalized event types from LLM providers."""
    AUDIO = "audio"                    # Audio chunk from model
    TEXT = "text"                      # Text transcript from model
    TOOL_CALL = "tool_call"            # Model requests tool execution
    TURN_COMPLETE = "turn_complete"    # Model finished its turn
    INTERRUPTION = "interruption"      # User interrupted (VAD)
    ERROR = "error"                    # Provider error
    CLOSE = "close"                    # Session closed normally


@dataclass
class LLMEvent:
    """Normalized event from LLM provider."""
    type: LLMEventType
    data: Any = None
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ToolCall:
    """Normalized tool call request."""
    id: str
    name: str
    args: dict


@dataclass
class ToolResult:
    """Normalized tool result to send back to provider."""
    id: str
    name: str
    result: Any
    error: str = None


class BaseLLM(ABC):
    """Abstract base class for real-time LLM providers.

    All providers must implement this interface. The interface models a
    real-time bidirectional session with normalized events, not a direct
    mapping to any specific provider's API.
    """

    @abstractmethod
    async def connect(self, config: "LLMConfig") -> None:
        """Establish connection to the LLM provider.

        Args:
            config: Configuration for the session including tools, voice, etc.

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If credentials are invalid
        """
        ...

    @abstractmethod
    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm;rate=16000") -> None:
        """Send audio input to the model.

        Args:
            audio_data: Raw PCM audio bytes
            mime_type: MIME type with sample rate info
        """
        ...

    @abstractmethod
    async def send_text(self, text: str) -> None:
        """Send text input to the model.

        Args:
            text: Text message from user
        """
        ...

    @abstractmethod
    async def send_tool_result(self, result: ToolResult) -> None:
        """Send tool execution result back to the model.

        Args:
            result: ToolResult with id, name, result/error
        """
        ...

    @abstractmethod
    async def receive(self) -> AsyncIterator[LLMEvent]:
        """Receive normalized events from the model.

        Yields:
            LLMEvent: Normalized events (audio, text, tool_call, turn_complete, etc.)
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the session gracefully."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if session is active."""
        ...

    @abstractmethod
    def classify_error(self, error: Exception) -> str:
        """Classify provider error for retry policy.

        Returns:
            One of: "transient", "permanent", "normal_close", "unsupported_voice"
        """
        ...


@dataclass
class LLMConfig:
    """Configuration for LLM session.

    This is provider-agnostic configuration that gets translated to
    provider-specific formats by each implementation.
    """
    # Model selection
    model: str

    # System prompt with memory/time context
    system_instruction: str

    # Voice settings
    voice_name: str

    # Audio settings
    input_sample_rate: int = 16000
    output_sample_rate: int = 24000
    vad_silence_ms: int = 200

    # Tools (neutral JSON schema format)
    tools: list[dict] = None

    # Provider-specific options
    provider_options: dict = None

    def __post_init__(self):
        if self.tools is None:
            self.tools = []
        if self.provider_options is None:
            self.provider_options = {}


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class LLMConnectionError(LLMProviderError):
    """Connection-related errors."""
    pass


class LLMAuthenticationError(LLMProviderError):
    """Authentication/credential errors."""
    pass


class LLMUnsupportedVoiceError(LLMProviderError):
    """Voice not supported by provider/model."""
    pass


class LLMTransientError(LLMProviderError):
    """Transient errors that may succeed on retry."""
    pass