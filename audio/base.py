"""Audio interface abstraction for ARGUS.

This module defines the AudioInterface protocol that all audio backends must implement.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Callable, Optional


class AudioInterface(ABC):
    """Abstract base class for audio input/output backends.

    Implementations must handle the thread-to-asyncio bridge for sounddevice callbacks.
    """

    @abstractmethod
    async def start_input(self, callback: Callable[[bytes], None]) -> None:
        """Start audio capture.

        Args:
            callback: Called with raw PCM audio bytes from the microphone.
                     Must be thread-safe (called from sounddevice callback thread).
        """
        ...

    @abstractmethod
    async def start_output(self) -> None:
        """Start audio playback preparation."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop both input and output, release resources."""
        ...

    @abstractmethod
    def put_audio(self, chunk: bytes) -> None:
        """Queue audio chunk for playback.

        Called from the async receive loop. Must be thread-safe.
        """
        ...

    @abstractmethod
    async def get_audio(self) -> Optional[bytes]:
        """Get next audio chunk for playback.

        Returns:
            Audio chunk bytes, or None if stopped/closed.
        """
        ...

    @property
    @abstractmethod
    def is_speaking(self) -> bool:
        """Whether audio is currently being played."""
        ...

    @property
    @abstractmethod
    def input_active(self) -> bool:
        """Whether audio input stream is active."""
        ...


class AudioConfig:
    """Audio configuration parameters."""

    def __init__(
        self,
        channels: int = 1,
        send_sample_rate: int = 16000,
        receive_sample_rate: int = 24000,
        chunk_size: int = 1024,
        vad_silence_ms: int = 200,
    ):
        self.channels = channels
        self.send_sample_rate = send_sample_rate
        self.receive_sample_rate = receive_sample_rate
        self.chunk_size = chunk_size
        self.vad_silence_ms = vad_silence_ms

    @classmethod
    def from_settings(cls, settings) -> "AudioConfig":
        """Create AudioConfig from ARGUS settings object."""
        return cls(
            channels=settings.audio.channels,
            send_sample_rate=settings.audio.send_sample_rate,
            receive_sample_rate=settings.audio.receive_sample_rate,
            chunk_size=settings.audio.chunk_size,
            vad_silence_ms=settings.audio.vad_silence_ms,
        )