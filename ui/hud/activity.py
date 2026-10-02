"""Agent and activity visualization widgets."""

from __future__ import annotations

import importlib

_runtime = importlib.import_module("ui._runtime")
globals().update({key: value for key, value in vars(_runtime).items() if not key.startswith("__")})

class AgentGridWidget(QWidget):
    """
    Vertical timeline agent display – polished JARVIS edition.
    Implements all 12 feedback points: hierarchy, color, spacing, activity stream.
    """

    # ── Per-agent accent colors (points 4 & 9) ──────────────────────────────
    _ACCENT = {
        "CORE":       "#00E5FF",   # brightest cyan  (special)
        "RESEARCH":   "#00E5FF",   # cyan
        "SECURITY":   "#1E90FF",   # blue
        "AUTOMATION": "#FFD700",   # gold
        "MEMORY":     "#BF7FFF",   # purple
        "VISION":     "#00FF7F",   # green
        "DEV":        "#E0E0E0",   # white
        "SYSTEM":     "#00CED1",   # teal
    }

    _STATUS = {
        "CORE":       "PRIMARY",
        "RESEARCH":   "ONLINE",
        "SECURITY":   "ACTIVE",
        "AUTOMATION": "IDLE",
        "MEMORY":     "PROCESSING",
        "VISION":     "ANALYZING",
        "DEV":        "ONLINE",
        "SYSTEM":     "ONLINE",
    }

    _ICONS = {
        "CORE":       "◉",
        "RESEARCH":   "⌕",
        "SECURITY":   "◆",
        "AUTOMATION": "⚡",
        "MEMORY":     "◉",
        "VISION":     "◎",
        "DEV":        "‹›",
        "SYSTEM":     "◈",
    }

    _AGENTS = [
        "CORE",
        "RESEARCH",
        "SECURITY",
        "AUTOMATION",
        "MEMORY",
        "VISION",
        "DEV",
        "SYSTEM",
    ]

    _OBJECTIVES = {
        "CORE":       ["Primary intelligence framework", "Coordinating sub-systems",
                       "Optimizing neural pathways", "Synchronizing agents"],
        "RESEARCH":   ["Scanning knowledge base", "Cross-referencing sources",
                       "Synthesizing findings", "Validating hypotheses"],
        "SECURITY":   ["Monitoring threat vectors", "Scanning network perimeter",
                       "Validating access tokens", "Auditing system logs"],
        "AUTOMATION": ["Executing task pipeline", "Scheduling workflows",
                       "Delegating subtasks", "Optimizing execution path"],
        "MEMORY":     ["Indexing context graph", "Retrieving episodic memory",
                       "Consolidating knowledge", "Pruning stale entries"],
        "VISION":     ["Processing visual input", "Analyzing screen state",
                       "Detecting UI elements", "Mapping spatial context"],
        "DEV":        ["Analyzing code structure", "Tracing dependencies",
                       "Reviewing logic flow", "Generating test cases"],
        "SYSTEM":     ["Monitoring diagnostics", "Tracking resource usage",
                       "Optimizing memory", "Balancing load distribution"],
    }

    # Event log entries for the Activity Stream (point 12)
    _LOG_TEMPLATES = [
        "Memory synchronized",
        "Threat scan complete",
        "Vision detected alignment",
        "Workflow optimized",
        "Knowledge base updated",
        "Security token refreshed",
        "Core cycle completed",
        "Task pipeline flushed",
        "Context graph pruned",
        "Neural pathway calibrated",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        self._agent_state: list[list] = []
        for name in self._AGENTS:
            self._agent_state.append([
                random.uniform(0.55, 0.98),   # [0] confidence
                random.uniform(0, 2 * math.pi),  # [1] phase
                0,                             # [2] obj index
                random.randint(60, 180),       # [3] obj countdown
                "active",                      # [4] status string
            ])

        self._active_idx = 0

        # Activity stream log (point 12)
        self._log_lines: list[str] = []
        self._log_scroll_offset = 0
        self._log_tick = 0
        for i in range(5):
            self._push_log()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(0)

        # ── Super-label (point 7): "COGNITIVE NETWORK" ──────────────────────
        super_lbl = QLabel("COGNITIVE NETWORK")
        super_lbl.setFont(QFont("Courier New", 7))
        super_lbl.setStyleSheet(
            f"color: {C.TEXT_DIM}; background: transparent; "
            "letter-spacing: 3px; opacity: 0.28;"
        )
        lay.addWidget(super_lbl)

        # ── Section header row (point 8: 13 px title) ───────────────────────
        hdr_row = QHBoxLayout()
        hdr = QLabel("AGENTS")
        hdr.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; letter-spacing: 3px;")
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()
        self._active_count_lbl = QLabel(f"{len(self._AGENTS)} ACTIVE")
        self._active_count_lbl.setFont(QFont("Courier New", 7))
        self._active_count_lbl.setStyleSheet(
            f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 1px;"
        )
        hdr_row.addWidget(self._active_count_lbl)
        lay.addLayout(hdr_row)
        lay.addSpacing(4)

        # ── Timeline entries (in scroll area so cards never get squashed) ────
        from PyQt6.QtWidgets import QScrollArea
        scroll_container = QWidget()
        scroll_container.setStyleSheet('background: transparent;')
        scroll_lay = QVBoxLayout(scroll_container)
        scroll_lay.setContentsMargins(0, 0, 0, 0)
        scroll_lay.setSpacing(0)
        self._cards: list[dict] = []
        for i, name in enumerate(self._AGENTS):
            is_core = (name == 'CORE')
            card = self._make_timeline_entry(name, i, is_core)
            scroll_lay.addWidget(card['widget'])
            self._cards.append(card)
        scroll_lay.addStretch()
        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll_container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet('QScrollArea { background: transparent; border: none; }')
        lay.addWidget(scroll_area, stretch=1)
        lay.addSpacing(2)
        # ── Activity Stream (point 12) ───────────────────────────────────────
        stream_super = QLabel("LIVE TELEMETRY")
        stream_super.setFont(QFont("Courier New", 7))
        stream_super.setStyleSheet(
            f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 3px;"
        )
        lay.addWidget(stream_super)

        stream_hdr = QLabel("EVENT LOG")
        stream_hdr.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        stream_hdr.setStyleSheet(
            f"color: {C.PRI}; background: transparent; letter-spacing: 2px;"
        )
        lay.addWidget(stream_hdr)
        lay.addSpacing(4)

        self._log_widget = QLabel()
        self._log_widget.setFont(QFont("Courier New", 7))
        self._log_widget.setStyleSheet(
            f"color: {C.TEXT_MED}; background: transparent; line-height: 160%;"
        )
        self._log_widget.setWordWrap(False)
        lay.addWidget(self._log_widget)

        lay.addStretch()

        # ── Timer ────────────────────────────────────────────────────────────
        self._tick = 0
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._animate)
        self._tmr.start(80)
        # Force immediate first render so CORE is highlighted from frame 1
        QTimer.singleShot(50, self._animate)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _push_log(self):
        import datetime
        t = datetime.datetime.now().strftime("%H:%M")
        msg = random.choice(self._LOG_TEMPLATES)
        self._log_lines.insert(0, f"{t}  {msg}")
        if len(self._log_lines) > 8:
            self._log_lines.pop()

    def _make_timeline_entry(self, name: str, idx: int, is_core: bool) -> dict:
        accent = self._ACCENT.get(name, C.PRI)

        # Uniform card height — CORE distinguished by color not size
        height = 44
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setFixedHeight(height)
        wl = QVBoxLayout(w)
        wl.setContentsMargins(4, 2, 4, 2)
        wl.setSpacing(0)
        wl.setSpacing(0)

        # ── Top row: icon · name · status · conf ────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(6)

        # Single icon only (no separate dot — eliminates double-dot)
        icon_lbl = QLabel(self._ICONS.get(name, "◈"))
        icon_lbl.setFont(QFont("Courier New", 9))
        icon_lbl.setStyleSheet(f"color: {accent}; background: transparent;")
        icon_lbl.setFixedWidth(18)
        top.addWidget(icon_lbl)

        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color: {accent}; background: transparent; letter-spacing: 1px;")
        top.addWidget(name_lbl)

        top.addStretch()

        # Shorten status to 4 chars max to prevent clipping
        _status_map = {"PRIMARY": "PRIM", "ONLINE": "ONLN", "ACTIVE": "ACTV",
                       "IDLE": "IDLE", "PROCESSING": "PROC", "ANALYZING": "ANLZ"}
        _st = _status_map.get(self._STATUS.get(name, "ONLINE"), "ONLN")
        status_lbl = QLabel(_st)
        status_lbl.setFont(QFont("Courier New", 6))
        status_lbl.setStyleSheet(f"color: {accent}; background: transparent; letter-spacing: 1px;")
        status_lbl.setFixedWidth(32)
        top.addWidget(status_lbl)

        conf_lbl = QLabel("92%")
        conf_lbl.setFont(QFont("Courier New", 6))
        conf_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        conf_lbl.setFixedWidth(28)
        top.addWidget(conf_lbl)

        wl.addLayout(top)

        # ── Bottom row: faint │ + objective text aligned under name ────────
        bot = QHBoxLayout()
        bot.setSpacing(4)

        # No connector line — indent only
        line_lbl = QLabel('')
        line_lbl.setFixedWidth(8)
        bot.addWidget(line_lbl)

        # Spacer to align with name (icon width=18 + spacing=6 = 24px offset)
        bot.addSpacing(6)

        obj_lbl = QLabel(self._OBJECTIVES[name][0])
        obj_lbl.setFont(QFont("Courier New", 6))
        obj_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        bot.addWidget(obj_lbl, stretch=1)

        wl.addLayout(bot)

        return {
            "widget":     w,
            "dot":        icon_lbl,   # alias so _animate still works
            "name_lbl":   name_lbl,
            "conf_lbl":   conf_lbl,
            "obj_lbl":    obj_lbl,
            "line_lbl":   line_lbl,
            "icon_lbl":   icon_lbl,
            "status_lbl": status_lbl,
            "accent":     accent,
            "is_core":    is_core,
        }

    def _animate(self):
        self._tick += 1

        # Rotate active agent every 10 s (125 * 80 ms = 10 000 ms)
        if self._tick % 125 == 0:
            self._active_idx = (self._active_idx + 1) % len(self._AGENTS)

        # Push a new log entry every ~3 seconds
        self._log_tick += 1
        if self._log_tick % 38 == 0:
            self._push_log()
            self._log_widget.setText("\n".join(self._log_lines[:5]))

        for i, name in enumerate(self._AGENTS):
            st    = self._agent_state[i]
            conf  = st[0]
            phase = st[1]

            # Pulse sine
            pulse = 0.5 + 0.5 * math.sin(phase + self._tick * 0.08)
            st[1] += 0.01

            # Rotate objective text
            st[3] -= 1
            if st[3] <= 0:
                objs  = self._OBJECTIVES.get(name, ["Operating"])
                st[2] = (st[2] + 1) % len(objs)
                st[3] = random.randint(90, 200)

            # Confidence drift
            conf += random.uniform(-0.02, 0.02)
            conf  = max(0.50, min(0.99, conf))
            st[0] = conf

            card      = self._cards[i]
            is_active = (i == self._active_idx)
            accent    = card["accent"]

            # ── Active agent: full accent color + highlight bg ───────────────
            if is_active:
                name_col   = accent
                conf_col   = accent
                obj_col    = C.TEXT_MED
                dot_col    = accent
                icon_col   = accent
                status_col = accent
                line_col   = accent
                bg_style   = f"background: rgba(0,229,255,18); border-left: 3px solid {accent}; border-radius: 2px;"
            else:
                name_col   = "#5a9090"
                conf_col   = "#3d6a6a"
                obj_col    = "#335858"
                dot_col    = "#3d6a6a"
                icon_col   = "#3d6a6a"
                status_col = "#335858"
                line_col   = "#1a3535"
                bg_style   = "background: transparent; border-left: 2px solid #1a3535;"

            # Apply bg to card widget
            card["widget"].setStyleSheet(bg_style)
            card["dot"].setStyleSheet(
                f"color: {dot_col}; background: transparent;"
            )
            card["icon_lbl"].setStyleSheet(
                f"color: {icon_col}; background: transparent;"
            )
            card["name_lbl"].setStyleSheet(
                f"color: {name_col}; background: transparent;"
            )
            card["conf_lbl"].setText(f"{int(conf * 100)}%")
            card["conf_lbl"].setStyleSheet(
                f"color: {conf_col}; background: transparent;"
            )
            card["status_lbl"].setStyleSheet(
                f"color: {status_col}; background: transparent; letter-spacing: 1px;"
            )
            card["obj_lbl"].setText(
                self._OBJECTIVES.get(name, ["Operating"])[st[2]]
            )
            card["obj_lbl"].setStyleSheet(
                f"color: {obj_col}; background: transparent;"
            )


