"""Single source for JARVIS UI colors, typography, spacing, radii and motion."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

THEME_PALETTES = {'arc_reactor': {'name': 'Arc Reactor Blue',
                 'BG': '#000306',
                 'PANEL': '#00080f',
                 'PANEL2': '#000b14',
                 'DARK': '#000408',
                 'DARK2': '#000c18',
                 'BAR_BG': '#010f1a',
                 'CARD': '#00090f',
                 'CARD_B': '#000e18',
                 'BORDER': '#0a2535',
                 'BORDER_B': '#1a5c7a',
                 'BORDER_A': '#0d3a55',
                 'STEEL': '#0f2a3a',
                 'WHITE': '#e8f8ff',
                 'WHITE_DIM': '#8ab8cc',
                 'PRI': '#00c8ff',
                 'PRI_DIM': '#3589a1',
                 'PRI_GHO': '#001520',
                 'PRI_GLOW': '#00c8ff14',
                 'ENERGY': '#00e5ff',
                 'ENERGY_D': '#0088bb',
                 'ACC': '#ff8c00',
                 'ACC2': '#ffb300',
                 'PURPLE': '#7e65ff',
                 'GREEN': '#00ff88',
                 'RED': '#ff2244',
                 'TEXT': '#7ae8ff',
                 'TEXT_DIM': '#598691',
                 'TEXT_MED': '#3a9ab0',
                 'RED_BG': '#200810',
                 'GREEN_BG': '#001a0d',
                 'PURPLE_BG': '#0a0a14',
                 'MUTED_C': '#ff3366',
                 'HOLOGRAM': '#00d4ff06',
                 'AMBER': '#ffb300',
                 'AMBER_D': '#cc8800',
                 'PURPLE_D': '#3d2fa0',
                 'GREEN_D': '#00aa55',
                 'GREEN_GLO': '#00ff8810',
                 'RED_D': '#aa1133'},
 'stealth_red': {'name': 'Stealth Red',
                 'BG': '#080203',
                 'PANEL': '#0f0406',
                 'PANEL2': '#140608',
                 'DARK': '#040202',
                 'DARK2': '#180810',
                 'BAR_BG': '#1a0a10',
                 'CARD': '#0f0406',
                 'CARD_B': '#180810',
                 'BORDER': '#350a15',
                 'BORDER_B': '#7a1a2a',
                 'BORDER_A': '#550d1a',
                 'STEEL': '#3a0f1a',
                 'WHITE': '#ffe8e8',
                 'WHITE_DIM': '#cc8a8a',
                 'PRI': '#ff2244',
                 'PRI_DIM': '#b26570',
                 'PRI_GHO': '#200810',
                 'PRI_GLOW': '#ff224414',
                 'ENERGY': '#ff4466',
                 'ENERGY_D': '#bb2244',
                 'ACC': '#ff8c00',
                 'ACC2': '#ffb300',
                 'PURPLE': '#ff61a0',
                 'GREEN': '#ff6644',
                 'RED': '#ff2244',
                 'TEXT': '#ffaaaa',
                 'TEXT_DIM': '#9b7171',
                 'TEXT_MED': '#b46565',
                 'RED_BG': '#20060a',
                 'GREEN_BG': '#1a0905',
                 'PURPLE_BG': '#160710',
                 'MUTED_C': '#ff6680',
                 'HOLOGRAM': '#ff224406',
                 'AMBER': '#ffb300',
                 'AMBER_D': '#b87800',
                 'PURPLE_D': '#7a2048',
                 'GREEN_D': '#c55b4c',
                 'GREEN_GLO': '#ff664410',
                 'RED_D': '#99152a'},
 'vibranium_purple': {'name': 'Vibranium Purple',
                      'BG': '#030108',
                      'PANEL': '#06020f',
                      'PANEL2': '#080314',
                      'DARK': '#020104',
                      'DARK2': '#0c0418',
                      'BAR_BG': '#0f051a',
                      'CARD': '#06020f',
                      'CARD_B': '#0c0418',
                      'BORDER': '#250a35',
                      'BORDER_B': '#5a1a7a',
                      'BORDER_A': '#3a0d55',
                      'STEEL': '#2a0f3a',
                      'WHITE': '#f0e8ff',
                      'WHITE_DIM': '#a88acc',
                      'PRI': '#a855f7',
                      'PRI_DIM': '#9c6ac5',
                      'PRI_GHO': '#1a0530',
                      'PRI_GLOW': '#a855f714',
                      'ENERGY': '#c084fc',
                      'ENERGY_D': '#7c3aed',
                      'ACC': '#f472b6',
                      'ACC2': '#fb923c',
                      'PURPLE': '#a855f7',
                      'GREEN': '#34d399',
                      'RED': '#f43f5e',
                      'TEXT': '#d8b4fe',
                      'TEXT_DIM': '#8c76a4',
                      'TEXT_MED': '#8f62f6',
                      'RED_BG': '#210711',
                      'GREEN_BG': '#041a13',
                      'PURPLE_BG': '#160724',
                      'MUTED_C': '#fb7185',
                      'HOLOGRAM': '#a855f706',
                      'AMBER': '#fb923c',
                      'AMBER_D': '#c35d16',
                      'PURPLE_D': '#6b21a8',
                      'GREEN_D': '#189069',
                      'GREEN_GLO': '#34d39910',
                      'RED_D': '#a81f3b'},
 'nanotech_gold': {'name': 'Nanotech Gold',
                   'BG': '#050400',
                   'PANEL': '#0a0800',
                   'PANEL2': '#0e0c00',
                   'DARK': '#040300',
                   'DARK2': '#141000',
                   'BAR_BG': '#1a1500',
                   'CARD': '#0a0800',
                   'CARD_B': '#0e0c00',
                   'BORDER': '#352a0a',
                   'BORDER_B': '#7a5c1a',
                   'BORDER_A': '#553a0d',
                   'STEEL': '#3a2a0f',
                   'WHITE': '#fffae8',
                   'WHITE_DIM': '#ccb88a',
                   'PRI': '#fbbf24',
                   'PRI_DIM': '#ac7423',
                   'PRI_GHO': '#1a1000',
                   'PRI_GLOW': '#fbbf2414',
                   'ENERGY': '#fcd34d',
                   'ENERGY_D': '#d97706',
                   'ACC': '#f97316',
                   'ACC2': '#fb923c',
                   'PURPLE': '#c084fc',
                   'GREEN': '#4ade80',
                   'RED': '#ef4444',
                   'TEXT': '#fef3c7',
                   'TEXT_DIM': '#8b7f50',
                   'TEXT_MED': '#b09a3a',
                   'RED_BG': '#210907',
                   'GREEN_BG': '#061a0b',
                   'PURPLE_BG': '#140c1c',
                   'MUTED_C': '#fb7185',
                   'HOLOGRAM': '#fbbf2406',
                   'AMBER': '#fbbf24',
                   'AMBER_D': '#a16207',
                   'PURPLE_D': '#7e4aa0',
                   'GREEN_D': '#2d9154',
                   'GREEN_GLO': '#4ade8010',
                   'RED_D': '#a72c2c'},
 'platinum': {'name': 'Platinum White',
              'BG': '#e9edf2',
              'PANEL': '#f4f6f8',
              'PANEL2': '#eef1f5',
              'DARK': '#dfe4ea',
              'DARK2': '#d5dce4',
              'BAR_BG': '#d1d7df',
              'CARD': '#f8f9fb',
              'CARD_B': '#e6eaf0',
              'BORDER': '#b8c1cb',
              'BORDER_B': '#8795a4',
              'BORDER_A': '#a4afbb',
              'STEEL': '#c4ccd5',
              'WHITE': '#15202b',
              'WHITE_DIM': '#4d5d6c',
              'PRI': '#006587',
              'PRI_DIM': '#2a6479',
              'PRI_GHO': '#dcebf1',
              'PRI_GLOW': '#006f9414',
              'ENERGY': '#006584',
              'ENERGY_D': '#005f7d',
              'ACC': '#8d4d00',
              'ACC2': '#795800',
              'PURPLE': '#634fa8',
              'GREEN': '#156b45',
              'RED': '#ad2d3a',
              'TEXT': '#263746',
              'TEXT_DIM': '#535f6c',
              'TEXT_MED': '#405668',
              'RED_BG': '#f6e3e6',
              'GREEN_BG': '#dfeee6',
              'PURPLE_BG': '#e9e5f4',
              'MUTED_C': '#aa2735',
              'HOLOGRAM': '#006f9408',
              'AMBER': '#8b6500',
              'AMBER_D': '#6e5000',
              'PURPLE_D': '#493887',
              'GREEN_D': '#0f5f3b',
              'GREEN_GLO': '#18794e12',
              'RED_D': '#962432'}}

FONT_FAMILIES = {
    "display": "Space Grotesk", "body": "Space Grotesk",
    "mono": "JetBrains Mono", "emoji": "Segoe UI Emoji",
}
FONT_FAMILY_ALIASES = {
    "Arial": "body", "Sans Serif": "body", "Helvetica": "body",
    "Helvetica Neue": "body", "Avenir Next": "body",
    "Courier New": "mono", "Menlo": "mono", "Consolas": "mono",
    "Monospace": "mono",
}
FONT_FALLBACKS = {
    "ui": {"Darwin": "Helvetica Neue", "Windows": "Segoe UI", "Linux": "DejaVu Sans"},
    "tech": {"Darwin": "Menlo", "Windows": "Consolas", "Linux": "DejaVu Sans Mono"},
}
FILE_CATEGORY_COLORS = {
    "image": "#00d4ff", "video": "#ff6b00", "audio": "#cc44ff",
    "pdf": "#ff4444", "word": "#4488ff", "excel": "#44bb44",
    "code": "#ffcc00", "archive": "#ff8844", "pptx": "#ff6622",
    "text": "#aaaaaa", "data": "#88ddff", "unknown": "#888888",
}

FONT_SIZES = {
    "micro": 11, "label": 12, "caption": 12, "body": 14,
    "section": 14, "title": 20, "display": 32,
    **{f"legacy_{size}": size for size in range(1, 129)},
}

FONT_LINE_HEIGHTS = {'micro': 16, 'label': 16, 'caption': 16, 'body': 20,
                     'section': 20, 'title': 28, 'display': 40}
LINE_HEIGHT_PERCENT = {"comfortable": 160}
FONT_WEIGHTS = {'regular': 400, 'medium': 500, 'semibold': 600, 'bold': 700}

SPACING = {
    "hairline": 1, "xxs": 2, "xs": 4, "sm": 8, "md": 12,
    "lg": 16, "xl": 24, "2xl": 32, "3xl": 48, "4xl": 64,
    **{f"legacy_{size}": size for size in range(0, 513)},
}

RADII = {
    "none": 0, "xs": 3, "sm": 4, "control": 5, "md": 6,
    "lg": 8, "xl": 12, "2xl": 16, "3xl": 24, "pill": 999,
    **{f"legacy_{size}": size for size in range(0, 65)},
}

LETTER_SPACING = {
    "normal": 0.0, "tight": 0.8, "subtle": 1.0, "wide": 2.0, "tracking": 3.0,
}

MOTION_MS = {'reduced': 0,
 'fast': 120,
 'normal': 180,
 'state': 240,
 'state_transition': 1200,
 'emphasis': 320,
 'legacy_230': 230,
 'legacy_300': 300,
 'legacy_450': 450,
 **{f'legacy_{duration}': duration for duration in range(0, 2001)}}

MOTION_EASING = {"standard": "OutQuart", "emphasis": "OutCubic", "reduced": "Linear"}

LAYOUT_SIZES = {
    "desktop_width": 1440, "desktop_height": 900,
    "desktop_min_width": 980, "desktop_min_height": 680,
    "desktop_header_height": 64, "navigation_button_target": 48,
    "navigation_rail": 72, "transcript_panel": 317, "execution_panel": 317,
    "compact_width": 420, "compact_height": 640, "compact_orb": 160,
    "compact_header_action_width": 112, "compact_visualizer_width": 124,
    "compact_visualizer_height": 32, "compact_tool_summary_height": 48,
    "compact_send_button_width": 72, "compact_mute_button_width": 160,
    "control_target": 44,
}

OPACITY = {
    "close_button_tint": 15,
    "active_card": 18,
    "rail_gradient_start": 240,
    "rail_gradient_middle": 220,
    "rail_gradient_end": 230,
}

DEFAULT_THEME = "arc_reactor"
TEXT_COLOR_KEYS = (
    "WHITE", "WHITE_DIM", "TEXT", "TEXT_DIM", "TEXT_MED", "PRI", "PRI_DIM",
    "ENERGY", "ACC", "ACC2", "PURPLE", "GREEN", "GREEN_D", "RED", "MUTED_C",
)
SURFACE_COLOR_KEYS = (
    "BG", "PANEL", "PANEL2", "DARK", "DARK2", "BAR_BG", "CARD", "CARD_B", "PRI_GHO",
    "RED_BG", "GREEN_BG", "PURPLE_BG",
)
SPECIAL_TEXT_PAIRS = {
    "warning toast": ("BG", "ACC2"),
    "primary button": ("BG", "PRI"),
}


def _luminance(color: str) -> float:
    value = color.lstrip("#")[:6]
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    first, second = _luminance(foreground), _luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def contrast_failures() -> list[str]:
    """Return text or focus tokens below their WCAG contrast thresholds."""
    failures = []
    for name, palette in THEME_PALETTES.items():
        for key in TEXT_COLOR_KEYS:
            if key not in palette:
                continue
            for surface in SURFACE_COLOR_KEYS:
                if contrast_ratio(palette[key], palette[surface]) < 4.5:
                    failures.append(f"{name}.{key} is below 4.5:1 against {surface}")
        for surface in SURFACE_COLOR_KEYS:
            if contrast_ratio(palette["PRI"], palette[surface]) < 3.0:
                failures.append(f"{name}.PRI focus boundary is below 3:1 against {surface}")
        for label, (foreground, background) in SPECIAL_TEXT_PAIRS.items():
            if contrast_ratio(palette[foreground], palette[background]) < 4.5:
                failures.append(f"{name}.{label} text is below 4.5:1")
    return failures


@dataclass(frozen=True, slots=True)
class UiTokens:
    palettes: Mapping[str, Mapping[str, str]]
    colors: Mapping[str, str]
    file_category_colors: Mapping[str, str]
    fonts: Mapping[str, str]
    font_family_aliases: Mapping[str, str]
    font_fallbacks: Mapping[str, Mapping[str, str]]
    font_sizes: Mapping[str, int]
    font_line_heights: Mapping[str, int]
    line_height_percent: Mapping[str, int]
    font_weights: Mapping[str, int]
    spacing: Mapping[str, int]
    radii: Mapping[str, int]
    letter_spacing: Mapping[str, float]
    opacity: Mapping[str, int]
    motion_ms: Mapping[str, int]
    motion_easing: Mapping[str, str]
    layout_sizes: Mapping[str, int]

    def palette(self, theme_name: str = DEFAULT_THEME) -> Mapping[str, str]:
        return self.palettes.get(theme_name, self.palettes[DEFAULT_THEME])


TOKENS = UiTokens(
    palettes=MappingProxyType({name: MappingProxyType(dict(palette)) for name, palette in THEME_PALETTES.items()}),
    colors=MappingProxyType(THEME_PALETTES[DEFAULT_THEME]),
    file_category_colors=MappingProxyType(FILE_CATEGORY_COLORS),
    fonts=MappingProxyType(FONT_FAMILIES),
    font_family_aliases=MappingProxyType(FONT_FAMILY_ALIASES),
    font_fallbacks=MappingProxyType({role: MappingProxyType(values) for role, values in FONT_FALLBACKS.items()}),
    font_sizes=MappingProxyType(FONT_SIZES),
    font_line_heights=MappingProxyType(FONT_LINE_HEIGHTS),
    line_height_percent=MappingProxyType(LINE_HEIGHT_PERCENT),
    font_weights=MappingProxyType(FONT_WEIGHTS),
    spacing=MappingProxyType(SPACING),
    radii=MappingProxyType(RADII),
    letter_spacing=MappingProxyType(LETTER_SPACING),
    opacity=MappingProxyType(OPACITY),
    motion_ms=MappingProxyType(MOTION_MS),
    motion_easing=MappingProxyType(MOTION_EASING),
    layout_sizes=MappingProxyType(LAYOUT_SIZES),
)
