"""Theme palette, typography, and runtime theme switching."""

from __future__ import annotations

import importlib

_runtime = importlib.import_module("ui._runtime")
globals().update({key: value for key, value in vars(_runtime).items() if not key.startswith("__")})

from .tokens import THEME_PALETTES, TOKENS

_UI_FONT_FALLBACK = TOKENS.font_fallbacks["ui"].get(_OS, "DejaVu Sans")
_TECH_FONT_FALLBACK = TOKENS.font_fallbacks["tech"].get(_OS, "DejaVu Sans Mono")
UI_FONT = TOKENS.fonts["body"]
TECH_FONT = TOKENS.fonts["mono"]
DISPLAY_FONT = UI_FONT
_FONTS_LOADED = False


def _load_bundled_fonts() -> tuple[str, str]:
    """Register project fonts once and retain readable native fallbacks."""
    global UI_FONT, TECH_FONT, DISPLAY_FONT, _FONTS_LOADED
    if _FONTS_LOADED:
        return UI_FONT, TECH_FONT

    resolved = {}
    for role, filename, preferred in (
        ("ui", "SpaceGrotesk-Variable.ttf", "Space Grotesk"),
        ("tech", "JetBrainsMono-Variable.ttf", "JetBrains Mono"),
    ):
        font_id = QFontDatabase.addApplicationFont(str(FONT_DIR / filename))
        families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
        if preferred in families:
            resolved[role] = preferred
        elif families:
            resolved[role] = families[0]

    UI_FONT = resolved.get("ui", _UI_FONT_FALLBACK)
    TECH_FONT = resolved.get("tech", _TECH_FONT_FALLBACK)
    DISPLAY_FONT = UI_FONT
    app = QApplication.instance()
    if app is not None:
        app.setFont(_QFont(UI_FONT, TOKENS.font_sizes["legacy_10"], _QFont.Weight.Normal))
    _FONTS_LOADED = True
    return UI_FONT, TECH_FONT


class QFont(_QFont):
    """Route legacy calls through the restrained two-family type system."""

    def __init__(self, *args):
        if args and isinstance(args[0], str):
            values = list(args)
            alias = TOKENS.font_family_aliases.get(values[0])
            is_tech = alias == "mono"
            if alias == "mono":
                values[0] = TECH_FONT
            elif alias == "body":
                values[0] = UI_FONT
            if len(values) >= 3 and values[2] in {
                _QFont.Weight.Bold, _QFont.Weight.ExtraBold, _QFont.Weight.Black,
            }:
                values[2] = _QFont.Weight.Medium if is_tech else _QFont.Weight.DemiBold
            args = tuple(values)
        super().__init__(*args)


class C:
    """Legacy color aliases; values come from the central design tokens."""


for _color_name, _color_value in TOKENS.palette().items():
    if _color_name.isupper():
        setattr(C, _color_name, _color_value)


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h); c.setAlpha(a); return c


# ---------------------------------------------------------------------------
# ThemeManager — dynamic color theming with presets
# ---------------------------------------------------------------------------

class ThemeManager:
    """Manages color themes for the JARVIS UI."""

    _COLOR_KEYS = (
        "BG", "PANEL", "PANEL2", "DARK", "DARK2", "BAR_BG", "CARD", "CARD_B",
        "BORDER", "BORDER_B", "BORDER_A", "STEEL", "PRI", "PRI_DIM", "PRI_GHO",
        "PRI_GLOW", "ENERGY", "ENERGY_D", "ACC", "ACC2", "PURPLE", "GREEN", "RED",
        "TEXT", "TEXT_DIM", "TEXT_MED", "WHITE", "WHITE_DIM", "RED_BG", "GREEN_BG",
        "PURPLE_BG", "MUTED_C", "HOLOGRAM", "AMBER", "AMBER_D", "PURPLE_D",
        "GREEN_D", "GREEN_GLO", "RED_D",
    )

    _THEMES = THEME_PALETTES

    _current = "arc_reactor"
    _listeners: list = []

    @classmethod
    def current_name(cls) -> str:
        return cls._current

    @classmethod
    def theme_names(cls) -> list[str]:
        return list(cls._THEMES.keys())

    @classmethod
    def theme_display_name(cls, key: str) -> str:
        return cls._THEMES.get(key, {}).get("name", key)

    @classmethod
    def set_theme(cls, key: str):
        if key not in cls._THEMES:
            return
        cls._current = key
        t = cls._THEMES[key]
        # Update the C class colors dynamically
        for attr in cls._COLOR_KEYS:
            if attr in t:
                setattr(C, attr, t[attr])
        # Notify listeners
        for cb in cls._listeners:
            try:
                cb(key)
            except Exception:
                pass

    @classmethod
    def add_listener(cls, cb):
        cls._listeners.append(cb)
