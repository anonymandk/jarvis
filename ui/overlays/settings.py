"""Shortcut, graphics, and settings overlays."""

from __future__ import annotations

import importlib

_legacy = importlib.import_module("ui._legacy")
globals().update({key: value for key, value in vars(_legacy).items() if not key.startswith("__")})

class ShortcutsOverlay(_OverlayBase):
    """Displays all keyboard shortcuts in a styled grid."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            ShortcutsOverlay {{
                background: {C.BG};
                border: 1px solid {C.BORDER_B};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(8)

        def _lbl(txt, size=9, bold=False, color=C.PRI, align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont(UI_FONT, size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setWordWrap(True)
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        layout.addWidget(_lbl("◈  KEYBOARD SHORTCUTS", 13, True))
        layout.addSpacing(4)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};")
        layout.addWidget(sep)
        layout.addSpacing(6)

        shortcuts = [
            ("F4",       "Toggle Microphone Mute"),
            ("F6",       "Minimize / Restore Window"),
            ("F11",      "Toggle Fullscreen"),
            ("Ctrl+/",   "Show This Help Panel"),
            ("Ctrl+M",   "Toggle Compact Mode"),
            ("Ctrl+Shift+T", "Cycle Color Theme"),
            ("Enter",    "Send Command (in input)"),
            ("Esc",      "Close Overlay / Dismiss"),
        ]

        for key, desc in shortcuts:
            row = QHBoxLayout()
            row.setSpacing(10)

            key_lbl = QLabel(key)
            key_lbl.setFixedWidth(80)
            key_lbl.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            key_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            key_lbl.setStyleSheet(f"""
                color: {C.PRI}; background: {C.PRI_GHO};
                border: 1px solid {C.BORDER}; border-radius: 3px;
                padding: 2px 6px;
            """)
            row.addWidget(key_lbl)

            desc_lbl = QLabel(desc)
            desc_lbl.setFont(QFont("Courier New", 9))
            desc_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
            row.addWidget(desc_lbl, stretch=1)

            layout.addLayout(row)

        layout.addSpacing(8)
        layout.addWidget(_lbl("Press Esc or Ctrl+/ to close", 7, color=C.TEXT_DIM))

        self._setup_overlay_base(close_callback=self.hide)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        super().keyPressEvent(event)


class GraphicsQualityCard(QPushButton):
    """Compact, theme-aware graphics option used by Settings."""

    _COPY = {
        "auto": ("AUTO", "Recommended", "· based on this device"),
        "low": ("LOW", "20 FPS", "· reduced detail"),
        "medium": ("MEDIUM", "30 FPS", "· balanced"),
        "high": ("HIGH", "60 FPS", "· full detail"),
    }

    def __init__(self, quality: str, parent=None):
        super().__init__(parent)
        self.quality = quality
        title, fps, detail = self._COPY[quality]
        self.setText("")
        self.setAccessibleName(f"{title.title()} graphics quality")
        self.setToolTip(f"{fps} {detail}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(78)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)
        self._title = QLabel(title, self)
        self._title.setFont(QFont(UI_FONT, 9, QFont.Weight.DemiBold))
        self._title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._title)

        data_row = QHBoxLayout()
        data_row.setContentsMargins(0, 0, 0, 0)
        data_row.setSpacing(4)
        self._fps = QLabel(fps, self)
        self._fps.setFont(QFont(TECH_FONT, 8, QFont.Weight.Medium))
        self._detail = QLabel(detail, self)
        self._desc = self._detail
        self._detail.setFont(QFont(UI_FONT, 8, QFont.Weight.Normal))
        for label in (self._fps, self._detail):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            data_row.addWidget(label)
        data_row.addStretch(1)
        layout.addLayout(data_row)
        self.refresh_theme(False)

    def refresh_theme(self, selected: bool):
        if selected:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 {C.PRI_GHO}, stop:0.78 {C.DARK2}, stop:1 {C.PRI_GLOW}
                    );
                    border: 1px solid {C.PRI}; border-radius: 6px;
                }}
                QPushButton:hover {{ background: {C.PRI_GLOW}; }}
            """)
            self._title.setStyleSheet(f"color: {C.WHITE}; background: transparent; border: none;")
            self._fps.setStyleSheet(f"color: {C.PRI}; background: transparent; border: none;")
            self._detail.setStyleSheet(f"color: {C.WHITE_DIM}; background: transparent; border: none;")
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {C.DARK};
                    border: 1px solid {C.BORDER}; border-radius: 6px;
                }}
                QPushButton:hover {{ border-color: {C.BORDER_B}; background: {C.PANEL2}; }}
            """)
            self._title.setStyleSheet(f"color: {C.WHITE_DIM}; background: transparent; border: none;")
            self._fps.setStyleSheet(f"color: {C.WHITE_DIM}; background: transparent; border: none;")
            self._detail.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")


class SettingsOverlay(_OverlayBase):
    """Unified settings panel for identity, theme, and graphics."""

    voice_changed = pyqtSignal(str, str, str)  # provider, voice_id, api_key
    name_changed = pyqtSignal(str)
    theme_changed = pyqtSignal(str)
    graphics_changed = pyqtSignal(str)
    graphics_mode_changed = pyqtSignal(str)
    intro_replay_changed = pyqtSignal(bool)
    tour_replay_requested = pyqtSignal()

    def __init__(self, parent=None, current_name: str = "",
                 current_voice: str = "puck", current_theme: str = "arc_reactor",
                 current_graphics: str = "medium", current_graphics_mode: str = "manual",
                 replay_intro: bool = False):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            SettingsOverlay {{
                background: {C.BG};
                border: 1px solid {C.BORDER_B};
                border-radius: 8px;
            }}
        """)

        self._current_name = current_name
        self._current_voice = current_voice
        self._current_theme = current_theme
        self._current_graphics = _normalize_graphics_quality(current_graphics)
        self._current_graphics_mode = current_graphics_mode if current_graphics_mode in {"auto", "manual"} else "auto"
        self._theme_labels: list[tuple[QLabel, str]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(6)

        def _lbl(txt, size=9, bold=False, color=None, align=Qt.AlignmentFlag.AlignCenter,
                 color_role="PRI"):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont("Courier New", size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            resolved = color if color is not None else getattr(C, color_role)
            w.setStyleSheet(f"color: {resolved}; background: transparent;")
            self._theme_labels.append((w, color_role))
            return w

        settings_title = _lbl("◈  SETTINGS", 13, True)
        settings_title_font = QFont(UI_FONT, 13, QFont.Weight.DemiBold)
        settings_title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
        settings_title.setFont(settings_title_font)
        layout.addWidget(settings_title)
        layout.addSpacing(2)

        # Tab bar
        tab_bar = QWidget()
        tab_bar.setFixedHeight(26)
        tb_lay = QHBoxLayout(tab_bar)
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.setSpacing(4)

        self._s_tabs: list[QPushButton] = []
        self._s_tab_names = ["IDENTITY", "THEME", "GRAPHICS"]
        self._s_active_tab = 0

        for i, name in enumerate(self._s_tab_names):
            btn = QPushButton(name)
            btn.setFixedHeight(23)
            btn.setFont(QFont(UI_FONT, 8, QFont.Weight.Medium))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._switch_s_tab(idx))
            self._s_tabs.append(btn)
            tb_lay.addWidget(btn)

        layout.addWidget(tab_bar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};")
        layout.addWidget(sep)

        # Stacked pages
        from PyQt6.QtWidgets import QStackedWidget
        self._s_stack = QStackedWidget()
        self._s_stack.setStyleSheet("background: transparent;")
        layout.addWidget(self._s_stack, stretch=1)

        # Page 0: Identity
        id_page = QWidget()
        id_page.setStyleSheet("background: transparent;")
        id_lay = QVBoxLayout(id_page)
        id_lay.setContentsMargins(4, 8, 4, 4)
        id_lay.setSpacing(8)

        id_lay.addWidget(_lbl("◈  YOUR NAME", 9, bold=True, color_role="PRI",
                              align=Qt.AlignmentFlag.AlignLeft))
        self._s_name_input = QLineEdit()
        self._s_name_input.setText(current_name)
        self._s_name_input.setPlaceholderText("e.g. Tony, Mirsab, Alex...")
        self._s_name_input.setFont(QFont(UI_FONT, 10))
        self._s_name_input.setFixedHeight(32)
        self._s_name_input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.DARK}; color: {C.WHITE};
                border: 1px solid {C.BORDER_B}; border-radius: 4px;
                padding: 4px 10px 4px 28px;
            }}
            QLineEdit:focus {{
                border: 1px solid {C.PRI};
                background: {C.DARK};
            }}
        """)
        id_lay.addWidget(self._s_name_input)

        save_name = QPushButton("▸  UPDATE IDENTITY")
        save_name.setFixedHeight(36)
        save_name.setFont(QFont(UI_FONT, 9, QFont.Weight.Medium))
        save_name.setCursor(Qt.CursorShape.PointingHandCursor)
        save_name.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRI_GHO}; color: {C.PRI};
                border: 1px solid {C.PRI}; border-radius: 4px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {qss_rgba(C.PRI, 34)};
                border: 1px solid {C.PRI};
                color: {C.ENERGY};
            }}
        """)
        save_name.clicked.connect(lambda: self.name_changed.emit(
            self._s_name_input.text().strip()))
        id_lay.addWidget(save_name)
        self._s_replay_intro = QCheckBox("Play greeting at startup")
        self._s_replay_intro.setChecked(bool(replay_intro))
        self._s_replay_intro.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        self._s_replay_intro.toggled.connect(self.intro_replay_changed.emit)
        id_lay.addWidget(self._s_replay_intro)
        self._s_replay_tour = QPushButton("REPLAY INTERFACE TOUR")
        self._s_replay_tour.setAccessibleName("Replay interface tour")
        self._s_replay_tour.clicked.connect(self.tour_replay_requested.emit)
        id_lay.addWidget(self._s_replay_tour)
        id_lay.addStretch()

        self._s_stack.addWidget(id_page)

        # Page 1: Theme
        th_page = QWidget()
        th_page.setStyleSheet("background: transparent;")
        th_lay = QVBoxLayout(th_page)
        th_lay.setContentsMargins(4, 8, 4, 4)
        th_lay.setSpacing(6)

        th_lay.addWidget(_lbl("COLOR THEME", 8, color_role="TEXT_DIM",
                              align=Qt.AlignmentFlag.AlignLeft))

        self._theme_btns: dict[str, QPushButton] = {}
        for key in ThemeManager.theme_names():
            display = ThemeManager.theme_display_name(key)
            btn = QPushButton(f"  {display}")
            btn.setFixedHeight(32)
            btn.setFont(QFont(UI_FONT, 9, QFont.Weight.Medium))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._select_theme(k))
            self._theme_btns[key] = btn
            th_lay.addWidget(btn)

        th_lay.addStretch()
        self._s_stack.addWidget(th_page)

        # Page 2: Graphics, including the device-based automatic profile.
        gfx_page = QWidget()
        gfx_page.setStyleSheet("background: transparent;")
        gfx_lay = QVBoxLayout(gfx_page)
        gfx_lay.setContentsMargins(4, 8, 4, 4)
        gfx_lay.setSpacing(10)
        gfx_lay.addWidget(_lbl(
            "GRAPHICS QUALITY", 8, bold=True, color_role="WHITE_DIM",
            align=Qt.AlignmentFlag.AlignLeft,
        ))
        gfx_lay.addWidget(_lbl(
            "Choose a performance profile. Changes apply instantly.",
            8, color_role="WHITE_DIM", align=Qt.AlignmentFlag.AlignLeft,
        ))

        gfx_row = QHBoxLayout()
        gfx_row.setSpacing(8)
        self._graphics_btns: dict[str, GraphicsQualityCard] = {}
        for quality in ("auto", "low", "medium", "high"):
            button = GraphicsQualityCard(quality)
            button.clicked.connect(lambda _, q=quality: self._select_graphics(q))
            self._graphics_btns[quality] = button
            gfx_row.addWidget(button, stretch=1)
        gfx_lay.addLayout(gfx_row)

        self._graphics_note = QLabel("")
        self._graphics_note.setFont(QFont(UI_FONT, 8))
        self._graphics_note.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        gfx_lay.addWidget(self._graphics_note)
        gfx_lay.addStretch()
        self._s_stack.addWidget(gfx_page)

        self._switch_s_tab(0)
        self._highlight_theme(current_theme)
        self._highlight_graphics(
            "auto" if self._current_graphics_mode == "auto" else self._current_graphics
        )
        self._setup_overlay_base(close_callback=self.hide)

    def _switch_s_tab(self, idx: int):
        self._s_active_tab = idx
        self._s_stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._s_tabs):
            if i == idx:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {C.PRI_GHO}; color: {C.PRI};
                        border: none; border-bottom: 2px solid {C.PRI};
                        border-radius: 3px; padding: 0 8px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent; color: {C.WHITE_DIM};
                        border: 1px solid {qss_rgba(C.BORDER, 68)}; border-radius: 3px; padding: 0 8px;
                    }}
                    QPushButton:hover {{ color: {C.PRI}; background: {C.PRI_GHO};
                                         border: 1px solid {C.BORDER_B}; }}
                """)

    def _select_theme(self, key: str):
        self._current_theme = key
        self.theme_changed.emit(key)
        self._highlight_theme(key)

    def _select_graphics(self, quality: str):
        if quality == "auto":
            self._current_graphics_mode = "auto"
            self._highlight_graphics("auto")
            self.graphics_mode_changed.emit("auto")
            return
        value = _normalize_graphics_quality(quality)
        self._current_graphics = value
        self._current_graphics_mode = "manual"
        self._highlight_graphics(value)
        self._graphics_note.setText(f"{value.upper()} quality active.")
        self.graphics_mode_changed.emit("manual")
        self.graphics_changed.emit(value)

    def _highlight_graphics(self, quality: str):
        value = quality if quality == "auto" else _normalize_graphics_quality(quality)
        for key, button in self._graphics_btns.items():
            button.refresh_theme(key == value)

    def set_auto_graphics_result(self, quality: str, reason: str):
        value = _normalize_graphics_quality(quality)
        self._graphics_btns["auto"]._desc.setText(f"{value.upper()} · recommended")
        self._graphics_note.setText(str(reason))
        if self._current_graphics_mode == "auto":
            self._highlight_graphics("auto")

    def refresh_theme(self):
        self.setStyleSheet(f"""
            SettingsOverlay {{
                background: {C.BG}; border: 1px solid {C.BORDER_B}; border-radius: 8px;
            }}
        """)
        for label, color_role in self._theme_labels:
            label.setStyleSheet(
                f"color: {getattr(C, color_role, C.TEXT)}; background: transparent;"
            )
        self._s_name_input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.DARK}; color: {C.WHITE};
                border: 1px solid {C.BORDER_B}; border-radius: 4px;
                padding: 4px 10px 4px 28px;
            }}
            QLineEdit:focus {{ border-color: {C.PRI}; background: {C.DARK}; }}
        """)
        self._switch_s_tab(self._s_active_tab)
        self._highlight_theme(self._current_theme)
        self._highlight_graphics(
            "auto" if self._current_graphics_mode == "auto" else self._current_graphics
        )
        self._graphics_note.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")

    def _highlight_theme(self, key: str):
        for k, btn in self._theme_btns.items():
            if k == key:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {C.PRI}; color: {C.BG};
                        border: none; border-radius: 4px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {C.DARK}; color: {C.TEXT_MED};
                        border: 1px solid {C.BORDER}; border-radius: 4px;
                    }}
                    QPushButton:hover {{ color: {C.PRI}; border: 1px solid {C.BORDER_B}; }}
                """)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        super().keyPressEvent(event)
