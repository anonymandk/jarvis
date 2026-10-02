# F7 Documentation and Final Assurance

Status: PASS on the available Linux host. This branch remains local; no PR was pushed and hosted CI was not run.

## Delivered

- Updated the clone command to `https://github.com/anonymandk/jarvis.git`, matching the repository being maintained.
- Added embedded desktop and web screenshots to `README.md`, plus links to the UI specification, evidence indexes, and design decisions. Screenshot text identifies the test-fixture states as synthetic.
- Rewrote `DESIGN.md` around the shared `design/tokens.json` source and the current desktop/web layout, state model, accessibility, motion behavior, and runtime telemetry limits.
- Expanded `CONTRIBUTING.md` with Python installation and QA instructions, web checks, Playwright capture steps, and the staged-secret scan.
- Added `CHANGELOG.md` and F7 decisions. `PRODUCT.md` and `LICENSE` were not edited.
- Regenerated web evidence from the production build: 12 Playwright fixtures plus the separate scrolled session-log capture under `docs/ui/evidence/f5/`.

## Executed evidence

- `npm ci` in `web/` — passed; 367 packages installed from the lockfile. npm reported that the local install-script policy did not approve `unrs-resolver`'s postinstall script; typecheck, lint, production build, and browser captures all completed successfully.
- `npm run typecheck` — passed.
- `npm run lint` — passed.
- `npm run build` — passed on Next.js 16.3.1; both app routes prerendered.
- `python scripts/generate_ui_tokens.py --check` — passed; generated Python and CSS tokens match `design/tokens.json`.
- `python scripts/capture_web_ui.py` — passed; captured authentication loading/sign-in, compact onboarding, all seven states, a populated console at 980×680, and reduced motion. The script also captured the scrolled session log, rejected horizontal overflow, and verified reduced-motion scrolling. Metrics are in `docs/ui/evidence/f5/capture-metrics.json`.
- `jarvis --self-test` with this worktree on `PYTHONPATH` and QA mode enabled — **8 pass, 0 warning, 0 fail; automated health 100%**. AI/voice, messaging, system, and vision groups still require supervised live certification; no real message or desktop mutation was performed.
- `scripts/qa.py automated` — **6 checks passed, 0 failed**. The full suite reported **300 tests passed**. Source compilation, dependency consistency, contrast for all five themes, offscreen UI evidence, and tracked-secret scanning passed. Report: `.qa-artifacts/20261002-020805/qa-report.md` (ignored, not committed).
- `bash scripts/pre-commit-check.sh` — passed; no secrets found in staged changes.
- `git diff --check` and token generation check — passed.

Validation note: an initial `npm run build` from the repository root returned `ENOENT` because `package.json` is in `web/`; the build passed when rerun from `web/`. The first screenshot-dimension check used the system Python, which has no Pillow; rerunning it with the QA virtualenv confirmed all 13 committed web PNGs have the expected viewport dimensions. Direct execution of `scripts/pre-commit-check.sh` returned `Permission denied` because the file is not executable; invoking it with `bash` passed.

The automated repository audit continues to report two P2 findings: 471 broad exception handlers and nine modules importing `google-generativeai`. F6 documents why the legacy SDK remains installed and why tool behavior was not changed without approval.

## Constraints and open items

- The BlackPearl DSH `FULL_ASSURANCE` and `REALITY_CHECK` launch pipelines remain unavailable in this Linux installation. The F0 architecture report records the BOM and Windows-only path problems. Their nearest available substitutes here are the repository's full QA/self-test/web-build/screenshot commands and the read-only independent document review recorded below.
- Screenshots use deterministic fixtures; they do not demonstrate an authenticated API or live Gemini Live session. The app still lacks structured tool-call, complete error/reconnect, measured RTT, and audio-amplitude events for the UI. Unavailable values remain `—` or “atividade”.
- Windows 11 and macOS execution, physical keyboard/screen-reader review, display scaling, secondary monitors, and the four supervised self-test groups remain outstanding.
- The MIT `LICENSE` attribution/provenance discrepancy identified at F0 is unresolved. It remains unchanged as the mission directs.
- The shell-injection and dispatcher-approval behavior changes identified in F6 remain open pending user approval. `PRODUCT.md` also remains unchanged because the mission requires approval to edit it.
- The README's publishing checklist was updated to compile the current `ui/` package. Repository publication, a pull request, and remote CI were outside this local branch run.

## Independent review

**R4: PASS.** A separate read-only reviewer found no blockers. The reviewer confirmed that the clone URL and documented commands match the repository, local documentation links resolve, `DESIGN.md` names `design/tokens.json` as the generated token source, and the capture/test claims match the local artifacts. It also confirmed that the fixtures are identified as synthetic and that `PRODUCT.md` and `LICENSE` are unchanged. No review correction was required.
