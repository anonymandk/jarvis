# Design System

## Source of truth

`ui/theme/tokens.py` is the runtime source for JARVIS UI color palettes, type families, sizes, weights, line heights and letter spacing, layout spacing, radii, opacity, and motion. `arc_reactor` is the active palette. Existing `stealth_red`, `vibranium_purple`, `nanotech_gold`, and `platinum` preferences remain available from that same registry. Legacy `C.*` names and font calls resolve through the tokens so existing widgets keep their public compatibility surface.

`docs/ui/figma-spec.md` defines screen structure, component roles, states, and accessibility behavior. This document and the tokens retain the PRODUCT.md / Arc Reactor identity: solid dark surfaces, cyan primary actions, semantic status colors, bundled fonts, and no decorative blur. The token palette adjusts low-contrast text colors; no spec-only palette or new font is introduced.

## Arc Reactor palette

| Role | Token | Value |
|---|---|---|
| Workspace | `BG` | `#000306` |
| Primary panel | `PANEL` | `#00080f` |
| Raised surface | `DARK2` | `#000c18` |
| Structural border | `BORDER` | `#0a2535` |
| Active border | `BORDER_B` | `#1a5c7a` |
| Reactor cyan | `PRI` | `#00c8ff` |
| Energy cyan | `ENERGY` | `#00e5ff` |
| Primary text | `WHITE` | `#e8f8ff` |
| Secondary text | `TEXT_MED` | `#3a9ab0` |
| Dim text | `TEXT_DIM` | `#598691` |
| Success | `GREEN` | `#00ff88` |
| Warning | `ACC2` | `#ffb300` |
| Error | `RED` | `#ff2244` |

Text and focus combinations are checked from the token registry. Text roles target at least 4.5:1 against each declared panel, state-card, and hover surface in every theme; warning-toast and primary-button text pairs are checked separately. The primary focus boundary targets at least 3:1 against the declared surfaces. The executable `scripts/check_ui_contrast.py` reports every palette's minimum ratios, and the UI token regression tests also enforce the thresholds.

## Typography

- UI text: bundled Space Grotesk.
- Technical data: bundled JetBrains Mono.
- Semantic sizes and line heights: display 32/40, title 20/28, section 14/20, body 14/20, label 12/16, and micro 11/16.
- The token registry retains numeric legacy size aliases while older dense widgets are replaced in later UI work. New components use semantic size names.

## Spacing, radii, and motion

- Spacing scale: 4, 8, 12, 16, 24, 32, 48, and 64 px. Compatibility aliases preserve existing values during the staged desktop refactor.
- Radii: 4, 6, 8, 12, 16, and 24 px, with 999 px reserved for pill controls. Compatibility aliases preserve existing component geometry.
- Motion: fast 120 ms, normal 180 ms, state change 240 ms, and emphasis 320 ms. Standard transitions use OutQuart easing, emphasis transitions use OutCubic, and reduced motion uses Linear with no continuous animation and zero-duration transitions where practical.

## Components and layout

The orb/reactor is the primary identity element. Panels use opaque dark fills and thin structural borders. Use cyan for primary actions and focus, with amber, green, and red reserved for semantic states. The UI labels every state with text and an icon as well as color, uses `—` for unavailable values, and describes the existing unmeasured waveform as activity.

The desktop implementation follows the shared component and state model in `docs/ui/figma-spec.md`. Compact mode retains its 80×80 collapsed control and provides a separate expanded surface. Settings preserve existing graphics profiles and user preferences.

## Motion and anti-patterns

Motion marks an action or meaningful state transition. Routine idle screens do not pulse continuously. Reduced motion respects the operating system preference and the explicit setting. Avoid decorative gradients, blur, dense scanlines, hover animation on every control, repeated all-caps labels, and fictitious hardware or connection telemetry.
