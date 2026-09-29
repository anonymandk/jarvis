"""Audio backend factory for JARVIS.

Creates the appropriate AudioInterface implementation based on configuration.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from audio.base import AudioConfig, AudioInterface
from audio.dummy import DummyAudio
from audio.sounddevice_io import SounddeviceInputOutput
from config.settings import get_settings

if TYPE_CHECKING:
    import asyncio
    import threading


def create_audio_backend(
    backend: str = "auto",
    config: Optional[AudioConfig] = None,
    **kwargs,
) -> AudioInterface:
    """Create audio backend instance.

    Args:
        backend: One of "sounddevice", "dummy", "auto"
        config: AudioConfig instance (uses settings if None)
        **kwargs: Additional arguments passed to backend constructor

    Returns:
        AudioInterface implementation

    Raises:
        ValueError: If backend is unknown or unavailable
    """
    if backend == "auto":
        # Auto-detect: try sounddevice, fall back to dummy
        try:
            import sounddevice as sd
            # Quick check if any input device available
            devices = sd.query_devices()
            has_input = any(d.get("max_input_channels", 0) > 0 for d in devices)
            backend = "sounddevice" if has_input else "dummy"
        except Exception:
            backend = "dummy"

    if backend == "sounddevice":
        return SounddeviceInputOutput(config=config, **kwargs)
    elif backend == "dummy":
        return DummyAudio(config=config, **kwargs)
    else:
        raise ValueError(f"Unknown audio backend: {backend}")


def get_audio_backend_from_settings(**kwargs) -> AudioInterface:
    """Create audio backend from JARVIS settings.

    Reads JARVIS_AUDIO_BACKEND env var (via settings) to determine backend.
    """
    settings = get_settings()
    backend = getattr(settings.audio, "backend", "auto")
    return create_audio_backend(backend=backend, **kwargs)