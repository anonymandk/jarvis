#!/usr/bin/env python3
"""Generate the desktop Python and web CSS token registries from design/tokens.json."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from pprint import pformat


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "design" / "tokens.json"
PYTHON_TARGET = ROOT / "ui" / "theme" / "tokens.py"
CSS_TARGET = ROOT / "web" / "src" / "app" / "design-tokens.css"


def _key(value: str) -> str:
    return re.sub(r"_+", "-", value).lower()


def _python(data: dict) -> str:
    literal = pformat(data, width=100, sort_dicts=False)
    return f'''"""Generated from design/tokens.json by scripts/generate_ui_tokens.py."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

_DATA = {literal}

THEME_PALETTES = _DATA["palettes"]
DEFAULT_THEME = _DATA["default_theme"]
FILE_CATEGORY_COLORS = _DATA["file_category_colors"]
FONT_FAMILIES = _DATA["fonts"]
FONT_FAMILY_ALIASES = _DATA["font_family_aliases"]
FONT_FALLBACKS = _DATA["font_fallbacks"]
FONT_SIZES = {{**_DATA["font_sizes"], **{{f"legacy_{{size}}": size for size in range(*_DATA["legacy_ranges"]["font_sizes"])}}}}
FONT_LINE_HEIGHTS = _DATA["font_line_heights"]
LINE_HEIGHT_PERCENT = _DATA["line_height_percent"]
FONT_WEIGHTS = _DATA["font_weights"]
SPACING = {{**_DATA["spacing"], **{{f"legacy_{{size}}": size for size in range(*_DATA["legacy_ranges"]["spacing"])}}}}
RADII = {{**_DATA["radii"], **{{f"legacy_{{size}}": size for size in range(*_DATA["legacy_ranges"]["radii"])}}}}
LETTER_SPACING = _DATA["letter_spacing"]
OPACITY = _DATA["opacity"]
MOTION_MS = {{**_DATA["motion_ms"], **{{f"legacy_{{duration}}": duration for duration in range(*_DATA["legacy_ranges"]["motion_ms"])}}}}
MOTION_EASING = _DATA["motion_easing"]
LAYOUT_SIZES = _DATA["layout_sizes"]
TEXT_COLOR_KEYS = tuple(_DATA["text_color_keys"])
SURFACE_COLOR_KEYS = tuple(_DATA["surface_color_keys"])
SPECIAL_TEXT_PAIRS = {{name: tuple(pair) for name, pair in _DATA["special_text_pairs"].items()}}


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
                    failures.append(f"{{name}}.{{key}} is below 4.5:1 against {{surface}}")
        for surface in SURFACE_COLOR_KEYS:
            if contrast_ratio(palette["PRI"], palette[surface]) < 3.0:
                failures.append(f"{{name}}.PRI focus boundary is below 3:1 against {{surface}}")
        for label, (foreground, background) in SPECIAL_TEXT_PAIRS.items():
            if contrast_ratio(palette[foreground], palette[background]) < 4.5:
                failures.append(f"{{name}}.{{label}} text is below 4.5:1")
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
    palettes=MappingProxyType({{name: MappingProxyType(dict(palette)) for name, palette in THEME_PALETTES.items()}}),
    colors=MappingProxyType(THEME_PALETTES[DEFAULT_THEME]),
    file_category_colors=MappingProxyType(FILE_CATEGORY_COLORS),
    fonts=MappingProxyType(FONT_FAMILIES),
    font_family_aliases=MappingProxyType(FONT_FAMILY_ALIASES),
    font_fallbacks=MappingProxyType({{role: MappingProxyType(values) for role, values in FONT_FALLBACKS.items()}}),
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
'''


def _font_stack(family: str, fallback: str) -> str:
    return f'"{family} Variable", {fallback}'


def _css(data: dict) -> str:
    default = data["palettes"][data["default_theme"]]
    aliases = data["css_color_aliases"]
    lines = ["/* Generated from design/tokens.json by scripts/generate_ui_tokens.py. */", ":root {"]
    for theme, palette in data["palettes"].items():
        prefix = f"color-{_key(theme)}-"
        for key, value in palette.items():
            if key == "name":
                continue
            lines.append(f"  --{prefix}{_key(key)}: {value};")
    for name, key in aliases.items():
        lines.append(f"  --{name}: {default[key]};")
    lines.extend([
        f'  --font-family-display: {_font_stack(data["fonts"]["display"], "system-ui, sans-serif")};',
        f'  --font-family-body: {_font_stack(data["fonts"]["body"], "system-ui, sans-serif")};',
        f'  --font-family-mono: {_font_stack(data["fonts"]["mono"], "ui-monospace, monospace")};',
        f'  --font-family-emoji: "{data["fonts"]["emoji"]}", sans-serif;',
    ])
    for name, value in data["font_sizes"].items():
        lines.append(f"  --font-size-{_key(name)}: {value}px;")
    for name, value in data["font_line_heights"].items():
        lines.append(f"  --line-height-{_key(name)}: {value}px;")
    for name, value in data["font_weights"].items():
        lines.append(f"  --font-weight-{_key(name)}: {value};")
    for name, value in data["spacing"].items():
        lines.append(f"  --space-{_key(name)}: {value}px;")
    for name, value in data["radii"].items():
        lines.append(f"  --radius-{_key(name)}: {value}px;")
    for name, value in data["letter_spacing"].items():
        lines.append(f"  --tracking-{_key(name)}: {value}px;")
    for name, value in data["opacity"].items():
        lines.append(f"  --opacity-{_key(name)}: {value / 255:.4f};")
    for name, value in data["motion_ms"].items():
        lines.append(f"  --motion-{_key(name)}: {value}ms;")
    easing = {"OutQuart": "cubic-bezier(.165,.84,.44,1)", "OutCubic": "cubic-bezier(.33,1,.68,1)", "Linear": "linear"}
    for name, value in data["motion_easing"].items():
        lines.append(f"  --motion-easing-{_key(name)}: {easing[value]};")
    for name, value in data["layout_sizes"].items():
        lines.append(f"  --layout-{_key(name)}: {value}px;")
    lines.extend(["}", ""])

    for theme, palette in data["palettes"].items():
        if theme == data["default_theme"]:
            selector = f':root[data-theme="{theme}"]'
        else:
            selector = f':root[data-theme="{theme}"]'
        lines.append(f"{selector} {{")
        for name, key in aliases.items():
            lines.append(f"  --{name}: {palette[key]};")
        lines.extend(["}", ""])

    lines.extend([
        "@theme inline {",
        "  --color-background: var(--background);",
        "  --color-foreground: var(--foreground);",
        "  --color-primary: var(--primary);",
        "  --color-primary-foreground: var(--primary-foreground);",
        "  --color-secondary: var(--secondary);",
        "  --color-muted-foreground: var(--muted-foreground);",
        "  --color-border: var(--border);",
        "  --color-bright: var(--bright);",
        "  --color-input: var(--input);",
        "  --color-accent: var(--accent);",
        "  --color-ring: var(--ring);",
        "  --color-destructive: var(--destructive);",
        "  --font-sans: var(--font-family-body);",
        "  --font-mono: var(--font-family-mono);",
        "}",
        "",
    ])
    for name, value in data["file_category_colors"].items():
        lines.insert(lines.index("}") if "}" in lines else 0, f"  --file-color-{_key(name)}: {value};")
    return "\n".join(lines)


def outputs() -> dict[Path, str]:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    return {PYTHON_TARGET: _python(data), CSS_TARGET: _css(data)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files are out of date")
    args = parser.parse_args()
    stale = []
    for path, content in outputs().items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(path.relative_to(ROOT))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Generated {path.relative_to(ROOT)}")
    if stale:
        print("Generated UI tokens are stale: " + ", ".join(map(str, stale)), file=sys.stderr)
        return 1
    if args.check:
        print("Generated UI tokens match design/tokens.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
