"""420×640 floating JARVIS compact experience."""

from __future__ import annotations

import importlib

_runtime = importlib.import_module("ui._runtime")
globals().update({key: value for key, value in vars(_runtime).items() if not key.startswith("__")})


class CompactModeWidget(QWidget):
    """Focused operator surface with conversation, core state, and direct input."""

    expand_requested = pyqtSignal()

    _STATES = {
        "IDLE": ("Em espera", "◇", "TEXT_MED"),
        "LISTENING": ("Ouvindo", "◖", "GREEN"),
        "THINKING": ("Processando", "◈", "PURPLE"),
        "PROCESSING": ("Processando", "◈", "PURPLE"),
        "SPEAKING": ("Falando", "◉", "PRI"),
        "RECONNECTING": ("Reconectando", "↻", "AMBER"),
        "ERROR": ("Erro", "!", "RED"),
        "MUTED": ("Microfone silenciado", "⌁", "TEXT_DIM"),
    }

    def __init__(
        self,
        parent=None,
        *,
        on_send=None,
        on_mute=None,
        graphics_quality: str = "medium",
        reduced_motion: bool = False,
        muted: bool = False,
    ):
        super().__init__(parent)
        from ui.hud.orb import ActivityVisualizer, ReactorOrb
        from ui.surfaces.connection import ConnectionStatusCard

        self._on_send = on_send
        self._on_mute = on_mute
        self._muted = bool(muted)
        self._state = "IDLE"
        self._recent_logs: list[str] = []
        self._closing_without_restore = False
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(
            TOKENS.layout_sizes["compact_width"], TOKENS.layout_sizes["compact_height"],
        )
        self.setAccessibleName("JARVIS compacto")
        self.setWindowTitle("JARVIS compacto")
        self.setStyleSheet(f"background: {C.BG}; color: {C.WHITE};")

        root = QVBoxLayout(self)
        root.setContentsMargins(
            TOKENS.spacing["lg"], TOKENS.spacing["md"],
            TOKENS.spacing["lg"], TOKENS.spacing["md"],
        )
        root.setSpacing(TOKENS.spacing["legacy_6"])

        header = QHBoxLayout()
        brand = QLabel("JARVIS")
        brand.setFont(QFont(UI_FONT, TOKENS.font_sizes["title"], QFont.Weight.DemiBold))
        brand.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        header.addWidget(brand)
        header.addStretch()
        self._expand_btn = QPushButton("Abrir janela")
        self._expand_btn.setAccessibleName("Voltar à janela completa")
        self._expand_btn.setMinimumSize(
            TOKENS.layout_sizes["compact_header_action_width"], TOKENS.layout_sizes["control_target"],
        )
        self._expand_btn.clicked.connect(self.expand_requested.emit)
        header.addWidget(self._expand_btn)
        root.addLayout(header)

        self._connection = ConnectionStatusCard(compact=True)
        root.addWidget(self._connection)

        center = QHBoxLayout()
        center.addStretch()
        self._orb = ReactorOrb(graphics_quality=graphics_quality, reduced_motion=reduced_motion)
        orb_size = TOKENS.layout_sizes["compact_orb"]
        self._orb.setFixedSize(orb_size, orb_size)
        center.addWidget(self._orb)
        center.addStretch()
        root.addLayout(center)

        self._state_label = QLabel("◇  Em espera")
        self._state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._state_label.setFont(QFont(UI_FONT, TOKENS.font_sizes["section"], QFont.Weight.DemiBold))
        self._state_label.setAccessibleName("Estado atual do JARVIS")
        root.addWidget(self._state_label)

        visualizer_row = QHBoxLayout()
        visualizer_row.addStretch()
        self._visualizer = ActivityVisualizer(graphics_quality=graphics_quality, reduced_motion=reduced_motion)
        self._visualizer.setFixedSize(
            TOKENS.layout_sizes["compact_visualizer_width"],
            TOKENS.layout_sizes["compact_visualizer_height"],
        )
        visualizer_row.addWidget(self._visualizer)
        activity_note = QLabel("Atividade · sem nível medido")
        activity_note.setAccessibleName("Atividade visual, sem nível de áudio medido")
        activity_note.setFont(QFont(UI_FONT, TOKENS.font_sizes["caption"]))
        activity_note.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        visualizer_row.addWidget(activity_note)
        visualizer_row.addStretch()
        root.addLayout(visualizer_row)

        self._transcript = QTextEdit()
        self._transcript.setReadOnly(True)
        self._transcript.setAccessibleName("Conversa desta sessão")
        self._transcript.setPlaceholderText("As mensagens desta sessão aparecem aqui.")
        self._transcript.setStyleSheet(f"""
            QTextEdit {{
                background: {C.PANEL}; color: {C.WHITE};
                border: 1px solid {C.BORDER}; border-radius: {TOKENS.radii['md']}px;
                padding: {TOKENS.spacing['sm']}px;
                font-size: {TOKENS.font_sizes['body']}px;
            }}
        """)
        root.addWidget(self._transcript, stretch=1)

        self._tool_summary = QLabel("Ferramentas · estado não publicado pelo cliente")
        self._tool_summary.setAccessibleName("Estado das ferramentas")
        self._tool_summary_text = "Ferramentas · estado não publicado pelo cliente"
        self._tool_summary.setMinimumHeight(TOKENS.layout_sizes["compact_tool_summary_height"])
        self._tool_summary.setWordWrap(True)
        self._tool_summary.setStyleSheet(f"""
            QLabel {{ background: {C.PANEL}; color: {C.TEXT_MED};
                border-left: 2px solid {C.BORDER_B}; border-radius: {TOKENS.radii['sm']}px;
                padding: {TOKENS.spacing['sm']}px; }}
        """)
        root.addWidget(self._tool_summary)

        input_row = QHBoxLayout()
        input_row.setSpacing(TOKENS.spacing["xs"])
        self._input = QLineEdit()
        self._input.setAccessibleName("Mensagem para JARVIS")
        self._input.setPlaceholderText("Escreva uma mensagem")
        self._input.setMinimumHeight(TOKENS.layout_sizes["control_target"])
        self._input.returnPressed.connect(self._send)
        self._input.setStyleSheet(f"""
            QLineEdit {{ background: {C.DARK}; color: {C.WHITE};
                border: 1px solid {C.BORDER}; border-radius: {TOKENS.radii['sm']}px;
                padding: {TOKENS.spacing['legacy_0']}px {TOKENS.spacing['sm']}px; }}
            QLineEdit:focus {{ border: 2px solid {C.PRI}; }}
        """)
        input_row.addWidget(self._input, stretch=1)
        self._send_btn = QPushButton("Enviar")
        self._send_btn.setAccessibleName("Enviar mensagem")
        self._send_btn.setMinimumSize(
            TOKENS.layout_sizes["compact_send_button_width"], TOKENS.layout_sizes["control_target"],
        )
        self._send_btn.clicked.connect(self._send)
        input_row.addWidget(self._send_btn)
        root.addLayout(input_row)

        footer = QHBoxLayout()
        self._mute_btn = QPushButton()
        self._mute_btn.setMinimumSize(
            TOKENS.layout_sizes["compact_mute_button_width"], TOKENS.layout_sizes["control_target"],
        )
        self._mute_btn.clicked.connect(self._toggle_mute)
        footer.addWidget(self._mute_btn)
        footer.addStretch()
        footer_hint = QLabel("Ctrl+M · modo compacto")
        footer_hint.setFont(QFont(UI_FONT, TOKENS.font_sizes["caption"]))
        footer_hint.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        footer.addWidget(footer_hint)
        root.addLayout(footer)
        self._refresh_controls()

    def set_state(self, state: str):
        value = str(state or "IDLE").strip().upper()
        self._state = value if value in self._STATES else "IDLE"
        label, icon, color_role = self._STATES[self._state]
        color = getattr(C, color_role)
        self._state_label.setText(f"{icon}  {label}")
        self._state_label.setStyleSheet(f"color: {color}; background: transparent;")
        self._state_label.setAccessibleDescription(f"Estado atual: {label}")
        if self._state == "ERROR":
            self._tool_summary.setText(
                "Erro sinalizado pelo cliente. Abra a janela completa e consulte Logs."
            )
            self._tool_summary.setAccessibleName("Orientação para recuperar de um erro")
        else:
            self._tool_summary.setText(self._tool_summary_text)
            self._tool_summary.setAccessibleName("Estado das ferramentas")
        self._orb.set_state(self._state.lower())
        self._visualizer.set_state(self._state.lower())

    def set_graphics_quality(self, quality: str):
        self._orb.set_graphics_quality(quality)
        self._visualizer.set_graphics_quality(quality)

    def set_reduced_motion(self, enabled: bool):
        self._orb.set_reduced_motion(enabled)
        self._visualizer.set_reduced_motion(enabled)

    def append_log(self, message: str):
        from PyQt6.QtGui import QTextCursor

        clean = str(message or "").strip()
        lower = clean.lower()
        if lower.startswith(("you:", "jarvis:", "err:")):
            self._recent_logs.append(clean)
            self._recent_logs = self._recent_logs[-3:]
            localized = [
                f"Você:{entry[4:]}" if entry.lower().startswith("you:") else
                f"Erro:{entry[4:]}" if entry.lower().startswith("err:") else entry
                for entry in self._recent_logs
            ]
            self._transcript.setPlainText("\n\n".join(localized))
            cursor = self._transcript.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self._transcript.setTextCursor(cursor)

    def set_tool_summary(self, text: str):
        self._tool_summary_text = str(text or "Ferramentas · estado não publicado pelo cliente")
        if self._state != "ERROR":
            self._tool_summary.setText(self._tool_summary_text)

    def _send(self):
        message = self._input.text().strip()
        if message and self._on_send is not None:
            self._input.clear()
            self._on_send(message)

    def _toggle_mute(self):
        if self._on_mute is not None:
            self._on_mute()

    def set_muted(self, muted: bool):
        self._muted = bool(muted)
        self._refresh_controls()

    def refresh_theme(self):
        self.setStyleSheet(f"background: {C.BG}; color: {C.WHITE};")
        self._connection.refresh_theme()
        self._transcript.setStyleSheet(f"""
            QTextEdit {{ background: {C.PANEL}; color: {C.WHITE};
                border: 1px solid {C.BORDER}; border-radius: {TOKENS.radii['md']}px;
                padding: {TOKENS.spacing['sm']}px; font-size: {TOKENS.font_sizes['body']}px; }}
        """)
        self._tool_summary.setStyleSheet(f"""
            QLabel {{ background: {C.PANEL}; color: {C.TEXT_MED};
                border-left: 2px solid {C.BORDER_B}; border-radius: {TOKENS.radii['sm']}px;
                padding: {TOKENS.spacing['sm']}px; }}
        """)
        self._refresh_controls()
        self._orb.update()
        self._visualizer.update()
        self.set_state(self._state)

    def _refresh_controls(self):
        label = "Ativar microfone" if self._muted else "Silenciar microfone"
        self._mute_btn.setText(label)
        self._mute_btn.setAccessibleName(label)
        self._mute_btn.setStyleSheet(f"""
            QPushButton {{ background: {C.PANEL}; color: {C.WHITE};
                border: 1px solid {C.BORDER_B}; border-radius: {TOKENS.radii['sm']}px; }}
            QPushButton:hover, QPushButton:focus {{ border: 2px solid {C.PRI}; }}
        """)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{ background: {C.PRI}; color: {C.BG}; font-weight: {TOKENS.font_weights['semibold']};
                border: 1px solid {C.PRI}; border-radius: {TOKENS.radii['sm']}px; }}
            QPushButton:hover, QPushButton:focus {{ background: {C.ENERGY}; border: 2px solid {C.WHITE}; }}
        """)
        self._expand_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: {TOKENS.radii['sm']}px; }}
            QPushButton:hover, QPushButton:focus {{ color: {C.WHITE}; border: 2px solid {C.PRI}; }}
        """)

    def close_without_restore(self):
        self._closing_without_restore = True
        self.close()

    def closeEvent(self, event):
        if not self._closing_without_restore:
            self.expand_requested.emit()
        event.accept()
