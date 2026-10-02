# JARVIS Architecture and F0 Baseline

Discovery snapshot: 2026-10-01, branch `origin/main` at `1a160ec`. This document records the executable repository state used before UI implementation. The local development worktree is based on that remote branch so existing changes in the user's separate clone remain untouched.

## System boundaries

```mermaid
flowchart LR
  subgraph Runtime[Local and hosted JARVIS runtime]
    Engine[JarvisLive in main.py]
    Contract[JarvisClient Protocol in core/jarvis_client.py]
    Engine --> Contract
  end

  subgraph Desktop[Desktop adapter]
    Facade[JarvisUI facade in ui.py]
    Window[MainWindow and Qt widgets in ui.py]
    Facade --> Window
  end

  subgraph Hosted[Hosted adapter]
    API[FastAPI WebSocket route]
    WSClient[WebSocketClient]
    Hook[use-jarvis-socket.ts]
    WebUI[Next.js web client]
    API --> WSClient --> Hook --> WebUI
  end

  Contract --> Facade
  Contract --> WSClient
```

### Runtime and client contract

`main.py` owns `JarvisLive`, Gemini Live session handling, audio flow, and tool dispatch. Its constructor accepts `client: JarvisClient`, stores that object as both `self.client` and the compatibility alias `self.ui`, and installs the text-command callback. `core/jarvis_client.py` defines the transport-neutral contract used by the desktop and hosted clients.

The protocol covers state, log, subtitle, theme, graphics quality, voice display, UI commands, mute, current file, and the voice selector. The runtime also uses optional client capabilities through `getattr` (including audio output and operational readiness); those capabilities are not declared in the current Protocol and need explicit review before any contract change.

### Desktop presentation adapter

`ui.py` currently contains 9,268 lines and 44 classes. `JarvisUI` is the public desktop adapter/facade; `MainWindow` owns most window composition, while widget and overlay classes share the same module. Qt signals dispatch state, log, transcript, progress, and command updates to the UI. The current compact mode is an 80×80 floating widget.

There is no `ui/` Python package yet. `main.py`, `awareness/engine.py`, the UI tests, and `scripts/qa_ui_probe.py` import names from `ui`; `pyproject.toml` lists `ui` as a Python module. `tests/test_phase1_decoupling.py` checks that `JarvisUI` still exposes the `JarvisClient` members. These imports are compatibility constraints for the package extraction.

### Hosted API and web presentation adapter

`api/server.py` authenticates hosted WebSocket sessions, creates `WebSocketClient`, and runs `JarvisLive` in cloud-safe/external-audio mode. The adapter translates client calls to the current JSON event vocabulary: `status`, `message`, `transcript`, `transcript_clear`, `preference`, `ui_command`, `progress`, `progress_end`, `progress_hide`, and `audio`. Its event queue is bounded at 256 entries and discards the oldest entry if full.

`web/src/hooks/use-jarvis-socket.ts` receives status, ready, message, transcript, audio, progress, and error events, and sends text, mute, and audio. It does not currently handle the adapter's `preference` or `ui_command` events. The WebSocket vocabulary is not the v1 envelope in `docs/ui/figma-spec.md`; a presentation mapper belongs in the adapters and must not add Gemini or action imports to the UI.

There is no structured `tool_call` event in the current UI client contract, no confirmed reconnecting/error state from the engine, no measured RTT, and no microphone/playback level event. The visible waveform is animation rather than measured audio. Until those signals are available, render unknown values as `—` and describe visual activity as “atividade”; do not change `main.py`, actions, API behavior, or prompt to manufacture missing telemetry.

## Mission snapshot verification

| Mission claim | Verified state in this snapshot |
|---|---|
| Python 3.11+, `main.py`/`ui.py` and public client protocol | Verified: Python minimum is 3.11; `main.py` is 2,145 lines and `ui.py` is 9,268 lines/44 classes; `JarvisClient` is in `core/jarvis_client.py`. |
| Desktop and web clients both exist | Verified: PyQt6 desktop is in `ui.py`; FastAPI and Next.js clients are in `api/` and `web/`. The TypeScript, TSX, and CSS sources under `web/src/` total 789 lines. |
| UI Figma specification is available | Verified on the selected `origin/main`: `docs/ui/figma-spec.md` exists. The spec's recognition section says it did not exist on 2026-09-29; that statement is historical after the spec PR merged. |
| Main UI module dimensions | Verified: `MainWindow` spans approximately lines 6578–9035; `HudCanvas` approximately 2110–3124; compact widget is 80×80. |
| Python package compatibility | Verified: `pyproject.toml` exports `main` and `ui` as top-level modules; compatibility tests import `JarvisUI` from `ui`. |
| Current tests and CI coverage | Verified: the full unittest discovery reports 269 tests across 16 modules, including 77 UI regression tests. Python CI runs only `test_phase1_decoupling`, `test_hosted_api`, and `test_core_resilience`; web CI runs `npm ci`, typecheck, lint, and build. Desktop regression tests are not in CI. |
| Theme/font baseline | Verified: `DESIGN.md` specifies the Arc Reactor palette, Space Grotesk and JetBrains Mono; both fonts and licenses are in `assets/fonts/`; `JARVIS.spec` bundles that directory. |
| Hosted protocol matches the proposed event envelope | Not verified: current event names/shapes differ from v1 and include no structured tool-call event. |
| Cross-platform behavior is proven by this run | Not verified: baseline ran on Linux only; Windows 11 and macOS were unavailable. |

