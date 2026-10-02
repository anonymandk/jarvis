"""Mainwindowlayout main-window behavior."""

from __future__ import annotations

import importlib

_runtime = importlib.import_module("ui._runtime")
globals().update({key: value for key, value in vars(_runtime).items() if not key.startswith("__")})

class _MainWindowLayoutMixin:
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
