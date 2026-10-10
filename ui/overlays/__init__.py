"""Setup, identity, and settings overlays for the desktop client."""

from .base import _OverlayBase
from .identity import (
    KeyTutorialOverlay,
    NameSignInOverlay,
    VoiceSelectOverlay,
    VoiceSelectorOverlay,
)
from .settings import GraphicsQualityCard, SettingsOverlay, ShortcutsOverlay
from .setup import SetupOverlay

__all__ = [
    "GraphicsQualityCard",
    "KeyTutorialOverlay",
    "NameSignInOverlay",
    "SettingsOverlay",
    "SetupOverlay",
    "ShortcutsOverlay",
    "VoiceSelectOverlay",
    "VoiceSelectorOverlay",
]