Other verified documentation drift: `README.md` still gives the clone URL for `MAL19INDUSTRIES/JARVIS-OS-V.2`, while the selected repository is `anonymandk/jarvis`. `LICENSE` is MIT with copyright attributed to Abyz. Both are report-only in this mission; `LICENSE` will not be edited.

Dependency drift: most entries in `requirements.txt` have no version bound, and `web/package.json` declares its direct dependencies as `latest` despite a committed lockfile. `requirements.txt` contains both `google-genai` and `google-generativeai`; the automated audit found live imports of the legacy SDK in nine files. F6 will determine whether those call sites can be removed without changing behavior.

## F0 execution plan

**Goal:** improve the existing JARVIS presentation surfaces while retaining engine, tool, API, and prompt behavior.

1. **F0 — Discovery and baseline:** architecture map, decisions, complete Python QA, `jarvis --self-test`, and web baseline.
2. **F1 — CI safety net:** run the complete Python suite in offscreen mode with isolated development dependencies and cache.
3. **F2 — UI package extraction:** move `ui.py` by responsibility, preserve its import surface, packaging, QA scripts, and generated screenshots/equivalence evidence.
4. **F3 — Tokens and event adapter:** consolidate tokens, enforce contrast, and map existing client calls/events to v1 without engine changes.
5. **F4 — Desktop UI:** implement spec layout, states, accessibility, compact overlay behavior, and legacy settings migration.
6. **F5 — Web UI:** align web layout and event mapping with shared tokens, pin dependencies, and capture the same states.
7. **F6 — Existing-code quality:** make only in-scope, tested fixes; audit high-impact tools before proposing behavior changes; report license ownership mismatch.
8. **F7 — Documentation and final assurance:** update docs, run complete verification, capture evidence, and report remaining platform/live checks.

Each phase is isolated on its own local branch, committed after its gate, then the next phase branches from that commit. No branch is pushed by this local workflow.

## Baseline evidence

Environment: Linux, Python 3.11.16, Node 24.21.0. Python dependencies from `requirements.txt` were installed in the worktree-local `.venv`.

| Command | Result |
|---|---|
| `QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/qa.py automated` | **3 passed, 2 failed**. Source compilation, dependency consistency, and secret scan passed. Full unittest and offscreen UI evidence failed. Report: `.qa-artifacts/20261001-164116/qa-report.md`. |
| Full QA-mode unittest discovery | **269 tests: 5 failures, 66 errors**. Errors mostly reference missing first-run-tour APIs (for example `FirstRunIntroOverlay`, intro cache/render helpers, and startup interaction gates); further test/UI mismatches are listed in the QA log. The five failures cover open-app normalization, default voice, graphics setting persistence, setup overlay centering, and generic system log filtering. Log: `.qa-artifacts/unittest-full.log`. |
| QA offscreen UI probe | **Failed** before capture because `ui.INTRO_SEQUENCE_VERSION` is absent. This prevents baseline screenshot collection through the current probe. |
| `.venv/bin/jarvis --self-test` | Direct entrypoint failed to import `scripts.self_test`; `scripts/` is not installed as a package. With `PYTHONPATH="$PWD" QT_QPA_PLATFORM=offscreen`, the self-test ran: **7 pass, 1 fail (SYSTEM)**, health 88%, with 4 supervised groups still required. Report: `.qa-artifacts/self-test-20261001T204055Z.json`. |
| Web baseline under Node 24.21.0 | `npm ci`, `npm run typecheck`, `npm run lint`, and `npm run build` all passed. Full output is preserved locally in `.qa-artifacts/web-baseline.log` (ignored, not committed). `npm ci` reported one install script not approved by the local npm policy; the production build still completed. |
| BlackPearl `CODE_ARCHAEOLOGY` launcher | **Unavailable as shipped here**: Node fails on a UTF-8 BOM at the shebang. Inspection also found Windows-only absolute paths in `dsh-team.js` and `dsh-delegate.js`. The role/skill files exist, but the configured DSH pipeline cannot run on this Linux installation without modifying its launcher/configuration. The discovery review therefore used read-only BlackPearl skill guidance and independent read-only agent inspection; no BlackPearl runtime files were changed. |

