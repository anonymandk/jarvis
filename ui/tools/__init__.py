"""Research progress, task queue, tool logs, and mission controls."""

from __future__ import annotations

import importlib

_runtime = importlib.import_module("ui._runtime")
globals().update({key: value for key, value in vars(_runtime).items() if not key.startswith("__")})

class ResearchProgressWidget(QWidget):
    """Compact, factual progress surface for a long-running JARVIS task."""

    _update_sig = pyqtSignal(object)
    _hide_sig = pyqtSignal()

    def __init__(
        self,
        parent=None,
        *,
        task_title: str = "PESQUISA APROFUNDADA",
        accessible_name: str = "Progresso da pesquisa aprofundada",
    ):
        super().__init__(parent)
        self.setFixedHeight(106)
        self.setAccessibleName(accessible_name)
        self._task_title = str(task_title or "TASK").upper()
        self._visible_mode = False
        self._question = ""
        self._state = "running"
        self._display_generation = 0
        self._fade_animation = None
        self._update_sig.connect(self._apply_update)
        self._hide_sig.connect(self.hide)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(TOKENS.spacing["legacy_48"], TOKENS.spacing["legacy_2"], TOKENS.spacing["legacy_48"], TOKENS.spacing["legacy_6"])
        outer.setSpacing(TOKENS.spacing["legacy_0"])

        self._shell = QFrame()
        self._shell.setObjectName("researchProgressShell")
        self._shell.setMaximumWidth(820)
        shell_lay = QVBoxLayout(self._shell)
        shell_lay.setContentsMargins(TOKENS.spacing["legacy_16"], TOKENS.spacing["legacy_10"], TOKENS.spacing["legacy_16"], TOKENS.spacing["legacy_10"])
        shell_lay.setSpacing(TOKENS.spacing["legacy_6"])

        header = QHBoxLayout()
        header.setSpacing(TOKENS.spacing["legacy_8"])
        self._title = QLabel(self._task_title)
        self._title.setFont(QFont(UI_FONT, TOKENS.font_sizes["legacy_9"], QFont.Weight.DemiBold))
        header.addWidget(self._title)
        header.addStretch()
        self._status = QLabel("Em segundo plano · 0%")
        self._status.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_8"], QFont.Weight.Medium))
        header.addWidget(self._status)
        shell_lay.addLayout(header)

        self._question_lbl = QLabel("Preparando resumo da pesquisa")
        self._question_lbl.setFont(QFont(UI_FONT, TOKENS.font_sizes["legacy_10"], QFont.Weight.Medium))
        self._question_lbl.setWordWrap(False)
        shell_lay.addWidget(self._question_lbl)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(5)
        self._bar.setAccessibleName("Progresso da pesquisa aprofundada")
        shell_lay.addWidget(self._bar)

        self._phase = QLabel("Na fila")
        self._phase.setFont(QFont(UI_FONT, TOKENS.font_sizes["legacy_8"], QFont.Weight.Normal))
        shell_lay.addWidget(self._phase)

        outer.addStretch()
        outer.addWidget(self._shell, stretch=1)
        outer.addStretch()
        self.refresh_theme()
        self.hide()

    def start(self, question: str, visible: bool = False):
        self._update_sig.emit({
            "question": str(question or self._task_title.title()),
            "percent": 0,
            "phase": "Queued",
            "state": "running",
            "visible": bool(visible),
        })

    def update_progress(
        self,
        question: str,
        percent: int,
        phase: str,
        artifacts: list[str] | None = None,
        warnings: list[str] | None = None,
        visible: bool | None = None,
    ):
        self._update_sig.emit({
            "question": str(question or self._question or self._task_title.title()),
            "percent": max(0, min(100, int(percent or 0))),
            "phase": str(phase or "Researching"),
            "state": "completed" if int(percent or 0) >= 100 else "running",
            "artifacts": list(artifacts or []),
            "warnings": list(warnings or []),
            "visible": self._visible_mode if visible is None else bool(visible),
        })

    def finish(self, state: str, detail: str):
        self._update_sig.emit({
            "question": self._question or self._task_title.title(),
            "percent": self._bar.value(),
            "phase": str(detail or state),
            "state": str(state or "failed").lower(),
        })

    def dismiss(self):
        self._hide_sig.emit()

    def _apply_update(self, update: dict):
        self._question = str(update.get("question") or self._question or self._task_title.title())
        self._state = str(update.get("state") or "running")
        self._visible_mode = bool(update.get("visible", self._visible_mode))
        percent = max(0, min(100, int(update.get("percent", 0) or 0)))
        phase = str(update.get("phase") or "Pesquisando")
        artifacts = update.get("artifacts") or []
        warnings = update.get("warnings") or []

        if self._state == "running" and percent == 0:
            self._display_generation += 1

        self._question_lbl.setText(self._question)
        self._question_lbl.setToolTip(self._question)
        self._bar.setValue(percent)
        if self._state == "completed":
            status_label = "Concluído"
            if artifacts:
                phase = f"Relatório pronto: {Path(str(artifacts[0])).name}"
            if warnings:
                phase += f"  ·  {len(warnings)} aviso(s)"
        elif self._state == "failed":
            status_label = "Falhou"
        elif self._state == "cancelled":
            status_label = "Cancelado"
        else:
            status_label = "Em andamento" if self._visible_mode else "Em segundo plano"
        self._status.setText(f"{status_label}  ·  {percent}%")
        self._phase.setText(phase)
        self.refresh_theme()

        if self.isHidden():
            self.show()
            effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)
            self._fade_animation = QPropertyAnimation(effect, b"opacity", self)
            self._fade_animation.setDuration(TOKENS.motion_ms["legacy_180"])
            self._fade_animation.setStartValue(0.0)
            self._fade_animation.setEndValue(1.0)
            self._fade_animation.setEasingCurve(
                getattr(QEasingCurve.Type, TOKENS.motion_easing["standard"])
            )
            self._fade_animation.start()

        if self._state in {"completed", "failed", "cancelled"}:
            generation = self._display_generation
            QTimer.singleShot(9000, lambda: self._dismiss_if_current(generation))

    def _dismiss_if_current(self, generation: int):
        if generation == self._display_generation:
            self.dismiss()

    def refresh_theme(self):
        state_color = {
            "completed": C.GREEN,
            "failed": C.RED,
            "cancelled": C.ACC,
        }.get(self._state, C.PRI)
        self._shell.setStyleSheet(f"""
            QFrame#researchProgressShell {{
                background: {C.PANEL}; border: 1px solid {C.BORDER_B}; border-radius: {TOKENS.radii['legacy_7']}px;
            }}
        """)
        self._title.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; letter-spacing: {TOKENS.letter_spacing['subtle']}px;")
        self._status.setStyleSheet(f"color: {state_color}; background: transparent;")
        self._question_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        self._phase.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        self._bar.setStyleSheet(f"""
            QProgressBar {{ background: {C.DARK2}; border: none; border-radius: {TOKENS.radii['legacy_2']}px; }}
            QProgressBar::chunk {{ background: {state_color}; border-radius: {TOKENS.radii['legacy_2']}px; }}
        """)


