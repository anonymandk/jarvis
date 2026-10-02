# JARVIS Design System

JARVIS is a personal desktop AI operator with a companion hosted web console.
The interface should feel capable, focused, and present. State is easy to read,
voice and text are equally available, and repeated work stays direct after
setup.

`PRODUCT.md` defines the product principles and anti-references. The
[UI specification](docs/ui/figma-spec.md) defines the screen structure,
components, visible states, and accessibility requirements. This file records
the implemented visual system and its current limits.

## Design sources

[`design/tokens.json`](design/tokens.json) is the shared source of color,
typography, spacing, radii, motion, and layout values. Run
`python scripts/generate_ui_tokens.py` to update the Python and web outputs;
`python scripts/generate_ui_tokens.py --check` verifies that generated files
match the source. `ui/theme/tokens.py` serves the desktop client, and the
generated CSS variables serve the Next.js client. Tests enforce token parity
and the QA contrast script checks the registered palettes.

The default palette is **Arc Reactor**. The established
`stealth_red`, `vibranium_purple`, `nanotech_gold`, and `platinum` themes remain
available for existing user preferences. No new font family or runtime design
dependency is required.

## Color

The palette uses near-black surfaces, restrained blue borders, cyan for primary
actions and focus, and semantic colors for status. These values are generated
from `design/tokens.json`:

| Role | Token | Arc Reactor value |
|---|---|---|
| Workspace | `BG` | `#000306` |
| Main panel | `PANEL` | `#00080f` |
| Raised panel | `PANEL2` | `#000b14` |
| Structural border | `BORDER` | `#0a2535` |
| Active border | `BORDER_B` | `#1a5c7a` |
| Reactor cyan | `PRI` | `#00c8ff` |
| Energy cyan | `ENERGY` | `#00e5ff` |
| Main text | `WHITE` | `#e8f8ff` |
| Secondary text | `TEXT_MED` | `#3a9ab0` |
| Success | `GREEN` | `#00ff88` |
| Warning | `ACC2` | `#ffb300` |
| Error | `RED` | `#ff2244` |

Use opaque dark surfaces and thin borders. Reserve amber, green, and red for
their semantic states. Do not add decorative blur, generic dashboard cards,
unexplained alerts, or visual telemetry without a runtime source.

## Typography and geometry

- **Display and interface text:** bundled Space Grotesk.
- **Technical values, logs, and timestamps:** bundled JetBrains Mono.
- **Platform emoji fallback:** Segoe UI Emoji, followed by system fallbacks.
- **Type sizes:** micro 11 px; label/caption 12 px; body/section 14 px; title
  20 px; display 32 px. The token file pairs these with line heights from 16 to
  40 px.
- **Spacing:** shared scale from 1 and 2 px detail values through 4, 8, 12, 16,
  24, 32, 48, and 64 px.
- **Radii:** restrained 3–24 px values; 999 px is reserved for pill controls.

Desktop reference geometry is 1440×900, with a 980×680 minimum tested viewport,
a 64 px top bar, a 72 px navigation rail, and 317 px transcript and execution
panels. The compact conversation surface is 420×640. Its 160 px reactor is
accompanied by status, recent conversation, controls, and text input; the
collapsed legacy 80×80 dock is no longer the compact interaction surface.

## Desktop and web composition

The reactor is the memorable focal point. Conversation, execution, connection,
and logs remain separate so users can scan the current state and recent work
without turning the interface into a cockpit. The web client follows the same
composition using responsive layout and the shared color, type, spacing, and
motion tokens.

The PyQt desktop and Next.js web client are presentation adapters. They display
values received from the existing client contracts; they do not add Gemini or
action logic. The compact window remains a focused conversation surface, while
the main desktop and web layouts provide the fuller workspace.

## State and content

Use a visible label and icon as well as color for each state:

| State | Label |
|---|---|
| `idle` | Em espera |
| `listening` | Ouvindo |
| `processing` | Processando |
| `speaking` | Falando |
| `reconnecting` | Reconectando |
| `error` | Erro |
| `muted` | Microfone silenciado |

Use PT-BR microcopy with simple verbs and consistent names for the same action.
Errors should state what the interface observed and give the available next
step; they must not guess a cause. Show an unavailable value as `—`, never as
zero. The current waveform is animation, so call it **atividade** rather than
audio level.

The current runtime does not provide structured tool-call events, measured
Gemini round-trip latency, audio amplitude, or complete structured error and
reconnect details to both clients. A visible fixture state is evidence of the
adapter's presentation, not proof that the live service emitted that event.
Request any missing signal in the relevant phase report; do not manufacture it
inside the UI.

## Motion and accessibility

Motion marks a user action or a meaningful state transition. The token set uses
120 ms fast, 180 ms normal, 240 ms state, and 320 ms emphasis durations with
OutQuart and OutCubic easing. It does not use an idle pulse as decoration.

The reduced-motion preference respects the operating-system/browser setting
and is also available in desktop settings. It stops continuous motion and
requests immediate conversation scrolling. The low graphics profile continues
to avoid continuous animation.

The UI aims for WCAG AA text contrast and a 3:1 focus boundary; the contrast
script checks all five registered palettes and special warning/button pairs.
Keyboard focus is visible, navigation follows the rail-to-conversation-to-tools
flow, controls expose accessible names, compact targets are at least 40×40 px,
and log text stays at least 12 px.

## Evidence

- [Desktop screenshots and offscreen Qt probe](docs/ui/evidence/f4/README.md)
- [Web screenshots and Playwright capture metrics](docs/ui/evidence/f5/README.md)
- [UI specification and implementation reports](docs/ui/README.md)

Desktop states were captured with isolated offscreen fixtures. Web states use
synthetic API and WebSocket fixtures. Both collections demonstrate visual
presentation; neither represents an authenticated live session.
