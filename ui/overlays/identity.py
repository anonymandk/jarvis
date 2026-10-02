"""Identity, voice-selection, and voice tutorial overlays."""

from __future__ import annotations

import importlib

_legacy = importlib.import_module("ui._legacy")
globals().update({key: value for key, value in vars(_legacy).items() if not key.startswith("__")})

class NameSignInOverlay(_OverlayBase):
    """Overlay that asks the user for their name so JARVIS can address them personally."""
    done = pyqtSignal(str)   # emits the entered name (or "" if skipped)

    def __init__(self, parent=None, existing_name: str = ""):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            NameSignInOverlay {{
                background: {C.BG};
                border: 1px solid {C.BORDER_B};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(10)

        def _lbl(txt, font_size=9, bold=False, color=C.PRI,
                 align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont("Courier New", font_size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        title_txt = "◈  UPDATE IDENTITY" if existing_name else "◈  IDENTITY PROTOCOL"
        sub_txt   = f"Currently: {existing_name}" if existing_name else "JARVIS needs to know who it's talking to."
        layout.addWidget(_lbl(title_txt, 13, True))
        layout.addWidget(_lbl(sub_txt, 9, color=C.PRI_DIM))
        layout.addSpacing(4)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep)
        layout.addSpacing(6)

        layout.addWidget(_lbl("ENTER YOUR NAME", 8, color=C.TEXT_DIM,
                               align=Qt.AlignmentFlag.AlignLeft))

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("e.g.  Tony,  Mirsab,  Alex …")
        if existing_name:
            self._name_input.setText(existing_name)
            self._name_input.selectAll()
        self._name_input.setFont(QFont("Courier New", 11))
        self._name_input.setFixedHeight(36)
        self._name_input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.DARK}; color: {C.WHITE};
                border: 1px solid {C.BORDER_B}; border-radius: 4px;
                padding: 4px 10px; letter-spacing: 1px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        self._name_input.returnPressed.connect(self._submit)
        layout.addWidget(self._name_input)

        layout.addSpacing(4)

        confirm_btn = QPushButton("▸  CONFIRM IDENTITY")
        confirm_btn.setFixedHeight(34)
        confirm_btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRI_GHO}; color: {C.PRI};
                border: 1px solid {C.PRI}; border-radius: 4px;
            }}
            QPushButton:hover {{ background: {C.DARK2}; border: 1px solid {C.PRI}; }}
        """)
        confirm_btn.clicked.connect(self._submit)
        layout.addWidget(confirm_btn)

        skip_btn = QPushButton("Skip — default to Sir")
        skip_btn.setFixedHeight(26)
        skip_btn.setFont(QFont("Courier New", 7))
        skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        skip_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_DIM};
                border: 1px solid {C.BORDER}; border-radius: 3px;
            }}
            QPushButton:hover {{ color: {C.TEXT_MED}; border: 1px solid {C.BORDER_B}; }}
        """)
        skip_btn.clicked.connect(lambda: self.done.emit("Sir"))
        layout.addWidget(skip_btn)

        layout.addSpacing(4)
        layout.addWidget(_lbl(
            "Your name is stored locally and never sent to any server.",
            7, color=C.TEXT_DIM
        ))

        self._drag_pos = None
        self._setup_overlay_base(close_callback=self.hide)

    def _submit(self):
        name = self._name_input.text().strip()
        if not name:
            self._name_input.setStyleSheet(
                self._name_input.styleSheet()
                + f" QLineEdit {{ border: 1px solid {C.RED}; }}"
            )
            return
        self.done.emit(name)