class ToolProgressWidget(QWidget):
    """Shows active tool execution with name, elapsed time, and spinner."""

    _show_sig = pyqtSignal(str)
    _hide_sig = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setStyleSheet(f"""
            QWidget {{
                background: {qss_rgba(C.PURPLE, 24)};
                border: 1px solid {qss_rgba(C.PURPLE, 68)};
                border-radius: {TOKENS.radii['legacy_4']}px;
            }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(TOKENS.spacing["legacy_10"], TOKENS.spacing["legacy_2"], TOKENS.spacing["legacy_10"], TOKENS.spacing["legacy_2"])
        lay.setSpacing(TOKENS.spacing["legacy_6"])

        self._spinner_chars = ["◐", "◓", "◑", "◒"]
        self._spinner_idx = 0

        self._spinner = QLabel("◐")
        self._spinner.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_10"]))
        self._spinner.setStyleSheet(f"color: {C.PURPLE}; background: transparent; border: none;")
        lay.addWidget(self._spinner)

        self._tool_lbl = QLabel("EXECUTING...")
        self._tool_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_8"], QFont.Weight.Bold))
        self._tool_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent; border: none;")
        lay.addWidget(self._tool_lbl, stretch=1)

        self._time_lbl = QLabel("0s")
        self._time_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_7"]))
        self._time_lbl.setStyleSheet(f"color: {C.PURPLE}; background: transparent; border: none;")
        lay.addWidget(self._time_lbl)

        self._start_time = 0.0
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._tick)

        self._show_sig.connect(self._on_show)
        self._hide_sig.connect(self._on_hide)
        self.hide()

    def show_tool(self, name: str):
        self._show_sig.emit(name)

    def hide_tool(self):
        self._hide_sig.emit()

    def _on_show(self, name: str):
        self._tool_lbl.setText(f"EXECUTING: {name.upper()}")
        self._start_time = time.time()
        self._spinner_idx = 0
        self._tmr.start(200)
        window = self.window()
        if getattr(window, "_command_center_open", True):
            self.show()

    def _on_hide(self):
        self._tmr.stop()
        self.hide()

    def _tick(self):
        self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_chars)
        self._spinner.setText(self._spinner_chars[self._spinner_idx])
        elapsed = time.time() - self._start_time
        if elapsed < 60:
            self._time_lbl.setText(f"{elapsed:.0f}s")
        else:
            m = int(elapsed // 60)
            s = int(elapsed % 60)
            self._time_lbl.setText(f"{m}m {s}s")


class TaskQueueWidget(QWidget):
    """Displays a live task queue parsed from JARVIS log messages."""

    _sig = pyqtSignal(str, str)  # (task_name, status)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks: list[dict] = []   # {name, status, ts}
        self._sig.connect(self._on_task)
        self.setStyleSheet("background: transparent;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"])
        lay.setSpacing(TOKENS.spacing["legacy_3"])

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._c_lay = QVBoxLayout(self._container)
        self._c_lay.setContentsMargins(TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"])
        self._c_lay.setSpacing(TOKENS.spacing["legacy_3"])
        self._c_lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(self._container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {C.BG}; width: 6px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_B}; border-radius: {TOKENS.radii['legacy_3']}px; min-height: 16px;
            }}
        """)
        lay.addWidget(scroll)
        self._empty_state = QLabel("Nenhuma tarefa em andamento. A atividade aparecerá aqui.", self)
        self._empty_state.setWordWrap(True)
        self._empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_state.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; padding: {TOKENS.spacing['legacy_10']}px;")
        lay.addWidget(self._empty_state)

    def push_task(self, name: str, status: str):
        self._sig.emit(name, status)

    def _on_task(self, name: str, status: str):
        # Update existing or add new
        for t in self._tasks:
            if t["name"] == name:
                t["status"] = status
                self._rebuild()
                return
        self._tasks.append({"name": name, "status": status, "ts": time.strftime("%H:%M:%S")})
        if len(self._tasks) > 20:
            self._tasks.pop(0)
        self._rebuild()

    def _rebuild(self):
        self._empty_state.setVisible(not self._tasks)
        # Clear layout
        while self._c_lay.count() > 1:
            item = self._c_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        STATUS_COLORS = {
            "active":  (C.ACC,    "▶"),
            "done":    (C.GREEN,  "✓"),
            "error":   (C.RED,    "✗"),
            "pending": (C.TEXT_DIM, "○"),
            "calling": (C.PURPLE, "◈"),
        }

        for task in reversed(self._tasks[-12:]):
            col, sym = STATUS_COLORS.get(task["status"], (C.TEXT_MED, "·"))
            row = QWidget()
            row.setStyleSheet(f"""
                QWidget {{
                    background: {C.CARD};
                    border: 1px solid {C.BORDER};
                    border-left: 2px solid {col};
                    border-radius: {TOKENS.radii['legacy_4']}px;
                }}
            """)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(TOKENS.spacing["legacy_6"], TOKENS.spacing["legacy_3"], TOKENS.spacing["legacy_6"], TOKENS.spacing["legacy_3"])
            rl.setSpacing(TOKENS.spacing["legacy_6"])

            sym_lbl = QLabel(sym)
            sym_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_8"], QFont.Weight.Bold))
            sym_lbl.setStyleSheet(f"color: {col}; background: transparent; border: none;")
            sym_lbl.setFixedWidth(12)
            rl.addWidget(sym_lbl)

            name_lbl = QLabel(task["name"][:28])
            name_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_8"]))
            name_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent; border: none;")
            rl.addWidget(name_lbl, stretch=1)

            ts_lbl = QLabel(task["ts"])
            ts_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["caption"]))
            ts_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")
            rl.addWidget(ts_lbl)

            self._c_lay.insertWidget(self._c_lay.count() - 1, row)


