"""Mainwindowlayout main-window behavior."""

from __future__ import annotations

import importlib

_runtime = importlib.import_module("ui._runtime")
globals().update({key: value for key, value in vars(_runtime).items() if not key.startswith("__")})

class _MainWindowLayoutMixin:
    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setObjectName("appHeader")
        w.setAccessibleName("Barra superior JARVIS")
        w.setFixedHeight(TOKENS.layout_sizes["desktop_header_height"])
        w.setStyleSheet(f"""
            QWidget#appHeader {{
                background: {C.PANEL};
                border-bottom: 1px solid {C.BORDER};
            }}
        """)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(
            TOKENS.spacing["legacy_20"], TOKENS.spacing["legacy_0"],
            TOKENS.spacing["lg"], TOKENS.spacing["legacy_0"],
        )
        lay.setSpacing(TOKENS.spacing["lg"])

        brand_col = QVBoxLayout()
        brand_col.setSpacing(TOKENS.spacing["xxs"])
        brand_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._header_brand_lbl = QLabel("JARVIS")
        self._header_brand_lbl.setObjectName("headerTitle")
        self._header_brand_lbl.setFont(QFont(UI_FONT, TOKENS.font_sizes["title"], QFont.Weight.DemiBold))
        self._header_brand_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        brand_col.addWidget(self._header_brand_lbl)
        self._header_mark_lbl = QLabel("Gemini Live")
        self._header_mark_lbl.setObjectName("headerMeta")
        self._header_mark_lbl.setFont(QFont(UI_FONT, TOKENS.font_sizes["caption"], QFont.Weight.Medium))
        self._header_mark_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        brand_col.addWidget(self._header_mark_lbl)
        lay.addLayout(brand_col)
        lay.addStretch()

        self._header_state_lbl = QLabel("◇  Em espera")
        self._header_state_lbl.setAccessibleName("Estado atual do JARVIS")
        self._header_state_lbl.setFont(QFont(UI_FONT, TOKENS.font_sizes["body"], QFont.Weight.DemiBold))
        self._header_state_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        lay.addWidget(self._header_state_lbl)
        self._header_mode_lbl = QLabel("Gemini Live · conexão —")
        self._header_mode_lbl.setAccessibleName("Estado da conexão não publicado pelo cliente")
        self._header_mode_lbl.setFont(QFont(UI_FONT, TOKENS.font_sizes["caption"]))
        self._header_mode_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        lay.addWidget(self._header_mode_lbl)
        lay.addStretch()

        right_col = QVBoxLayout()
        right_col.setSpacing(TOKENS.spacing["xxs"])
        right_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._clock_lbl = QLabel("00:00:00")
        self._clock_lbl.setAccessibleName("Horário local")
        self._clock_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["body"], QFont.Weight.Medium))
        self._clock_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        self._clock_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._clock_lbl)
        self._date_lbl = QLabel("")
        self._date_lbl.setFont(QFont(UI_FONT, TOKENS.font_sizes["caption"]))
        self._date_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._date_lbl)
        lay.addLayout(right_col)

        self._utility_btn = QPushButton("⚙")
        self._utility_btn.setAccessibleName("Abrir menu de configurações")
        self._utility_btn.setFixedSize(44, 44)
        self._utility_btn.setToolTip("Configurações e janela")
        self._utility_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._utility_menu = QMenu(self._utility_btn)
        self._utility_menu.addAction("Tela cheia", self._toggle_fullscreen)
        self._utility_menu.addAction("Configurações", self._show_settings)
        self._utility_menu.addAction("Modo compacto", self._toggle_compact_mode)
        self._utility_menu.addAction("Resumo do sistema", self._show_left_panel_popup)
        self._utility_menu.addSeparator()
        self._utility_menu.addAction("Atalhos de teclado", self._toggle_shortcuts_overlay)
        self._utility_menu.addAction("Visão focada", lambda: self._set_command_center(False))
        self._utility_btn.setMenu(self._utility_menu)
        lay.addWidget(self._utility_btn)
        self._style_header()
        return w

    def _tick_clock(self):
        _colon = ":" if int(time.time()) % 2 == 0 else " "
        self._clock_lbl.setText(time.strftime("%H") + _colon + time.strftime("%M") + _colon + time.strftime("%S"))
        now = time.localtime()
        weekdays = ("SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM")
        months = ("JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ")
        self._date_lbl.setText(f"{weekdays[now.tm_wday]} {now.tm_mday:02d} {months[now.tm_mon - 1]} {now.tm_year}")
        if hasattr(self, "_utc_lbl"):
            import datetime
            _off = datetime.datetime.now(datetime.timezone.utc).strftime("%z")
            self._utc_lbl.setText(f"UTC {_off[:3]}:{_off[3:]}")

    def _build_left_panel(self) -> QWidget:
        rail = QFrame()
        rail.setObjectName("navigationRail")
        rail.setFixedWidth(_NAV_W)
        rail.setAccessibleName("Navegação principal")
        rail.setStyleSheet(f"""
            QFrame#navigationRail {{
                background: {C.PANEL};
                border-right: 1px solid {C.BORDER};
            }}
        """)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(
            TOKENS.spacing["sm"], TOKENS.spacing["legacy_14"],
            TOKENS.spacing["sm"], TOKENS.spacing["md"],
        )
        layout.setSpacing(TOKENS.spacing["sm"])

        mark = QLabel("J")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setAccessibleName("JARVIS")
        mark.setFont(QFont(DISPLAY_FONT, TOKENS.font_sizes["title"], QFont.Weight.DemiBold))
        mark.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        layout.addWidget(mark)
        layout.addSpacing(TOKENS.spacing["sm"])

        nav_items = (
            ("◌", "Conversa", lambda: self._focus_conversation(), None),
            ("▤", "Tarefas", lambda: self._navigate_to_mission_tab(1), 1),
            ("⌘", "Ferramentas", lambda: self._navigate_to_mission_tab(3), 3),
            ("≡", "Logs", lambda: self._navigate_to_mission_tab(0), 0),
            ("▧", "Arquivos", lambda: self._navigate_to_mission_tab(2), 2),
        )
        self._nav_buttons: list[QPushButton] = []
        for icon, label, callback, tab_index in nav_items:
            button = QPushButton(icon)
            button.setAccessibleName(label)
            button.setToolTip(label)
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            button.setFixedSize(
                TOKENS.layout_sizes["navigation_button_target"],
                TOKENS.layout_sizes["navigation_button_target"],
            )
            button.setFont(QFont(UI_FONT, TOKENS.font_sizes["section"], QFont.Weight.Medium))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(callback)
            self._nav_buttons.append(button)
            layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._nav_buttons[0].setChecked(True)

        layout.addStretch()
        settings = QPushButton("⚙")
        settings.setAccessibleName("Abrir configurações")
        settings.setToolTip("Configurações")
        settings.setFixedSize(
            TOKENS.layout_sizes["navigation_button_target"],
            TOKENS.layout_sizes["navigation_button_target"],
        )
        settings.setFont(QFont(UI_FONT, TOKENS.font_sizes["section"], QFont.Weight.Medium))
        settings.setCursor(Qt.CursorShape.PointingHandCursor)
        settings.clicked.connect(self._show_settings)
        layout.addWidget(settings, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._nav_settings_btn = settings
        self._style_navigation_rail()
        return rail

    def _style_navigation_rail(self):
        for button in getattr(self, "_nav_buttons", []):
            selected = button.isChecked()
            button.setStyleSheet(f"""
                QPushButton {{
                    background: {C.PRI_GHO if selected else 'transparent'};
                    color: {C.PRI if selected else C.TEXT_MED};
                    border: 1px solid {C.PRI_DIM if selected else 'transparent'};
                    border-radius: {TOKENS.radii['md']}px;
                }}
                QPushButton:hover, QPushButton:focus {{
                    color: {C.WHITE}; border: 2px solid {C.PRI};
                }}
            """)
        settings = getattr(self, "_nav_settings_btn", None)
        if settings is not None:
            settings.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {C.TEXT_MED};
                    border: 1px solid transparent; border-radius: {TOKENS.radii['md']}px; }}
                QPushButton:hover, QPushButton:focus {{ color: {C.WHITE}; border: 2px solid {C.PRI}; }}
            """)

    def _navigate_to_mission_tab(self, index: int):
        if hasattr(self, "_mission"):
            self._mission._switch_tab(index)
        selected_label = {
            0: "Logs", 1: "Tarefas", 2: "Arquivos", 3: "Ferramentas",
        }.get(index)
        for button in getattr(self, "_nav_buttons", []):
            button.setChecked(button.accessibleName() == selected_label)
        self._style_navigation_rail()

    def _focus_conversation(self):
        if hasattr(self, "_chat_bubble"):
            self._chat_bubble._input.setFocus(Qt.FocusReason.ShortcutFocusReason)
        for button in getattr(self, "_nav_buttons", []):
            button.setChecked(button is self._nav_buttons[0])
        self._style_navigation_rail()

    def _build_transcript_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("transcriptPanel")
        panel.setAccessibleName("Conversa desta sessão")
        panel.setStyleSheet(f"background: {C.BG};")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(
            TOKENS.spacing["md"], TOKENS.spacing["legacy_14"],
            TOKENS.spacing["md"], TOKENS.spacing["md"],
        )
        layout.setSpacing(TOKENS.spacing["legacy_10"])

        heading = QHBoxLayout()
        title = QLabel("Conversa")
        title.setFont(QFont(UI_FONT, TOKENS.font_sizes["title"], QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        heading.addWidget(title)
        heading.addStretch()
        session = QLabel("Sessão atual")
        session.setAccessibleName("Mensagens da sessão atual")
        session.setFont(QFont(UI_FONT, TOKENS.font_sizes["caption"]))
        session.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        heading.addWidget(session)
        layout.addLayout(heading)

        self._chat_bubble = ChatBubbleWidget()
        self._chat_bubble.command_submitted.connect(self._send)
        self._log = self._chat_bubble
        layout.addWidget(self._chat_bubble, stretch=1)
        return panel

    def _build_legacy_overview(self) -> QWidget:
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
        lay.setContentsMargins(TOKENS.spacing["legacy_10"], TOKENS.spacing["legacy_12"], TOKENS.spacing["legacy_10"], TOKENS.spacing["legacy_10"])
        lay.setSpacing(TOKENS.spacing["legacy_10"])

        rail_title = QLabel("OVERVIEW")
        self._rail_title_lbl = rail_title
        rail_title.setFont(QFont(UI_FONT, TOKENS.font_sizes["legacy_10"], QFont.Weight.DemiBold))
        rail_title.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        lay.addWidget(rail_title)

        nav = QHBoxLayout(); nav.setSpacing(TOKENS.spacing["legacy_4"])
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
        ml.setContentsMargins(TOKENS.spacing["legacy_12"], TOKENS.spacing["legacy_10"], TOKENS.spacing["legacy_12"], TOKENS.spacing["legacy_8"])
        ml.setSpacing(TOKENS.spacing["legacy_3"])

        # Header
        sys_hdr = QLabel("Live system")
        self._system_title_lbl = sys_hdr
        sys_hdr.setFont(QFont(UI_FONT, TOKENS.font_sizes["legacy_9"], QFont.Weight.DemiBold))
        sys_hdr.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        ml.addWidget(sys_hdr)

        # Sparkline metrics — CPU, MEM, NET with live graphs
        self._spark_cpu = SparklineBar("CPU", C.PRI)
        self._spark_mem = SparklineBar("MEM", C.ENERGY)
        self._spark_net = SparklineBar("NET", C.ACC2)
        for spark in [self._spark_cpu, self._spark_mem, self._spark_net]:
            ml.addWidget(spark)
            spark.hide()

        ml.addSpacing(TOKENS.spacing["legacy_6"])

        # ── GPU Block (expanded) ────────────────────────────────────────────
        gpu_super = QLabel("HARDWARE")
        self._hardware_title_lbl = gpu_super
        gpu_super.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_6"]))
        gpu_super.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: {TOKENS.letter_spacing['wide']}px;")
        ml.addWidget(gpu_super)

        gpu_hdr_row = QHBoxLayout()
        gpu_hdr_lbl = QLabel("GPU")
        gpu_hdr_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_9"], QFont.Weight.Bold))
        gpu_hdr_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent; letter-spacing: {TOKENS.letter_spacing['wide']}px;")
        gpu_hdr_row.addWidget(gpu_hdr_lbl)
        gpu_hdr_lbl.hide()
        gpu_hdr_row.addStretch()
        self._gpu_pct_lbl = QLabel("0%")
        self._gpu_pct_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_9"], QFont.Weight.Bold))
        self._gpu_pct_lbl.setStyleSheet(f"color: {C.ENERGY}; background: transparent;")
        gpu_hdr_row.addWidget(self._gpu_pct_lbl)
        self._gpu_pct_lbl.hide()
        ml.addLayout(gpu_hdr_row)

        # chip name
        self._gpu_name_lbl = QLabel("Detecting...")
        self._gpu_name_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_7"]))
        self._gpu_name_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        ml.addWidget(self._gpu_name_lbl)

        ml.addSpacing(TOKENS.spacing["legacy_3"])

        # LOAD label + bar
        gpu_load_hdr = QLabel("LOAD")
        gpu_load_hdr.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_6"]))
        gpu_load_hdr.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: {TOKENS.letter_spacing['subtle']}px;")
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
                border-radius: {TOKENS.radii['legacy_3']}px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C.PRI}, stop:1 {C.ENERGY});
                border-radius: {TOKENS.radii['legacy_3']}px;
            }}
        """)
        ml.addWidget(self._gpu_load_bar)
        self._gpu_load_bar.hide()

        ml.addSpacing(TOKENS.spacing["legacy_3"])

        # VRAM row
        gpu_vram_row = QHBoxLayout()
        vram_lbl = QLabel("VRAM")
        vram_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_6"]))
        vram_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: {TOKENS.letter_spacing['subtle']}px;")
        gpu_vram_row.addWidget(vram_lbl)
        gpu_vram_row.addStretch()
        self._gpu_vram_lbl = QLabel("N/A")
        self._gpu_vram_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_7"], QFont.Weight.Bold))
        self._gpu_vram_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        gpu_vram_row.addWidget(self._gpu_vram_lbl)
        ml.addLayout(gpu_vram_row)

        ml.addSpacing(TOKENS.spacing["legacy_6"])

        # ── TMP sparkline (same style as CPU/MEM/NET) ───────────────────────
        self._spark_tmp = SparklineBar("TMP", C.ACC)
        ml.addWidget(self._spark_tmp)
        self._spark_tmp.hide()

        ml.addSpacing(TOKENS.spacing["legacy_4"])

        # Cognitive load with progress bar
        cog_hdr = QLabel("COGNITIVE LOAD")
        cog_hdr.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_6"], QFont.Weight.Bold))
        cog_hdr.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: {TOKENS.letter_spacing['wide']}px;")
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
        info_row = QHBoxLayout(); info_row.setSpacing(TOKENS.spacing["legacy_4"])
        self._uptime_lbl = QLabel("UP --:--")
        self._uptime_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_6"]))
        self._uptime_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        info_row.addWidget(self._uptime_lbl)
        info_row.addStretch()
        self._session_lbl = QLabel("00:00:00")
        self._session_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_6"]))
        self._session_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        info_row.addWidget(self._session_lbl)
        ml.addLayout(info_row)

        self._proc_lbl = QLabel("PROC  --")
        self._proc_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_6"]))
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
        from ui.surfaces.connection import ConnectionStatusCard

        w = QWidget()
        w.setObjectName("rightRail")
        w.setFixedWidth(_RIGHT_W)
        w.setAccessibleName("Execução, conexão e atividade")
        w.setStyleSheet(f"""
            QWidget#rightRail {{
                background: {C.BG};
                border-left: 1px solid {C.BORDER};
            }}
        """)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(
            TOKENS.spacing["md"], TOKENS.spacing["legacy_14"],
            TOKENS.spacing["md"], TOKENS.spacing["md"],
        )
        lay.setSpacing(TOKENS.spacing["md"])

        self._connection_status = ConnectionStatusCard()
        lay.addWidget(self._connection_status)
        section_title = QLabel("Execução")
        section_title.setFont(QFont(UI_FONT, TOKENS.font_sizes["title"], QFont.Weight.DemiBold))
        section_title.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        lay.addWidget(section_title)

        self._mission = MissionControlPanel()
        self._mission._switch_tab(1)

        # Build assets page content
        assets_inner = QWidget()
        assets_inner.setStyleSheet("background: transparent;")
        al = QVBoxLayout(assets_inner)
        al.setContentsMargins(TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"])
        al.setSpacing(TOKENS.spacing["legacy_6"])
        self._drop_zone = FileDropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)
        al.addWidget(self._drop_zone)
        self._file_hint = QLabel("Nenhum arquivo. Solte um item aqui ou escolha no seletor.")
        self._file_hint.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_7"]))
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
        w.setAccessibleName("Barra de comandos do JARVIS")
        w.setFixedHeight(72)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(TOKENS.spacing["legacy_14"], TOKENS.spacing["legacy_8"], TOKENS.spacing["legacy_14"], TOKENS.spacing["legacy_8"])
        lay.setSpacing(TOKENS.spacing["legacy_12"])

        # ── Rail anchor: identity plus real application state ────────────────
        anchor = QWidget(w)
        anchor.setObjectName("CommandRailAnchor")
        anchor.setFixedWidth(174)
        anchor_lay = QVBoxLayout(anchor)
        anchor_lay.setContentsMargins(TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_1"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_1"])
        anchor_lay.setSpacing(TOKENS.spacing["legacy_2"])

        title_row = QHBoxLayout()
        title_row.setContentsMargins(TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"])
        title_row.setSpacing(TOKENS.spacing["legacy_7"])
        self._rail_status_dot = QLabel("●")
        self._rail_status_dot.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_7"], QFont.Weight.Medium))
        self._rail_status_dot.setAccessibleName("JARVIS status indicator")
        title_row.addWidget(self._rail_status_dot)
        self._command_title_lbl = QLabel("JARVIS")
        self._command_title_lbl.setFont(QFont(UI_FONT, TOKENS.font_sizes["caption"], QFont.Weight.DemiBold))
        title_row.addWidget(self._command_title_lbl)
        title_row.addStretch()
        anchor_lay.addLayout(title_row)

        self._rail_mode_lbl = QLabel("Em espera")
        self._rail_mode_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["caption"], QFont.Weight.Medium))
        self._rail_mode_lbl.setAccessibleName("Estado atual do JARVIS")
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
        track.setAccessibleName("Controles do JARVIS")
        self._rail_control_track = track
        track_lay = QHBoxLayout(track)
        track_lay.setContentsMargins(TOKENS.spacing["legacy_2"], TOKENS.spacing["legacy_2"], TOKENS.spacing["legacy_2"], TOKENS.spacing["legacy_2"])
        track_lay.setSpacing(TOKENS.spacing["legacy_0"])

        def _ctrl_btn(txt, width):
            b = QPushButton(txt)
            b.setFixedSize(width, 40)
            b.setFont(QFont(UI_FONT, TOKENS.font_sizes["caption"], QFont.Weight.DemiBold))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            return b

        def _track_separator():
            separator = QFrame(track)
            separator.setObjectName("CommandRailDivider")
            separator.setFrameShape(QFrame.Shape.VLine)
            separator.setFixedSize(1, 24)
            return separator

        self._mute_btn = QPushButton("Microfone ativo")
        self._mute_btn.setFixedSize(140, 44)
        self._mute_btn.setFont(QFont(UI_FONT, TOKENS.font_sizes["caption"], QFont.Weight.DemiBold))
        self._mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mute_btn.setToolTip("Alternar microfone (F4)")
        self._mute_btn.setAccessibleName("Microfone ativo")
        self._mute_btn.clicked.connect(self._toggle_mute)
        track_lay.addWidget(self._mute_btn)
        track_lay.addWidget(_track_separator())

        self._tts_btn = _ctrl_btn("Voz", 124)
        self._tts_btn.setToolTip("Alterar a voz do JARVIS")
        self._tts_btn.setAccessibleName("Alterar voz do JARVIS")
        self._tts_btn.clicked.connect(self._show_tts_select)
        self._update_tts_btn()
        track_lay.addWidget(self._tts_btn)
        track_lay.addWidget(_track_separator())

        self._name_btn = _ctrl_btn("Nome", 112)
        self._name_btn.setToolTip("Alterar como JARVIS chama você")
        self._name_btn.setAccessibleName("Alterar nome do operador")
        self._name_btn.clicked.connect(self._show_name_signin)
        self._update_name_btn()
        track_lay.addWidget(self._name_btn)
        track_lay.addWidget(_track_separator())

        # Theme cycle button
        self._theme_btn = _ctrl_btn("Tema", 100)
        self._theme_btn.setToolTip("Alternar tema visual")
        self._theme_btn.setAccessibleName("Alternar tema visual")
        self._theme_btn.clicked.connect(self._cycle_theme)
        track_lay.addWidget(self._theme_btn)
        lay.addWidget(track)

        lay.addStretch(1)

        # Hidden shortcut mirrors retain existing keyboard-accessible functions
        # without adding visual noise to the rail.
        shortcut_mirrors = QWidget(w)
        shortcut_mirrors.hide()
        mirror_lay = QHBoxLayout(shortcut_mirrors)
        mirror_lay.setContentsMargins(TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_0"])

        fs_btn = QPushButton("TELA CHEIA", shortcut_mirrors)
        fs_btn.setAccessibleName("Toggle fullscreen")
        fs_btn.setToolTip("Toggle fullscreen (F11)")
        fs_btn.clicked.connect(self._toggle_fullscreen)
        mirror_lay.addWidget(fs_btn)

        compact_btn = QPushButton("COMPACTO", shortcut_mirrors)
        compact_btn.setToolTip("Modo compacto (Ctrl+M)")
        compact_btn.setAccessibleName("Alternar modo compacto")
        compact_btn.clicked.connect(self._toggle_compact_mode)
        mirror_lay.addWidget(compact_btn)

        help_btn = QPushButton("ATALHOS", shortcut_mirrors)
        help_btn.setToolTip("Atalhos de teclado (Ctrl+/)")
        help_btn.setAccessibleName("Mostrar atalhos de teclado")
        help_btn.clicked.connect(self._toggle_shortcuts_overlay)
        mirror_lay.addWidget(help_btn)

        self._quit_btn = QPushButton("Sair")
        self._quit_btn.setObjectName("JarvisQuitButton")
        self._quit_btn.setAccessibleName("Sair do JARVIS")
        self._quit_btn.setToolTip("Sair do JARVIS")
        self._quit_btn.setFixedSize(72, 44)
        self._quit_btn.setFont(QFont(UI_FONT, TOKENS.font_sizes["caption"], QFont.Weight.DemiBold))
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
        lay.setContentsMargins(TOKENS.spacing["legacy_14"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_14"], TOKENS.spacing["legacy_1"])
        lay.setSpacing(TOKENS.spacing["legacy_0"])
        lay.addStretch(1)

        self._maker_signature_lbl = QLabel("amd.creationz™", strip)
        self._maker_signature_lbl.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_7"], QFont.Weight.Medium))
        self._maker_signature_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._maker_signature_lbl.setAccessibleName("amd.creationz trademark")
        self._maker_signature_lbl.setToolTip("JARVIS interface by amd.creationz")
        lay.addWidget(self._maker_signature_lbl)

        self._style_maker_signature()
        return strip
