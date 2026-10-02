"""Conversation bubbles, dialogue focus, and live subtitles."""

from __future__ import annotations

import importlib

_runtime = importlib.import_module("ui._runtime")
globals().update({key: value for key, value in vars(_runtime).items() if not key.startswith("__")})

class ChatBubbleWidget(QWidget):
    """Chat-bubble style conversation view replacing raw text log."""

    _sig = pyqtSignal(str)
    command_submitted = pyqtSignal(str)   # emitted when user sends a command

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sig.connect(self._on_message)
        self.setStyleSheet("background: transparent;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px; }}
            QScrollBar:vertical {{
                background: {C.BG}; width: 6px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_B}; border-radius: 3px; min-height: 16px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self._container = QWidget()
        self._container.setStyleSheet(f"background: {C.PANEL};")
        self._c_lay = QVBoxLayout(self._container)
        self._c_lay.setContentsMargins(8, 8, 8, 8)
        self._c_lay.setSpacing(6)
        self._c_lay.addStretch()

        self._scroll.setWidget(self._container)
        lay.addWidget(self._scroll, stretch=1)

        # ── Command input bar pinned at bottom ───────────────────────────
        input_bar = QWidget()
        self._input_bar = input_bar
        input_bar.setFixedHeight(42)
        input_bar.setStyleSheet(f"""
            QWidget {{
                background: {C.DARK};
                border-top: 1px solid {C.BORDER};
            }}
        """)
        ib_lay = QHBoxLayout(input_bar)
        ib_lay.setContentsMargins(6, 4, 6, 4)
        ib_lay.setSpacing(6)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a message to JARVIS…")
        self._input.setFont(QFont(UI_FONT, 10))
        self._input.setFixedHeight(32)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.DARK};
                color: {C.WHITE};
                border: 1px solid {qss_rgba(C.ENERGY, 85)};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QLineEdit:focus {{
                border: 1px solid {C.ENERGY};
                background: {C.DARK2};
            }}
            QLineEdit::placeholder {{
                color: {C.TEXT_DIM};
            }}
        """)
        self._input.returnPressed.connect(self._submit)
        ib_lay.addWidget(self._input, stretch=1)

        send_btn = QPushButton("▸")
        self._send_btn = send_btn
        send_btn.setFixedSize(32, 32)
        send_btn.setFont(QFont(DISPLAY_FONT, 12, QFont.Weight.DemiBold))
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {qss_rgba(C.ENERGY, 34)};
                color: {C.ENERGY};
                border: 1px solid {qss_rgba(C.ENERGY, 102)};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {qss_rgba(C.ENERGY, 68)};
                border: 1px solid {C.ENERGY};
                color: {C.WHITE};
            }}
        """)
        send_btn.clicked.connect(self._submit)
        ib_lay.addWidget(send_btn)

        lay.addWidget(input_bar)

        self._messages: list[dict] = []

    def refresh_theme(self):
        """Restyle the live conversation and rebuild existing bubbles."""
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px; }}
            QScrollBar:vertical {{ background: {C.BG}; width: 6px; border: none; }}
            QScrollBar::handle:vertical {{ background: {C.BORDER_B}; border-radius: 3px; min-height: 16px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        self._scroll.viewport().setStyleSheet(f"background: {C.PANEL};")
        self._container.setStyleSheet(f"background: {C.PANEL};")
        self._input_bar.setStyleSheet(f"""
            QWidget {{ background: {C.DARK}; border-top: 1px solid {C.BORDER}; }}
        """)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.DARK}; color: {C.WHITE}; border: 1px solid {C.ENERGY};
                border-radius: 4px; padding: 4px 10px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.ENERGY}; background: {C.DARK2}; }}
            QLineEdit::placeholder {{ color: {C.TEXT_DIM}; }}
        """)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRI_GHO}; color: {C.ENERGY};
                border: 1px solid {C.ENERGY_D}; border-radius: 4px;
            }}
            QPushButton:hover {{ background: {C.DARK2}; border-color: {C.ENERGY}; color: {C.WHITE}; }}
        """)

        saved_messages = list(self._messages)
        if hasattr(self, "_typing_timer"):
            self._typing_timer.stop()
        while self._c_lay.count() > 1:
            item = self._c_lay.takeAt(0)
            if item and item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self._messages.clear()
        prefixes = {"user": "You: ", "ai": "JARVIS: ", "file": "FILE: ", "error": "ERR: ", "sys": "SYS: "}
        for message in saved_messages:
            self._skip_typing = True
            self._on_message(prefixes.get(message["sender"], "SYS: ") + message["text"])

    def _typing_tick(self):
        self._typing_idx += 1
        if self._typing_idx > len(self._typing_body):
            self._typing_timer.stop()
            # Remove temp bubble
            if hasattr(self, '_typing_bubble') and self._typing_bubble:
                self._c_lay.removeWidget(self._typing_bubble)
                self._typing_bubble.deleteLater()
                self._typing_bubble = None
            # Render final message properly
            self._skip_typing = True
            self._on_message(self._typing_full)
            return
        partial = 'JARVIS: ' + self._typing_body[:self._typing_idx]
        if hasattr(self, '_typing_bubble') and self._typing_bubble:
            self._c_lay.removeWidget(self._typing_bubble)
            self._typing_bubble.deleteLater()
        lbl = QLabel(partial + '▌')
        lbl.setFont(QFont(UI_FONT, 9))
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f'color: {C.PRI}; background: {C.PRI_GHO}; border: 1px solid {qss_rgba(C.PRI, 68)}; border-radius: 6px; padding: 6px 10px;')
        self._c_lay.addWidget(lbl)
        self._typing_bubble = lbl
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _submit(self):
        txt = self._input.text().strip()
        if not txt:
            return
        self._input.clear()
        self.command_submitted.emit(txt)

    def append_log(self, text: str):
        """Thread-safe message append — compatible with LogWidget API."""
        self._sig.emit(text)

    def _on_message(self, text: str):
        # Typing animation for JARVIS messages
        if text.lower().startswith('jarvis:') and not getattr(self, '_skip_typing', False):
            body = text[7:].strip()
            self._typing_idx = 0
            self._typing_body = body
            self._typing_full = text
            if not hasattr(self, '_typing_timer'):
                from PyQt6.QtCore import QTimer as _QT
                self._typing_timer = _QT(self)
                self._typing_timer.timeout.connect(self._typing_tick)
            self._typing_timer.start(12)
            return

        self._skip_typing = False
        tl = text.lower().strip()

        # Determine message type
        if tl.startswith("you:"):
            sender = "user"
            display = text[4:].strip()
            align = Qt.AlignmentFlag.AlignRight
            bg_col = C.BORDER
            border_col = C.PRI_DIM
            text_col = C.WHITE
            name = "YOU"
        elif tl.startswith("jarvis:"):
            sender = "ai"
            display = text[7:].strip()
            align = Qt.AlignmentFlag.AlignLeft
            bg_col = C.PRI_GHO
            border_col = C.PRI
            text_col = C.PRI
            name = "JARVIS"
        elif tl.startswith("file:"):
            sender = "file"
            display = text[5:].strip()
            align = Qt.AlignmentFlag.AlignLeft
            bg_col = C.GREEN_BG
            border_col = C.GREEN_D
            text_col = C.GREEN
            name = "FILE"
        elif "err" in tl or tl.startswith("err:"):
            sender = "error"
            display = text
            align = Qt.AlignmentFlag.AlignLeft
            bg_col = C.RED_BG
            border_col = C.RED_D
            text_col = C.RED
            name = "ERROR"
        else:
            sender = "sys"
            display = text.replace("SYS: ", "").replace("SYS:", "")
            align = Qt.AlignmentFlag.AlignLeft
            bg_col = C.PURPLE_BG
            border_col = C.ACC
            text_col = C.ACC2
            name = "SYS"

        ts = time.strftime("%H:%M")

        # Build bubble widget
        bubble = QWidget()
        bubble.setStyleSheet("background: transparent;")
        b_lay = QHBoxLayout(bubble)
        b_lay.setContentsMargins(0, 0, 0, 0)
        b_lay.setSpacing(0)

        if sender == "user":
            b_lay.addStretch()

        card = QWidget()
        max_w = 280 if sender == "user" else 300
        card.setMaximumWidth(max_w)
        card.setStyleSheet(f"""
            QWidget {{
                background: {bg_col};
                border: 1px solid {border_col};
                border-radius: 8px;
            }}
        """)
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(10, 6, 10, 6)
        c_lay.setSpacing(3)

        # Header: name + timestamp
        hdr = QHBoxLayout()
        hdr.setSpacing(4)
        name_lbl = QLabel(name)
        name_lbl.setFont(QFont(DISPLAY_FONT, 8, QFont.Weight.DemiBold))
        name_lbl.setStyleSheet(f"color: {text_col}; background: transparent; border: none;")
        hdr.addWidget(name_lbl)
        hdr.addStretch()
        ts_lbl = QLabel(ts)
        ts_lbl.setFont(QFont(UI_FONT, 7))
        ts_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")
        hdr.addWidget(ts_lbl)
        c_lay.addLayout(hdr)

        # Message text
        msg = QLabel(display)
        msg.setFont(QFont(UI_FONT, 10))
        msg.setWordWrap(True)
        msg.setStyleSheet(f"color: {C.WHITE}; background: transparent; border: none;")
        c_lay.addWidget(msg)

        b_lay.addWidget(card)

        if sender != "user":
            b_lay.addStretch()

        self._c_lay.insertWidget(self._c_lay.count() - 1, bubble)
        self._messages.append({"sender": sender, "text": display, "ts": ts})

        # Keep max 200 messages
        if len(self._messages) > 200:
            self._messages.pop(0)
            item = self._c_lay.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        # Auto-scroll to bottom
        QTimer.singleShot(50, self._scroll_bottom)

    def _scroll_bottom(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())


