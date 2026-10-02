# F5 Reality Check — Web client

Status: PASS. Implementation, automated gates, and independent review are complete.

## Scope delivered

- `design/tokens.json` is the shared source for the Python token module and generated web CSS. The generator supports `--check`, and the parity tests ensure both outputs are current.
- The existing web layout now follows the shared Arc Reactor tokens and the desktop composition. Auth and onboarding copy is PT-BR, controls keep visible focus, reactor transitions are finite, and conversation scrolling uses `auto` when the browser/OS requests reduced motion.
- The socket adapter converts current status, message, transcript, progress, error, audio, and ready frames into the v1 envelope; already-versioned envelopes are validated and accepted. It does not synthesize tool calls, latency, audio level, or recoverability.
- Direct web dependencies are pinned to exact versions, and the lockfile installs cleanly.
- A stale WebSocket close/error/message can no longer replace the state of a newer socket. This was found while exercising the UI in React Strict Mode and is guarded in the hook.

## Executed evidence

- `npm ci` — passed; 367 packages installed from the lockfile.
- `npm run typecheck` — passed.
- `npm run lint` — passed.
- `npm run build` — passed on Next.js 16.3.1.
- `python scripts/generate_ui_tokens.py --check` — generated Python and CSS match `design/tokens.json`.
- `/home/darker/jarvis-worktrees/f0-baseline/.venv/bin/python -m pytest -q tests/test_ui_token_generation.py` — 2 passed.
- `/home/darker/jarvis-worktrees/f0-baseline/.venv/bin/python scripts/qa.py automated` — final run 20261002-014310: 6 checks passed, 0 failed; all 300 Python tests passed, including the offscreen UI probe and contrast audit. The detailed report is in the local ignored artifact `.qa-artifacts/20261002-014310/qa-report.md`.
- `/home/darker/jarvis-worktrees/f0-baseline/.venv/bin/python scripts/capture_web_ui.py` — 12 viewport fixtures plus a separate scrolled session-log capture. The script serves the production build, mocks API and websocket input, checks all seven state labels, checks reduced-motion CSS and verifies that a new message requests `auto` scrolling, rejects horizontal overflow, and verifies that the command field fits in the 980×680 viewport. See the [F5 evidence index](evidence/f5/README.md).

## Limits

- The Playwright API, account, progress, and state data are synthetic. No authenticated hosted API or Gemini Live session was available, so server interoperability, microphone permission, real audio, and real reconnect timing remain unverified.
- A log row in the evidence uses an explicit v1 envelope; the current hosted WebSocket sends messages and progress but does not emit the legacy `log` event.
- The web client does not surface backend `preference` or `ui_command` frames because this console has no matching settings/command surface.
- Windows 11, macOS, high-DPI scaling, and a physical screen reader/keyboard review were not available on this Linux host.
- The automated repository audit still reports 471 broad `Exception` handlers and legacy `google.generativeai` imports in nine modules. These are non-blocking F6 findings outside the web files changed here.

## Independent review

The independent finish-gate review passed on cycle 3. Cycle 1 found that JavaScript smooth-scrolling bypassed the reduced-motion CSS rule. The console now selects `auto` under the browser preference, and the production Playwright fixture delivers a message, observes its rendered count at the `scrollIntoView` call, and asserts `auto`. The reviewer confirmed that both remaining review notes were resolved and found no F5 blockers.
