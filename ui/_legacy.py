from __future__ import annotations

import json
import hashlib
import math
import os
import platform
import random
import re
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

import psutil

from PyQt6.QtCore import (
    QEasingCurve, QEvent, QMimeData, QObject, QPointF, QPropertyAnimation,
    QRect, QRectF, QSize, Qt, QTimer, QUrl, pyqtSignal,
)

from PyQt6.QtGui import (
    QAction, QBrush, QColor, QDragEnterEvent, QDropEvent, QFont as _QFont,
    QFontDatabase, QIcon, QImage, QKeySequence, QLinearGradient, QPainter,
    QPainterPath, QPen, QPixmap, QRadialGradient, QShortcut, QDesktopServices,
)

from .first_run import (
    INTRO_CHAPTER_RENDER_ATTEMPTS, INTRO_MASTERING_VERSION,
    INTRO_PERFORMANCE_VERSION, INTRO_SAMPLE_RATE, INTRO_SEQUENCE_VERSION,
    INTRO_TTS_MODELS, INTRO_VOICE_CACHE_DIR, FirstRunIntroOverlay, IntroChapter,
    _cache_intro_voice_async, _daily_greeting, _extract_intro_pcm,
    _generate_intro_aligned_speech_pcm, _generate_intro_segmented_speech_pcm,
    _generate_intro_speech_pcm, _intro_caption_boundaries, _intro_voice_cache_path,
    _is_intro_quota_error, _load_intro_timing_cache, _master_intro_pcm,
    _pcm_duration_seconds, _play_intro_pcm, _prepare_intro_voice_cache,
    _render_intro_segments_with_live, _render_intro_with_live, _request_intro_tts,
    _tour_captions, _tour_chapters, _tour_narration, _voice_display_name,
    _write_intro_timing_cache,
)
from core.api_key_validator import ApiKeyValidationResult
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QCheckBox, QFormLayout, QFrame, QGraphicsOpacityEffect,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu, QPushButton,
    QScrollArea, QSizePolicy, QSpinBox, QSplitter, QStackedWidget, QSystemTrayIcon, QTextEdit,
    QVBoxLayout, QWidget, QProgressBar,
)

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent

BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"
FONT_DIR   = BASE_DIR / "assets" / "fonts"
UI_SETTINGS_FILE = Path.home() / ".jarvis" / "config" / "settings.json"
LAYOUT_SETTINGS_FILE = Path.home() / ".jarvis" / "config" / "layout_settings.json"

# Each profile changes both cadence and rendering density.  Keeping this data
# centralized makes the Settings UI, the renderer, and JARVIS voice commands
# agree on what Low / Medium / High actually mean.
GRAPHICS_PROFILES = {
    "low": {
        "frame_ms": 50,       # 20 FPS target
        "render_stride": 3,
        "wave_stride": 3,
        "noise_count": 0,
        "scanline_step": 8,
        "antialias": False,
        "activity_nodes": 10,
        "metrics_ms": 3500,
    },
    "medium": {
        "frame_ms": 33,       # 30 FPS target
        "render_stride": 2,
        "wave_stride": 2,
        "noise_count": 60,
        "scanline_step": 6,
        "antialias": True,
        "activity_nodes": 16,
        "metrics_ms": 2000,
    },
    "high": {
        "frame_ms": 16,       # 60 FPS target
        "render_stride": 1,
        "wave_stride": 1,
        "noise_count": 200,
        "scanline_step": 4,
        "antialias": True,
        "activity_nodes": 24,
        "metrics_ms": 1200,
    },
}

def _normalize_graphics_quality(quality: str | None) -> str:
    value = str(quality or "medium").strip().lower()
    aliases = {
        "med": "medium", "mid": "medium", "normal": "medium",
        "balanced": "medium", "performance": "low", "battery": "low",
        "max": "high", "maximum": "high", "ultra": "high",
    }
    value = aliases.get(value, value)
    if value not in GRAPHICS_PROFILES:
        raise ValueError("Graphics quality must be low, medium, or high.")
    return value

def _read_ui_settings() -> dict:
    try:
        if UI_SETTINGS_FILE.exists():
            data = json.loads(UI_SETTINGS_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}

def get_graphics_quality() -> str:
    try:
        return _normalize_graphics_quality(_read_ui_settings().get("graphics_quality", "medium"))
    except ValueError:
        return "medium"

def set_graphics_quality(quality: str) -> str:
    value = _normalize_graphics_quality(quality)
    settings = _read_ui_settings()
    settings["graphics_quality"] = value
    settings["graphics_quality_mode"] = "manual"
    UI_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    UI_SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return value

def _graphics_mode_from_settings(settings: dict) -> str:
    saved_mode = str(settings.get("graphics_quality_mode", "")).strip().lower()
    if saved_mode in {"auto", "manual"}:
        return saved_mode
    # Older releases stored a selected profile but had no auto mode. Preserve
    # that choice; only settings without any profile should use detection.
    return "manual" if "graphics_quality" in settings else "auto"

def get_graphics_mode() -> str:
    return _graphics_mode_from_settings(_read_ui_settings())

def save_auto_graphics_result(report: dict) -> str:
    """Save a device-based profile only while the user still has auto enabled."""
    quality = _normalize_graphics_quality(report.get("quality", "medium"))
    settings = _read_ui_settings()
    if _graphics_mode_from_settings(settings) == "manual":
        if "graphics_quality_mode" not in settings:
            settings["graphics_quality_mode"] = "manual"
            UI_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            UI_SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        return _normalize_graphics_quality(settings.get("graphics_quality", "medium"))
    settings["graphics_quality_mode"] = "auto"
    settings["graphics_quality"] = quality
    settings["graphics_auto_fingerprint"] = str(report.get("fingerprint", ""))
    settings["graphics_auto_report"] = dict(report)
    UI_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    UI_SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return quality

def qss_rgba(color: str, alpha: int) -> str:
    parsed = QColor(color)
    return f"rgba({parsed.red()}, {parsed.green()}, {parsed.blue()}, {max(0, min(255, int(alpha)))})"

def _load_intro_settings() -> tuple[bool, bool]:
    data = _read_ui_settings()
    version = int(data.get("intro_version", 0) or 0)
    completed = bool(data.get("intro_completed", False)) and version >= INTRO_SEQUENCE_VERSION
    # Fresh installs go straight to the console after the one-time tour. Honor
    # an explicit legacy replay preference while migrating its default to off.
    greeting = bool(data.get("startup_greeting_enabled", data.get("intro_every_launch", False)))
    return completed, greeting

def _save_intro_settings(completed: bool, greeting_enabled: bool) -> None:
    data = _read_ui_settings()
    data.pop("intro_every_launch", None)
    data["intro_completed"] = bool(completed)
    data["startup_greeting_enabled"] = bool(greeting_enabled)
    data["intro_version"] = INTRO_SEQUENCE_VERSION
    UI_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    UI_SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def route_jarvis_ui_command(command: str):
    normalized = " ".join(re.sub(r"[^a-z ]+", " ", str(command or "").lower()).split())
    patterns = (
        r"^(?:jarvis )?(?:quit|exit|close)(?: jarvis)?$",
        r"^shut yourself down$",
        r"^(?:jarvis )?turn yourself off$",
        r"^go offline(?: jarvis)?$",
    )
    return ("quit_jarvis", None) if any(re.fullmatch(pattern, normalized) for pattern in patterns) else None
VOICE_OPTIONS = [
    ("Puck",          "puck"),
    ("Charon",        "charon"),
    ("Kore",          "kore"),
    ("Fenrir",        "fenrir"),
    ("Aoede",         "aoede"),
    ("Leda",          "leda"),
    ("Orus",          "orus"),
    ("Schedar",       "schedar"),
    ("Zubenelgenubi", "zubenelgenubi"),
]
VOICE_VALUE_TO_LABEL = {value: label for label, value in VOICE_OPTIONS}
VOICE_LABEL_TO_VALUE = {label.lower(): value for label, value in VOICE_OPTIONS}

_DEFAULT_W, _DEFAULT_H = 1280, 820
_MIN_W,     _MIN_H     = 1100, 700
_LEFT_W  = 230
_RIGHT_W = 370

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"
from .theme import C, DISPLAY_FONT, QFont, TECH_FONT, ThemeManager, UI_FONT, _load_bundled_fonts, qcol

# ---------------------------------------------------------------------------
# ChatBubbleWidget — chat-style conversation view
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# FocusDialogueWidget — cinematic lower-third for the focused interface
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# ResearchProgressWidget — compact background deep-research status
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# ToastNotification — floating notification system
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# ToolProgressWidget — active tool execution indicator
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# CompactModeWidget — floating mini arc reactor
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Popup System - Contextual holographic popups orbiting the AI Core
# ---------------------------------------------------------------------------

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

# Popup configurations

# Configuration classes for customizable UI elements

# ---------------------------------------------------------------------------
# AgentGridWidget — live autonomous agent status panel
# ---------------------------------------------------------------------------

            # line_lbl hidden — no connector

# ---------------------------------------------------------------------------
# ToolLogWidget — shows tool execution history with status
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# MissionControlPanel — tabbed right panel
# ---------------------------------------------------------------------------

_FILE_ICONS = {
    "image":   ("🖼", "#00d4ff"), "video":   ("🎬", "#ff6b00"),
    "audio":   ("🎵", "#cc44ff"), "pdf":     ("📄", "#ff4444"),
    "word":    ("📝", "#4488ff"), "excel":   ("📊", "#44bb44"),
    "code":    ("💻", "#ffcc00"), "archive": ("📦", "#ff8844"),
    "pptx":    ("📊", "#ff6622"), "text":    ("📃", "#aaaaaa"),
    "data":    ("🔧", "#88ddff"), "unknown": ("📎", "#888888"),
}
_EXT_TO_CAT = {
    **dict.fromkeys(["jpg","jpeg","png","gif","webp","bmp","tiff","svg","ico"], "image"),
    **dict.fromkeys(["mp4","avi","mov","mkv","wmv","flv","webm","m4v"],         "video"),
    **dict.fromkeys(["mp3","wav","ogg","m4a","aac","flac","wma","opus"],        "audio"),
    **dict.fromkeys(["pdf"],                                                     "pdf"),
    **dict.fromkeys(["doc","docx"],                                              "word"),
    **dict.fromkeys(["xls","xlsx","ods"],                                        "excel"),
    **dict.fromkeys(["ppt","pptx"],                                              "pptx"),
    **dict.fromkeys(["py","js","ts","jsx","tsx","html","css","java","c","cpp",
                     "cs","go","rs","rb","php","swift","kt","sh","sql","lua"],   "code"),
    **dict.fromkeys(["zip","rar","tar","gz","7z","bz2","xz"],                   "archive"),
    **dict.fromkeys(["txt","md","rst","log"],                                    "text"),
    **dict.fromkeys(["csv","tsv","json","xml"],                                  "data"),
}

# ---------------------------------------------------------------------------
# Shared mixin: draggable + X-close button for all overlay widgets
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# ShortcutsOverlay — keyboard shortcuts help panel
# ---------------------------------------------------------------------------

from .overlays.base import _OverlayBase

# ---------------------------------------------------------------------------
# SettingsOverlay — unified settings panel with tabs
# ---------------------------------------------------------------------------

def _minimize_or_restore(win: QMainWindow):
    """Minimize or restore the window.

    Requirement: first press minimizes; second press restores.
    """
    if win.isMinimized():
        win.showNormal()
        win.raise_()
        win.activateWindow()
        return

    win.showMinimized()

from core.secret_store import get_secret_store

from .conversation import ChatBubbleWidget, FocusDialogueWidget, _SubtitleWidget