The QA audit also reported 469 broad `except Exception` handlers, legacy `google-generativeai` imports in nine runtime files, and 263 hex color literals in `ui.py`. These are findings for their scoped phases, not blanket permission for mass rewrites.

## F1 CI safety net

`.github/workflows/ci.yml` now installs runtime requirements together with the development-only `requirements-dev.txt`, caches both manifests, sets `QT_QPA_PLATFORM=offscreen`, and runs `python -m pytest -q tests` instead of the previous three-module subset. It also enables `JARVIS_QA_MODE=1` and creates a per-run workspace under `runner.temp`, matching the test harness's tool-safety isolation. The hosted API job still provisions PostgreSQL and Redis and runs Alembic migrations before tests. The web job retains its npm lockfile cache and typecheck/lint/build steps.


The first full run identified 71 pre-existing test failures: missing first-run and onboarding behavior, adaptive graphics preferences, mission empty states, and smaller UI/action mismatches. Those behaviors were implemented without changing `JarvisLive`, action effects, hosted API behavior, or the prompt. The first-run tour plays only the selected Gemini voice from a versioned local PCM cache, and readiness stays gated until the intro ends. Playback errors release that gate so setup can be retried. Fresh settings leave recurring startup greetings disabled; the older `intro_every_launch` preference is migrated only when the user explicitly enabled it. The setup guide links directly to the official AI Studio key page. The `open_app` fix now removes polite command words while translating the recognized display name back to the same platform launcher target. Two older graphics tests were updated because their former three-button/manual-only expectations conflicted with the newer regression contract for auto mode; the three actual quality profiles remain low, medium, and high.

The final local run on Linux with Python 3.11.16, `JARVIS_QA_MODE=1`, and `JARVIS_QA_WORKSPACE=.qa-artifacts/f1-qa-workspace` produced **272 passed** with one upstream deprecation warning. `scripts/qa.py automated` reported **5 passed, 0 failed**; its three P2 audit findings are the existing broad exception handling, deprecated Gemini SDK imports, and hard-coded UI colors. Offscreen UI evidence was captured under ignored artifact `.qa-artifacts/20261001-213205/`. Legacy graphics settings that already stored a profile now migrate to manual mode so auto detection cannot overwrite the user's choice, and theme refresh keeps the Auto card selected when automatic mode is active. The workflow YAML was parsed locally and checked for the full-suite and isolated-workspace steps; the staged secret scan and whitespace checks passed. The GitHub workflow has not run because this branch remains local. PostgreSQL/Redis migration execution is therefore still a remote-CI check. Final test output: ignored local artifact `.qa-artifacts/f1-full-tests.log`.

## F2 UI package extraction

`ui.py` is now the `ui/` package. `ui/__init__.py` retains the historical `import ui` surface by proxying the implementation module, while `ui/facade.py` exposes `JarvisUI` and `_RootShim`. The compatibility implementation is `ui/_runtime.py`; it owns shared application constants and composes the split widgets. The package modules are:

| Package/module | Responsibility |
|---|---|
| `ui/theme/` | Theme manager, color compatibility surface, and font setup |
| `ui/conversation/` | Chat bubbles, focus dialogue, and subtitles |
| `ui/tools/` | Tool progress, task queue, tool log, and mission control |
| `ui/notifications/` | Toasts, popups, presence notifications |
| `ui/hud/` | Orb/HUD canvas, metrics, activity visualization, graphs, and painting |
| `ui/console/` | Log panel |
| `ui/files/` | File drop zone and file display helpers |
| `ui/overlays/` | Shared overlay behavior, setup, settings, identity and voice dialogs |
| `ui/compact/` | Floating compact mode |
| `ui/vision/` | Vision preview window |
| `ui/windows/` | Main window startup, layout, settings, identity, onboarding, and interaction mixins |
| `ui/first_run.py` | First-run narration and intro rendering/cache helpers |
| `ui/facade.py` | Stable `JarvisUI` adapter over the composed Qt window |
| `ui/_runtime.py` | Shared runtime definitions, Qt signals, composition, and compatibility globals |