class FocusDialogueWidget(QWidget):
    """Shows the current exchange without turning focus mode into a chat sidebar."""

    _sig = pyqtSignal(str)
    command_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sig.connect(self._apply_message)
        self.setFixedHeight(106)
        self.setStyleSheet("background: transparent;")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(48, 2, 48, 10)
        outer.setSpacing(0)

        self._shell = QFrame()
        self._shell.setObjectName("focusDialogueShell")
        self._shell.setMaximumWidth(760)
        shell_lay = QVBoxLayout(self._shell)
        shell_lay.setContentsMargins(16, 9, 16, 9)
        shell_lay.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)
        self._channel_lbl = QLabel("DIALOGUE LINK")
        self._channel_lbl.setFont(QFont(DISPLAY_FONT, 8, QFont.Weight.DemiBold))
        header.addWidget(self._channel_lbl)
        header.addStretch()
        self._live_lbl = QLabel("●  LIVE")
        self._live_lbl.setFont(QFont(UI_FONT, 7, QFont.Weight.DemiBold))
        header.addWidget(self._live_lbl)
        shell_lay.addLayout(header)
        self._channel_lbl.hide()
        self._live_lbl.hide()

        message_row = QHBoxLayout()
        message_row.setSpacing(10)
        self._speaker_lbl = QLabel("JARVIS")
        self._speaker_lbl.setFixedWidth(62)
        self._speaker_lbl.setFont(QFont(DISPLAY_FONT, 8, QFont.Weight.DemiBold))
        message_row.addWidget(self._speaker_lbl, alignment=Qt.AlignmentFlag.AlignTop)
        self._message_lbl = QLabel("Standing by.")
        self._message_lbl.setFont(QFont(UI_FONT, 10, QFont.Weight.Medium))
        self._message_lbl.setWordWrap(True)
        self._message_lbl.setMaximumHeight(34)
        message_row.addWidget(self._message_lbl, stretch=1)
        shell_lay.addLayout(message_row)

        input_row = QHBoxLayout()
        input_row.setSpacing(7)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Give JARVIS a command")
        self._input.setFont(QFont(UI_FONT, 9))
        self._input.setFixedHeight(30)
        self._input.returnPressed.connect(self._submit)
        input_row.addWidget(self._input, stretch=1)
        self._send_btn = QPushButton("SEND")
        self._send_btn.setFont(QFont(UI_FONT, 8, QFont.Weight.DemiBold))
        self._send_btn.setFixedSize(64, 30)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.clicked.connect(self._submit)
        input_row.addWidget(self._send_btn)
        shell_lay.addLayout(input_row)

        outer.addStretch()
        outer.addWidget(self._shell, stretch=1)
        outer.addStretch()
        self.refresh_theme()

    def append_log(self, text: str):
        self._sig.emit(str(text or ""))

    def _apply_message(self, text: str):
        clean = str(text or "").strip()
        if not clean:
            return
        lower = clean.lower()
        if lower.startswith("you:"):
            speaker, body, color = "YOU", clean[4:].strip(), C.WHITE
        elif lower.startswith("jarvis:"):
            speaker, body, color = "JARVIS", clean[7:].strip(), C.PRI
        elif lower.startswith("err:") or "error" in lower:
            speaker, body, color = "ALERT", clean.replace("ERR:", "").strip(), C.RED
        else:
            speaker = "SYSTEM"
            body = clean.replace("SYS:", "").strip()
            color = C.TEXT_MED
        self._speaker_lbl.setText(speaker)
        self._speaker_lbl.setStyleSheet(f"color: {color}; background: transparent;")
        self._message_lbl.setText(body)

    def _submit(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.command_submitted.emit(text)

    def refresh_theme(self):
        self._shell.setStyleSheet(f"""
            QFrame#focusDialogueShell {{
                background: {C.PANEL}; border: 1px solid {C.BORDER_B}; border-radius: 7px;
            }}
        """)
        self._channel_lbl.setStyleSheet(
            f"color: {C.TEXT_MED}; background: transparent; letter-spacing: 1px;"
        )
        self._live_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent;")
        self._speaker_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        self._message_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.DARK}; color: {C.WHITE}; border: 1px solid {C.BORDER};
                border-radius: 4px; padding: 0 10px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
            QLineEdit::placeholder {{ color: {C.TEXT_DIM}; }}
        """)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRI_GHO}; color: {C.PRI}; border: 1px solid {C.PRI_DIM};
                border-radius: 4px;
            }}
            QPushButton:hover, QPushButton:focus {{ background: {C.CARD}; border-color: {C.PRI}; }}
            QPushButton:pressed {{ background: {C.DARK2}; }}
        """)