class VoiceSelectOverlay(_OverlayBase):
    """Popup overlay for selecting JARVIS voice (used in first-run setup flow)."""
    done = pyqtSignal(str)   # emits selected voice value (e.g. "puck")

    def __init__(self, parent=None, current_voice: str = "puck"):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            VoiceSelectOverlay {{
                background: {C.BG};
                border: 1px solid {C.BORDER_B};
                border-radius: 8px;
            }}
        """)

        self._selected = current_voice.lower()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(10)

        def _lbl(txt, font_size=9, bold=False, color=C.PRI,
                 align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont("Courier New", font_size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        layout.addWidget(_lbl("◈  VOICE SELECTION", 13, True))
        layout.addWidget(_lbl("Choose the voice JARVIS will speak with.", 9, color=C.PRI_DIM))
        layout.addSpacing(4)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep)
        layout.addSpacing(4)

        # Voice buttons grid — 3 columns
        self._voice_btns: dict[str, QPushButton] = {}
        grid = QHBoxLayout()
        col_layouts = [QVBoxLayout(), QVBoxLayout(), QVBoxLayout()]
        for col in col_layouts:
            col.setSpacing(6)

        for i, (label, value) in enumerate(VOICE_OPTIONS):
            btn = QPushButton(label)
            btn.setFixedHeight(32)
            btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, v=value: self._select(v))
            self._voice_btns[value] = btn
            col_layouts[i % 3].addWidget(btn)

        for col in col_layouts:
            col.addStretch()
            grid.addLayout(col)
        layout.addLayout(grid)

        layout.addSpacing(6)

        confirm_btn = QPushButton("▸  CONFIRM VOICE")
        confirm_btn.setFixedHeight(34)
        confirm_btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRI_GHO}; color: {C.PRI};
                border: 1px solid {C.PRI}; border-radius: 4px;
            }}
            QPushButton:hover {{ background: {C.DARK2}; }}
        """)
        confirm_btn.clicked.connect(lambda: self.done.emit(self._selected))
        layout.addWidget(confirm_btn)

        # Apply initial selection highlight
        self._select(self._selected)
        self._drag_pos = None
        self._setup_overlay_base(close_callback=self.hide)

    def _select(self, value: str):
        self._selected = value
        for v, btn in self._voice_btns.items():
            if v == value:
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


