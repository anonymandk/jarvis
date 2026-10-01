# UI Decisions

Decisions made for the JARVIS UI mission. Dates use the repository's client timezone, America/Campo_Grande.

| Date | Decision | Reason |
|---|---|---|
| 2026-10-01 | Use both desktop and web scope, delivering desktop first. | The request's scope field is blank; this is the specified default and both surfaces are present in the repository. |
| 2026-10-01 | Use `SPEC`: PRODUCT.md controls product principles and anti-references; `docs/ui/figma-spec.md` controls layout, components, visible states, event mapping, and accessibility. | This resolves the document conflict according to the mission's default rule. |
| 2026-10-01 | Keep the Arc Reactor identity from DESIGN.md and use a single final token set in DESIGN.md plus `ui/theme/tokens.py`. Adjust individual colors when needed to meet WCAG AA; do not mix in the spec's separate palette. | Retains the existing visual identity while providing one source of runtime truth and measurable contrast. |
| 2026-10-01 | Keep bundled Space Grotesk for UI text and JetBrains Mono for technical data. Do not add Rajdhani, Orbitron, or Inter. | The repository already bundles the chosen families and their OFL licenses; no new font dependency is needed. |
| 2026-10-01 | Use solid, opaque panels and no decorative blur. Use a high-opacity dark fill only for the floating overlay, with fully opaque text and verified contrast. | Preserves the PRODUCT/DESIGN guidance against decorative glass while allowing the spec's overlay treatment. |
| 2026-10-01 | Keep the existing 80×80 orb as the collapsed quick-access state and make the spec's 420×640 surface its expanded compact overlay. | Preserves the small floating control while making the spec's compact conversation, status, tools, and input reachable. |
| 2026-10-01 | Label state with Portuguese text and an icon as well as color; show unavailable values as `—`, and label non-measured audio motion as “atividade”. | Color alone is insufficient; the current client does not emit RTT or audio amplitude and the product forbids fabricated telemetry. |
| 2026-10-01 | Keep JarvisLive, actions, hosted API, and prompt behavior unchanged. Translate only existing client calls/events in presentation adapters; document missing `tool_call`, structured `error`, `reconnecting`, RTT, and audio-level signals as follow-up requests. | Maintains the mission's engine/API boundary and prevents UI state from implying signals the backend does not provide. |
| 2026-10-01 | Honor OS reduced-motion preference and provide an explicit reduced-motion setting. Routine animation runs only for state/action transitions; the existing “low” graphics profile remains free of continuous animation. | Meets accessibility and legacy graphics-profile requirements without losing the reactor identity. |
| 2026-10-01 | Treat Linux as the available test host; do not claim Windows 11 or macOS verification without those systems. | The requested Windows 11 checks cannot be run in the current environment. |

## Still to verify during implementation

- Exact AA ratios for every final token on normal text, large text, and control boundaries.
- Keyboard tab order, accessible names, 40×40 overlay targets, and 12 px minimum log text.
- Migration of `ui_settings`, `layout_settings`, and low/medium/high graphics profiles without data loss.
- Screenshot coverage for desktop, expanded and collapsed compact states, all session states, reduced motion, and each graphics profile.