class _SubtitleWidget(QWidget):
    """Centered, scrolling subtitle display with morph fade-out."""

    _MAX_VISIBLE = 5          # max visible lines in viewport
    _HOLD_MS = 5000           # hold after last chunk before fade starts
    _FADE_MS = 800            # duration of the dissolve animation
    _LINE_H = 22
    _SCROLL_SPEED = 0.18      # lerp factor per frame for smooth scroll

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumHeight(80)
        self.setMaximumHeight(220)

        self._chunks: list[list[str]] = []
        self._newest_idx = -1

        # Smooth scroll state
        self._scroll_y = 0.0          # current scroll offset (pixels)
        self._scroll_target = 0.0     # target scroll offset
        self._auto_scroll = True      # follow latest text automatically
        self._scroll_max = 0.0        # max scroll range

        # Fade-out state
        self._opacity = 1.0
        self._fading = False
        self._fade_start = 0.0

        # Hold timer — fires after 5s of silence, starts the fade
        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._begin_fade)

        # Animation timer (60fps) — drives scroll + fade
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._anim_tick)

        self.setMinimumHeight(80)
        self.setMaximumHeight(220)
        self.setStyleSheet("background: transparent;")

        self._font = QFont(UI_FONT, 13, QFont.Weight.Medium)
        self._done_col = qcol(C.TEXT)
        self._active_col = qcol(C.PRI)
        self._line_h = self._LINE_H

    def set_text(self, text: str):
        """Append a new transcription chunk — shown immediately."""
        text = (text or "").strip()
        if not text:
            return
        words = text.split()
        if not words:
            return

        # If we were fading, cancel and restore
        if self._fading:
            self._fading = False
            self._opacity = 1.0

        self._newest_idx = len(self._chunks)
        self._chunks.append(words)

        # Recalculate scroll target (respects _auto_scroll flag)
        self._recalc_scroll_target()

        # Stop any pending hold timer — it will be restarted by start_hold_timer()
        # which is called externally only when JARVIS finishes talking (turn_complete).
        self._hold_timer.stop()

        # Ensure animation timer is running for scroll
        if not self._anim_timer.isActive():
            self._anim_timer.start()

        self.update()

    def start_hold_timer(self):
        """Start (or restart) the fade-out hold timer. Call this when JARVIS finishes speaking."""
        if self._chunks:
            self._hold_timer.stop()
            self._hold_timer.start(self._HOLD_MS)

    def clear_subtitle(self):
        """Immediately clear everything."""
        self._hold_timer.stop()
        self._anim_timer.stop()
        self._chunks.clear()
        self._newest_idx = -1
        self._scroll_y = 0.0
        self._scroll_target = 0.0
        self._scroll_max = 0.0
        self._auto_scroll = True
        self._opacity = 1.0
        self._fading = False
        self.update()

    def _recalc_scroll_target(self):
        """Calculate how far we need to scroll to keep latest lines visible."""
        total_lines = self._build_line_count()
        visible_h = self.rect().adjusted(12, 4, -12, -4).height()
        max_visible = max(1, int(visible_h / self._line_h))
        if total_lines > max_visible:
            self._scroll_max = float((total_lines - max_visible) * self._line_h)
        else:
            self._scroll_max = 0.0
        # Only auto-follow if user hasn't manually scrolled
        if self._auto_scroll:
            self._scroll_target = self._scroll_max
        else:
            # Clamp user's position to new max without jumping to bottom
            self._scroll_target = min(self._scroll_target, self._scroll_max)

    def wheelEvent(self, event):
        """Manual scroll with mouse wheel / trackpad."""
        if not self._chunks or self._scroll_max <= 0:
            return
        delta = event.angleDelta().y()
        # Scroll up = positive delta, scroll down = negative
        step = self._line_h
        if delta > 0:
            self._scroll_target = max(0.0, self._scroll_target - step)
            self._auto_scroll = False
        else:
            self._scroll_target = min(self._scroll_max, self._scroll_target + step)
            # If scrolled back to bottom, re-enable auto-scroll
            if self._scroll_target >= self._scroll_max:
                self._auto_scroll = True

        if not self._anim_timer.isActive():
            self._anim_timer.start()
        event.accept()

    def _build_line_count(self) -> int:
        """Count wrapped lines using the same logic as paintEvent."""
        from PyQt6.QtGui import QFontMetrics
        fm = QFontMetrics(self._font)
        max_w = self.rect().adjusted(12, 4, -12, -4).width() - 16
        if max_w <= 0:
            return 0
        space_w = fm.horizontalAdvance(" ")
        count = 0
        line_w = 0
        line_has_words = False
        for chunk in self._chunks:
            for w in chunk:
                w_width = fm.horizontalAdvance(w)
                needed = w_width + (space_w if line_has_words else 0)
                if line_has_words and (line_w + needed) > max_w:
                    count += 1
                    line_w = w_width
                    line_has_words = True
                else:
                    line_w += needed
                    line_has_words = True
        if line_has_words:
            count += 1
        return count

    def _begin_fade(self):
        """Start the morph dissolve animation."""
        self._fading = True
        self._fade_start = time.time()
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def _anim_tick(self):
        """Drive smooth scroll and fade-out at 60fps."""
        needs_update = False

        # Smooth scroll interpolation
        diff = self._scroll_target - self._scroll_y
        if abs(diff) > 0.5:
            self._scroll_y += diff * self._SCROLL_SPEED
            needs_update = True
        elif abs(diff) > 0.01:
            self._scroll_y = self._scroll_target
            needs_update = True

        # Fade-out animation
        if self._fading:
            elapsed = (time.time() - self._fade_start) * 1000.0
            progress = min(1.0, elapsed / self._FADE_MS)
            # Ease-out cubic
            t = 1.0 - progress
            self._opacity = t * t * t
            needs_update = True

            if progress >= 1.0:
                # Fade complete — clear everything
                self._anim_timer.stop()
                self._chunks.clear()
                self._newest_idx = -1
                self._scroll_y = 0.0
                self._scroll_target = 0.0
                self._opacity = 1.0
                self._fading = False
                self.update()
                return

        if needs_update:
            self.update()
        else:
            # Nothing to animate — stop timer to save CPU
            if not self._fading:
                self._anim_timer.stop()

    def paintEvent(self, _):
        if not self._chunks:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setOpacity(self._opacity)

        rect = self.rect().adjusted(12, 4, -12, -4)

        # Semi-transparent background panel for readability
        _bg_col = QColor(0, 5, 12, int(160 * self._opacity))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(_bg_col))
        _r = self.rect().adjusted(4, 2, -4, -2)
        _rr = 6
        p.drawRoundedRect(_r, _rr, _rr)

        # Semi-transparent background panel for readability
        _bg_col = QColor(0, 5, 12, int(160 * self._opacity))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(_bg_col))
        _r = self.rect().adjusted(4, 2, -4, -2)
        _rr = 6
        p.drawRoundedRect(_r, _rr, _rr)
        p.setFont(self._font)
        fm = p.fontMetrics()
        max_w = rect.width() - 16
        space_w = fm.horizontalAdvance(" ")

        # Build all lines: list of (word, color) tuples
        all_lines: list[list[tuple[str, QColor]]] = []
        line: list[tuple[str, QColor]] = []
        line_w = 0

        for ci, chunk in enumerate(self._chunks):
            col = self._active_col if ci == self._newest_idx else self._done_col
            for w in chunk:
                w_width = fm.horizontalAdvance(w)
                needed = w_width + (space_w if line else 0)

                if line and (line_w + needed) > max_w:
                    all_lines.append(line)
                    line = []
                    line_w = 0

                line.append((w, col))
                if line_w > 0:
                    line_w += space_w + w_width
                else:
                    line_w = w_width

        if line:
            all_lines.append(line)

        if not all_lines:
            return

        # Clip to widget area
        p.setClipRect(rect)

        # Draw all lines with scroll offset applied
        base_y = rect.top() + fm.ascent() + 2 - self._scroll_y

        for row_idx, row in enumerate(all_lines):
            y = base_y + row_idx * self._line_h

            # Skip lines that are scrolled out of view
            if y < rect.top() - self._line_h or y > rect.bottom() + self._line_h:
                continue

            total_line_w = sum(fm.horizontalAdvance(w) for w, _ in row) + space_w * max(0, len(row) - 1)
            x = rect.left() + (rect.width() - total_line_w) / 2

            for w, col in row:
                # Glow for active (newest) line
                if col == self._active_col:
                    _gc = QColor(col); _gc.setAlpha(50)
                    for _ox, _oy in [(-1,0),(1,0),(0,-1),(0,1)]:
                        p.setPen(QPen(_gc))
                        p.drawText(QPointF(x + _ox, y + _oy), w)
                if col == self._active_col:
                    _gc = QColor(col); _gc.setAlpha(50)
                    for _ox, _oy in [(-1,0),(1,0),(0,-1),(0,1)]:
                        p.setPen(QPen(_gc))
                        p.drawText(QPointF(x + _ox, y + _oy), w)
                p.setPen(QPen(col))
                p.drawText(QPointF(x, y), w)
                x += fm.horizontalAdvance(w) + space_w
