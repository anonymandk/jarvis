#!/usr/bin/env python3
"""Validate text and focus contrast for each registered UI color palette."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.theme.tokens import (
    SURFACE_COLOR_KEYS,
    SPECIAL_TEXT_PAIRS,
    THEME_PALETTES,
    TEXT_COLOR_KEYS,
    contrast_failures,
    contrast_ratio,
)


def main() -> int:
    failures = contrast_failures()
    for name, palette in THEME_PALETTES.items():
        text_minimum = min(
            contrast_ratio(palette[key], palette[surface])
            for key in TEXT_COLOR_KEYS
            if key in palette
            for surface in SURFACE_COLOR_KEYS
        )
        focus_ratio = min(
            contrast_ratio(palette["PRI"], palette[surface])
            for surface in SURFACE_COLOR_KEYS
        )
        special = min(
            contrast_ratio(palette[foreground], palette[background])
            for foreground, background in SPECIAL_TEXT_PAIRS.values()
        )
        print(
            f"{name}: text min {text_minimum:.2f}:1, focus {focus_ratio:.2f}:1, "
            f"special text min {special:.2f}:1"
        )
    if failures:
        print("Contrast validation failed:\n- " + "\n- ".join(failures), file=sys.stderr)
        return 1
    print("WCAG AA text and focus contrast passed for every registered palette.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