class KeyTutorialOverlay(_OverlayBase):
    """Slides in over VoiceSelectorOverlay when an external voice is chosen without a key."""

    # Emits the entered API key when saved
    saved = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, parent, provider: str, current_key: str = ""):
        super().__init__(parent)
        from actions.tts_engine import PROVIDER_TUTORIAL
        info = PROVIDER_TUTORIAL.get(provider, {})

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            KeyTutorialOverlay {{
                background: {C.BG};
                border: 1px solid {C.ACC};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(10)

        def _lbl(txt, size=9, bold=False, color=C.PRI,
                 align=Qt.AlignmentFlag.AlignLeft):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont("Courier New", size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            w.setWordWrap(True)
            return w

        # Header
        title = info.get("title", f"{provider.upper()} API Key Setup")
        layout.addWidget(_lbl(f"◈  {title}", 11, True, C.ACC,
                              Qt.AlignmentFlag.AlignCenter))
        layout.addSpacing(2)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.ACC};"); layout.addWidget(sep)
        layout.addSpacing(4)

        # Steps
        for step in info.get("steps", []):
            layout.addWidget(_lbl(step, 9, color=C.WHITE))

        layout.addSpacing(6)

        # URL hint
        url = info.get("url", "")
        if url:
            layout.addWidget(_lbl(f"🔗  {url}", 8, color=C.PRI_DIM,
                                  align=Qt.AlignmentFlag.AlignCenter))

        layout.addSpacing(6)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep2)

        layout.addWidget(_lbl("API KEY", 8, bold=True, color=C.ACC))

        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("Paste your API key here…")
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setFont(QFont("Courier New", 9))
        self._key_input.setFixedHeight(32)
        self._key_input.setText(current_key)
        self._key_input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.DARK}; color: {C.WHITE};
                border: 1px solid {C.ACC}; border-radius: 3px; padding: 3px 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.ACC2}; }}
        """)
        layout.addWidget(self._key_input)

        layout.addSpacing(4)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)

        back_btn = QPushButton("← BACK")
        back_btn.setFixedHeight(30)
        back_btn.setFont(QFont("Courier New", 8))
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px;
            }}
            QPushButton:hover {{ color: {C.PRI}; border: 1px solid {C.BORDER_B}; }}
        """)
        back_btn.clicked.connect(self.cancelled.emit)
        btn_row.addWidget(back_btn)

        save_btn = QPushButton("▸  SAVE KEY & ACTIVATE")
        save_btn.setFixedHeight(30)
        save_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRI_GHO}; color: {C.PRI};
                border: 1px solid {C.PRI}; border-radius: 3px;
            }}
            QPushButton:hover {{ background: {C.DARK2}; }}
        """)
        save_btn.clicked.connect(lambda: self.saved.emit(self._key_input.text().strip()))
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

        self._drag_pos = None
        self._setup_overlay_base(close_callback=self.cancelled.emit)


class VoiceSelectorOverlay(_OverlayBase):
    """
    Voice selector with three grouped sections:
      ── GEMINI ──        (no API key needed)
      ── OPENAI TTS ──    (API key required)
      ── ELEVENLABS ──    (API key required)

    Clicking an external voice without a saved key shows KeyTutorialOverlay.
    """

    # Emits (provider, voice_id, api_key)
    done = pyqtSignal(str, str, str)

    def __init__(self, parent=None,
                 current_provider: str = "gemini",
                 current_voice_id: str = "orus",
                 current_api_key:  str = ""):
        super().__init__(parent)
        from actions.tts_engine import PROVIDER_VOICES, EXTERNAL_PROVIDERS
        self._provider  = current_provider.lower()
        self._voice_id  = current_voice_id
        self._api_key   = current_api_key
        self._ext_providers = EXTERNAL_PROVIDERS

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            VoiceSelectorOverlay {{
                background: {C.BG};
                border: 1px solid {C.BORDER_B};
                border-radius: 8px;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Main content (scrollable) ──────────────────────────────────────
        self._main = QWidget()
        self._main.setStyleSheet("background: transparent;")
        main_lay = QVBoxLayout(self._main)
        main_lay.setContentsMargins(26, 20, 26, 16)
        main_lay.setSpacing(8)

        def _lbl(txt, size=9, bold=False, color=C.PRI,
                 align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont("Courier New", size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        main_lay.addWidget(_lbl("◈  SELECT VOICE", 13, True))
        main_lay.addWidget(_lbl("Default: Orus  ·  Gemini", 8, color=C.PRI_DIM))
        main_lay.addSpacing(2)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};"); main_lay.addWidget(sep)

        # Track all voice buttons: (provider, voice_id) → QPushButton
        self._voice_btns: dict[tuple[str, str], QPushButton] = {}

        SECTION_LABELS = {
            "gemini":     "── GEMINI ──",
        }
        SECTION_COLORS = {
            "gemini":     C.ENERGY,
        }
        SECTION_KEY_HINT = {
            "gemini":     "no key required",
        }

        for provider, voices in PROVIDER_VOICES.items():
            main_lay.addSpacing(4)
            # Section header
            sec_col = SECTION_COLORS.get(provider, C.PRI)
            key_hint = SECTION_KEY_HINT.get(provider, "")
            hdr_w = QWidget()
            hdr_w.setStyleSheet("background: transparent;")
            hdr_lay = QHBoxLayout(hdr_w)
            hdr_lay.setContentsMargins(0, 0, 0, 0)
            hdr_lay.setSpacing(8)
            # Color-coded left accent bar
            bar = QWidget()
            bar.setFixedWidth(3)
            bar.setStyleSheet(f"background: {sec_col}; border-radius: 1px;")
            hdr_lay.addWidget(bar)
            hdr_lay.addWidget(_lbl(SECTION_LABELS[provider], 8, bold=True,
                                   color=sec_col, align=Qt.AlignmentFlag.AlignLeft))
            if key_hint:
                hint_lbl = _lbl(key_hint, 6, color=C.TEXT_DIM,
                                align=Qt.AlignmentFlag.AlignLeft)
                hdr_lay.addWidget(hint_lbl)
            hdr_lay.addStretch()
            main_lay.addSpacing(12)
            main_lay.addWidget(hdr_w)
            main_lay.addSpacing(4)

            # Voice buttons — 3 per row
            row_lay: QHBoxLayout | None = None
            for i, (label, vid) in enumerate(voices):
                if i % 3 == 0:
                    row_lay = QHBoxLayout(); row_lay.setSpacing(5)
                    main_lay.addLayout(row_lay)

                btn = QPushButton(label)
                btn.setFixedHeight(28)
                btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(
                    lambda _, p=provider, v=vid: self._on_voice_clicked(p, v)
                )
                self._voice_btns[(provider, vid)] = btn
                row_lay.addWidget(btn)  # type: ignore[union-attr]

            # Pad last row if not full
            remainder = len(voices) % 3
            if remainder and row_lay:
                for _ in range(3 - remainder):
                    row_lay.addStretch()

        main_lay.addSpacing(6)


        # Confirm button
        main_lay.addSpacing(16)
        confirm_btn = QPushButton("▸  ACTIVATE VOICE")
        confirm_btn.setFixedHeight(36)
        confirm_btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setStyleSheet(f"""
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
        confirm_btn.clicked.connect(self._confirm)
        main_lay.addWidget(confirm_btn)

        # Wrap in scroll area so API key field is always reachable
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._main)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.verticalScrollBar().setStyleSheet(f"""
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_B};
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)
        outer.addWidget(scroll)

        # ── Tutorial overlay (hidden until needed) ─────────────────────────
        self._tutorial: KeyTutorialOverlay | None = None

        # Apply initial highlight
        self._highlight(self._provider, self._voice_id)
        pass  # key section removed

        self._drag_pos = None
        self._setup_overlay_base(close_callback=self.hide)

    # ------------------------------------------------------------------

    def _on_voice_clicked(self, provider: str, voice_id: str):
        self._provider = provider
        self._voice_id = voice_id
        self._highlight(provider, voice_id)
        pass  # key section removed

    def _highlight(self, provider: str, voice_id: str):
        for (p, v), btn in self._voice_btns.items():
            active = (p == provider and v == voice_id)
            if active:
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
                        border: 1px solid {qss_rgba(C.BORDER, 85)}; border-radius: 4px;
                        border-top: 1px solid {C.BORDER};
                    }}
                    QPushButton:hover {{ color: {C.PRI}; border: 1px solid {C.BORDER_B};
                                        border-top: 1px solid {C.PRI}; }}
                """)

    def _confirm(self):
        if self._provider in self._ext_providers:
            key = self._key_input.text().strip()
            if not key:
                # No key — show tutorial overlay
                self._show_tutorial()
                return
            self._api_key = key
        self.done.emit(self._provider, self._voice_id, self._api_key)

    def _show_tutorial(self):
        if self._tutorial:
            self._tutorial.deleteLater()
        tut = KeyTutorialOverlay(self, self._provider, self._api_key)
        tut.setGeometry(0, 0, self.width(), self.height())
        tut.saved.connect(self._on_tutorial_saved)
        tut.cancelled.connect(self._on_tutorial_cancelled)
        tut.show()
        self._tutorial = tut

    def _on_tutorial_saved(self, key: str):
        if self._tutorial:
            self._tutorial.hide()
            self._tutorial = None
        if key:
            self._api_key = key
            self._key_input.setText(key)
            self.done.emit(self._provider, self._voice_id, self._api_key)

    def _on_tutorial_cancelled(self):
        if self._tutorial:
            self._tutorial.hide()
            self._tutorial = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._tutorial:
            self._tutorial.setGeometry(0, 0, self.width(), self.height())