No widget redesign was intended in F2. Package discovery in `pyproject.toml`, compile targets in `scripts/qa.py`, source auditing in `core/qa_audit.py`, and the PyInstaller hidden-import list were updated to recognize the package. The legacy import and patching surface remains covered by the existing UI and `test_phase1_decoupling` regressions.

F2 was checked on Linux/Python 3.11.16. The full suite returned **272 passed, 1 upstream deprecation warning**; `scripts/qa.py automated` returned **5 passed, 0 failed** with the same three P2 audit findings recorded in F1. `pip install --dry-run --no-deps .` succeeded. All Python files in `ui/` are below the 800-line cap (largest: `ui/hud/paint.py`, 751 lines). The offscreen widget probe matched the F1 probe exactly at the 1280×820 and 980×680 main-window sizes and the settings graphics view: control counts, accessible names, and measured dimensions were identical. Evidence is local/ignored at `.qa-artifacts/20261001-220553/`; `test_phase1_decoupling` ran as part of the full suite. The source tree was compiled with `python -m compileall -q ui`. Remote GitHub CI and packaging on Windows/macOS remain unverified.

## F3 design tokens and event adapter

`ui/theme/tokens.py` is the central UI source for the Arc Reactor colors, retained theme presets, font families and platform fallbacks, font sizes/line heights/weights, letter spacing, spacing, radii, opacity, motion durations/easing, and established file-category icon colors. Existing QFont families, sizes, letter spacing, Qt layout spacing calls, stylesheet spacing/type/radius values, easing curves, and animation durations reference token roles or compatibility aliases that preserve their previous visual values. The semantic scale follows the UI spec; newly built components use those semantic roles.

The token contrast validator checks text-role colors against twelve declared panel, state-card, and hover surfaces in each theme at 4.5:1, plus the warning-toast and primary-button text pairs; the primary focus boundary must reach 3:1. `scripts/check_ui_contrast.py` reports each palette's minimum ratios and exits nonzero on a failure. The QA audit scans every `ui/**/*.py` file and permits hexadecimal color literals only in `ui/theme/tokens.py`; it also rejects numeric RGB/RGBA colors and imports from `actions/` or `google/` in UI modules. The token regression suite asserts these boundaries, validates all registered themes and preserved file-category colors, and guards font families, typography, spacing, radii, and motion against new raw values.

`ui/adapters/events.py` provides `JarvisEventMapper`, which wraps each event in the v1 envelope (`v`, `type`, UTC `ts`, session ID, sequence, payload). It maps known `set_state` values to the normalized state vocabulary, `show_subtitle`/`clear_subtitle` to transcript events, `You:`/`Jarvis:` log prefixes to final transcript entries, and `SYS:`/`WARN:`/`ERR:` lines to structured log levels. In the actual callback order, `clear_subtitle` opens a turn, subtitle chunks and the later `You:` log share it, and the final `Jarvis:` log closes it. Event sequencing and turn assignment are synchronized for concurrent callers. Unknown state strings produce no event. Tool, metric, and structured error events are available only through methods that require explicit caller-provided facts; the current engine does not call them.

`core/voice_catalog.py` owns the vendor-neutral voice names shared by the selector and speech engine; `actions/tts_engine.py` re-exports the same values for compatibility. The UI receives optional greeting and segmented-narration renderers through `JarvisUI`; `main.py` supplies the Gemini implementation from `core/intro_tts.py`. The UI package itself imports neither `actions/` nor Gemini, and this boundary change leaves `JarvisLive` conversation/tool behavior untouched. No `core/jarvis_client.py`, `api/`, prompt, or tool-routing behavior changed in F3.

F3 verification on Linux/Python 3.11.16: `QT_QPA_PLATFORM=offscreen python -m pytest -q tests` returned **291 passed, 1 upstream deprecated-SDK warning**. `scripts/qa.py automated` returned **6 passed, 0 failed**, with two inherited P2 findings (471 broad exception handlers and legacy `google-generativeai` imports); report: `.qa-artifacts/20261001-231838/qa-report.md`. Contrast checks passed in all five palettes (minimum normal text 4.50:1, focus 4.51:1, and special text 5.45:1). The F3 offscreen UI probe is byte-for-byte identical to F2's `.qa-artifacts/20261001-222724/ui/ui-probe.json`. `pip install --dry-run --no-deps .`, Python compilation, `git diff --check`, and the UI import/color audit passed. The R4 reviewer used all three allowed cycles; its final boundary/RGBA findings were fixed, then locally rechecked without opening a fourth independent-review cycle. Live Windows/macOS accessibility and font rendering still need those platforms.
