"""Dummy audio implementation for testing and headless environments.

This backend simulates audio I/O without requiring hardware.
Useful for:
- CI/CD pipelines
- Cloud deployments without audio devices
- Unit tests
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import Callable, Optional

from audio.base import AudioConfig, AudioInterface

logger = logging.getLogger("argus.audio.dummy")


class DummyAudio(AudioInterface):
    """Dummy audio backend that simulates I/O without hardware.

    Uses in-memory queues to simulate audio flow.
    """

    def __init__(
        self,
        config: Optional[AudioConfig] = None,
        *,
        external_audio: bool = False,
        speaking_lock: Optional[asyncio.Lock] = None,
        is_speaking_ref: Optional[Callable[[], bool]] = None,
        set_speaking_cb: Optional[Callable[[bool], None]] = None,
        muted_cb: Optional[Callable[[], bool]] = None,
        shutdown_event: Optional[asyncio.Event] = None,
        turn_done_event: Optional[asyncio.Event] = None,
        audio_in_queue: Optional[asyncio.Queue] = None,
        out_queue: Optional[asyncio.Queue] = None,
        send_audio_cb: Optional[Callable[[bytes, str], None]] = None,
        tts_engine_check: Optional[Callable[[], bool]] = None,
    ):
        self._config = config or AudioConfig(
            channels=1,
            send_sample_rate=16000,
            receive_sample_rate=24000,
            chunk_size=1024,
            vad_silence_ms=200,
        )
        self._external_audio = external_audio

        # State refs
        self._speaking_lock = speaking_lock or asyncio.Lock()
        self._is_speaking_ref = is_speaking_ref or (lambda: False)
        self._set_speaking_cb = set_speaking_cb or (lambda v: None)
        self._muted_cb = muted_cb or (lambda: False)
        self._shutdown_event = shutdown_event or asyncio.Event()
        self._turn_done_event = turn_done_event
        self._audio_in_queue = audio_in_queue
        self._out_queue = out_queue
        self._send_audio_cb = send_audio_cb
        self._tts_engine_check = tts_engine_check or (lambda: False)

        # Simulated audio buffers
        self._input_buffer: deque = deque()
        self._output_buffer: deque = deque()
        self._input_started = False
        self._output_started = False
        self._simulated_input_task: Optional[asyncio.Task] = None

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking_ref()

    @property
    def input_active(self) -> bool:
        return self._input_started

    async def start_input(self, callback: Callable[[bytes], None]) -> None:
        """Simulate starting microphone input.

        In dummy mode, we generate silence or accept injected audio.
        """
        self._input_started = True
        logger.info("[ARGUS] 🎤 Dummy mic started (simulated)")

    async def start_output(self) -> None:
        """Simulate starting audio output."""
        self._output_started = True
        logger.info("[ARGUS] 🔊 Dummy playback started (simulated)")

    async def stop(self) -> None:
        """Stop simulated audio."""
        self._shutdown_event.set()
        self._input_started = False
        self._output_started = False
        self._set_speaking_cb(False)

        if self._simulated_input_task:
            self._simulated_input_task.cancel()
            try:
                await self._simulated_input_task
            except asyncio.CancelledError:
                pass

        logger.info("[ARGUS] 🔇 Dummy audio stopped")

    def put_audio(self, chunk: bytes) -> None:
        """Queue audio chunk for simulated playback."""
        if self._audio_in_queue is not None:
            try:
                self._audio_in_queue.put_nowait(chunk)
            except asyncio.QueueFull:
                pass
        else:
            self._output_buffer.append(chunk)

    async def get_audio(self) -> Optional[bytes]:
        """Get next audio chunk from simulated input."""
        if self._audio_in_queue is not None:
            try:
                return await asyncio.wait_for(
                    self._audio_in_queue.get(),
                    timeout=0.1
                )
            except asyncio.TimeoutError:
                if (
                    self._turn_done_event
                    and self._turn_done_event.is_set()
                    and self._audio_in_queue.empty()
                ):
                    self._set_speaking_cb(False)
                    self._turn_done_event.clear()
                return None
        return None

    def inject_input(self, audio_bytes: bytes) -> None:
        """Inject simulated microphone input for testing.

        Args:
            audio_bytes: Raw PCM audio data to simulate as microphone input.
        """
        if self._audio_in_queue is not None:
            try:
                self._audio_in_queue.put_nowait(audio_bytes)
            except asyncio.QueueFull:
                pass

    def get_output_buffer(self) -> bytes:
        """Get all played audio for verification in tests.

        Returns:
            Concatenated audio bytes that were 'played'.
        """
        result = b"".join(self._output_buffer)
        self._output_buffer.clear()
        return result

    async def play_loop(self) -> None:
        """Simulated playback loop."""
        while not self._shutdown_event.is_set():
            chunk = await self.get_audio()
            if chunk is None:
                await asyncio.sleep(0.01)
                continue

            if self._tts_engine_check() and self._external_audio:
                continue

            self._set_speaking_cb(True)
            self._output_buffer.append(chunk)

            if self._external_audio and self._send_audio_cb:
                try:
                    self._send_audio_cb(
                        chunk,
                        f"audio/pcm;rate={self._config.receive_sample_rate}"
                    )
                except Exception:
                    pass

    async def send_realtime_loop(self) -> None:
        """Simulated send realtime loop."""
        while not self._shutdown_event.is_set():
            if self._out_queue is None:
                return
            try:
                msg = await asyncio.wait_for(self._out_queue.get(), timeout=0.1)
                if msg is None:
                    return
                # In dummy mode, we just acknowledge
            except asyncio.TimeoutError:
                continue
            except Exception:
                return