class ToolLogWidget(QWidget):
    """Displays tool execution log with color-coded status."""

    _sig = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[dict] = []
        self._sig.connect(self._on_entry)
        self.setStyleSheet("background: transparent;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"])
        lay.setSpacing(TOKENS.spacing["legacy_3"])

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._c_lay = QVBoxLayout(self._container)
        self._c_lay.setContentsMargins(TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"])
        self._c_lay.setSpacing(TOKENS.spacing["legacy_3"])
        self._c_lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(self._container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {C.BG}; width: 6px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_B}; border-radius: {TOKENS.radii['legacy_3']}px; min-height: 16px;
            }}
        """)
        lay.addWidget(scroll)
        self._empty_state = QLabel("Nenhuma ferramenta em execução. As ações aparecerão aqui.", self)
        self._empty_state.setWordWrap(True)
        self._empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_state.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; padding: {TOKENS.spacing['legacy_10']}px;")
        lay.addWidget(self._empty_state)

    def push(self, text: str):
        self._sig.emit(text)

    def _on_entry(self, text: str):
        self._entries.append({"text": text, "ts": time.strftime("%H:%M:%S")})
        if len(self._entries) > 30:
            self._entries.pop(0)
        self._rebuild()

    def _rebuild(self):
        self._empty_state.setVisible(not self._entries)
        while self._c_lay.count() > 1:
            item = self._c_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for entry in reversed(self._entries[-15:]):
            txt = entry["text"]
            # Color-code by content
            if "✓" in txt or "done" in txt.lower() or "→" in txt:
                col = C.GREEN
            elif "❌" in txt or "error" in txt.lower() or "fail" in txt.lower():
                col = C.RED
            elif "🔧" in txt or "📞" in txt or "calling" in txt.lower():
                col = C.PURPLE
            elif "⚠" in txt:
                col = C.ACC
            else:
                col = C.TEXT_MED

            row = QWidget()
            row.setStyleSheet(f"""
                QWidget {{
                    background: {C.CARD};
                    border: 1px solid {C.BORDER};
                    border-left: 2px solid {col};
                    border-radius: {TOKENS.radii['legacy_4']}px;
                }}
            """)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(TOKENS.spacing["legacy_6"], TOKENS.spacing["legacy_3"], TOKENS.spacing["legacy_6"], TOKENS.spacing["legacy_3"])
            rl.setSpacing(TOKENS.spacing["legacy_6"])

            ts_lbl = QLabel(entry["ts"])
            ts_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_7"]))
            ts_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")
            ts_lbl.setFixedWidth(44)
            rl.addWidget(ts_lbl)

            msg_lbl = QLabel(txt[:40])
            msg_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["caption"]))
            msg_lbl.setWordWrap(True)
            msg_lbl.setStyleSheet(f"color: {col}; background: transparent; border: none;")
            rl.addWidget(msg_lbl, stretch=1)

            self._c_lay.insertWidget(self._c_lay.count() - 1, row)


class MissionControlPanel(QWidget):
    """
    Tabbed mission-control right panel with:
      COMMS | TASKS | ASSETS | TOOLS
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"])
        outer.setSpacing(TOKENS.spacing["legacy_0"])

        # ── Tab bar ──────────────────────────────────────────────────────────
        tab_bar = QWidget()
        self._tab_bar = tab_bar
        tab_bar.setFixedHeight(32)
        tab_bar.setStyleSheet(f"""
            QWidget {{
                background: {C.DARK};
                border-bottom: 1px solid {C.BORDER};
            }}
        """)
        tb_lay = QHBoxLayout(tab_bar)
        tb_lay.setContentsMargins(TOKENS.spacing["legacy_4"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_4"], TOKENS.spacing["legacy_0"])
        tb_lay.setSpacing(TOKENS.spacing["legacy_2"])

        self._tabs: list[QPushButton] = []
        self._tab_names = ["Logs", "Tarefas", "Arquivos", "Ferramentas"]
        self._active_tab = 0

        for i, name in enumerate(self._tab_names):
            btn = QPushButton(name)
            btn.setMinimumHeight(40)
            btn.setAccessibleName(name)
            btn.setFont(QFont(DISPLAY_FONT, TOKENS.font_sizes["legacy_8"], QFont.Weight.DemiBold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._switch_tab(idx))
            self._tabs.append(btn)
            tb_lay.addWidget(btn)

        outer.addWidget(tab_bar)

        # ── Stacked pages ────────────────────────────────────────────────────
        from PyQt6.QtWidgets import QStackedWidget
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")
        outer.addWidget(self._stack, stretch=1)

        # Page 0: COMMS — conversation log
        self.log_widget = LogWidget()
        self._stack.addWidget(self.log_widget)

        # Page 1: TASKS — task queue
        self.task_widget = TaskQueueWidget()
        self._stack.addWidget(self.task_widget)

        # Page 2: ASSETS — file drop zone (built externally, placeholder here)
        self._assets_page = QWidget()
        self._assets_page.setStyleSheet("background: transparent;")
        self._stack.addWidget(self._assets_page)

        # Page 3: TOOLS — tool execution log
        self.tool_widget = ToolLogWidget()
        self._stack.addWidget(self.tool_widget)

        self._switch_tab(0)

    def set_command_center_open(self, is_open: bool):
        """Keep chat visible in focus mode; reveal all mission tools on demand."""
        self._tab_bar.setVisible(is_open)
        if not is_open:
            self._switch_tab(0)

    def refresh_theme(self):
        self._tab_bar.setStyleSheet(f"""
            QWidget {{ background: {C.DARK}; border-bottom: 1px solid {C.BORDER}; }}
        """)
        self._switch_tab(self._active_tab)
        if hasattr(self.log_widget, "refresh_theme"):
            self.log_widget.refresh_theme()

    def _switch_tab(self, idx: int):
        self._active_tab = idx
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._tabs):
            if i == idx:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {C.PRI_GHO};
                        color: {C.PRI};
                        border: 2px solid {C.PRI};
                        border-bottom: 2px solid {C.PRI};
                        border-radius: {TOKENS.radii['legacy_3']}px;
                        padding: {TOKENS.spacing['legacy_0']}px {TOKENS.spacing['legacy_6']}px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {C.TEXT_DIM};
                        border: none;
                        border-radius: {TOKENS.radii['legacy_3']}px;
                        padding: {TOKENS.spacing['legacy_0']}px {TOKENS.spacing['legacy_6']}px;
                    }}
                    QPushButton:hover {{
                        color: {C.TEXT_MED};
                        background: {C.PRI_GHO};
                    }}
                    QPushButton:focus {{
                        color: {C.WHITE};
                        border: 2px solid {C.PRI};
                    }}
                """)

    def set_assets_widget(self, w: QWidget):
        """Called from _build_right_panel to inject the FileDropZone page."""
        lay = QVBoxLayout(self._assets_page)
        lay.setContentsMargins(TOKENS.spacing["legacy_8"], TOKENS.spacing["legacy_8"], TOKENS.spacing["legacy_8"], TOKENS.spacing["legacy_8"])
        lay.setSpacing(TOKENS.spacing["legacy_6"])
        lay.addWidget(w)
        lay.addStretch()
