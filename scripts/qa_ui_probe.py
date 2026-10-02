#!/usr/bin/env python3
"""Render representative PyQt surfaces and collect accessibility metrics."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QAbstractButton, QComboBox, QLineEdit
from PyQt6.QtTest import QTest

import ui


class _NoSecrets:
    def get(self, _key):
        return None


def _metrics(widget) -> dict:
    controls = []
    seen = set()
    for kind in (QAbstractButton, QComboBox, QLineEdit):
        for control in widget.findChildren(kind):
            if id(control) not in seen:
                controls.append(control)
                seen.add(id(control))
    missing_names = []
    small_controls = []
    undersized_targets = []
    for control in controls:
        if not control.isVisible():
            continue
        label = control.accessibleName().strip()
        visible_text = getattr(control, "text", lambda: "")()
        placeholder = getattr(control, "placeholderText", lambda: "")()
        if not label and not str(visible_text or placeholder).strip():
            missing_names.append(control.metaObject().className())
        if control.width() < 24 or control.height() < 24:
            small_controls.append({
                "type": control.metaObject().className(),
                "width": control.width(),
                "height": control.height(),
            })
        if isinstance(control, QAbstractButton) and (
            control.width() < 40 or control.height() < 40
        ):
            undersized_targets.append({
                "name": label or str(visible_text or placeholder),
                "width": control.width(),
                "height": control.height(),
            })
    return {
        "controls": len(controls),
        "missing_accessible_names": missing_names,
        "controls_below_24px": small_controls,
        "buttons_below_40px": undersized_targets,
    }


def _capture(widget, path: Path, results: dict, name: str):
    QApplication.instance().processEvents()
    QTest.qWait(60)
    widget.update()
    widget.grab().save(str(path))
    results[name] = _metrics(widget)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    temp_settings = args.output / "ui-settings.json"
    temp_layout = args.output / "layout-settings.json"
    temp_api = args.output / "api-keys.json"

    patchers = [
        patch.object(ui, "UI_SETTINGS_FILE", temp_settings),
        patch.object(ui, "LAYOUT_SETTINGS_FILE", temp_layout),
        patch.object(ui, "API_FILE", temp_api),
        patch.object(ui, "get_secret_store", return_value=_NoSecrets()),
        patch.object(ui.MainWindow, "_setup_system_tray", lambda self: None),
        patch.object(ui.MainWindow, "_update_metrics", lambda self: None),
        patch.object(ui.MainWindow, "_restore_detached_panels", lambda self: None),
        patch.object(ui.MainWindow, "_start_layout_autosave", lambda self: None),
        patch.object(ui.MainWindow, "_start_auto_graphics_detection", lambda self: None),
        patch.object(
            ui.MainWindow, "_show_setup",
            lambda self: (setattr(self, "_ready", True), setattr(self, "_interaction_gated", False)),
        ),
    ]
    for patcher in patchers:
        patcher.start()
    try:
        temp_settings.write_text(json.dumps({
            "intro_completed": True,
            "intro_version": ui.INTRO_SEQUENCE_VERSION,
            "startup_greeting_enabled": False,
        }), encoding="utf-8")
        window = ui.MainWindow("face.png")
        ui.ThemeManager.set_theme("arc_reactor")
        results = {}
        screenshots = args.output / "screenshots"
        (screenshots / "desktop").mkdir(parents=True, exist_ok=True)
        (screenshots / "compact").mkdir(parents=True, exist_ok=True)
        (screenshots / "settings").mkdir(parents=True, exist_ok=True)
        window.resize(1440, 900)
        window.show()
        app.processEvents()
        _capture(window, screenshots / "desktop" / "empty-1440x900.png", results, "desktop-empty")
        window._on_motion_preference_changed("reduced")
        window._apply_state("SPEAKING")
        app.processEvents()
        _capture(window, screenshots / "desktop" / "motion-reduced.png", results, "desktop-motion-reduced")
        window._on_motion_preference_changed("system")
        window._apply_state("IDLE")

        window._navigate_to_mission_tab(0)
        window._mission.log_widget._tmr.stop()
        window._mission.log_widget._queue.clear()
        window._mission.log_widget._typing = False
        window._mission.log_widget.clear()
        window._mission.log_widget.append_log("JARVIS: Sessão pronta para mensagens.")
        QTest.qWait(480)
        _capture(window, screenshots / "desktop" / "logs-populated.png", results, "desktop-logs")
        window._navigate_to_mission_tab(3)
        _capture(window, screenshots / "desktop" / "tools-empty.png", results, "desktop-tools-empty")
        window._navigate_to_mission_tab(2)
        _capture(window, screenshots / "desktop" / "files-empty.png", results, "desktop-files-empty")
        window._navigate_to_mission_tab(1)

        window._log.append_log("You: Olá, JARVIS.")
        window._log.append_log("JARVIS: Estou pronto para ajudar.")
        QTest.qWait(420)
        _capture(window, screenshots / "desktop" / "conversation-populated.png", results, "desktop-conversation")
        window._chat_bubble.refresh_theme()
        window._chat_bubble._messages.clear()
        window._chat_bubble.refresh_theme()

        state_screens = {
            "idle": "IDLE", "listening": "LISTENING", "processing": "THINKING",
            "speaking": "SPEAKING", "reconnecting": "RECONNECTING", "error": "ERROR",
            "muted": "MUTED",
        }
        for label, state in state_screens.items():
            window._apply_state(state)
            if label == "error":
                window._connection_status.set_connection("error")
            app.processEvents()
            _capture(
                window, screenshots / "desktop" / f"state-{label}.png", results,
                f"desktop-{label}",
            )
            if label == "error":
                window._connection_status.clear_connection()

        for quality in ("low", "medium", "high"):
            window._apply_graphics_quality_live(quality)
            window._apply_state("LISTENING")
            app.processEvents()
            _capture(
                window, screenshots / "desktop" / f"graphics-{quality}.png", results,
                f"desktop-graphics-{quality}",
            )

        for toast in tuple(ui.ToastManager._toasts):
            toast._dismiss()
        ui.ToastManager._toasts.clear()
        window._chat_bubble._messages.clear()
        window._chat_bubble.refresh_theme()
        window._mission.log_widget._tmr.stop()
        window._mission.log_widget._queue.clear()
        window._mission.log_widget._typing = False
        window._mission.log_widget.clear()
        window.resize(980, 680)
        window._apply_state("IDLE")
        app.processEvents()
        _capture(window, screenshots / "desktop" / "minimum-980x680.png", results, "desktop-minimum")

        settings = ui.SettingsOverlay(
            current_graphics="medium",
            current_graphics_mode="auto",
        )
        settings.resize(600, 500)
        settings.show()
        for index, label in enumerate(("identity", "theme", "graphics-and-motion")):
            settings._switch_s_tab(index)
            app.processEvents()
            _capture(
                settings, screenshots / "settings" / f"{label}.png", results,
                f"settings-{label}",
            )
        settings.hide()
        settings.deleteLater()

        window.resize(1440, 900)
        window._apply_graphics_quality_live("medium")
        window._on_motion_preference_changed("system")
        window._apply_state("IDLE")
        window._toggle_compact_mode()
        app.processEvents()
        compact = window._compact_widget
        for label, state in state_screens.items():
            compact.set_state(state)
            app.processEvents()
            _capture(
                compact, screenshots / "compact" / f"state-{label}-420x640.png", results,
                f"compact-{label}",
            )
        compact.set_state("LISTENING")
        for index in range(5):
            compact.append_log(f"You: Mensagem {index + 1}")
        app.processEvents()
        _capture(compact, screenshots / "compact" / "three-recent-messages-420x640.png", results, "compact-three-recent-messages")
        compact.set_reduced_motion(True)
        app.processEvents()
        _capture(compact, screenshots / "compact" / "motion-reduced-420x640.png", results, "compact-motion-reduced")
        compact.close_without_restore()
        window._toggle_compact_mode()

        window.hide()
        window.deleteLater()
        app.processEvents()
        (args.output / "ui-probe.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    finally:
        for patcher in reversed(patchers):
            patcher.stop()
    print(args.output / "ui-probe.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