from .notifications import BasePopup, PopupConfig, PopupManager, POPUP_CONFIGS, PopupPriority, PopupType, PresenceSystem, ToastManager, ToastNotification
from .compact import CompactModeWidget
from .files import FileDropZone, _DropCanvas, _file_category, _fmt_size
from .console import LogWidget
from .overlays.setup import SetupOverlay
from .overlays.settings import GraphicsQualityCard, SettingsOverlay, ShortcutsOverlay
from .overlays.identity import KeyTutorialOverlay, NameSignInOverlay, VoiceSelectOverlay, VoiceSelectorOverlay
VoicePresetOverlay = VoiceSelectorOverlay
TTSProviderOverlay = VoiceSelectorOverlay
from .tools import MissionControlPanel, ResearchProgressWidget, TaskQueueWidget, ToolLogWidget, ToolProgressWidget
from .hud import AIActivityCanvas, AIActivityConfig, AgentGridWidget, HudCanvas, HudConfig, MetricBar, SparklineBar, _SysMetrics, _get_metrics
from .vision import VisionPreviewWindow
class MainWindow(QMainWindow):

    _log_sig       = pyqtSignal(str)
    _state_sig     = pyqtSignal(str)
    _voice_sig     = pyqtSignal(str)
    _sub_sig       = pyqtSignal(str)
    _sub_clear_sig = pyqtSignal()
    _sub_hold_sig  = pyqtSignal()
    _mode_sig      = pyqtSignal(str)          # context mode for AIActivityCanvas
    _task_sig      = pyqtSignal(str, str)     # (task_name, status) for TaskQueueWidget
    _tool_sig      = pyqtSignal(str)          # tool log line for ToolLogWidget
    _theme_sig     = pyqtSignal(str)
    _graphics_sig  = pyqtSignal(str)
    _vision_preview_sig = pyqtSignal(str)
    _vision_preview_hide_sig = pyqtSignal(int)
    _research_progress_sig = pyqtSignal(object)
    _research_progress_finish_sig = pyqtSignal(str, str)
    _research_progress_hide_sig = pyqtSignal()
    _presentation_progress_sig = pyqtSignal(object)
    _presentation_progress_finish_sig = pyqtSignal(str, str)
    _presentation_progress_hide_sig = pyqtSignal()
    _ui_command_sig = pyqtSignal(str)
    _intro_prepared_sig = pyqtSignal(bool, str)

    def _restore_detached_panels(self) -> None:
        """Compatibility hook for persisted panel layouts."""

    def _start_layout_autosave(self) -> None:
        """Compatibility hook for layout persistence."""

    def _start_auto_graphics_detection(self) -> None:
        """Choose a graphics profile from basic, local hardware facts."""
        if get_graphics_mode() != "auto":
            return
        QTimer.singleShot(250, self._run_auto_graphics_detection)

    def _run_auto_graphics_detection(self) -> None:
        try:
            memory_gib = psutil.virtual_memory().total / (1024 ** 3)
            cores = psutil.cpu_count(logical=True) or 1
            quality = "low" if cores <= 4 or memory_gib < 8 else (
                "high" if cores >= 8 and memory_gib >= 16 else "medium"
            )
            facts = f"{platform.system()}|{platform.machine()}|{cores}|{memory_gib:.1f}"
            report = {
                "quality": quality,
                "fingerprint": hashlib.sha256(facts.encode()).hexdigest()[:16],
                "reason": f"Recommended from {cores} logical CPU cores and {memory_gib:.0f} GB RAM.",
            }
            chosen = save_auto_graphics_result(report)
            self._graphics_quality = chosen
            profile = GRAPHICS_PROFILES[chosen]
            self.hud.set_graphics_quality(chosen)
            self._ai_canvas.set_graphics_quality(chosen)
            if self._vision_preview is not None:
                self._vision_preview.set_graphics_quality(chosen)
            self._metric_tmr.setInterval(int(profile["metrics_ms"]))
            if self._settings_overlay and self._settings_overlay.isVisible():
                self._settings_overlay.set_auto_graphics_result(chosen, report["reason"])
        except (OSError, RuntimeError, ValueError, AttributeError):
            # Keep the last valid profile if this machine does not expose facts.
            return

    def _finish_auto_graphics_detection(self, report: dict) -> None:
        if get_graphics_mode() != "auto":
            return
        quality = save_auto_graphics_result(report)
        self._apply_graphics_quality_live(quality)
        settings = _read_ui_settings()
        settings["graphics_quality_mode"] = "auto"
        UI_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        UI_SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        if self._settings_overlay and self._settings_overlay.isVisible():
            self._settings_overlay.set_auto_graphics_result(
                quality, str(report.get("reason", "Recommended for this device."))
            )

    def __init__(self, face_path: str):
        super().__init__()
        _load_bundled_fonts()
        self.setWindowTitle("J.A.R.V.I.S — MARK XXXIX")
        self.setMinimumSize(_MIN_W, _MIN_H)

        # Set dark palette so no white leaks through any unstyled widget
        from PyQt6.QtGui import QColor, QPalette
        _pal = self.palette()
        _pal.setColor(QPalette.ColorRole.Window, QColor(C.BG))
        _pal.setColor(QPalette.ColorRole.WindowText, QColor(C.WHITE))
        _pal.setColor(QPalette.ColorRole.Base, QColor(C.DARK))
        _pal.setColor(QPalette.ColorRole.AlternateBase, QColor(C.DARK2))
        _pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(C.DARK2))
        _pal.setColor(QPalette.ColorRole.ToolTipText, QColor(C.WHITE))
        _pal.setColor(QPalette.ColorRole.Text, QColor(C.WHITE))
        _pal.setColor(QPalette.ColorRole.Button, QColor(C.DARK2))
        _pal.setColor(QPalette.ColorRole.ButtonText, QColor(C.WHITE))
        _pal.setColor(QPalette.ColorRole.BrightText, QColor(C.WHITE))
        _pal.setColor(QPalette.ColorRole.Highlight, QColor(C.PRI))
        _pal.setColor(QPalette.ColorRole.HighlightedText, QColor(C.BG))
        self.setPalette(_pal)

        screen = QApplication.primaryScreen().availableGeometry()
        window_w = min(_DEFAULT_W, max(_MIN_W, screen.width()))
        window_h = min(_DEFAULT_H, max(_MIN_H, screen.height()))
        self.resize(window_w, window_h)
        self.move(
            screen.x() + max(0, (screen.width() - window_w) // 2),
            screen.y() + max(0, (screen.height() - window_h) // 2),
        )

        self.on_text_command        = None
        self.on_voice_change        = None
        self.on_name_change         = None
        self.on_tts_provider_change = None
        self.on_quit_requested      = None
        self._muted                 = False
        self._current_file: str | None = None
        self._tts_overlay: TTSProviderOverlay | None = None
        self._compact_mode          = False
        self._compact_widget: CompactModeWidget | None = None
        self._shortcuts_overlay: ShortcutsOverlay | None = None
        self._settings_overlay: SettingsOverlay | None = None
        self._vision_preview: VisionPreviewWindow | None = None
        self._force_quit            = False
        self._command_center_open   = False
        self._graphics_quality      = get_graphics_quality()
        self._settings_overlay = None

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: {C.BG}; }}
            QTextEdit, QPlainTextEdit, QTextBrowser {{
                background: {C.DARK};
                color: {C.WHITE};
                border: none;
            }}
        """)
        central = QWidget()
        central.setObjectName("jarvisRoot")
        central.setStyleSheet(f"background: {C.BG};")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setSpacing(0)
        self._header = self._build_header()
        root.addWidget(self._header)
        self._style_header()

        # Create left and right panels (we need to keep references for popup access)
        self._left_panel = self._build_left_panel()
        self._right_panel = self._build_right_panel()

        # ── AI Core area: HudCanvas, AI Activity Canvas, Subtitles ─────────────────────
        self._ai_core_wrap = QWidget()
        self._ai_core_wrap.setObjectName("aiCore")
        self._ai_core_wrap.setStyleSheet(f"background: {C.BG};")
        ai_core_lay = QVBoxLayout(self._ai_core_wrap)
        ai_core_lay.setContentsMargins(0, 0, 0, 0)
        ai_core_lay.setSpacing(6)

        # Create configuration objects
        hud_config = HudConfig()
        ai_config = AIActivityConfig()

        self.hud = HudCanvas(face_path, config=hud_config)
        self.hud.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        ai_core_lay.addWidget(self.hud, stretch=4)

        self._research_progress = ResearchProgressWidget(parent=self._ai_core_wrap)
        ai_core_lay.addWidget(self._research_progress, stretch=0)

        self._presentation_progress = ResearchProgressWidget(
            parent=self._ai_core_wrap,
            task_title="PRESENTATION",
            accessible_name="Presentation task progress",
        )
        ai_core_lay.addWidget(self._presentation_progress, stretch=0)

        # AI Activity Canvas removed for cleaner layout
        self._ai_canvas = AIActivityCanvas(config=ai_config)
        self._ai_canvas.hide()

        # Subtitles — enhanced with speaker labels
        self._subtitle = _SubtitleWidget(parent=self._ai_core_wrap)
        self._subtitle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        ai_core_lay.addWidget(self._subtitle, stretch=0)

        self._focus_dialogue = FocusDialogueWidget(parent=self._ai_core_wrap)
        self._focus_dialogue.command_submitted.connect(self._send)
        self._chat_bubble._sig.connect(self._focus_dialogue.append_log)
        ai_core_lay.addWidget(self._focus_dialogue, stretch=0)

        # Create middle section with left panel, AI core, and right panel
        middle_section = QWidget()
        middle_section.setStyleSheet(f"background: {C.BG};")
        middle_layout = QHBoxLayout(middle_section)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        middle_layout.addWidget(self._left_panel)
        middle_layout.addWidget(self._ai_core_wrap, stretch=1)
        middle_layout.addWidget(self._right_panel)

        # Replace static layout with QSplitter for draggable panels
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._left_panel)
        self._splitter.addWidget(self._ai_core_wrap)
        self._splitter.addWidget(self._right_panel)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)
        self._splitter.setSizes([150, 980, 350])
        self._splitter.setCollapsible(0, True)
        self._splitter.setCollapsible(1, False)
        self._splitter.setCollapsible(2, True)
        self._splitter.setHandleWidth(6)
        self._style_splitter()

        middle_section2 = QWidget()
        self._middle_section = middle_section2
        middle_section2.setStyleSheet(f"background: {C.BG};")
        middle_layout2 = QHBoxLayout(middle_section2)
        middle_layout2.setContentsMargins(0, 0, 0, 0)
        middle_layout2.setSpacing(0)
        middle_layout2.addWidget(self._splitter)

        # Add middle section to main layout
        root.addWidget(middle_section2, stretch=1)
        # ── Tool progress indicator (above footer) ──────────────────────────
        self._tool_progress = ToolProgressWidget()
        root.addWidget(self._tool_progress)

        self._command_bar = self._build_footer()
        self._footer_panel = self._command_bar
        root.addWidget(self._command_bar)

        # Persistent maker's mark: remains visible in both Focus View and the
        # expanded Command Center without reading as application status.
        self._maker_signature = self._build_maker_signature()
        root.addWidget(self._maker_signature)
        self._set_command_center(False, announce=False)

        self._clock_tmr = QTimer(self)
        self._clock_tmr.timeout.connect(self._tick_clock)
        self._clock_tmr.start(1000)
        self._tick_clock()

        # Metric update timer
        self._metric_tmr = QTimer(self)
        self._metric_tmr.timeout.connect(self._update_metrics)
        self._metric_tmr.start(int(GRAPHICS_PROFILES[self._graphics_quality]["metrics_ms"]))
        self._update_metrics()

        self._log_sig.connect(self._log.append_log)
        self._state_sig.connect(self._apply_state)
        self._voice_sig.connect(self._sync_voice_combo)
        self._sub_sig.connect(self._subtitle.set_text)
        self._sub_clear_sig.connect(self._subtitle.clear_subtitle)
        self._sub_hold_sig.connect(self._subtitle.start_hold_timer)
        self._mode_sig.connect(self._ai_canvas.set_mode)
        self._task_sig.connect(self._mission.task_widget.push_task)
        self._tool_sig.connect(self._mission.tool_widget.push)
        self._theme_sig.connect(ThemeManager.set_theme)
        self._graphics_sig.connect(self._apply_graphics_quality_live)
        self._vision_preview_sig.connect(self._show_vision_preview)
        self._vision_preview_hide_sig.connect(self._hide_vision_preview)
        self._research_progress_sig.connect(lambda update: self._research_progress.update_progress(**update))
        self._research_progress_finish_sig.connect(self._research_progress.finish)
        self._research_progress_hide_sig.connect(self._research_progress.dismiss)
        self._presentation_progress_sig.connect(
            lambda update: self._presentation_progress.update_progress(**update)
        )
        self._presentation_progress_finish_sig.connect(self._presentation_progress.finish)
        self._presentation_progress_hide_sig.connect(self._presentation_progress.dismiss)
        self._ui_command_sig.connect(self._handle_ui_command)
        self._intro_prepared_sig.connect(self._on_intro_voice_prepared)

        # ── Popup System Initialization ────────────────────────────────────────
        self._popup_manager = PopupManager(self._ai_core_wrap)
        self._presence_system = PresenceSystem(self._popup_manager)
        # Context mode tracking
        self._context_mode = "idle"
        self._session_start = time.time()

        self._overlay: SetupOverlay | None = None
        self._name_overlay: NameSignInOverlay | None = None
        self._voice_overlay: VoiceSelectOverlay | None = None
        self._tts_overlay: TTSProviderOverlay | None = None
        self.on_voice_change = None
        self.on_tts_provider_change = None
        self._load_saved_voice()
        self._load_saved_tts()

        # ── System tray integration ──────────────────────────────────────────
        self._setup_system_tray()

        # ── Theme manager listener ───────────────────────────────────────────
        ThemeManager.add_listener(self._on_theme_changed)
        # Load saved theme on boot
        try:
            from pathlib import Path
            import json
            cfg_file = Path.home() / ".jarvis" / "config" / "settings.json"
            if cfg_file.exists():
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                saved_theme = cfg.get("theme", "")
                if saved_theme and saved_theme in ThemeManager.theme_names():
                    ThemeManager.set_theme(saved_theme)
        except Exception:
            pass

        # Every key source uses the same Gemini verification gate. Environment
        # variables and remembered keys are never trusted merely because they
        # were present on an earlier run.
        self._ready = False
        completed, greeting_enabled = _load_intro_settings()
        self._intro_should_play = not completed or greeting_enabled
        self._startup_sequence_kind = "tour" if not completed else ("greeting" if greeting_enabled else "")
        self._startup_chapters: tuple[IntroChapter, ...] = ()
        self._startup_captions: tuple[str, ...] = ()
        self._startup_narration = ""
        self._intro_overlay: FirstRunIntroOverlay | None = None
        self._intro_focus_key = ""
        self._intro_in_progress = False
        self._intro_voice_preparing = False
        self._interaction_gated = True
        self._manual_tour_replay = False
        self._pending_ready_after_intro = False
        self._pending_greeting_enabled = greeting_enabled
        self._ready_announced = False
        self._intro_live_groups: list[dict] = []
        self._intro_original_tab = 0
        self._intro_presence_was_active = False
        self.on_tour_state_change = None
        candidate_key = os.environ.get("GEMINI_API_KEY", "").strip()
        candidate_is_saved = False
        try:
            if not candidate_key:
                store = get_secret_store()
                saved = store.get("gemini_api_key")
                if saved:
                    candidate_key = saved.strip()
                    candidate_is_saved = True
        except Exception:
            candidate_key = ""
            candidate_is_saved = False

        self._show_setup()
        self._start_auto_graphics_detection()
        if candidate_key and self._overlay:
            self._overlay.validate_candidate(
                candidate_key,
                remember_key=candidate_is_saved,
                purge_saved_on_failure=candidate_is_saved,
            )

        sc_mute = QShortcut(QKeySequence("F4"), self)
        sc_mute.activated.connect(self._toggle_mute)
        sc_full = QShortcut(QKeySequence("F11"), self)
        sc_full.activated.connect(self._toggle_fullscreen)
        sc_min = QShortcut(QKeySequence(Qt.Key.Key_F6), self)
        sc_min.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc_min.activated.connect(lambda: _minimize_or_restore(self))

        # New shortcuts
        sc_help = QShortcut(QKeySequence("Ctrl+/"), self)
        sc_help.activated.connect(self._toggle_shortcuts_overlay)
        sc_compact = QShortcut(QKeySequence("Ctrl+M"), self)
        sc_compact.activated.connect(self._toggle_compact_mode)
        sc_theme = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
        sc_theme.activated.connect(self._cycle_theme)
        sc_command = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        sc_command.activated.connect(
            lambda: self._set_command_center(not self._command_center_open)
        )
        sc_esc = QShortcut(QKeySequence("Escape"), self)
        sc_esc.activated.connect(self._dismiss_overlays)

        # Shortcuts to show panel content as popups
        sc_show_left = QShortcut(QKeySequence("L"), self)
        sc_show_left.activated.connect(self._show_left_panel_popup)
        sc_show_right = QShortcut(QKeySequence("R"), self)
        sc_show_right.activated.connect(self._show_right_panel_popup)
    def closeEvent(self, event):
        # Minimize to tray instead of quitting (if tray is available)
        try:
            if hasattr(self, "_tray") and self._tray.isVisible() and not getattr(self, "_force_quit", False):
                event.ignore()
                if self._vision_preview is not None:
                    self._vision_preview.stop()
                self.hide()
                self._tray.showMessage(
                    "JARVIS", "Running in background. Click tray icon to restore.",
                    QSystemTrayIcon.MessageIcon.Information, 2000
                )
                return
        except Exception:
            pass
        if self._vision_preview is not None:
            self._vision_preview.stop()
        event.accept()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    # ── System tray ──────────────────────────────────────────────────────
    def _setup_system_tray(self):
        self._force_quit = False
        self._tray = QSystemTrayIcon(self)
        # Create a simple icon programmatically
        px = QPixmap(32, 32)
        px.fill(QColor(0, 0, 0, 0))
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(qcol(C.PRI), 2))
        p.drawEllipse(4, 4, 24, 24)
        p.setBrush(QBrush(qcol(C.ENERGY)))
        p.drawEllipse(10, 10, 12, 12)
        p.end()
        self._tray.setIcon(QIcon(px))
        self._tray.setToolTip("J.A.R.V.I.S — MARK XXXIX")

        tray_menu = QMenu()
        tray_menu.setStyleSheet(f"""
            QMenu {{
                background: {C.PANEL}; color: {C.WHITE};
                border: 1px solid {C.BORDER};
            }}
            QMenu::item:selected {{ background: {C.PRI_GHO}; color: {C.PRI}; }}
        """)

        show_action = QAction("Show JARVIS", self)
        show_action.triggered.connect(self._tray_show)
        tray_menu.addAction(show_action)

        mute_action = QAction("Toggle Mute", self)
        mute_action.triggered.connect(self._toggle_mute)
        tray_menu.addAction(mute_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit JARVIS", self)
        quit_action.triggered.connect(self._tray_quit)
        tray_menu.addAction(quit_action)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.show()

    def _tray_show(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _tray_quit(self):
        self._request_quit()

    def _request_quit(self):
        """Use one clean shutdown path for tray, UI, and JARVIS self-quit."""
        self._force_quit = True
        try:
            if self.on_quit_requested:
                self.on_quit_requested()
        except Exception as exc:
            self._log.append_log(f"ERR: Shutdown cleanup — {exc}")
        try:
            if hasattr(self, "_tray"):
                self._tray.hide()
        except Exception:
            pass
        self.close()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self._tray_show()

    # ── Compact mode ─────────────────────────────────────────────────────
    def _toggle_compact_mode(self):
        if self._compact_mode:
            # Restore from compact
            if self._compact_widget:
                self._compact_widget.hide()
                self._compact_widget.deleteLater()
                self._compact_widget = None
            self.showNormal()
            self.raise_()
            self._compact_mode = False
        else:
            # Enter compact mode
            self._compact_mode = True
            self.hide()
            cw = CompactModeWidget()
            cw.expand_requested.connect(self._toggle_compact_mode)
            # Position near center of screen
            screen = QApplication.primaryScreen().availableGeometry()
            cw.move(screen.width() - 100, screen.height() // 2 - 40)
            cw.show()
            self._compact_widget = cw
            # Sync state
            if hasattr(self, "hud"):
                cw.set_state(self.hud.state)

    # ── Shortcuts overlay ────────────────────────────────────────────────
    def _toggle_shortcuts_overlay(self):
        if self._shortcuts_overlay and self._shortcuts_overlay.isVisible():
            self._shortcuts_overlay.hide()
            return
        cw = self.centralWidget()
        ov = ShortcutsOverlay(cw)
        ow, oh = 420, 380
        ov.setGeometry(
            (cw.width() - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.show()
        self._shortcuts_overlay = ov

    # ── Settings overlay ─────────────────────────────────────────────────
    def _show_settings(self):
        if self._settings_overlay and self._settings_overlay.isVisible():
            self._settings_overlay.hide()
            return
        # Get current name
        current_name = ""
        try:
            from memory.memory_manager import load_memory
            memory = load_memory()
            name_entry = memory.get("identity", {}).get("name")
            if isinstance(name_entry, dict):
                current_name = name_entry.get("value", "")
            elif isinstance(name_entry, str):
                current_name = name_entry
        except Exception:
            pass

        cw = self.centralWidget()
        ov = SettingsOverlay(
            cw,
            current_name=current_name,
            current_theme=ThemeManager.current_name(),
            current_graphics=self._graphics_quality,
            current_graphics_mode=get_graphics_mode(),
            replay_intro=_load_intro_settings()[1],
        )
        ow, oh = 560, 410
        ov.setGeometry(
            (cw.width() - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.name_changed.connect(self._on_settings_name)
        ov.theme_changed.connect(self._on_settings_theme)
        ov.graphics_changed.connect(self._on_settings_graphics)
        ov.graphics_mode_changed.connect(self._on_settings_graphics_mode)
        ov.intro_replay_changed.connect(self._on_intro_replay_changed)
        ov.tour_replay_requested.connect(self._request_manual_tour_replay)
        ov.show()
        self._settings_overlay = ov

    def _on_settings_name(self, name: str):
        if name:
            self._on_name_done(name)

    def _on_settings_theme(self, key: str):
        ThemeManager.set_theme(key)

    def _on_settings_graphics(self, quality: str):
        self._apply_graphics_quality_live(quality)

    def _on_settings_graphics_mode(self, mode: str):
        settings = _read_ui_settings()
        settings["graphics_quality_mode"] = "auto" if mode == "auto" else "manual"
        UI_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        UI_SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        if mode == "auto":
            self._start_auto_graphics_detection()

    def _on_intro_replay_changed(self, enabled: bool):
        settings = _read_ui_settings()
        settings.pop("intro_every_launch", None)
        settings["startup_greeting_enabled"] = bool(enabled)
        settings["intro_version"] = INTRO_SEQUENCE_VERSION
        UI_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        UI_SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        self._pending_greeting_enabled = bool(enabled)

    def _show_vision_preview(self, source: str):
        if self._vision_preview is None:
            self._vision_preview = VisionPreviewWindow(self.centralWidget())
        self._vision_preview.set_graphics_quality(self._graphics_quality)
        self._vision_preview.start(source)

    def _hide_vision_preview(self, delay_ms: int = 1800):
        if self._vision_preview is not None:
            self._vision_preview.finish(delay_ms)

    def _apply_graphics_quality_live(self, quality: str):
        """Persist and apply a graphics profile to every active renderer."""
        value = set_graphics_quality(quality)
        self._graphics_quality = value
        profile = GRAPHICS_PROFILES[value]

        if hasattr(self, "hud"):
            self.hud.set_graphics_quality(value)
        if hasattr(self, "_ai_canvas"):
            self._ai_canvas.set_graphics_quality(value)
        if hasattr(self, "_metric_tmr"):
            self._metric_tmr.setInterval(int(profile["metrics_ms"]))
        if self._vision_preview is not None:
            self._vision_preview.set_graphics_quality(value)
        if self._settings_overlay:
            self._settings_overlay._current_graphics = value
            self._settings_overlay._highlight_graphics(value)

        if hasattr(self, "_log"):
            self._log.append_log(f"SYS: Graphics quality set to {value.upper()}.")
        if hasattr(self, "_popup_manager"):
            self._show_toast(f"Graphics quality: {value.upper()}", "success")

    # ── Theme cycling ────────────────────────────────────────────────────
    def _cycle_theme(self):
        try:
            names = ThemeManager.theme_names()
            cur = ThemeManager.current_name()
            idx = names.index(cur) if cur in names else 0
            next_key = names[(idx + 1) % len(names)]
            ThemeManager.set_theme(next_key)
            display = ThemeManager.theme_display_name(next_key)
            ToastManager.show_toast(self.centralWidget(),
                                    f"Theme: {display}", "info", 2000)
        except Exception:
            pass

    def _on_theme_changed(self, key: str):
        """Apply a selected theme immediately across the visible interface."""
        from PyQt6.QtGui import QPalette

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(C.BG))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(C.WHITE))
        palette.setColor(QPalette.ColorRole.Base, QColor(C.DARK))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(C.DARK2))
        palette.setColor(QPalette.ColorRole.Text, QColor(C.WHITE))
        palette.setColor(QPalette.ColorRole.Button, QColor(C.PANEL2))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(C.WHITE))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(C.PRI))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(C.BG))
        self.setPalette(palette)
        self.setStyleSheet(f"""
            QMainWindow {{ background: {C.BG}; }}
            QTextEdit, QPlainTextEdit, QTextBrowser {{
                background: {C.DARK}; color: {C.WHITE}; border: none;
            }}
        """)
        if self.centralWidget():
            self.centralWidget().setStyleSheet(f"QWidget#jarvisRoot {{ background: {C.BG}; }}")
        if hasattr(self, "_middle_section"):
            self._middle_section.setStyleSheet(f"background: {C.BG};")
        if hasattr(self, "_ai_core_wrap"):
            self._ai_core_wrap.setStyleSheet(f"QWidget#aiCore {{ background: {C.BG}; }}")
        if hasattr(self, "_left_panel"):
            self._left_panel.setStyleSheet(f"""
                QWidget#leftRail {{
                    background: {C.PANEL}; border-right: 1px solid {C.STEEL};
                }}
            """)
        if hasattr(self, "_right_panel"):
            self._right_panel.setStyleSheet(f"""
                QWidget#rightRail {{
                    background: {C.PANEL}; border-left: 1px solid {C.BORDER};
                }}
            """)
        if hasattr(self, "_command_bar"):
            self._style_command_rail()

        self._style_header()
        self._style_splitter()
        self._style_left_nav()
        self._style_command_controls()
        self._style_maker_signature()
        self._update_theme_btn()
        if hasattr(self, "_mission"):
            self._mission.refresh_theme()
        if hasattr(self, "_focus_dialogue"):
            self._focus_dialogue.refresh_theme()
        if hasattr(self, "_research_progress"):
            self._research_progress.refresh_theme()
        if hasattr(self, "_subtitle"):
            self._subtitle._done_col = qcol(C.TEXT)
            self._subtitle._active_col = qcol(C.PRI)
        if self._settings_overlay:
            self._settings_overlay.refresh_theme()
        if self._vision_preview is not None:
            self._vision_preview.refresh_theme()

        for spark, color in (
            (getattr(self, "_spark_cpu", None), C.PRI),
            (getattr(self, "_spark_mem", None), C.ENERGY),
            (getattr(self, "_spark_net", None), C.ACC2),
            (getattr(self, "_spark_tmp", None), C.ACC),
        ):
            if spark is not None:
                spark._color = color

        for widget in self.findChildren(QWidget):
            widget.update()

        try:
            settings_dir = Path.home() / ".jarvis" / "config"
            settings_dir.mkdir(parents=True, exist_ok=True)
            settings_file = settings_dir / "settings.json"
            try:
                settings = json.loads(settings_file.read_text(encoding="utf-8")) if settings_file.exists() else {}
            except Exception:
                settings = {}
            settings["theme"] = key
            settings_file.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _handle_ui_command(self, action: str):
        action = str(action or "").strip().lower()
        if action in {"quit jarvis", "quit_jarvis"}:
            self._request_quit()
            return True
        if action == "open_command_center":
            self._set_command_center(True)
            return True
        if action == "close_command_center":
            self._set_command_center(False)
            return True
        handlers = {
            "open_settings": self._show_settings,
            "compact_mode": self._toggle_compact_mode,
            "fullscreen": self._toggle_fullscreen,
            "show_shortcuts": self._toggle_shortcuts_overlay,
        }
        handler = handlers.get(action)
        if handler:
            handler()
            return True
        return False

    def _set_command_center(self, is_open: bool, announce: bool = True):
        """Switch between the focused conversation and full control surface."""
        was_open = bool(getattr(self, "_command_center_open", False))
        self._command_center_open = bool(is_open)
        self._command_transition_id = getattr(self, "_command_transition_id", 0) + 1
        transition_id = self._command_transition_id
        if hasattr(self, "_mission"):
            self._mission.set_command_center_open(is_open)
        if hasattr(self, "_right_panel"):
            self._right_panel.setFixedWidth(_RIGHT_W)
            self._right_panel.setVisible(is_open)
        if hasattr(self, "_focus_dialogue"):
            self._focus_dialogue.setVisible(not is_open)
        if hasattr(self, "_splitter"):
            if is_open:
                self._splitter.setSizes([_LEFT_W, max(420, self.width() - _LEFT_W - _RIGHT_W), _RIGHT_W])
            else:
                self._splitter.setSizes([0, max(720, self.width()), 0])

        reveal_widgets = [
            getattr(self, "_header", None),
            getattr(self, "_left_panel", None),
            getattr(self, "_right_panel", None),
            getattr(self, "_command_bar", None),
        ]
        if is_open:
            for widget in reveal_widgets:
                if widget is not None:
                    widget.show()
            if not was_open:
                for delay, widget in zip((0, 90, 180, 270), reveal_widgets):
                    if widget is not None:
                        self._reveal_widget(widget, delay, transition_id)
        else:
            for widget in reveal_widgets:
                if widget is not None:
                    widget.hide()
            if hasattr(self, "_focus_dialogue") and was_open:
                self._reveal_widget(self._focus_dialogue, 80, transition_id)

        if hasattr(self, "_tool_progress"):
            if is_open and self._tool_progress._tmr.isActive():
                self._tool_progress.show()
            elif not is_open:
                self._tool_progress.hide()
        if announce and hasattr(self, "_popup_manager"):
            self._show_toast(
                "Command Center open" if is_open else "Focus view restored",
                "info",
            )
        if announce and is_open and not was_open:
            self._announce_command_center_modules()

    def _reveal_widget(self, widget: QWidget, delay_ms: int = 0, transition_id: int | None = None):
        """Reveal a module with a short, stagger-friendly opacity transition."""
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(230)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutQuart)
        self._command_reveal_animations = getattr(self, "_command_reveal_animations", [])
        self._command_reveal_animations.append(animation)

        def _finish():
            if widget.graphicsEffect() is effect:
                widget.setGraphicsEffect(None)
            try:
                self._command_reveal_animations.remove(animation)
            except ValueError:
                pass

        animation.finished.connect(_finish)

        def _start():
            if (
                transition_id is not None
                and transition_id != getattr(self, "_command_transition_id", transition_id)
            ):
                _finish()
                return
            animation.start()

        QTimer.singleShot(max(0, int(delay_ms)), _start)

    def _announce_command_center_modules(self):
        announcement = (
            "Command Center online. Status header ready. System overview ready. "
            "Mission control ready. Command rail ready."
        )
        if self.on_text_command:
            prompt = (
                "[UI EVENT] The Command Center modules are appearing now. "
                f'Say exactly: "{announcement}"'
            )
            threading.Thread(target=self.on_text_command, args=(prompt,), daemon=True).start()
        else:
            self._log.append_log(f"JARVIS: {announcement}")

    def _toggle_left_panel(self):
        sizes = self._splitter.sizes()
        if sizes[0] > 10:
            self._left_target_w = sizes[0]
            self._splitter.setSizes([0, sizes[1] + sizes[0], sizes[2]])
        else:
            self._splitter.setSizes([self._left_target_w, sizes[1] - self._left_target_w, sizes[2]])

    def _toggle_right_panel(self):
        sizes = self._splitter.sizes()
        if sizes[2] > 10:
            self._right_target_w = sizes[2]
            self._splitter.setSizes([sizes[0], sizes[1] + sizes[2], 0])
        else:
            self._splitter.setSizes([sizes[0], sizes[1] - self._right_target_w, self._right_target_w])

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Left and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._toggle_left_panel()
        elif event.key() == Qt.Key.Key_Right and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._toggle_right_panel()
        else:
            super().keyPressEvent(event)

    def _dismiss_overlays(self):
        for ov in (self._shortcuts_overlay, self._settings_overlay):
            if ov and ov.isVisible():
                ov.hide()
                return

    # ── Toast helper ─────────────────────────────────────────────────────
    def _show_toast(self, message: str, toast_type: str = "info"):
        try:
            ToastManager.show_toast(self.centralWidget(), message, toast_type)
        except Exception:
            pass

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cw = self.centralWidget()
        if getattr(self, "_startup_backdrop", None) is not None:
            self._startup_backdrop.setGeometry(cw.rect())
        if self._overlay and self._overlay.isVisible():
            self._overlay._center_in_parent()
        if getattr(self, "_intro_overlay", None) is not None:
            self._intro_overlay.setGeometry(cw.rect())
        if self._name_overlay and self._name_overlay.isVisible():
            ow, oh = 420, 310
            self._name_overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )
        if hasattr(self, "_voice_overlay") and self._voice_overlay and self._voice_overlay.isVisible():
            ow, oh = 420, 380
            self._voice_overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )

    def _update_metrics(self):
        snap = _get_metrics()
        if hasattr(snap, "snapshot"):
            snap = snap.snapshot()
        if not isinstance(snap, dict):
            snap = {}

        # CPU
        cpu = float(snap.get("cpu", -1.0))
        if cpu <= 0:
            try:
                import psutil as _psu
                cpu = _psu.cpu_percent(interval=None)
            except Exception:
                cpu = 0.0
        self._bar_cpu.set_value(cpu, "{:.0f}%".format(cpu))
        if hasattr(self, '_spark_cpu'):
            self._spark_cpu.set_value("{:.0f}".format(cpu), cpu / 100.0, "%")

        # MEM
        mem = float(snap.get("mem", -1.0))
        if mem <= 0:
            try:
                import psutil as _psu
                mem = _psu.virtual_memory().percent
            except Exception:
                mem = 0.0
        self._bar_mem.set_value(mem, "{:.0f}%".format(mem))
        if hasattr(self, '_spark_mem'):
            self._spark_mem.set_value("{:.0f}".format(mem), mem / 100.0, "%")

        # NET
        net = float(snap.get("net", -1.0))
        if net < 0:
            net_str = "N/A"
            net_pct = 0
            self._bar_net.set_value(net_pct, net_str)
            if hasattr(self, '_spark_net'):
                self._spark_net.set_value(net_str, 0.0, "")
        elif net < 1.0:
            net_str = f"{net*1024:.0f}KB/s"
            net_pct = min(100, net * 10)
            self._bar_net.set_value(net_pct, net_str)
            if hasattr(self, '_spark_net'):
                self._spark_net.set_value(net_str, net_pct / 100.0, "")
        else:
            net_str = f"{net:.1f}MB/s"
            net_pct = min(100, net * 10)
            self._bar_net.set_value(net_pct, net_str)
            if hasattr(self, '_spark_net'):
                self._spark_net.set_value(net_str, net_pct / 100.0, "")

        # GPU — cache chip/VRAM from system_profiler, simulate load
        if not getattr(self, '_gpu_info_cached', False):
            try:
                import subprocess as _sp, re as _re2
                _r = _sp.run(["system_profiler", "SPDisplaysDataType"],
                             capture_output=True, text=True, timeout=3)
                _cm = _re2.search(r"Chipset Model:\s*(.+)", _r.stdout)
                _vm = _re2.search(r"VRAM.*?:\s*([\d.]+ \w+)", _r.stdout)
                self._gpu_chip = _cm.group(1).strip() if _cm else "Integrated GPU"
                self._gpu_chip = self._gpu_chip.replace(" Graphics", "").replace("Intel ", "")
                self._gpu_vram_str = _vm.group(1) if _vm else "Shared"
                self._gpu_info_cached = True
            except Exception:
                self._gpu_chip = "Integrated GPU"
                self._gpu_vram_str = "Shared"
                self._gpu_info_cached = True
        if hasattr(self, '_gpu_name_lbl'):
            self._gpu_name_lbl.setText(getattr(self, '_gpu_chip', 'Integrated GPU'))
        if hasattr(self, '_gpu_vram_lbl'):
            self._gpu_vram_lbl.setText(getattr(self, '_gpu_vram_str', 'Shared'))
        gpu = float(snap.get("gpu", -1.0))
        if hasattr(self, '_gpu_pct_lbl'):
            self._gpu_pct_lbl.setText("{:.0f}%".format(gpu) if gpu >= 0 else "N/A")
        if hasattr(self, '_gpu_load_bar'):
            self._gpu_load_bar.setValue(int(gpu) if gpu >= 0 else 0)
        self._bar_gpu.set_value(max(0.0, gpu), "{:.0f}%".format(gpu) if gpu >= 0 else "N/A")

        # Temperature is shown only when the operating system exposes a real sensor.
        tmp = snap["tmp"]
        if tmp < 0:
            self._bar_tmp.set_value(0, "N/A")
            if hasattr(self, '_spark_tmp'):
                self._spark_tmp.set_value("N/A", 0.0, "")
        else:
            tmp_pct = min(100, tmp)
            self._bar_tmp.set_value(tmp_pct, "{:.0f}°C".format(tmp))
            if hasattr(self, '_spark_tmp'):
                self._spark_tmp.set_value("{:.0f}".format(tmp), tmp / 100.0, "°C")

        try:
            boot_t  = psutil.boot_time()
            elapsed = time.time() - boot_t
            h = int(elapsed // 3600)
            m = int((elapsed % 3600) // 60)
            self._uptime_lbl.setText(f"UP  {h:02d}:{m:02d}")
        except Exception:
            self._uptime_lbl.setText("UP  --:--")

        try:
            proc_count = len(psutil.pids())
            self._proc_lbl.setText(f"PROC  {proc_count}")
        except Exception:
            self._proc_lbl.setText("PROC  --")

        # Session timer
        try:
            if hasattr(self, "_session_start"):
                se = time.time() - self._session_start
                sh = int(se // 3600)
                sm = int((se % 3600) // 60)
                ss = int(se % 60)
                if hasattr(self, "_session_lbl"):
                    self._session_lbl.setText(f"SESSION  {sh:02d}:{sm:02d}:{ss:02d}")
        except Exception:
            pass

        # AI Cognition bar — driven by state
        try:
            if hasattr(self, "_bar_cog") and hasattr(self, "hud"):
                state = getattr(self.hud, "state", "LISTENING")
                cog_pct = {
                    "THINKING": random.uniform(70, 95),
                    "PROCESSING": random.uniform(55, 80),
                    "SPEAKING": random.uniform(30, 50),
                    "LISTENING": random.uniform(5, 20),
                }.get(state, random.uniform(2, 10))
                self._bar_cog.set_value(cog_pct, f"{cog_pct:.0f}%")
        except Exception:
            pass

    def _style_splitter(self):
        if not hasattr(self, "_splitter"):
            return
        self._splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {C.BORDER};
                width: 4px;
            }}
            QSplitter::handle:hover {{ background: {C.BORDER_B}; }}
        """)

    def _style_header(self):
        if not hasattr(self, "_header") and not hasattr(self, "_utility_btn"):
            return
        header = getattr(self, "_header", None)
        if header is not None:
            header.setStyleSheet(f"""
                QWidget#appHeader {{
                    background: {C.DARK};
                    border-bottom: 1px solid {C.BORDER};
                }}
            """)
        if hasattr(self, "_utility_btn"):
            self._utility_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.PANEL2}; color: {C.TEXT_MED};
                    border: 1px solid {C.BORDER}; border-radius: 6px;
                    font-size: 12px;
                }}
                QPushButton:hover {{ color: {C.WHITE}; border-color: {C.BORDER_B}; }}
                QPushButton::menu-indicator {{ image: none; }}
            """)
        if hasattr(self, "_utility_menu"):
            self._utility_menu.setStyleSheet(f"""
                QMenu {{
                    background: {C.PANEL}; color: {C.WHITE};
                    border: 1px solid {C.BORDER}; padding: 6px;
                }}
                QMenu::item {{ padding: 7px 24px 7px 10px; border-radius: 4px; }}
                QMenu::item:selected {{ background: {C.PRI_GHO}; color: {C.PRI}; }}
                QMenu::separator {{ height: 1px; background: {C.BORDER}; margin: 5px; }}
            """)
        label_styles = (
            ("_header_brand_lbl", C.WHITE),
            ("_header_mark_lbl", C.TEXT_MED),
            ("_header_state_lbl", C.GREEN),
            ("_header_mode_lbl", C.TEXT_MED),
            ("_clock_lbl", C.WHITE),
            ("_date_lbl", C.TEXT_DIM),
            ("_utc_lbl", C.TEXT_DIM),
        )
        for attr, color in label_styles:
            label = getattr(self, attr, None)
            if label is not None:
                label.setStyleSheet(f"color: {color}; background: transparent;")

    def _style_left_nav(self):
        for attr, color in (
            ("_rail_title_lbl", C.WHITE),
            ("_system_title_lbl", C.TEXT_MED),
            ("_hardware_title_lbl", C.TEXT_DIM),
            ("_gpu_name_lbl", C.TEXT_MED),
            ("_gpu_vram_lbl", C.TEXT_MED),
            ("_uptime_lbl", C.TEXT_DIM),
            ("_session_lbl", C.TEXT_DIM),
            ("_proc_lbl", C.TEXT_MED),
        ):
            label = getattr(self, attr, None)
            if label is not None:
                label.setStyleSheet(f"color: {color}; background: transparent;")
        for button in (getattr(self, "_left_system_btn", None), getattr(self, "_left_agents_btn", None)):
            if button is None:
                continue
            if button.isChecked():
                button.setStyleSheet(f"""
                    QPushButton {{
                        background: {C.PRI_GHO}; color: {C.PRI};
                        border: 1px solid {C.PRI_DIM}; border-radius: 5px;
                    }}
                """)
            else:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent; color: {C.TEXT_MED};
                        border: 1px solid {C.BORDER}; border-radius: 5px;
                    }}
                    QPushButton:hover {{ color: {C.WHITE}; border-color: {C.BORDER_B}; }}
                """)

    def _style_command_button(self, button: QPushButton, color: str, hover: str):
        button.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {color};
                border: 1px solid transparent; border-radius: 5px;
                padding: 0 11px;
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO}; color: {hover}; border-color: {C.BORDER_B};
            }}
            QPushButton:focus {{
                background: {C.PRI_GHO}; color: {hover};
                border: 1px solid {hover};
            }}
            QPushButton:pressed {{ background: {C.DARK2}; color: {C.WHITE}; }}
            QPushButton:disabled {{ color: {C.TEXT_DIM}; background: transparent; }}
        """)

    def _style_command_rail(self):
        rail = getattr(self, "_dock_frame", None)
        if rail is not None:
            rail.setStyleSheet(f"""
                QWidget#JarvisCommandRail {{
                    background: {C.BAR_BG};
                    border-top: 1px solid {C.BORDER_B};
                    border-bottom: 1px solid {C.BORDER};
                }}
                QFrame#CommandControlTrack {{
                    background: {C.PANEL2};
                    border: 1px solid {C.BORDER};
                    border-radius: 6px;
                }}
                QFrame#CommandRailDivider {{
                    color: {C.BORDER};
                    background: {C.BORDER};
                    border: none;
                }}
            """)
        if hasattr(self, "_rail_divider"):
            self._rail_divider.setStyleSheet(f"color: {C.BORDER_B};")
        if hasattr(self, "_command_title_lbl"):
            self._command_title_lbl.setStyleSheet(
                f"color: {C.WHITE}; background: transparent; letter-spacing: 1px;"
            )
        if hasattr(self, "_rail_mode_lbl"):
            self._rail_mode_lbl.setStyleSheet(
                f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 1px;"
            )
        if hasattr(self, "_rail_status_dot"):
            self._rail_status_dot.setStyleSheet(f"color: {C.PRI}; background: transparent;")

    def _style_maker_signature(self):
        strip = getattr(self, "_maker_signature", None)
        if strip is not None:
            strip.setStyleSheet(f"""
                QWidget#JarvisMakerSignature {{
                    background: {C.BG};
                    border: none;
                }}
            """)
        label = getattr(self, "_maker_signature_lbl", None)
        if label is not None:
            label.setStyleSheet(
                f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 1px;"
            )

    def _style_command_controls(self):
        self._style_command_rail()
        if hasattr(self, "_tts_btn"):
            self._style_command_button(self._tts_btn, C.TEXT_MED, C.PRI)
        if hasattr(self, "_name_btn"):
            self._style_command_button(self._name_btn, C.TEXT_MED, C.PRI)
        if hasattr(self, "_theme_btn"):
            self._style_command_button(self._theme_btn, C.TEXT_MED, C.PRI)
        if hasattr(self, "_quit_btn"):
            self._quit_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {C.RED};
                    border: 1px solid {C.RED_D}; border-radius: 5px;
                    padding: 0 13px;
                }}
                QPushButton:hover, QPushButton:focus {{
                    background: {C.RED_BG}; color: {C.MUTED_C}; border-color: {C.RED};
                }}
                QPushButton:pressed {{ background: {C.DARK2}; }}
            """)
        if hasattr(self, "_mute_btn"):
            self._style_mute_btn()

    def _update_theme_btn(self):
        if hasattr(self, "_theme_btn"):
            display = ThemeManager.theme_display_name(ThemeManager.current_name())
            self._theme_btn.setText(f"THEME  ·  {display}")

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setObjectName("appHeader")
        w.setFixedHeight(58)
        w.setStyleSheet(f"""
            QWidget#appHeader {{
                background: {C.DARK};
                border-bottom: 1px solid {C.BORDER};
            }}
        """)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(12)

        # ── Left: Stark Industries branding ──────────────────────────────────
        left_col = QVBoxLayout(); left_col.setSpacing(1)
        left_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        stark = QLabel("JARVIS")
        self._header_brand_lbl = stark
        stark.setObjectName("headerTitle")
        stark.setFont(QFont("Arial", 15, QFont.Weight.DemiBold))
        stark.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        left_col.addWidget(stark)

        sub_stark = QLabel("MARK XXXIX")
        self._header_mark_lbl = sub_stark
        sub_stark.setObjectName("headerMeta")
        sub_stark.setFont(QFont("Arial", 7, QFont.Weight.Medium))
        sub_stark.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; letter-spacing: 1px;")
        left_col.addWidget(sub_stark)
        lay.addLayout(left_col)

        lay.addStretch()

        # ── Centre: JARVIS title ──────────────────────────────────────────────
        mid = QVBoxLayout(); mid.setSpacing(1)
        mid.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title = QLabel("●  ONLINE")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 9, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {C.GREEN}; background: transparent;")
        self._header_state_lbl = title
        mid.addWidget(title)

        sub = QLabel("LISTENING")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setFont(QFont("Arial", 7, QFont.Weight.Medium))
        sub.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; letter-spacing: 1px;")
        self._header_mode_lbl = sub
        mid.addWidget(sub)
        lay.addLayout(mid)

        lay.addStretch()

        # ── Right: clock + threat level + status ─────────────────────────────
        right_col = QVBoxLayout(); right_col.setSpacing(2)
        right_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Status row
        status_row = QHBoxLayout(); status_row.setSpacing(8)
        status_row.setAlignment(Qt.AlignmentFlag.AlignRight)

        right_col.addLayout(status_row)

        # Clock row
        clock_row = QHBoxLayout(); clock_row.setSpacing(4)
        clock_row.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._clock_lbl = QLabel("00:00:00")
        self._clock_lbl.setFont(QFont("Arial", 12, QFont.Weight.DemiBold))
        self._clock_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        self._clock_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        clock_row.addWidget(self._clock_lbl)
        right_col.addLayout(clock_row)

        self._date_lbl = QLabel("")
        self._date_lbl.setFont(QFont("Arial", 7))
        self._date_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 1px;")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._date_lbl)

        self._utc_lbl = QLabel("")
        self._utc_lbl.setFont(QFont("Arial", 6))
        self._utc_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 1px;")
        self._utc_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._utc_lbl)
        lay.addLayout(right_col)

        self._utility_btn = QPushButton("•••")
        self._utility_btn.setFixedSize(38, 34)
        self._utility_btn.setToolTip("Window and settings")
        self._utility_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._utility_menu = QMenu(self._utility_btn)
        self._utility_menu.addAction("Fullscreen", self._toggle_fullscreen)
        self._utility_menu.addAction("Settings", self._show_settings)
        self._utility_menu.addAction("Compact Mode", self._toggle_compact_mode)
        self._utility_menu.addSeparator()
        self._utility_menu.addAction("Keyboard Shortcuts", self._toggle_shortcuts_overlay)
        self._utility_menu.addAction("Close Command Center", lambda: self._set_command_center(False))
        self._utility_btn.setMenu(self._utility_menu)
        lay.addWidget(self._utility_btn)
        self._style_header()
        return w

    def _tick_clock(self):
        _colon = ":" if int(time.time()) % 2 == 0 else " "
        self._clock_lbl.setText(time.strftime("%H") + _colon + time.strftime("%M") + _colon + time.strftime("%S"))
        self._date_lbl.setText(time.strftime("%a %d %b %Y").upper())
        if hasattr(self, "_utc_lbl"):
            import datetime
            _off = datetime.datetime.now(datetime.timezone.utc).strftime("%z")
            self._utc_lbl.setText(f"UTC {_off[:3]}:{_off[3:]}")

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        w.setObjectName("leftRail")
        w.setFixedWidth(_LEFT_W)
        w.setStyleSheet(f"""
            QWidget#leftRail {{
                background: {C.PANEL};
                border-right: 1px solid {C.STEEL};
            }}
        """)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 12, 10, 10)
        lay.setSpacing(10)

        rail_title = QLabel("OVERVIEW")
        self._rail_title_lbl = rail_title
        rail_title.setFont(QFont("Arial", 10, QFont.Weight.DemiBold))
        rail_title.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        lay.addWidget(rail_title)

        nav = QHBoxLayout(); nav.setSpacing(4)
        self._left_system_btn = QPushButton("System")
        self._left_agents_btn = QPushButton("Agents")
        for button in (self._left_system_btn, self._left_agents_btn):
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(30)
            nav.addWidget(button)
        self._left_system_btn.setChecked(True)
        lay.addLayout(nav)

        # ── System Status (redesigned) ──────────────────────────────────────
        metrics_w = QWidget()
        metrics_w.setObjectName("systemOverview")
        metrics_w.setStyleSheet("background: transparent;")
        ml = QVBoxLayout(metrics_w)
        ml.setContentsMargins(12, 10, 12, 8)
        ml.setSpacing(3)

        # Header
        sys_hdr = QLabel("Live system")
        self._system_title_lbl = sys_hdr
        sys_hdr.setFont(QFont("Arial", 9, QFont.Weight.DemiBold))
        sys_hdr.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        ml.addWidget(sys_hdr)

        # Sparkline metrics — CPU, MEM, NET with live graphs
        self._spark_cpu = SparklineBar("CPU", C.PRI)
        self._spark_mem = SparklineBar("MEM", C.ENERGY)
        self._spark_net = SparklineBar("NET", C.ACC2)
        for spark in [self._spark_cpu, self._spark_mem, self._spark_net]:
            ml.addWidget(spark)
            spark.hide()

        ml.addSpacing(6)

        # ── GPU Block (expanded) ────────────────────────────────────────────
        gpu_super = QLabel("HARDWARE")
        self._hardware_title_lbl = gpu_super
        gpu_super.setFont(QFont("Courier New", 6))
        gpu_super.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 2px;")
        ml.addWidget(gpu_super)

        gpu_hdr_row = QHBoxLayout()
        gpu_hdr_lbl = QLabel("GPU")
        gpu_hdr_lbl.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        gpu_hdr_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent; letter-spacing: 2px;")
        gpu_hdr_row.addWidget(gpu_hdr_lbl)
        gpu_hdr_lbl.hide()
        gpu_hdr_row.addStretch()
        self._gpu_pct_lbl = QLabel("0%")
        self._gpu_pct_lbl.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        self._gpu_pct_lbl.setStyleSheet(f"color: {C.ENERGY}; background: transparent;")
        gpu_hdr_row.addWidget(self._gpu_pct_lbl)
        self._gpu_pct_lbl.hide()
        ml.addLayout(gpu_hdr_row)

        # chip name
        self._gpu_name_lbl = QLabel("Detecting...")
        self._gpu_name_lbl.setFont(QFont("Courier New", 7))
        self._gpu_name_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        ml.addWidget(self._gpu_name_lbl)

        ml.addSpacing(3)

        # LOAD label + bar
        gpu_load_hdr = QLabel("LOAD")
        gpu_load_hdr.setFont(QFont("Courier New", 6))
        gpu_load_hdr.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 1px;")
        ml.addWidget(gpu_load_hdr)
        gpu_load_hdr.hide()

        self._gpu_load_bar = QProgressBar()
        self._gpu_load_bar.setRange(0, 100)
        self._gpu_load_bar.setValue(0)
        self._gpu_load_bar.setFixedHeight(6)
        self._gpu_load_bar.setTextVisible(False)
        self._gpu_load_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {C.BORDER};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C.PRI}, stop:1 {C.ENERGY});
                border-radius: 3px;
            }}
        """)
        ml.addWidget(self._gpu_load_bar)
        self._gpu_load_bar.hide()

        ml.addSpacing(3)

        # VRAM row
        gpu_vram_row = QHBoxLayout()
        vram_lbl = QLabel("VRAM")
        vram_lbl.setFont(QFont("Courier New", 6))
        vram_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 1px;")
        gpu_vram_row.addWidget(vram_lbl)
        gpu_vram_row.addStretch()
        self._gpu_vram_lbl = QLabel("N/A")
        self._gpu_vram_lbl.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        self._gpu_vram_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        gpu_vram_row.addWidget(self._gpu_vram_lbl)
        ml.addLayout(gpu_vram_row)

        ml.addSpacing(6)

        # ── TMP sparkline (same style as CPU/MEM/NET) ───────────────────────
        self._spark_tmp = SparklineBar("TMP", "#FF6B35")
        ml.addWidget(self._spark_tmp)
        self._spark_tmp.hide()

        ml.addSpacing(4)

        # Cognitive load with progress bar
        cog_hdr = QLabel("COGNITIVE LOAD")
        cog_hdr.setFont(QFont("Courier New", 6, QFont.Weight.Bold))
        cog_hdr.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 2px;")
        ml.addWidget(cog_hdr)
        cog_hdr.hide()
        # Keep MetricBar references for data compatibility. Cognition is the
        # only visible bar because the other values already use spark rows.
        self._bar_cpu = MetricBar("CPU", C.TEXT_MED)
        self._bar_mem = MetricBar("MEM", C.TEXT_MED)
        self._bar_net = MetricBar("NET", C.TEXT_MED)
        self._bar_gpu = MetricBar("GPU", C.TEXT_MED)
        self._bar_tmp = MetricBar("TMP", C.TEXT_MED)
        self._bar_cog = MetricBar("COG", C.TEXT_MED)
        for b in [self._bar_cpu, self._bar_mem, self._bar_net, self._bar_gpu, self._bar_tmp, self._bar_cog]:
            ml.addWidget(b)

        # Info row
        info_row = QHBoxLayout(); info_row.setSpacing(4)
        self._uptime_lbl = QLabel("UP --:--")
        self._uptime_lbl.setFont(QFont("Courier New", 6))
        self._uptime_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        info_row.addWidget(self._uptime_lbl)
        info_row.addStretch()
        self._session_lbl = QLabel("00:00:00")
        self._session_lbl.setFont(QFont("Courier New", 6))
        self._session_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        info_row.addWidget(self._session_lbl)
        ml.addLayout(info_row)

        self._proc_lbl = QLabel("PROC  --")
        self._proc_lbl.setFont(QFont("Courier New", 6))
        self._proc_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        ml.addWidget(self._proc_lbl)

        self._left_stack = QStackedWidget()
        self._left_stack.setStyleSheet("background: transparent; border: none;")
        self._left_stack.addWidget(metrics_w)

        # ── Agent grid (fills remaining space) ───────────────────────────────
        self._agent_grid = AgentGridWidget()
        self._left_stack.addWidget(self._agent_grid)
        lay.addWidget(self._left_stack, stretch=1)

        def _show_left_page(index: int):
            self._left_stack.setCurrentIndex(index)
            self._left_system_btn.setChecked(index == 0)
            self._left_agents_btn.setChecked(index == 1)
            self._style_left_nav()

        self._left_system_btn.clicked.connect(lambda: _show_left_page(0))
        self._left_agents_btn.clicked.connect(lambda: _show_left_page(1))
        self._style_left_nav()

        return w

    def _feed_sparklines(self):
        """Feed sparkline bars from existing metric bar data."""
        try:
            # Extract numeric values from existing metric bars
            cpu_text = self._bar_cpu._val.text() if hasattr(self._bar_cpu, '_val') else "0"
            mem_text = self._bar_mem._val.text() if hasattr(self._bar_mem, '_val') else "0"
            net_text = self._bar_net._val.text() if hasattr(self._bar_net, '_val') else "0"

            cpu_pct = float(cpu_text.replace('%', '').strip() or '0') / 100.0
            mem_pct = float(mem_text.replace('%', '').strip() or '0') / 100.0

            self._spark_cpu.set_value(cpu_text.replace('%','').strip(), cpu_pct, "%")
            self._spark_mem.set_value(mem_text.replace('%','').strip(), mem_pct, "%")
            self._spark_net.set_value(net_text.strip(), 0.0, "")
        except Exception:
            pass

    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        w.setObjectName("rightRail")
        w.setFixedWidth(_RIGHT_W)
        w.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(
                    x1:1, y1:0, x2:0, y2:0,
                    stop:0 rgba(0, 4, 8, 240),
                    stop:0.5 rgba(0, 10, 18, 220),
                    stop:1 rgba(0, 8, 14, 230)
                );
                border-left: 1px solid {C.BORDER};
            }}
        """)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Mission Control Panel (tabbed) ───────────────────────────────────
        self._mission = MissionControlPanel()
        # Use ChatBubbleWidget instead of raw LogWidget for COMMS tab
        self._chat_bubble = ChatBubbleWidget()
        self._mission._stack.removeWidget(self._mission.log_widget)
        self._mission.log_widget.deleteLater()
        self._mission._stack.insertWidget(0, self._chat_bubble)
        self._mission.log_widget = self._chat_bubble
        self._mission._switch_tab(0)
        self._log = self._chat_bubble  # keep _log reference for compatibility
        self._chat_bubble.command_submitted.connect(self._send)

        # Build assets page content
        assets_inner = QWidget()
        assets_inner.setStyleSheet("background: transparent;")
        al = QVBoxLayout(assets_inner)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(6)
        self._drop_zone = FileDropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)
        al.addWidget(self._drop_zone)
        self._file_hint = QLabel("No file loaded — drop or click above")
        self._file_hint.setFont(QFont("Courier New", 7))
        self._file_hint.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self._file_hint.setWordWrap(True)
        al.addWidget(self._file_hint)
        self._mission.set_assets_widget(assets_inner)

        lay.addWidget(self._mission, stretch=1)

        # Hidden combo for voice tracking (not shown — controls are in CommandBar)
        self._voice_combo = QComboBox()
        self._voice_combo.hide()
        for label, value in VOICE_OPTIONS:
            self._voice_combo.addItem(label, value)
        self._voice_combo.setCurrentIndex(self._voice_combo.findData("charon"))
        self._voice_combo.currentTextChanged.connect(self._on_voice_changed)

        return w

    def _build_footer(self) -> QWidget:
        w = QWidget()
        self._dock_frame = w
        w.setObjectName("JarvisCommandRail")
        w.setAccessibleName("JARVIS command rail")
        w.setFixedHeight(72)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(12)

        # ── Rail anchor: identity plus real application state ────────────────
        anchor = QWidget(w)
        anchor.setObjectName("CommandRailAnchor")
        anchor.setFixedWidth(174)
        anchor_lay = QVBoxLayout(anchor)
        anchor_lay.setContentsMargins(0, 1, 0, 1)
        anchor_lay.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(7)
        self._rail_status_dot = QLabel("●")
        self._rail_status_dot.setFont(QFont(TECH_FONT, 7, QFont.Weight.Medium))
        self._rail_status_dot.setAccessibleName("JARVIS status indicator")
        title_row.addWidget(self._rail_status_dot)
        self._command_title_lbl = QLabel("COMMAND RAIL")
        self._command_title_lbl.setFont(QFont(UI_FONT, 9, QFont.Weight.DemiBold))
        title_row.addWidget(self._command_title_lbl)
        title_row.addStretch()
        anchor_lay.addLayout(title_row)

        self._rail_mode_lbl = QLabel("LOCAL  /  LISTENING")
        self._rail_mode_lbl.setFont(QFont(TECH_FONT, 7, QFont.Weight.Medium))
        self._rail_mode_lbl.setAccessibleName("JARVIS current state")
        anchor_lay.addWidget(self._rail_mode_lbl)
        lay.addWidget(anchor)

        sep2 = QFrame(w)
        sep2.setObjectName("CommandRailDivider")
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFixedSize(1, 34)
        self._rail_divider = sep2
        lay.addWidget(sep2)

        lay.addStretch(1)

        # ── One continuous control track, not a row of unrelated cards ──────
        track = QFrame(w)
        track.setObjectName("CommandControlTrack")
        track.setAccessibleName("Command controls")
        self._rail_control_track = track
        track_lay = QHBoxLayout(track)
        track_lay.setContentsMargins(2, 2, 2, 2)
        track_lay.setSpacing(0)

        def _ctrl_btn(txt, width):
            b = QPushButton(txt)
            b.setFixedSize(width, 40)
            b.setFont(QFont(UI_FONT, 8, QFont.Weight.DemiBold))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            return b

        def _track_separator():
            separator = QFrame(track)
            separator.setObjectName("CommandRailDivider")
            separator.setFrameShape(QFrame.Shape.VLine)
            separator.setFixedSize(1, 24)
            return separator

        self._mute_btn = QPushButton("MIC  ·  ON")
        self._mute_btn.setFixedSize(112, 40)
        self._mute_btn.setFont(QFont(UI_FONT, 8, QFont.Weight.DemiBold))
        self._mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mute_btn.setToolTip("Toggle microphone (F4)")
        self._mute_btn.setAccessibleName("Microphone active")
        self._mute_btn.clicked.connect(self._toggle_mute)
        track_lay.addWidget(self._mute_btn)
        track_lay.addWidget(_track_separator())

        self._tts_btn = _ctrl_btn("VOICE", 142)
        self._tts_btn.setToolTip("Change JARVIS voice")
        self._tts_btn.setAccessibleName("Change JARVIS voice")
        self._tts_btn.clicked.connect(self._show_tts_select)
        self._update_tts_btn()
        track_lay.addWidget(self._tts_btn)
        track_lay.addWidget(_track_separator())

        self._name_btn = _ctrl_btn("NAME", 142)
        self._name_btn.setToolTip("Change operator name")
        self._name_btn.setAccessibleName("Change operator name")
        self._name_btn.clicked.connect(self._show_name_signin)
        self._update_name_btn()
        track_lay.addWidget(self._name_btn)
        track_lay.addWidget(_track_separator())

        # Theme cycle button
        self._theme_btn = _ctrl_btn("THEME", 176)
        self._theme_btn.setToolTip("Cycle JARVIS theme")
        self._theme_btn.setAccessibleName("Cycle JARVIS theme")
        self._theme_btn.clicked.connect(self._cycle_theme)
        track_lay.addWidget(self._theme_btn)
        lay.addWidget(track)

        lay.addStretch(1)

        # Hidden shortcut mirrors retain existing keyboard-accessible functions
        # without adding visual noise to the rail.
        shortcut_mirrors = QWidget(w)
        shortcut_mirrors.hide()
        mirror_lay = QHBoxLayout(shortcut_mirrors)
        mirror_lay.setContentsMargins(0, 0, 0, 0)

        fs_btn = QPushButton("FULLSCREEN", shortcut_mirrors)
        fs_btn.setAccessibleName("Toggle fullscreen")
        fs_btn.setToolTip("Toggle fullscreen (F11)")
        fs_btn.clicked.connect(self._toggle_fullscreen)
        mirror_lay.addWidget(fs_btn)

        compact_btn = QPushButton("COMPACT", shortcut_mirrors)
        compact_btn.setToolTip("Compact Mode (Ctrl+M)")
        compact_btn.setAccessibleName("Toggle compact mode")
        compact_btn.clicked.connect(self._toggle_compact_mode)
        mirror_lay.addWidget(compact_btn)

        help_btn = QPushButton("SHORTCUTS", shortcut_mirrors)
        help_btn.setToolTip("Keyboard Shortcuts (Ctrl+/)")
        help_btn.setAccessibleName("Show keyboard shortcuts")
        help_btn.clicked.connect(self._toggle_shortcuts_overlay)
        mirror_lay.addWidget(help_btn)

        self._quit_btn = QPushButton("QUIT")
        self._quit_btn.setObjectName("JarvisQuitButton")
        self._quit_btn.setAccessibleName("Quit JARVIS")
        self._quit_btn.setToolTip("Quit JARVIS")
        self._quit_btn.setFixedSize(78, 44)
        self._quit_btn.setFont(QFont(UI_FONT, 8, QFont.Weight.DemiBold))
        self._quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._quit_btn.clicked.connect(self._request_quit)
        lay.addWidget(self._quit_btn)
        self._update_theme_btn()
        self._style_command_controls()

        return w

    def _build_maker_signature(self) -> QWidget:
        """Build the quiet, persistent creator signature beneath the shell."""
        strip = QWidget()
        self._maker_signature = strip
        strip.setObjectName("JarvisMakerSignature")
        strip.setAccessibleName("JARVIS creator trademark")
        strip.setFixedHeight(20)

        lay = QHBoxLayout(strip)
        lay.setContentsMargins(14, 0, 14, 1)
        lay.setSpacing(0)
        lay.addStretch(1)

        self._maker_signature_lbl = QLabel("amd.creationz™", strip)
        self._maker_signature_lbl.setFont(QFont(TECH_FONT, 7, QFont.Weight.Medium))
        self._maker_signature_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._maker_signature_lbl.setAccessibleName("amd.creationz trademark")
        self._maker_signature_lbl.setToolTip("JARVIS interface by amd.creationz")
        lay.addWidget(self._maker_signature_lbl)

        self._style_maker_signature()
        return strip

    def _show_left_panel_popup(self):
        """Show left panel content as a popup."""
        # Gather information from left panel components
        info_lines = ["LEFT PANEL INFORMATION"]

        # Add system metrics if available
        if hasattr(self, '_bar_cpu'):
            cpu_val = getattr(self._bar_cpu, 'value', 0)
            info_lines.append(f"CPU Usage: {cpu_val:.0f}%")
        if hasattr(self, '_bar_mem'):
            mem_val = getattr(self._bar_mem, 'value', 0)
            info_lines.append(f"Memory Usage: {mem_val:.0f}%")
        if hasattr(self, '_bar_net'):
            net_val = getattr(self._bar_net, 'value', 0)
            info_lines.append(f"Network: {net_val:.0f}%")
        if hasattr(self, '_bar_gpu'):
            gpu_val = getattr(self._bar_gpu, 'value', 0)
            info_lines.append(f"GPU: {gpu_val:.0f}%")

        # Add agent info if available
        if hasattr(self, '_agent_grid'):
            # AgentGridWidget has a fixed number of agents
            agent_count = len(self._agent_grid._AGENTS)
            info_lines.append(f"Active Agents: {agent_count}")

        info_lines.append("")
        info_lines.append("Press L again to refresh this information")

        # Join lines and show as popup
        message = "\n".join(info_lines)
        self._popup_manager.show_popup(
            message,
            PopupType.INFORMATION
        )

    def _show_right_panel_popup(self):
        """Show right panel content as a popup."""
        # Gather information from right panel components
        info_lines = ["RIGHT PANEL INFORMATION"]

        # Add mission info
        info_lines.append("Mission Control Panel")

        # Add chat status
        if hasattr(self, '_mission'):
            if hasattr(self._mission, 'log_widget'):
                info_lines.append("Chat Status: Active")
            else:
                info_lines.append("Chat Status: Inactive")

            # Add current tab info
            if hasattr(self._mission, '_stack'):
                current_index = self._mission._stack.currentIndex()
                tab_names = ["COMMS", "INTEL", "FILES", "ASSETS", "TOOLS", "MEMORY"]
                if 0 <= current_index < len(tab_names):
                    current_tab = tab_names[current_index]
                    info_lines.append(f"Current Tab: {current_tab}")

        info_lines.append("")
        info_lines.append("Press R again to refresh this information")

        # Join lines and show as popup
        message = "\n".join(info_lines)
        self._popup_manager.show_popup(
            message,
            PopupType.INFORMATION
        )

    def _on_file_selected(self, path: str):
        self._current_file = path
        p    = Path(path)
        cat  = _file_category(p)
        icon, _ = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size = _fmt_size(p.stat().st_size)
        self._file_hint.setText(f"{icon}  {p.name}  ·  {size}  ·  Tell JARVIS what to do with it")
        self._log.append_log(f"FILE: {p.name} ({size}) loaded")
        if self.on_text_command:
            msg = (
                f"[FILE_UPLOADED] path={path} | name={p.name} | "
                f"type={p.suffix.lstrip('.')} | size={size} | "
                f"Briefly tell the user you can see the file '{p.name}' "
                f"({size}) has been uploaded and ask what they'd like to do with it."
            )
            threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        self._style_mute_btn()
        if self._muted:
            self._apply_state("MUTED")
            self._log.append_log("SYS: Microphone muted.")
        else:
            self._apply_state("LISTENING")
            self._log.append_log("SYS: Microphone active.")

    def _get_selected_voice(self) -> str:
        idx = self._voice_combo.currentIndex()
        voice_name = self._voice_combo.itemData(idx)
        if isinstance(voice_name, str) and voice_name:
            return voice_name
        label = self._voice_combo.currentText().strip().lower()
        return VOICE_LABEL_TO_VALUE.get(label, "charon")

    def _on_voice_changed(self, _voice_label: str):
        """Handle voice selection change"""
        voice_name = self._get_selected_voice()
        self._log.append_log(f"SYS: Voice changed to {voice_name}.")
        os.environ["GEMINI_VOICE_NAME"] = voice_name
        try:
            cfg = json.loads(API_FILE.read_text(encoding="utf-8")) if API_FILE.exists() else {}
        except Exception:
            cfg = {}
        cfg.pop("gemini_api_key", None)
        cfg["voice_name"] = voice_name
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            API_FILE.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        except Exception as e:
            self._log.append_log(f"SYS: Could not save voice selection: {e}")
        if self.on_voice_change:
            try:
                self.on_voice_change(voice_name)
            except Exception as e:
                self._log.append_log(f"SYS: Voice callback error: {e}")

    def _style_mute_btn(self):
        if self._muted:
            self._mute_btn.setText("MIC  ·  MUTED")
            self._mute_btn.setAccessibleName("Microphone muted")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.RED_BG};
                    color: {C.MUTED_C};
                    border: 1px solid {C.RED};
                    border-radius: 5px;
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    background: {C.DARK2};
                    border: 1px solid {C.MUTED_C};
                }}
            """)
        else:
            self._mute_btn.setText("MIC  ·  ON")
            self._mute_btn.setAccessibleName("Microphone active")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.GREEN_BG};
                    color: {C.GREEN};
                    border: 1px solid {C.GREEN_D};
                    border-radius: 5px;
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    background: {C.DARK2};
                    border: 1px solid {C.GREEN};
                }}
            """)

    def _send(self, txt: str = ""):
        """Handle command submission. Called via ChatBubbleWidget signal."""
        try:
            txt = str(txt or "").strip()
            if not txt:
                return
            if (not getattr(self, "_ready", True)
                    or getattr(self, "_interaction_gated", False)
                    or getattr(self, "_intro_in_progress", False)
                    or getattr(self, "_intro_voice_preparing", False)):
                return
            self._log.append_log(f"You: {txt}")
            normalized = re.sub(r"[^a-z ]+", " ", txt.lower())
            normalized = " ".join(normalized.split())
            if normalized in {
                "open command center", "open the command center", "show command center",
                "show the command center", "open command ceneter", "open the command ceneter",
            }:
                self._set_command_center(True)
                self._log.append_log("JARVIS: Command Center is open.")
                return
            if normalized in {
                "close command center", "close the command center", "hide command center",
                "hide the command center", "return to focus view",
            }:
                self._set_command_center(False)
                self._log.append_log("JARVIS: Returning to focus view.")
                return
            if self.on_text_command:
                def _dispatch():
                    try:
                        self.on_text_command(txt)
                    except Exception as exc:
                        self._log_sig.emit(f"ERR: Message processing failed: {exc}")
                threading.Thread(target=_dispatch, daemon=True).start()
        except Exception as exc:
            # Exceptions escaping a PyQt signal handler can abort the process.
            # Keep JARVIS alive and surface the problem in its own log instead.
            try:
                self._log.append_log(f"ERR: Message processing failed: {exc}")
            except Exception:
                print(f"[JARVIS] Message processing failed: {exc}")

    def _apply_state(self, state: str):
        self.hud.state    = state
        self.hud.speaking = (state == "SPEAKING")
        if hasattr(self, "_rail_mode_lbl"):
            self._rail_mode_lbl.setText(f"LOCAL  /  {state}")
            rail_color = {
                "MUTED": C.RED,
                "THINKING": C.ACC2,
                "PROCESSING": C.ACC2,
                "SPEAKING": C.PRI,
                "LISTENING": C.GREEN,
            }.get(state, C.TEXT_DIM)
            self._rail_mode_lbl.setStyleSheet(
                f"color: {rail_color}; background: transparent; letter-spacing: 1px;"
            )
            if hasattr(self, "_rail_status_dot"):
                self._rail_status_dot.setStyleSheet(
                    f"color: {rail_color}; background: transparent;"
                )
        if hasattr(self, "_header_mode_lbl"):
            self._header_mode_lbl.setText(state)
            state_color = {
                "MUTED": C.RED,
                "THINKING": C.ACC2,
                "PROCESSING": C.ACC2,
                "SPEAKING": C.PRI,
                "LISTENING": C.TEXT_MED,
            }.get(state, C.TEXT_MED)
            self._header_mode_lbl.setStyleSheet(
                f"color: {state_color}; background: transparent; letter-spacing: 1px;"
            )
        # Sync AI canvas state
        if hasattr(self, "_ai_canvas"):
            self._ai_canvas.state = state
            # Map state to canvas mode if no specific context is set
            if state == "SPEAKING":
                self._ai_canvas.set_mode("speaking")
            elif state == "THINKING":
                self._ai_canvas.set_mode(getattr(self, "_context_mode", "thinking"))
            elif state == "LISTENING":
                self._ai_canvas.set_mode("listening")

        # Sync compact mode widget state
        if self._compact_widget:
            self._compact_widget.set_state(state)

        # Show toast for state transitions
        if state == "THINKING":
            self._show_toast("JARVIS is thinking...", "info")
        elif state == "PROCESSING":
            self._show_toast("Processing request...", "info")

    def _parse_log_for_context(self, text: str):
        """Detect context from log messages and feed task/tool widgets."""
        tl = text.lower()

        # Context mode detection
        if any(k in tl for k in ("code_helper", "dev_agent", "coding", "python", "javascript")):
            mode = "coding"
        elif any(k in tl for k in ("file_processor", "screen_process", "analyzing", "document")):
            mode = "analyzing"
        elif any(k in tl for k in ("web_search", "flight_finder", "weather", "research")):
            mode = "researching"
        elif "thinking" in tl or "🔧" in text:
            mode = "thinking"
        else:
            mode = getattr(self, "_context_mode", "idle")

        if mode != getattr(self, "_context_mode", "idle"):
            self._context_mode = mode
            try:
                self._mode_sig.emit(mode)
            except Exception:
                pass

        # Task queue feeding
        TOOL_MAP = {
            "open_app": "Open Application",
            "web_search": "Web Search",
            "deep_research": "Deep Research",
            "weather_report": "Weather Report",
            "browser_control": "Browser Control",
            "file_controller": "File Controller",
            "send_message": "Send Message",
            "reminder": "Set Reminder",
            "youtube_video": "YouTube",
            "screen_process": "Vision Analysis",
            "computer_settings": "System Settings",
            "desktop_control": "Desktop Control",
            "email_control": "Email",
            "media_control": "Media Control",
            "code_helper": "Code Assistant",
            "dev_agent": "Dev Agent",
            "web_search": "Web Search",
            "file_processor": "File Processor",
            "computer_control": "Computer Control",
            "game_updater": "Game Updater",
            "flight_finder": "Flight Finder",
        }
        for key, label in TOOL_MAP.items():
            if key in tl:
                if "📞" in text or "🔧" in text:
                    status = "calling"
                    # Show tool progress indicator
                    if hasattr(self, "_tool_progress"):
                        self._tool_progress.show_tool(label)
                elif "→" in text or "done" in tl or "✓" in text:
                    status = "done"
                    # Hide tool progress indicator
                    if hasattr(self, "_tool_progress"):
                        self._tool_progress.hide_tool()
                elif "❌" in text or "error" in tl or "fail" in tl:
                    status = "error"
                    if hasattr(self, "_tool_progress"):
                        self._tool_progress.hide_tool()
                    self._show_toast(f"Tool error: {label}", "error")
                else:
                    status = "active"
                try:
                    self._task_sig.emit(label, status)
                except Exception:
                    pass
                break

        # Tool log feeding — forward SYS/tool lines to tool widget
        if "🔧" in text or "📞" in text or "→" in text:
            try:
                self._tool_sig.emit(text)
            except Exception:
                pass

    def _check_config(self) -> bool:
        if not API_FILE.exists(): return False
        try:
            d = json.loads(API_FILE.read_text(encoding="utf-8"))
            if "gemini_api_key" in d:
                d.pop("gemini_api_key", None)
                try:
                    API_FILE.write_text(json.dumps(d, indent=4), encoding="utf-8")
                except Exception:
                    pass
            return bool(d.get("os_system"))
        except Exception:
            return False

    def _load_saved_voice(self):
        try:
            if hasattr(self, '_voice_combo'):
                d = json.loads(API_FILE.read_text(encoding="utf-8")) if API_FILE.exists() else {}
                voice_name = d.get("voice_name", d.get("tts_voice_id", "charon"))
                if isinstance(voice_name, str):
                    voice_name = voice_name.strip().lower()
                if voice_name not in VOICE_VALUE_TO_LABEL:
                    voice_name = "charon"
                index = self._voice_combo.findData(voice_name)
                if index >= 0:
                    self._voice_combo.setCurrentIndex(index)
                else:
                    self._voice_combo.setCurrentIndex(self._voice_combo.findData("charon"))
                os.environ["GEMINI_VOICE_NAME"] = self._get_selected_voice()
        except Exception:
            pass

    def _sync_voice_combo(self, voice_name: str):
        self._voice_combo.blockSignals(True)
        idx = self._voice_combo.findData(voice_name.lower())
        if idx >= 0:
            self._voice_combo.setCurrentIndex(idx)
        self._voice_combo.blockSignals(False)

    def _show_setup(self):
        cw = self.centralWidget()
        self._ensure_startup_backdrop()
        ov = SetupOverlay(cw, replay_every_launch=self._pending_greeting_enabled)
        ov.setFixedSize(460, 540)
        ov.done.connect(self._on_setup_done)
        self._overlay = ov
        ov.show()
        ov.raise_()
        ov._center_in_parent()

    def _legacy_on_setup_done(self, key: str, os_name: str, remember_key: bool):
        from core.api_key_validator import normalize_gemini_api_key

        normalized_key = normalize_gemini_api_key(key)
        verified_key = getattr(self._overlay, "_verified_key", "") if self._overlay else ""
        if not normalized_key or normalized_key != verified_key:
            self._log.append_log("ERR: Setup blocked because the Gemini API key was not verified.")
            self._ready = False
            return
        key = normalized_key

        # Persist API key only if user explicitly opts in.
        if remember_key and isinstance(key, str) and key.strip():
            try:
                store = get_secret_store()
                store.set("gemini_api_key", key.strip())
                self._log.append_log("SYS: Gemini API key saved to OS keychain.")
            except Exception as e:
                self._log.append_log(f"SYS: Could not save key to keychain: {e}")

        os.makedirs(CONFIG_DIR, exist_ok=True)

        try:
            cfg = json.loads(API_FILE.read_text(encoding="utf-8")) if API_FILE.exists() else {}
        except Exception:
            cfg = {}
        # Do NOT persist the Gemini API key to disk. Keep it in-memory for this session only.
        cfg.pop("gemini_api_key", None)
        cfg["os_system"] = os_name
        API_FILE.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        try:
            # Set the API key for this running process only. This ensures the key is
            # available to modules that read `os.environ['GEMINI_API_KEY']` without
            # writing it to disk — the user must re-enter it on next start.
            if isinstance(key, str) and key.strip():
                os.environ["GEMINI_API_KEY"] = key.strip()
                self._log.append_log("SYS: Gemini API key set for this session (not saved).")
        except Exception:
            pass
        self._ready = True
        if self._overlay:
            self._overlay.hide()
            self._overlay = None
        self._apply_state("LISTENING")
        self._log.append_log("SYS: INITIATING SYSTEMS, SIR...")
        self._log.append_log("SYS: CORE SYSTEMS ONLINE")
        self._log.append_log("SYS: NEURAL NETWORK ACTIVE  [OK]")
        self._log.append_log("SYS: PARALLAX UI COMPLETE   [OK]")
        self._log.append_log("SYS: VOICE SYNTHESIS READY  [OK]")
        self._log.append_log(f"SYS: PLATFORM {os_name.upper()} DETECTED")
        self._log.append_log("SYS: JARVIS MARK XXXIX - ALL SYSTEMS NOMINAL")
        # After setup: show voice popup first, then name popup
        self._show_voice_select_then_name()

    def _ensure_startup_backdrop(self):
        cw = self.centralWidget()
        if cw is None:
            return
        backdrop = getattr(self, "_startup_backdrop", None)
        if backdrop is None:
            backdrop = QWidget(cw)
            backdrop.setObjectName("StartupBackdrop")
            backdrop.setAccessibleName("JARVIS startup setup")
            backdrop.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            backdrop.setStyleSheet(f"background: {C.BG};")
            self._startup_backdrop = backdrop
        backdrop.setGeometry(cw.rect())
        backdrop.show()
        backdrop.lower()
        if getattr(self, "_overlay", None) is not None:
            self._overlay.raise_()

    def _clear_startup_backdrop(self):
        backdrop = getattr(self, "_startup_backdrop", None)
        if backdrop is not None:
            backdrop.hide()
            backdrop.deleteLater()
            self._startup_backdrop = None

    def _on_setup_done(self, key: str, os_name: str, remember_key: bool):
        from core.api_key_validator import normalize_gemini_api_key, validate_gemini_api_key

        normalized = normalize_gemini_api_key(key)
        overlay = self._overlay
        if overlay is not None:
            self._pending_greeting_enabled = overlay.replay_intro_enabled()
        completed, _saved_greeting = _load_intro_settings()
        self._intro_should_play = (not completed) or self._pending_greeting_enabled
        self._startup_sequence_kind = "tour" if not completed else (
            "greeting" if self._pending_greeting_enabled else ""
        )
        verified = getattr(overlay, "_verified_key", "") if overlay is not None else ""
        if not normalized or normalized != verified:
            if overlay is not None:
                overlay._key_input.setText(normalized)
                overlay.set_validating()

            def _validate():
                result = validate_gemini_api_key(normalized)
                if overlay is not None:
                    overlay.validation_finished.emit(
                        result.valid, result.message, normalized, remember_key
                    )

            threading.Thread(target=_validate, daemon=True).start()
            return

        self._finish_setup_after_key_validation(
            normalized, os_name, remember_key,
            ApiKeyValidationResult(True, "API key validated."),
        )

    def _finish_setup_after_key_validation(self, key, os_name, remember_key, result):
        if not result.valid:
            if self._overlay is not None:
                self._overlay.set_validation_error(result.message)
            self._ready = False
            return
        if remember_key:
            try:
                get_secret_store().set("gemini_api_key", key)
            except (OSError, RuntimeError, ValueError) as exc:
                self._log.append_log(f"ERR: Could not save key to keychain: {exc}")
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            cfg = json.loads(API_FILE.read_text(encoding="utf-8")) if API_FILE.exists() else {}
        except (OSError, json.JSONDecodeError):
            cfg = {}
        cfg.pop("gemini_api_key", None)
        cfg["os_system"] = os_name
        API_FILE.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        os.environ["GEMINI_API_KEY"] = key
        self._ready = False
        self._pending_ready_after_intro = True
        self._interaction_gated = True
        if self._intro_should_play:
            self._prepare_intro_voice()
        else:
            if self._overlay is not None:
                self._overlay.hide()
                self._overlay = None
            self._clear_startup_backdrop()
            self._continue_after_intro()

    def _prepare_intro_voice(self):
        kind = self._startup_sequence_kind or "greeting"
        if kind == "tour":
            self._startup_chapters = _tour_chapters(datetime.now())
            self._startup_captions = tuple(item.caption for item in self._startup_chapters)
            self._startup_narration = " ".join(self._startup_captions)
        else:
            self._startup_chapters = ()
            self._startup_captions = FirstRunIntroOverlay._CAPTIONS
            self._startup_narration = " ".join(self._startup_captions)
        self._intro_voice_preparing = True
        voice = self._get_selected_voice()
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        captions = self._startup_captions if kind == "tour" else None

        def _prepare():
            ready, message = _prepare_intro_voice_cache(
                voice, self._startup_narration, key,
                sequence_kind=kind, captions=captions,
            )
            self._intro_prepared_sig.emit(ready, message)

        threading.Thread(target=_prepare, name="jarvis-intro-prepare", daemon=True).start()

    def _on_intro_voice_prepared(self, ready: bool, message: str):
        self._intro_voice_preparing = False
        if ready:
            self._start_first_run_intro()
        else:
            self._on_intro_playback_failed(message or "Gemini could not prepare the introduction.")

    def _start_first_run_intro(self):
        try:
            kind = self._startup_sequence_kind or "greeting"
            if kind == "tour":
                self._prepare_live_intro_widgets("tour")
                self._popup_manager.dismiss_all_popups()
            if self._overlay is not None:
                self._overlay.hide()
            self._intro_in_progress = True
            self._interaction_gated = True
            self._intro_overlay = FirstRunIntroOverlay(
                self.centralWidget(),
                duration_s=(FirstRunIntroOverlay._TOUR_DURATION_S if kind == "tour"
                            else FirstRunIntroOverlay._GREETING_DURATION_S),
                speak=True,
                voice_name=self._get_selected_voice(),
                api_key=os.environ.get("GEMINI_API_KEY", ""),
                chapters=self._startup_chapters,
                narration=self._startup_narration,
                captions=self._startup_captions,
                sequence_kind=kind,
            )
            self._intro_overlay.setGeometry(self.centralWidget().rect())
            self._intro_overlay.caption_changed.connect(self._show_intro_caption)
            self._intro_overlay.chapter_changed.connect(self._on_intro_chapter_changed)
            self._intro_overlay._speech_error.connect(self._on_intro_playback_failed)
            self._intro_overlay.finished.connect(self._on_intro_finished)
            self._intro_overlay.show()
            self._intro_overlay.raise_()
            self._intro_overlay._start_narration()
        except Exception as exc:
            traceback.print_exc()
            self._intro_terminal_report("FAILED", str(exc))
            self._on_intro_playback_failed(str(exc), report=False)

    def _intro_terminal_report(self, state: str, detail: str = ""):
        if state == "FAILED":
            self._log.append_log(f"ERR: Introduction failed: {detail}")
        elif state == "COMPLETED":
            self._log.append_log("SYS: Introduction completed.")

    def _on_intro_playback_failed(self, message: str, report: bool = True):
        overlay = getattr(self, "_intro_overlay", None)
        if overlay is not None:
            overlay.stop_speech()
            overlay.hide()
            overlay.deleteLater()
            self._intro_overlay = None
        if self._startup_sequence_kind == "tour":
            self._mission._switch_tab(0)
            self._restore_live_intro_widgets(handoff_to_comms=True)
        self._intro_in_progress = False
        self._intro_voice_preparing = False
        self._interaction_gated = False
        if self._manual_tour_replay:
            self._manual_tour_replay = False
            if self.on_tour_state_change:
                self.on_tour_state_change(False)
        if report:
            self._intro_terminal_report("FAILED", message)
        if self._pending_ready_after_intro and self._overlay is not None:
            self._overlay.set_validation_error(message)
            self._overlay.show()
            self._overlay.raise_()
            self._overlay._center_in_parent()

    def _on_intro_finished(self):
        _save_intro_settings(True, self._pending_greeting_enabled)
        if self._startup_sequence_kind == "tour":
            self._restore_live_intro_widgets(handoff_to_comms=True)
        self._intro_in_progress = False
        if self._intro_overlay is not None:
            self._intro_overlay.deleteLater()
            self._intro_overlay = None
        self._interaction_gated = False
        self._intro_terminal_report("COMPLETED")
        if self._manual_tour_replay:
            self._manual_tour_replay = False
            if self.on_tour_state_change:
                self.on_tour_state_change(False)
        if self._pending_ready_after_intro:
            self._continue_after_intro()
        else:
            self._clear_startup_backdrop()

    def _continue_after_intro(self):
        self._pending_ready_after_intro = False
        self._intro_in_progress = False
        self._intro_voice_preparing = False
        self._interaction_gated = False
        setup_overlay = self._overlay
        self._overlay = None
        if setup_overlay is not None:
            setup_overlay.hide()
            setup_overlay.deleteLater()
        self._ready = True
        self._ready_announced = True
        self._clear_startup_backdrop()
        self._show_voice_select_then_name()

    def _request_manual_tour_replay(self):
        if self._interaction_gated or self._intro_in_progress or self._intro_voice_preparing:
            return
        self._startup_sequence_kind = "tour"
        self._startup_chapters = _tour_chapters()
        self._startup_captions = tuple(item.caption for item in self._startup_chapters)
        self._startup_narration = " ".join(self._startup_captions)
        self._manual_tour_replay = True
        self._intro_in_progress = True
        self._intro_voice_preparing = True
        self._interaction_gated = True
        if self.on_tour_state_change:
            self.on_tour_state_change(True)
        self._prepare_intro_voice()

    def _show_intro_caption(self, text: str):
        self._subtitle.clear_subtitle()
        self._subtitle.set_text(str(text or ""))

    def _intro_rect_for_widget(self, widget, padding: int = 0) -> QRectF:
        if widget is None or widget.width() <= 0 or widget.height() <= 0:
            return QRectF()
        root = self.centralWidget()
        overlay = self._intro_overlay or root
        origin = widget.mapTo(root, QPointF(0, 0).toPoint())
        if overlay is not root:
            offset = overlay.geometry().topLeft()
            origin -= offset
        rect = QRectF(origin.x(), origin.y(), widget.width(), widget.height())
        return rect.adjusted(-padding, -padding, padding, padding)

    def _on_intro_chapter_changed(self, focus: str, label: str, tab_index: int):
        if tab_index >= 0 and not self._command_center_open:
            self._command_center_open = True
            self._mission.set_command_center_open(True)
            for surface in (self._header, self._left_panel, self._right_panel, self._command_bar):
                surface.show()
            self._splitter.setSizes([_LEFT_W, max(420, self.width() - _LEFT_W - _RIGHT_W), _RIGHT_W])
        if tab_index >= 0:
            self._mission._switch_tab(tab_index)
        elif focus != "mission_tools" and self._mission._active_tab == 3:
            self._mission._switch_tab(0)
        self._intro_focus_key = focus
        if focus == "input":
            self._chat_bubble.show()
            self._chat_bubble._input.show()
        overlay = getattr(self, "_intro_overlay", None)
        if overlay is None:
            return
        widgets = {
            "core": self.hud, "subtitles": self._subtitle, "header": self._header,
            "awareness": self._left_panel, "mission_comms": self._mission,
            "mission_tasks": self._mission, "mission_assets": self._mission,
            "mission_tools": self._mission, "input": self._chat_bubble._input,
            "dock": self._footer_panel, "handoff": self._chat_bubble,
        }
        widget = widgets.get(focus, self._ai_core_wrap)
        rect = self._intro_rect_for_widget(widget, 8 if focus == "core" else 4)
        if focus == "core" and rect.isValid():
            diameter = min(rect.width(), rect.height()) * 0.62
            rect = QRectF(rect.center().x() - diameter / 2,
                          rect.center().y() - diameter / 2,
                          diameter, diameter)
        persistent = (self._intro_rect_for_widget(self._header),)
        overlay.set_spotlight(rect, label, "ellipse" if focus == "core" else "rect", persistent)

    def _prepare_live_intro_widgets(self, kind: str = "tour"):
        if not self._intro_live_groups:
            self._intro_original_tab = self._mission._active_tab
            self._intro_original_command_center = self._command_center_open
            if kind == "tour" and not self._command_center_open:
                self._command_center_open = True
                self._mission.set_command_center_open(True)
                for surface in (self._header, self._left_panel, self._right_panel, self._command_bar):
                    surface.show()
                self._splitter.setSizes([
                    _LEFT_W, max(420, self.width() - _LEFT_W - _RIGHT_W), _RIGHT_W
                ])
            definitions = (
                ("core", self._ai_core_wrap, 0.0, 6.0),
                ("awareness", self._left_panel, 6.0, 9.0),
                ("communications", self._right_panel, 8.8, 15.0),
                ("dock", self._footer_panel, 15.0, 18.0),
            )
            for name, widget, start, end in definitions:
                # The tour owns its opacity effects; command-center reveal animations
                # may replace Qt effects while the chapter is active.
                original_effect = None
                original_visible = widget.isVisible()
                effect = None if name == "dock" else QGraphicsOpacityEffect(widget)
                if effect is not None:
                    widget.setGraphicsEffect(effect)
                    effect.setOpacity(0.0)
                if name == "dock":
                    widget.hide()
                self._intro_live_groups.append({
                    "name": name, "widget": widget, "start": start, "end": end,
                    "effect": effect, "original_effect": original_effect,
                    "original_visible": original_visible, "completed": False,
                })
        timer = self._presence_system._presence_tmr
        self._intro_presence_was_active = timer.isActive()
        timer.stop()

    def _apply_live_intro_progress(self, seconds: float):
        position = max(0.0, float(seconds))
        for group in self._intro_live_groups:
            widget = group["widget"]
            start, end = group["start"], group["end"]
            if group["name"] == "dock":
                widget.setVisible(position >= start)
            if position >= end:
                group["completed"] = True
                if group["effect"] is not None:
                    widget.setGraphicsEffect(None)
                    group["effect"] = None
            elif position < start:
                if group["effect"] is not None:
                    group["effect"].setOpacity(0.0)
                group["completed"] = False
            elif group["effect"] is not None:
                group["effect"].setOpacity(min(1.0, max(0.01, (position - start) / max(0.01, end - start))))

    def _restore_live_intro_widgets(self, handoff_to_comms: bool = False):
        for group in self._intro_live_groups:
            widget = group["widget"]
            if widget.graphicsEffect() is not None:
                widget.setGraphicsEffect(None)
            original = group.get("original_effect")
            if original is not None:
                try:
                    widget.setGraphicsEffect(original)
                except RuntimeError:
                    widget.setGraphicsEffect(None)
            widget.setVisible(group.get("original_visible", True))
        self._intro_live_groups.clear()
        target_tab = 0 if handoff_to_comms else self._intro_original_tab
        if not getattr(self, "_intro_original_command_center", True):
            self._set_command_center(False, announce=False)
        self._mission._switch_tab(target_tab)
        if self._intro_presence_was_active:
            self._presence_system._presence_tmr.start(15000)

    def _check_and_show_name_signin(self):
        """Show the name sign-in overlay only if no name is saved in memory."""
        try:
            from memory.memory_manager import load_memory
            memory = load_memory()
            name_entry = memory.get("identity", {}).get("name")
            name = None
            if isinstance(name_entry, dict):
                name = name_entry.get("value")
            elif isinstance(name_entry, str):
                name = name_entry
            if name and name.strip():
                # Name already known — no need to ask
                return
        except Exception:
            pass
        self._show_name_signin()

    def _show_voice_select_then_name(self):
        """Show voice popup only on first boot (no saved voice); then chain name popup."""
        # Check if a voice has already been saved
        voice_already_set = False
        try:
            if API_FILE.exists():
                d = json.loads(API_FILE.read_text(encoding="utf-8"))
                if d.get("voice_name"):
                    voice_already_set = True
        except Exception:
            pass

        if voice_already_set:
            # Voice already chosen — skip straight to name check
            self._check_and_show_name_signin()
            return

        current = self._get_selected_voice()
        ov = VoiceSelectOverlay(self.centralWidget(), current_voice=current)
        cw = self.centralWidget()
        ow, oh = 420, 380
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )

        def _voice_done(voice_value: str):
            ov.hide()
            self._voice_overlay = None
            # Apply and persist the chosen voice
            idx = self._voice_combo.findData(voice_value)
            if idx >= 0:
                self._voice_combo.setCurrentIndex(idx)
            self._update_voice_btn()
            # Chain into name popup
            self._check_and_show_name_signin()

        ov.done.connect(_voice_done)
        ov.show()
        self._voice_overlay = ov

    def _show_name_signin(self):
        # Pre-fill with existing name if one is saved
        existing_name = ""
        try:
            from memory.memory_manager import load_memory
            memory = load_memory()
            name_entry = memory.get("identity", {}).get("name")
            if isinstance(name_entry, dict):
                existing_name = name_entry.get("value", "")
            elif isinstance(name_entry, str):
                existing_name = name_entry
        except Exception:
            pass

        # Don't open a second copy if already visible
        if self._name_overlay and self._name_overlay.isVisible():
            self._name_overlay.raise_()
            return

        ov = NameSignInOverlay(self.centralWidget(), existing_name=existing_name)
        cw = self.centralWidget()
        ow, oh = 420, 310
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.done.connect(self._on_name_done)
        ov._close_btn.clicked.disconnect()
        ov._close_btn.clicked.connect(self._close_name_overlay)
        ov.show()
        self._name_overlay = ov

    def _close_name_overlay(self):
        if self._name_overlay:
            self._name_overlay.hide()
            self._name_overlay.deleteLater()
            self._name_overlay = None

    def _on_name_done(self, name: str):
        if self._name_overlay:
            self._name_overlay.hide()
            self._name_overlay.deleteLater()
            self._name_overlay = None
        if not name or not name.strip():
            # X button was pressed — don't overwrite saved name
            return
        # Always save — "Sir" is the default when skipped
        save_name = name.strip() if name.strip() else "Sir"
        try:
            from memory.memory_manager import update_memory
            update_memory({"identity": {"name": {"value": save_name}}})
            self._log.append_log(f"SYS: Identity set — {save_name}.")
            self._log.append_log(f"JARVIS: The workshop is now at your disposal, {save_name}.")
            self._log.append_log("JARVIS: All systems nominal. How may I assist you today?")
        except Exception as e:
            self._log.append_log(f"SYS: Could not save name: {e}")
        # Notify JarvisLive so it can update the running session immediately
        if self.on_name_change:
            try:
                self.on_name_change(save_name)
            except Exception as e:
                self._log.append_log(f"SYS: Name callback error: {e}")
        # Refresh the button label to show current name
        self._update_name_btn()

    def _update_name_btn(self):
        """Update the Change Name button to show the currently saved name."""
        if not hasattr(self, "_name_btn"):
            return
        try:
            from memory.memory_manager import load_memory
            memory = load_memory()
            name_entry = memory.get("identity", {}).get("name")
            name = None
            if isinstance(name_entry, dict):
                name = name_entry.get("value")
            elif isinstance(name_entry, str):
                name = name_entry
            if name and name.strip() and name.strip().lower() not in ("sir", "madam"):
                display_name = name.strip()
                if len(display_name) > 14:
                    display_name = display_name[:13].rstrip() + "…"
                self._name_btn.setText(f"NAME  ·  {display_name}")
            else:
                self._name_btn.setText("NAME  ·  SET")
        except Exception:
            self._name_btn.setText("NAME")

    def _show_voice_select(self):
        if self._voice_overlay and self._voice_overlay.isVisible():
            self._voice_overlay.raise_()
            return

        current = self._get_selected_voice()

        ov = VoiceSelectorOverlay(
            self.centralWidget(),
            current_provider="gemini",
            current_voice_id=current,
            current_api_key="",
        )
        cw = self.centralWidget()
        ow, oh = 520, 540
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.done.connect(self._on_tts_select_done)
        ov._close_btn.clicked.disconnect()
        ov._close_btn.clicked.connect(self._close_voice_overlay)
        ov.show()
        self._voice_overlay = ov

    def _close_voice_overlay(self):
        if self._voice_overlay:
            self._voice_overlay.hide()
            self._voice_overlay.deleteLater()
            self._voice_overlay = None

    def _on_voice_select_done(self, voice_value: str):
        if hasattr(self, "_voice_overlay") and self._voice_overlay:
            self._voice_overlay.hide()
            self._voice_overlay.deleteLater()
            self._voice_overlay = None
        # Sync the hidden combo so existing voice-change logic fires
        idx = self._voice_combo.findData(voice_value)
        if idx >= 0:
            self._voice_combo.setCurrentIndex(idx)
        self._update_voice_btn()

    def _update_voice_btn(self):
        """Update the voice button label to show the currently selected voice."""
        if not hasattr(self, "_voice_btn"):
            return
        try:
            voice_val = self._get_selected_voice()
            label = VOICE_VALUE_TO_LABEL.get(voice_val, voice_val.title())
            self._voice_btn.setText(f"◈  {label.upper()}  ·  CHANGE VOICE")
        except Exception:
            self._voice_btn.setText("◈  CHANGE VOICE")

    # ------------------------------------------------------------------
    # TTS Provider overlay
    # ------------------------------------------------------------------

    def _load_saved_tts(self):
        """Read saved TTS config and update the button label."""
        self._update_tts_btn()

    def _show_tts_select(self):
        # Don't open a second copy if already visible
        if self._tts_overlay and self._tts_overlay.isVisible():
            self._tts_overlay.raise_()
            return

        # Read current provider + voice from JSON; API key from keychain
        provider = "gemini"
        voice_id = "orus"
        api_key  = ""
        try:
            if API_FILE.exists():
                d = json.loads(API_FILE.read_text(encoding="utf-8"))
                provider = d.get("tts_provider", "gemini")
                voice_id = d.get("tts_voice_id", "orus")
        except Exception:
            pass
        try:
            api_key = get_secret_store().get("tts_api_key") or ""
        except Exception:
            pass

        ov = VoiceSelectorOverlay(
            self.centralWidget(),
            current_provider=provider,
            current_voice_id=voice_id,
            current_api_key=api_key,
        )
        cw = self.centralWidget()
        ow, oh = 520, 540
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.done.connect(self._on_tts_select_done)
        # Wire X button to also clear the reference
        ov._close_cb = self._close_tts_overlay
        ov._close_btn.clicked.disconnect()
        ov._close_btn.clicked.connect(self._close_tts_overlay)
        ov.show()
        self._tts_overlay = ov

    def _close_tts_overlay(self):
        if self._tts_overlay:
            self._tts_overlay.hide()
            self._tts_overlay.deleteLater()
            self._tts_overlay = None

    def _on_tts_select_done(self, provider: str, voice_id: str, api_key: str):
        if self._tts_overlay:
            self._tts_overlay.hide()
            self._tts_overlay.deleteLater()
            self._tts_overlay = None

        # Save API key to OS keychain — never written to disk in plain text
        if api_key:
            try:
                get_secret_store().set("tts_api_key", api_key)
            except Exception as e:
                self._log.append_log(f"SYS: Could not save TTS key to keychain: {e}")

        # Persist only non-sensitive fields to JSON
        try:
            cfg = json.loads(API_FILE.read_text(encoding="utf-8")) if API_FILE.exists() else {}
        except Exception:
            cfg = {}
        cfg["tts_provider"] = provider
        cfg["tts_voice_id"] = voice_id
        if provider == "gemini":
            cfg["voice_name"] = voice_id
            os.environ["GEMINI_VOICE_NAME"] = voice_id
        cfg.pop("tts_api_key",  None)   # scrub any legacy plain-text key
        cfg.pop("tts_preset",   None)   # scrub old preset field
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            API_FILE.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        except Exception as e:
            self._log.append_log(f"SYS: Could not save TTS config: {e}")

        # Derive a friendly label for the log
        from actions.tts_engine import PROVIDER_VOICES
        label = voice_id
        for lbl, vid in PROVIDER_VOICES.get(provider, []):
            if vid == voice_id:
                label = lbl
                break
        self._log.append_log(f"SYS: Voice → {label}  ({provider})")
        self._update_tts_btn()

        # Keep the hidden Gemini combo in sync (used by on_voice_change callback)
        if provider == "gemini" and hasattr(self, "_voice_combo"):
            idx = self._voice_combo.findData(voice_id)
            if idx >= 0:
                # Block the signal so we don't double-fire on_voice_change
                self._voice_combo.blockSignals(True)
                self._voice_combo.setCurrentIndex(idx)
                self._voice_combo.blockSignals(False)
            _cache_intro_voice_async(voice_id)

        if self.on_tts_provider_change:
            try:
                self.on_tts_provider_change(provider, api_key, voice_id)
            except Exception as e:
                self._log.append_log(f"SYS: TTS callback error: {e}")

    def _update_tts_btn(self):
        """Update the TTS button label to show the active voice name."""
        if not hasattr(self, "_tts_btn"):
            return
        try:
            provider = "gemini"
            voice_id = "orus"
            if API_FILE.exists():
                d = json.loads(API_FILE.read_text(encoding="utf-8"))
                provider = d.get("tts_provider", "gemini")
                voice_id = d.get("tts_voice_id", "orus")
            from actions.tts_engine import PROVIDER_VOICES
            label = voice_id.title()
            for lbl, vid in PROVIDER_VOICES.get(provider, []):
                if vid == voice_id:
                    label = lbl
                    break
            self._tts_btn.setText(f"VOICE  ·  {label}")
        except Exception:
            self._tts_btn.setText("VOICE")

from .facade import JarvisUI, _RootShim

def _sync_ui_component_globals():
    """Keep split component modules compatible with the legacy patch surface."""
    for module_name, module in tuple(sys.modules.items()):
        if not module_name.startswith("ui.") or module is sys.modules.get(__name__):
            continue
        namespace = getattr(module, "__dict__", None)
        if namespace is None:
            continue
        for name, value in globals().items():
            namespace.setdefault(name, value)

_sync_ui_component_globals()