class AIActivityCanvas(QWidget):
    """
    Context-aware animated visualization that sits below the HUD face.
    Modes: idle | listening | thinking | speaking | coding | analyzing | researching
    """

    def __init__(self, parent=None, config: AIActivityConfig = None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

        # Use default config if none provided
        self.config = config or AIActivityConfig()

        self.mode  = "idle"   # idle | listening | thinking | speaking | coding | analyzing | researching
        self.state = "LISTENING"

        # Animation state
        self._tick      = 0
        self._nodes: list[list[float]] = []   # [x, y, vx, vy, pulse, phase]
        self._edges: list[tuple[int,int,float]] = []  # (i, j, alpha)
        self._streams: list[list[float]] = []  # [x, y, vx, vy, life, max_life]
        self._bars: list[float] = []           # equalizer bar heights
        self._scan_angle = 0.0
        self._data_packets: list[list[float]] = []  # [edge_idx, t, speed]

        self._init_nodes(self.config.node_count)
        self._init_bars(self.config.bar_count)

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self.set_graphics_quality(get_graphics_quality())

    def set_graphics_quality(self, quality: str):
        value = _normalize_graphics_quality(quality)
        profile = GRAPHICS_PROFILES[value]
        self._graphics_quality = value
        self._antialias = bool(profile["antialias"])
        self._quality_node_count = int(profile["activity_nodes"])
        self._tmr.setInterval(int(profile["frame_ms"]))
        self._init_nodes(self._quality_node_count)
        if not self._tmr.isActive():
            self._tmr.start()
        self.update()

    def _init_nodes(self, n: int):
        self._nodes = []
        for i in range(n):
            ang = (i / n) * 2 * math.pi + random.uniform(-0.3, 0.3)
            r   = random.uniform(0.25, 0.45)
            self._nodes.append([
                0.5 + r * math.cos(ang),   # x (normalized)
                0.5 + r * math.sin(ang),   # y (normalized)
                random.uniform(-0.0008, 0.0008),  # vx
                random.uniform(-0.0008, 0.0008),  # vy
                random.uniform(0, 1),       # pulse phase
                random.uniform(0, 2 * math.pi),   # individual phase
            ])
        # Build edges: connect nearby nodes using config threshold
        self._edges = []
        for i in range(len(self._nodes)):
            for j in range(i + 1, len(self._nodes)):
                ni, nj = self._nodes[i], self._nodes[j]
                dist = math.hypot(ni[0] - nj[0], ni[1] - nj[1])
                if dist < self.config.edge_distance_threshold:
                    self._edges.append((i, j, random.uniform(0.3, 0.8)))

    def _init_bars(self, n: int):
        self._bars = [random.uniform(0.1, 0.4) for _ in range(n)]

    def set_mode(self, mode: str):
        if mode != self.mode:
            self.mode = mode
            if mode == "coding":
                self._init_nodes(min(16, self._quality_node_count))
            elif mode == "analyzing":
                self._init_nodes(min(10, self._quality_node_count))
            elif mode == "researching":
                self._init_nodes(min(20, self._quality_node_count))
            else:
                self._init_nodes(self._quality_node_count)

    def _step(self):
        self._tick += 1
        W, H = max(1, self.width()), max(1, self.height())

        is_active = self.state in ("THINKING", "SPEAKING", "PROCESSING")
        speed_mul = 2.5 if is_active else 0.6

        # Update nodes
        for nd in self._nodes:
            nd[0] += nd[2] * speed_mul
            nd[1] += nd[3] * speed_mul
            nd[4]  = (nd[4] + 0.018 * speed_mul) % 1.0
            nd[5]  = (nd[5] + 0.04  * speed_mul) % (2 * math.pi)
            # Bounce off edges
            if nd[0] < 0.08 or nd[0] > 0.92: nd[2] *= -1
            if nd[1] < 0.08 or nd[1] > 0.92: nd[3] *= -1
            nd[0] = max(0.08, min(0.92, nd[0]))
            nd[1] = max(0.08, min(0.92, nd[1]))

        # Rebuild edges dynamically using config threshold
        if self._tick % 30 == 0:
            self._edges = []
            for i in range(len(self._nodes)):
                for j in range(i + 1, len(self._nodes)):
                    ni, nj = self._nodes[i], self._nodes[j]
                    dist = math.hypot(ni[0] - nj[0], ni[1] - nj[1])
                    if dist < self.config.edge_distance_threshold:
                        self._edges.append((i, j, min(1.0, self.config.edge_distance_threshold / max(dist, 0.01) - 0.5)))

        # Data packets flowing along edges (respect config limit)
        if (self.config.show_data_packets and is_active and
            random.random() < 0.12 and self._edges and
            len(self._data_packets) < self.config.max_data_packets):
            ei = random.randint(0, len(self._edges) - 1)
            # Apply data_packet_velocity setting
            velocity_multiplier = {
                "slow": 0.5,
                "medium": 1.0,
                "fast": 1.5
            }.get(self.config.data_packet_velocity, 1.0)
            base_speed = random.uniform(0.008, 0.02)
            self._data_packets.append([ei, 0.0, base_speed * velocity_multiplier])
        self._data_packets = [
            [p[0], p[1] + p[2], p[2]] for p in self._data_packets if p[1] < 1.0
        ]

        # Equalizer bars (respect config flag)
        if self.config.show_equalizer_bars:
            target_h = 0.6 if self.state == "SPEAKING" else (0.35 if is_active else 0.12)
            for i in range(len(self._bars)):
                tgt = random.uniform(0.05, target_h) if is_active else random.uniform(0.03, 0.12)
                self._bars[i] += (tgt - self._bars[i]) * 0.18

        # Scanner (respect config flag)
        if self.config.show_scanner:
            scan_spd = 2.8 if is_active else 0.9
            self._scan_angle = (self._scan_angle + scan_spd) % 360

        # Data streams (respect config limit and flag)
        if (self.config.show_data_streams and is_active and
            random.random() < 0.08 and
            len(self._streams) < self.config.max_data_streams):
            self._streams.append([
                random.uniform(0.1, 0.9) * W, 0.0,
                random.uniform(-0.5, 0.5), random.uniform(1.5, 3.5),
                1.0, 1.0
            ])
        self._streams = [
            [s[0]+s[2], s[1]+s[3], s[2], s[3], s[4]-0.025, s[5]]
            for s in self._streams if s[4] > 0 and 0 <= s[1] <= H
        ]

        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, self._antialias)
        p.fillRect(self.rect(), qcol(C.BG))

        W, H = self.width(), self.height()
        if W < 10 or H < 10:
            return

        mode = self.mode
        is_active = self.state in ("THINKING", "SPEAKING", "PROCESSING")

        # ── Precision grid background (always shown) ────────────────────────
        p.setPen(QPen(qcol(C.PRI_GHO, 40), 1))
        for x in range(0, W, 20):
            p.drawLine(QPointF(x, 0), QPointF(x, H))
        for y in range(0, H, 20):
            p.drawLine(QPointF(0, y), QPointF(W, y))

        # ── Mode label (always shown) ───────────────────────────────────────
        mode_labels = {
            "coding":      ("◈ DEPENDENCY GRAPH",    C.ACC2),
            "analyzing":   ("◈ DOCUMENT MAP",         C.PRI),
            "researching": ("◈ KNOWLEDGE NETWORK",    C.PURPLE),
            "thinking":    ("◈ REASONING CHAIN",      C.ACC),
            "speaking":    ("◈ AUDIO SYNTHESIS",      C.GREEN),
            "listening":   ("◈ AUDIO CAPTURE",        C.PRI),
            "idle":        ("◈ STANDBY",              C.TEXT_DIM),
        }
        lbl_txt, lbl_col = mode_labels.get(mode, ("◈ AI ACTIVITY", C.TEXT_MED))
        p.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        p.setPen(QPen(qcol(lbl_col), 1))
        p.drawText(QRectF(8, 4, W - 16, 14), Qt.AlignmentFlag.AlignLeft, lbl_txt)

        # ── Separator line (always shown) ───────────────────────────────────
        p.setPen(QPen(qcol(C.BORDER), 1))
        p.drawLine(QPointF(0, 20), QPointF(W, 20))

        # ── Draw based on mode (respect config) ─────────────────────────────
        draw_y0 = 24
        draw_h  = H - draw_y0 - 4

        if mode in ("speaking",):
            if self.config.show_equalizer_bars:  # Spectrum uses equalizer bars
                self._draw_spectrum(p, W, draw_y0, draw_h)
        elif mode in ("coding", "analyzing", "researching", "thinking", "idle", "listening"):
            if self.config.show_nodes or self.config.show_edges:  # Network needs nodes or edges
                self._draw_network(p, W, draw_y0, draw_h, mode)

        # ── Data streams overlay (respect config) ───────────────────────────
        if self.config.show_data_streams:
            for s in self._streams:
                a = max(0, min(255, int(s[4] * 180)))
                p.setPen(QPen(qcol(C.PRI, a), 1))
                p.drawLine(QPointF(s[0], s[1]), QPointF(s[0] - s[2]*3, s[1] - s[3]*3))

    def _draw_network(self, p: QPainter, W: int, y0: int, H: int, mode: str):
        if not self._nodes:
            return

        node_col = {
            "coding":      C.ACC2,
            "analyzing":   C.PRI,
            "researching": C.PURPLE,
            "thinking":    C.ACC,
            "listening":   C.PRI,
        }.get(mode, C.TEXT_MED)

        edge_col = {
            "coding":      C.ACC2,
            "analyzing":   C.PRI,
            "researching": C.PURPLE,
            "thinking":    C.ACC,
        }.get(mode, C.BORDER_B)

        # Draw edges (respect config)
        if self.config.show_edges:
            # Apply edge_opacity setting
            opacity_multiplier = {
                "low": 0.5,
                "medium": 1.0,
                "high": 1.5
            }.get(self.config.edge_opacity, 1.0)
            for (i, j, alpha) in self._edges:
                ni, nj = self._nodes[i], self._nodes[j]
                x1, y1 = ni[0] * W, y0 + ni[1] * H
                x2, y2 = nj[0] * W, y0 + nj[1] * H
                a = max(0, min(255, int(alpha * 80 * opacity_multiplier)))
                p.setPen(QPen(qcol(edge_col, a), 1))
                p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Draw data packets on edges (respect config)
        if self.config.show_data_packets:
            for pkt in self._data_packets:
                ei = int(pkt[0])
                if ei >= len(self._edges):
                    continue
                i, j, _ = self._edges[ei]
                ni, nj = self._nodes[i], self._nodes[j]
                t = pkt[1]
                px = (ni[0] + (nj[0] - ni[0]) * t) * W
                py = y0 + (ni[1] + (nj[1] - ni[1]) * t) * H
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(qcol(node_col, 220)))
                p.drawEllipse(QPointF(px, py), 3, 3)

        # Draw nodes with enhanced glow (respect config)
        if self.config.show_nodes:
            for nd in self._nodes:
                nx, ny = nd[0] * W, y0 + nd[1] * H
                pulse  = 0.5 + 0.5 * math.sin(nd[5])
                # Apply node_size setting
                size_multiplier = {
                    "small": 0.7,
                    "medium": 1.0,
                    "large": 1.5
                }.get(self.config.node_size, 1.0)
                r_base = (4.0 + pulse * 2.5) * size_multiplier
                # Multi-layer glow
                for gi in range(4):
                    gr = r_base + gi * 2.5
                    ga = max(0, int(60 * pulse * (1 - gi / 4)))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QBrush(qcol(node_col, ga)))
                    p.drawEllipse(QPointF(nx, ny), gr, gr)
                # Core
                p.setBrush(QBrush(qcol(node_col, 200)))
                p.drawEllipse(QPointF(nx, ny), r_base * 0.6, r_base * 0.6)

        # Mode-specific overlays (respect config where applicable)
        if mode == "coding" and self.config.show_nodes:
            # Draw bracket decorations on some nodes
            p.setPen(QPen(qcol(C.ACC2, 80), 1))
            for i, nd in enumerate(self._nodes[:4]):
                nx, ny = nd[0] * W, y0 + nd[1] * H
                bl = 8
                p.drawLine(QPointF(nx-bl, ny-bl), QPointF(nx-bl+4, ny-bl))
                p.drawLine(QPointF(nx-bl, ny-bl), QPointF(nx-bl, ny-bl+4))

        elif mode == "researching" and self.config.show_nodes:
            # Draw expanding rings around hub nodes
            if self._nodes:
                hub = self._nodes[0]
                hx, hy = hub[0] * W, y0 + hub[1] * H
                t = (self._tick % 60) / 60.0
                for ri in range(3):
                    r = (t + ri / 3) * min(W, H) * 0.3
                    a = max(0, int(120 * (1 - (t + ri / 3))))
                    p.setPen(QPen(qcol(C.PURPLE, a), 1))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawEllipse(QPointF(hx, hy), r, r)

        elif mode == "analyzing" and self.config.show_scanner:
            # Scanning sweep line
            sr = min(W, H) * 0.4
            cx, cy = W * 0.5, y0 + H * 0.5
            rad = math.radians(self._scan_angle)
            p.setPen(QPen(qcol(C.PRI, 60), 1))
            p.drawLine(QPointF(cx, cy),
                       QPointF(cx + sr * math.cos(rad), cy + sr * math.sin(rad)))

    def _draw_spectrum(self, p: QPainter, W: int, y0: int, H: int):
        # Respect spectrum_type setting
        if self.config.spectrum_type == "off" or not self.config.show_equalizer_bars:
            return
        if self.config.spectrum_type == "off":
            return

        n = len(self._bars)
        if n == 0:
            return
        bw  = W / n
        mid = y0 + H * 0.5

        if self.config.spectrum_type == "waveform":
            # Draw waveform instead of bars
            for i in range(len(self._bars) - 1):
                x1 = i * bw + bw/2
                x2 = (i + 1) * bw + bw/2
                y1 = mid - self._bars[i] * H * 0.8
                y2 = mid - self._bars[i + 1] * H * 0.8
                p.setPen(QPen(qcol(C.PRI, 180), 2))
                p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            # Glow effect for waveform
            for i in range(len(self._bars) - 1):
                x1 = i * bw + bw/2
                x2 = (i + 1) * bw + bw/2
                y1 = mid - self._bars[i] * H * 0.8
                y2 = mid - self._bars[i + 1] * H * 0.8
                p.setPen(QPen(qcol(C.WHITE, 60), 4))
                p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        else:
            # Default bars style (original implementation)
            for i, h in enumerate(self._bars):
                bh  = h * H * 0.9
                bx  = i * bw + 1
                # Color gradient: low=cyan, mid=green, high=orange
                t   = h / 0.6
                if t < 0.5:
                    col = qcol(C.PRI, 200)
                elif t < 0.8:
                    col = qcol(C.GREEN, 200)
                else:
                    col = qcol(C.ACC, 220)
                p.fillRect(QRectF(bx, mid - bh/2, max(1, bw - 2), bh), col)
                # Glow top
                p.fillRect(QRectF(bx, mid - bh/2 - 2, max(1, bw - 2), 2),
                           qcol(C.WHITE, 80))
