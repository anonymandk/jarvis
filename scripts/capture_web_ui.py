#!/usr/bin/env python3
"""Capture reproducible web UI states using synthetic API/WebSocket fixtures."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, Playwright, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
OUTPUT = ROOT / "docs/ui/evidence/f5/screenshots"
BASE_URL = "http://127.0.0.1:3107"
API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"
STATES = ["idle", "listening", "processing", "speaking", "reconnecting", "error", "muted"]
STATE_LABELS = {
    "idle": "Em espera",
    "listening": "Ouvindo",
    "processing": "Processando",
    "speaking": "Falando",
    "reconnecting": "Reconectando",
    "error": "Erro",
    "muted": "Microfone silenciado",
}


def wait_for_server() -> subprocess.Popen[str]:
    if not (WEB / ".next/BUILD_ID").is_file():
        raise RuntimeError("Build the web app with `npm run build` before capturing evidence")
    process = subprocess.Popen(
        ["npm", "run", "start", "--", "--hostname", "127.0.0.1", "--port", "3107"],
        cwd=WEB,
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    import urllib.request

    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError(f"Next.js exited with status {process.returncode}")
        try:
            urllib.request.urlopen(BASE_URL, timeout=1).close()
            return process
        except Exception:
            time.sleep(0.5)
    process.terminate()
    raise RuntimeError("Next.js did not become ready within 60 seconds")


def mock_api(page: Page, *, configured: bool, delay_auth: float = 0) -> None:
    def handle(route: Any) -> None:
        path = route.request.url.removeprefix(API_URL)
        if path == "/auth/me":
            if delay_auth:
                time.sleep(delay_auth)
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "id": "evidence-user",
                    "email": "operador@example.test",
                    "display_name": "Operador",
                    "gemini_configured": configured,
                }),
            )
        elif path == "/actions":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"actions": [
                    {"name": "deep_research", "description": "Pesquisa aprofundada"},
                    {"name": "create_document", "description": "Criar documento"},
                    {"name": "system_status", "description": "Consultar sistema"},
                ]}),
            )
        else:
            route.fulfill(status=204, body="")

    page.route(f"{API_URL}/**", handle)


def set_session(page: Page) -> None:
    page.add_init_script("window.localStorage.setItem('jarvis_session', 'synthetic-evidence-token')")


def mock_socket(page: Page, frames: list[dict[str, Any]]) -> None:
    def handle_socket(socket: Any) -> None:
        for frame in frames:
            socket.send(json.dumps(frame))

    page.route_web_socket(f"{WS_URL}/ws?*", handle_socket)


def capture(page: Page, relative: str) -> dict[str, Any]:
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUTPUT / relative), full_page=False, animations="disabled")
    metrics = page.evaluate("({width: innerWidth, height: innerHeight, documentWidth: document.documentElement.scrollWidth, documentHeight: document.documentElement.scrollHeight})")
    if metrics["documentWidth"] > metrics["width"]:
        raise AssertionError(f"Horizontal overflow at {relative}: {metrics}")
    return metrics


def make_page(browser: Browser, width: int, height: int, reduced_motion: bool = False) -> Page:
    context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
    page = context.new_page()
    if reduced_motion:
        page.emulate_media(reduced_motion="reduce")
    return page


def run(browser: Browser) -> list[dict[str, Any]]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    evidence: list[dict[str, Any]] = []

    page = make_page(browser, 1440, 900)
    mock_api(page, configured=True, delay_auth=0.8)
    set_session(page)
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.locator(".boot-screen").wait_for()
    page.screenshot(path=str(OUTPUT / "auth-loading-1440x900.png"), full_page=False, animations="disabled")
    loading_metrics = page.evaluate("({width: innerWidth, height: innerHeight, documentWidth: document.documentElement.scrollWidth, documentHeight: document.documentElement.scrollHeight})")
    evidence.append({"name": "auth-loading", **loading_metrics})
    page.close()

    page = make_page(browser, 1440, 900)
    page.goto(BASE_URL, wait_until="networkidle")
    page.get_by_role("heading", name="Retomar sessão").wait_for()
    evidence.append({"name": "auth", **capture(page, "auth-1440x900.png")})
    page.close()

    page = make_page(browser, 420, 640)
    mock_api(page, configured=False)
    set_session(page)
    page.goto(BASE_URL, wait_until="networkidle")
    page.get_by_role("heading", name="Conecte sua camada de inteligência.").wait_for()
    evidence.append({"name": "onboarding-compact", **capture(page, "onboarding-420x640.png")})
    page.close()

    for state in STATES:
        page = make_page(browser, 1440, 900)
        mock_api(page, configured=True)
        set_session(page)
        mock_socket(page, [{"type": "status", "state": state}])
        page.goto(BASE_URL, wait_until="networkidle")
        page.get_by_role("heading", name=STATE_LABELS[state], exact=True).wait_for(timeout=10000)
        page.locator(".connection-connected").wait_for(timeout=10000)
        evidence.append({"name": f"state-{state}", **capture(page, f"state-{state}-1440x900.png")})
        page.close()

    page = make_page(browser, 980, 680)
    mock_api(page, configured=True)
    set_session(page)
    mock_socket(page, [
        {"type": "status", "state": "processing"},
        {"type": "message", "role": "user", "content": "Pesquise as atualizações do projeto."},
        {"type": "message", "role": "assistant", "content": "Encontrei três atualizações recentes."},
        {"type": "progress", "kind": "research", "label": "Pesquisa aprofundada", "percent": 66, "phase": "Analisando fontes"},
        {"v": 1, "type": "log", "ts": "2026-10-02T12:00:00Z", "session_id": "synthetic-session", "seq": 8, "payload": {"level": "info", "source": "research", "message": "Pesquisa iniciada"}},
    ])
    page.goto(BASE_URL, wait_until="networkidle")
    page.get_by_text("Analisando fontes").wait_for()
    page.get_by_text("Pesquisa iniciada").wait_for()
    page.locator(".connection-connected").wait_for(timeout=10000)
    evidence.append({"name": "populated-minimum", **capture(page, "populated-980x680.png")})
    composer = page.locator(".command-composer").bounding_box()
    if composer is None or composer["y"] + composer["height"] > 680:
        raise AssertionError(f"Command input falls below the 980×680 viewport: {composer}")
    page.locator("#session-logs").scroll_into_view_if_needed()
    page.get_by_text("Pesquisa iniciada").wait_for(state="visible")
    page.screenshot(path=str(OUTPUT / "session-logs-980x680.png"), full_page=False, animations="disabled")
    page.close()

    page = make_page(browser, 1440, 900, reduced_motion=True)
    mock_api(page, configured=True)
    set_session(page)
    page.add_init_script("""window.__jarvisScrollCalls = []; const nativeScrollIntoView = Element.prototype.scrollIntoView; Element.prototype.scrollIntoView = function(options) { window.__jarvisScrollCalls.push({behavior: typeof options === 'object' ? options.behavior : options, messageCount: document.querySelectorAll('.message').length}); return nativeScrollIntoView.call(this, options); };""")
    mock_socket(page, [
        {"type": "status", "state": "speaking"},
        {"type": "message", "role": "assistant", "content": "Mensagem com movimento reduzido."},
    ])
    page.goto(BASE_URL, wait_until="networkidle")
    page.get_by_role("heading", name="Falando", exact=True).wait_for()
    page.get_by_text("Mensagem com movimento reduzido.").wait_for()
    page.locator(".connection-connected").wait_for(timeout=10000)
    scroll_calls = page.evaluate("window.__jarvisScrollCalls")
    if not scroll_calls or scroll_calls[-1]["behavior"] != "auto" or scroll_calls[-1]["messageCount"] < 1:
        raise AssertionError(f"Reduced-motion message arrival did not request auto scrolling: {scroll_calls}")
    motion = page.locator(".reactor .orbit-a").evaluate("node => ({reduced: matchMedia('(prefers-reduced-motion: reduce)').matches, duration: getComputedStyle(node).animationDuration})")
    if not motion["reduced"] or motion["duration"] not in {"1e-05s", "0.00001s"}:
        raise AssertionError(f"Reduced-motion CSS was not applied: {motion}")
    evidence.append({"name": "reduced-motion", **capture(page, "reduced-motion-1440x900.png")})
    page.close()

    return evidence


def main() -> None:
    process = wait_for_server()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                evidence = run(browser)
            finally:
                browser.close()
        (OUTPUT.parent / "capture-metrics.json").write_text(json.dumps(evidence, indent=2) + "\n")
        print(f"Captured {len(evidence)} web UI fixtures in {OUTPUT}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    main()
