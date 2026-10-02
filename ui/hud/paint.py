"""Canvas painter for the JARVIS reactor HUD."""

from __future__ import annotations

import importlib

_legacy = importlib.import_module("ui._legacy")
globals().update({key: value for key, value in vars(_legacy).items() if not key.startswith("__")})

class HudCanvasPaintMixin:
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, self._antialias)
        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        fw = min(W, H)
        is_active = self.speaking or self.state in ("THINKING", "PROCESSING")

        # ═══ LAYER 1: Deep space background ════════════════════════════════
        _is_light_theme = QColor(C.BG).lightness() > 150
        _bg = QRadialGradient(QPointF(cx, cy + H * 0.06), max(W, H) * 0.9)
        if _is_light_theme:
            _bg.setColorAt(0.0, qcol(C.CARD))
            _bg.setColorAt(0.45, qcol(C.PANEL))
            _bg.setColorAt(1.0, qcol(C.DARK))
        else:
            _bg.setColorAt(0.0, qcol(C.DARK))
            _bg.setColorAt(0.45, qcol(C.BG))
            _bg.setColorAt(1.0, qcol(C.PANEL))
        p.fillRect(self.rect(), _bg)

        # ═══ LAYER 2: Massive secondary ring system ═══════════════════════
        mega_mult = 1.5 if is_active else 1.0
        for r_mult, rot_spd, opac, w in self._mega_rings[::self._render_stride]:
            r = fw * r_mult * 0.28
            angle = self._tick * rot_spd * mega_mult
            a = max(0, int(self._brightness * 6 * opac))
            if a < 1:
                continue
            ox = math.cos(angle * 0.5) * fw * 0.01
            oy = math.sin(angle * 0.3) * fw * 0.008

            # Draw as full ellipse for scale
            p.setPen(QPen(qcol(C.PRI,a), w))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx + ox, cy + oy), r, r * 0.32)

            # Tick marks on the largest ring
            if r_mult > 2.5:
                p.setPen(QPen(qcol(C.PRI,max(0, a - 4)), 0.3))
                for deg in range(0, 360, 10 * self._render_stride):
                    rad = math.radians(deg + angle * 50)
                    ex = cx + ox + math.cos(rad) * r
                    ey = cy + oy + math.sin(rad) * r * 0.32
                    ix = cx + ox + math.cos(rad) * (r - 6)
                    iy = cy + oy + math.sin(rad) * (r - 6) * 0.32
                    p.drawLine(QPointF(ex, ey), QPointF(ix, iy))

        # Radial grid lines
        for deg in range(0, 360, 30 * self._render_stride):
            rad = math.radians(deg + self._tick * 0.012)
            a = max(0, int(self._brightness * 5))
            if a < 1:
                continue
            p.setPen(QPen(qcol(C.PRI,a), 0.3))
            p.drawLine(QPointF(cx, cy), QPointF(cx + math.cos(rad) * fw * 0.58, cy + math.sin(rad) * fw * 0.58))

        # ═══ LAYER 3: Ambient depth particles ═════════════════════════════
        for di in range(0, len(self._depth_pts), self._render_stride):
            dx, dy, sz, phase = self._depth_pts[di]
            parallax = 0.5 + (di % 3) * 0.25
            dx2 = dx + math.sin(self._tick * 0.001 * parallax + phase) * 0.025
            dy2 = dy + math.cos(self._tick * 0.0008 * parallax + phase) * 0.02
            sx = cx + dx2 * fw
            sy = cy + dy2 * fw
            pulse = 0.3 + 0.7 * math.sin(self._tick * 0.012 + phase)
            a = max(0, int(self._brightness * 25 * pulse))
            if a < 2:
                continue
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.PRI,a)))
            p.drawEllipse(QPointF(sx, sy), sz, sz)

        # ═══ LAYER 4: Wave field ══════════════════════════════════════════
        wave_top = cy - H * 0.05
        wave_bot = cy + H * 0.45
        wave_l   = cx - W * 0.52
        wave_w   = W * 1.04
        wave_h   = wave_bot - wave_top
        t_wave   = self._tick * 0.015

        for nx, ny, phase in self._wave_pts[::self._wave_stride]:
            wx = wave_l + nx * wave_w
            wy_base = wave_top + ny * wave_h
            wave_y = math.sin(nx * 6.0 + t_wave + phase) * 8.0
            wave_y += math.sin(ny * 4.0 - t_wave * 0.7 + phase * 0.5) * 5.0
            wy = wy_base + wave_y
            dist = math.hypot(wx - cx, wy - cy) / (fw * 0.7)
            a = max(0, int(self._brightness * 40 * (1.0 - dist * 0.6) * self._wave_opacity))
            if a < 2:
                continue
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.PRI,a)))
            p.drawEllipse(QPointF(wx, wy), 0.6, 0.6)

        # ═══ LAYER 5: Hexagonal frame — STRONG ════════════════════════════
        sphere_r = fw * 0.52 * self._scale
        hex_r = sphere_r * 1.10
        hex_a = max(0, int(self._brightness * 80))
        if hex_a > 1:
            hex_pts = []
            for hi in range(6):
                angle = math.radians(60 * hi - 30 + self._tick * 0.02)
                hx = cx + math.cos(angle) * hex_r
                hy = cy + math.sin(angle) * hex_r * 0.85
                hex_pts.append(QPointF(hx, hy))

            # Main hex lines
            hex_col = qcol(C.PRI,hex_a)
            p.setPen(QPen(hex_col, 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            hex_path = QPainterPath()
            hex_path.moveTo(hex_pts[0])
            for hp in hex_pts[1:]:
                hex_path.lineTo(hp)
            hex_path.lineTo(hex_pts[0])
            p.drawPath(hex_path)

            # Segmented inner hex (rotated 30 deg)
            inner_hex_path = QPainterPath()
            inner_pts = []
            for hi in range(6):
                angle = math.radians(60 * hi + self._tick * 0.02)
                hx = cx + math.cos(angle) * hex_r * 0.94
                hy = cy + math.sin(angle) * hex_r * 0.94 * 0.85
                inner_pts.append(QPointF(hx, hy))
            for si in range(0, len(inner_pts), 2):
                seg = [inner_pts[si], inner_pts[(si + 1) % 6]]
                p.setPen(QPen(qcol(C.PRI,max(0, hex_a - 15)), 0.6))
                p.drawLine(seg[0], seg[1])

            # Tick marks along each hex edge
            p.setPen(QPen(qcol(C.PRI,max(0, hex_a - 10)), 0.5))
            for hi in range(6):
                p1 = hex_pts[hi]
                p2 = hex_pts[(hi + 1) % 6]
                for t in range(0, 11):
                    frac = t / 10.0
                    mx = p1.x() + (p2.x() - p1.x()) * frac
                    my = p1.y() + (p2.y() - p1.y()) * frac
                    dx_n = p2.y() - p1.y()
                    dy_n = -(p2.x() - p1.x())
                    dlen = math.hypot(dx_n, dy_n)
                    if dlen > 0:
                        dx_n /= dlen; dy_n /= dlen
                    tick_len = 6 if t % 5 == 0 else 3
                    p.drawLine(QPointF(mx, my), QPointF(mx + dx_n * tick_len, my + dy_n * tick_len))

            # Vertex dots — bright
            for hp in hex_pts:
                # Vertex glow
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(qcol(C.ENERGY,max(0, int(hex_a * 0.3)))))
                p.drawEllipse(hp, 8, 8)
                # Vertex core
                p.setBrush(QBrush(qcol(C.ENERGY,min(255, hex_a + 40))))
                p.drawEllipse(hp, 2.5, 2.5)

            # Coordinate labels at two vertices
            p.setFont(QFont("Courier New", 6))
            p.setPen(QPen(qcol(C.PRI,max(0, hex_a - 20)), 0.8))
            p.drawText(QPointF(hex_pts[0].x() + 10, hex_pts[0].y() - 4), "037.4\u00b0")
            p.drawText(QPointF(hex_pts[3].x() - 55, hex_pts[3].y() + 14), "217.8\u00b0")

        # ═══ LAYER 5b: Targeting reticle ═══════════════════════════════════
        ret_r = sphere_r * 1.18
        ret_a = max(0, int(self._brightness * 120))
        if ret_a > 1:
            # Crosshairs
            p.setPen(QPen(qcol(C.PRI,ret_a), 0.4))
            ch_gap = sphere_r * 0.6
            ch_len = ret_r
            p.drawLine(QPointF(cx - ch_len, cy), QPointF(cx - ch_gap, cy))
            p.drawLine(QPointF(cx + ch_gap, cy), QPointF(cx + ch_len, cy))
            p.drawLine(QPointF(cx, cy - ch_len), QPointF(cx, cy - ch_gap))
            p.drawLine(QPointF(cx, cy + ch_gap), QPointF(cx, cy + ch_len))

            # Degree markers around perimeter
            p.setFont(QFont("Courier New", 5))
            for deg in range(0, 360, 45):
                rad = math.radians(deg)
                mx = cx + math.cos(rad) * ret_r
                my = cy + math.sin(rad) * ret_r * 0.85
                # Tick
                ix = cx + math.cos(rad) * (ret_r - 5)
                iy = cy + math.sin(rad) * (ret_r - 5) * 0.85
                p.setPen(QPen(qcol(C.PRI,ret_a), 0.4))
                p.drawLine(QPointF(ix, iy), QPointF(mx, my))
                # Label
                if deg % 90 == 0:
                    labels = {0: "000", 90: "090", 180: "180", 270: "270"}
                    lx = cx + math.cos(rad) * (ret_r + 8)
                    ly = cy + math.sin(rad) * (ret_r + 8) * 0.85
                    p.setPen(QPen(qcol(C.PRI,max(0, ret_a - 3)), 0.6))
                    p.drawText(QPointF(lx - 10, ly + 3), labels.get(deg, str(deg)))

        # ═══ LAYER 6: Spherical lattice — signature element ════════════════
        lat_r = sphere_r * 1.02
        lat_a = max(0, int(self._brightness * 40))
        if lat_a > 1:
            # Latitude rings
            for li in range(1, self._LATTICE_RINGS):
                frac = li / self._LATTICE_RINGS
                phi = frac * math.pi
                ring_r = math.sin(phi) * lat_r
                y_off = math.cos(phi) * lat_r * 0.85

                pts = []
                for deg in range(0, 361, 4):
                    rad = math.radians(deg + self._tick * 0.03 + li * 15)
                    x = math.cos(rad) * ring_r
                    y = math.sin(rad) * ring_r * 0.85 - y_off * 0.85
                    # Apply rotation
                    crx = math.cos(self._rotation_x * 0.8)
                    srx = math.sin(self._rotation_x * 0.8)
                    yt = y * crx
                    zt = y * srx
                    # Perspective fade
                    fade = max(0.3, (zt / lat_r + 1) / 2)
                    a = int(lat_a * fade)
                    if a > 1:
                        pts.append((cx + x, cy + yt, a))

                if len(pts) > 2:
                    for pi in range(len(pts) - 1):
                        x1, y1, a1 = pts[pi]
                        x2, y2, a2 = pts[pi + 1]
                        a = (a1 + a2) // 2
                        p.setPen(QPen(qcol(C.PRI,a), 0.3))
                        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

            # Longitude arcs
            for li in range(self._LATTICE_ARCS):
                angle = li * (180 / self._LATTICE_ARCS) + self._tick * 0.015
                rad = math.radians(angle)
                pts = []
                for seg in range(0, 181, 3):
                    phi = math.radians(seg)
                    x = math.sin(phi) * math.cos(rad) * lat_r
                    y = math.sin(phi) * math.sin(rad) * lat_r * 0.85
                    z = math.cos(phi) * lat_r
                    crx = math.cos(self._rotation_x * 0.8)
                    srx = math.sin(self._rotation_x * 0.8)
                    yr = y * crx - z * srx
                    zr = y * srx + z * crx
                    depth = (zr / lat_r + 1) / 2
                    a = int(lat_a * max(0.2, depth))
                    if a > 1:
                        pts.append((cx + x, cy - yr, a))

                if len(pts) > 2:
                    for pi in range(len(pts) - 1):
                        x1, y1, a1 = pts[pi]
                        x2, y2, a2 = pts[pi + 1]
                        a = (a1 + a2) // 2
                        p.setPen(QPen(qcol(C.PRI,a), 0.25))
                        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # ═══ LAYER 7: Orbital rings — varied styles ═══════════════════════
        cos_rx = math.cos(self._rotation_x)
        sin_rx = math.sin(self._rotation_x)
        cos_ry = math.cos(self._rotation_y)
        sin_ry = math.sin(self._rotation_y)

        for ri, (r_frac, tilt_x, tilt_z, w, _, style) in enumerate(self._orbital_rings):
            ring_r = sphere_r * r_frac
            r_angle = math.radians(self._ring_angles[ri])
            r_a = max(0, int(self._brightness * 50 * (1.2 if is_active else 0.5)))
            if r_a < 2:
                continue

            col = qcol(C.ENERGY,r_a)
            p.setBrush(Qt.BrushStyle.NoBrush)

            path_pts = []
            for deg in range(0, 361, 3):
                rad = math.radians(deg + r_angle)
                x = math.cos(rad) * ring_r
                y = math.sin(rad) * ring_r * math.cos(tilt_x)
                z = math.sin(rad) * ring_r * math.sin(tilt_z)
                xr = x * cos_ry - z * sin_ry
                zr = x * sin_ry + z * cos_ry
                yr = y * cos_rx - zr * sin_rx
                path_pts.append(QPointF(cx + xr, cy - yr))

            if len(path_pts) > 1:
                if style == 1:
                    pen = QPen(col, w)
                    pen.setDashPattern([8, 6])
                    p.setPen(pen)
                elif style == 2:
                    seg_len = 30
                    p.setPen(QPen(col, w))
                    for si in range(0, len(path_pts) - seg_len, seg_len * 2):
                        seg = path_pts[si:si + seg_len + 1]
                        if len(seg) > 1:
                            seg_path = QPainterPath()
                            seg_path.moveTo(seg[0])
                            for pt in seg[1:]:
                                seg_path.lineTo(pt)
                            p.drawPath(seg_path)
                    continue
                elif style == 3:
                    pen = QPen(col, w * 0.6)
                    pen.setDashPattern([2, 8])
                    p.setPen(pen)
                else:
                    p.setPen(QPen(col, w))

                path = QPainterPath()
                path.moveTo(path_pts[0])
                for pt in path_pts[1:]:
                    path.lineTo(pt)
                p.drawPath(path)

        # ═══ LAYER 8: Connection lines ════════════════════════════════════
        proj_nodes = {}
        for idx in range(0, len(self._nodes), self._render_stride):
            nd = self._nodes[idx]
            sx, sy, z2, depth = self._proj(nd[0], nd[1], nd[2], sphere_r, cx, cy)
            if z2 > -0.3:
                proj_nodes[idx] = (sx, sy, z2, depth)

        for ci, cj, dist, same_cluster in self._connections[::self._render_stride]:
            if ci in proj_nodes and cj in proj_nodes:
                x1, y1, z1, d1 = proj_nodes[ci]
                x2, y2, z2, d2 = proj_nodes[cj]
                avg_d = (d1 + d2) / 2
                threshold = 0.32 if same_cluster else 0.18
                strength = 1.0 - dist / threshold
                if same_cluster:
                    strength *= 1.5
                la = max(0, int(self._brightness * avg_d * strength * 50))
                if la > 2:
                    lc = qcol(C.PRI,la) if same_cluster else qcol(C.PRI,la)
                    p.setPen(QPen(lc, 0.5))
                    p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # ═══ LAYER 9: Energy pulses ═══════════════════════════════════════
        pulse_colors = [qcol(C.ENERGY,255), qcol(C.WHITE,255), qcol(C.GREEN,255)]
        for si, ei, t, spd, cidx in self._pulses:
            if si in proj_nodes and ei in proj_nodes:
                x1, y1, z1, d1 = proj_nodes[si]
                x2, y2, z2, d2 = proj_nodes[ei]
                px = x1 + (x2 - x1) * t
                py = y1 + (y2 - y1) * t
                depth = d1 + (d2 - d1) * t
                pa = max(0, min(255, int(220 * depth * (1.0 - abs(t - 0.5) * 1.5))))
                if pa > 5:
                    col = pulse_colors[cidx % len(pulse_colors)]
                    p.setPen(Qt.PenStyle.NoPen)
                    gc = QColor(col); gc.setAlpha(int(pa * 0.2))
                    p.setBrush(QBrush(gc))
                    p.drawEllipse(QPointF(px, py), 14, 14)
                    cc = QColor(col); cc.setAlpha(pa)
                    p.setBrush(QBrush(cc))
                    p.drawEllipse(QPointF(px, py), 3.5, 3.5)

        # ═══ LAYER 10: Neural nodes ═══════════════════════════════════════
        sorted_n = sorted(proj_nodes.items(), key=lambda x: x[1][2])
        # Cluster colors derived from theme
        _pri = QColor(C.PRI)
        _pr = _pri.red(); _pg = _pri.green(); _pb = _pri.blue()
        cluster_hues = [
            (_pr, _pg, _pb),
            (min(255, _pr + 30), min(255, _pg + 20), min(255, _pb + 10)),
            (max(0, _pr - 20), max(0, _pg - 10), min(255, _pb + 30)),
            (max(0, _pr - 40), max(0, _pg - 20), max(0, _pb - 10)),
            (min(255, _pr + 50), min(255, _pg + 40), min(255, _pb + 20)),
            (_pr, min(255, _pg + 30), min(255, _pb + 20)),
            (max(0, _pr - 10), min(255, _pg + 10), min(255, _pb + 40)),
            (min(255, _pr + 20), min(255, _pg + 40), _pb),
        ]

        for idx, (sx, sy, z2, depth) in sorted_n:
            nd = self._nodes[idx]
            r, theta, phi, sz, br, phase, cid = nd
            pulse = 0.6 + 0.4 * math.sin(self._tick * 0.04 + phase)
            draw_sz = sz * (0.3 + 0.7 * depth) * pulse
            bright = self._brightness * depth * br * pulse * 2.0
            if z2 < -0.3:
                bright *= 0.1
            a = max(0, min(255, int(bright * 255)))
            if a < 3:
                continue

            if cid >= 0:
                cr, cg, cb = cluster_hues[cid % len(cluster_hues)]
            else:
                _f = QColor(C.PRI); cr, cg, cb = _f.red(), _f.green(), _f.blue()

            ga = max(0, int(a * 0.18))
            if ga > 2:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(cr, cg, cb, ga)))
                p.drawEllipse(QPointF(sx, sy), draw_sz * 5, draw_sz * 5)

            ia = max(0, int(a * 0.45))
            if ia > 2:
                p.setBrush(QBrush(QColor(cr, cg, cb, ia)))
                p.drawEllipse(QPointF(sx, sy), draw_sz * 2.0, draw_sz * 2.0)

            p.setBrush(QBrush(QColor(min(255, cr+60), min(255, cg+40), min(255, cb+20), a)))
            p.drawEllipse(QPointF(sx, sy), draw_sz, draw_sz)

        # ═══ LAYER 11: Shell particles ═════════════════════════════════════
        for theta, phi, sz, phase in self._shell[::self._render_stride]:
            sx, sy, z2, depth = self._proj(1.0, theta, phi, sphere_r, cx, cy)
            if z2 < 0.05:
                continue
            pulse = 0.5 + 0.5 * math.sin(self._tick * 0.05 + phase)
            a = max(0, min(255, int(self._brightness * depth * pulse * 200)))
            if a < 4:
                continue
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.ENERGY,a)))
            p.drawEllipse(QPointF(sx, sy), sz * pulse, sz * pulse)

        # ═══ LAYER 11b: Micro-details — telemetry labels ══════════════════
        detail_a = max(0, int(self._brightness * 18))
        if detail_a > 2:
            p.setFont(QFont("Courier New", 5))
            # Scattered labels around the orb
            details = [
                (0.58, 0.25, "NODE-{:02d}  {:.0f}%".format(
                    (self._tick // 200) % 64, 85 + 10 * math.sin(self._tick * 0.01))),
                (-0.55, 0.35, "MEM: {:.0f}KB".format(
                    128 + 32 * math.sin(self._tick * 0.008))),
                (0.45, -0.48, "LAT {:.1f}°".format(
                    37.4 + 0.3 * math.sin(self._tick * 0.005))),
                (-0.42, -0.52, "SYS {:.1f}%".format(
                    94 + 3 * math.sin(self._tick * 0.012))),
                (0.62, -0.15, "CYCLE {}".format(
                    (self._tick // 100) % 999)),
                (-0.60, -0.12, "DEPTH {:.02f}".format(
                    0.85 + 0.1 * math.sin(self._tick * 0.006))),
                (0.20, 0.60, "ACTIVE".format()),
                (-0.25, 0.58, "{:.1f}ms".format(
                    2.4 + 0.8 * math.sin(self._tick * 0.015))),
            ]
            for dx, dy, label in details:
                lx = cx + dx * sphere_r
                ly = cy + dy * sphere_r
                flicker = 0.7 + 0.3 * math.sin(self._tick * 0.02 + dx * 10)
                a = int(detail_a * flicker)
                p.setPen(QPen(qcol(C.PRI,a), 0.8))
                p.drawText(QPointF(lx, ly), label)

        # ═══ LAYER 12: Core energy — SHARP ════════════════════════════════
        core_base = sphere_r * 0.065
        ca = max(0, min(255, int(self._brightness * 255)))

        # Outer diffuse glow
        for i in range(18, 0, -1):
            frc = i / 18
            r = core_base * frc * 7.0
            a = int(ca * 0.05 * frc)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.PRI,a)))
            p.drawEllipse(QPointF(cx, cy), r, r)

        # Mid glow — brighter
        for i in range(10, 0, -1):
            frc = i / 10
            r = core_base * frc * 4.0
            a = int(ca * 0.28 * frc)
            p.setBrush(QBrush(qcol(C.ENERGY,a)))
            p.drawEllipse(QPointF(cx, cy), r, r)

        # SHARP thin rings — creates premium look
        for sr in [core_base * 2.0, core_base * 3.0, core_base * 4.5]:
            ring_a = max(0, int(ca * 0.25 * (1.0 - sr / (core_base * 5.0))))
            if ring_a > 2:
                p.setPen(QPen(qcol(C.ENERGY,ring_a), 0.6))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QPointF(cx, cy), sr, sr)

        # Inner core — intense
        for i in range(5, 0, -1):
            frc = i / 5
            r = core_base * frc * 2.0
            a = int(ca * 0.55 * frc)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.ENERGY,a)))
            p.drawEllipse(QPointF(cx, cy), r, r)

        # White hot center with HARD edge
        p.setBrush(QBrush(qcol(C.ENERGY,min(255, int(ca * 0.95)))))
        p.drawEllipse(QPointF(cx, cy), core_base * 0.35, core_base * 0.35)

        # Sharp highlight on center
        p.setBrush(QBrush(qcol(C.ENERGY,min(255, int(ca * 0.6)))))
        p.drawEllipse(QPointF(cx - core_base * 0.1, cy - core_base * 0.1), core_base * 0.15, core_base * 0.15)

        # ═══ LAYER 13: Corner anchors — CONNECTED ═════════════════════════
        bl = 50
        bc = qcol(C.PRI, 180)
        m = fw * 0.47
        hl, hr = cx - m, cx + m
        ht, hb = cy - m, cy + m

        # Thin telemetry lines connecting corners to orb
        telemetry_a = max(0, int(self._brightness * 18))
        if telemetry_a > 1:
            p.setPen(QPen(qcol(C.PRI,telemetry_a), 0.4))
            # Horizontal measurement lines
            p.drawLine(QPointF(hl + bl, ht), QPointF(cx - sphere_r * 0.9, ht))
            p.drawLine(QPointF(hr - bl, ht), QPointF(cx + sphere_r * 0.9, ht))
            p.drawLine(QPointF(hl + bl, hb), QPointF(cx - sphere_r * 0.9, hb))
            p.drawLine(QPointF(hr - bl, hb), QPointF(cx + sphere_r * 0.9, hb))
            # Vertical
            p.drawLine(QPointF(hl, ht + bl), QPointF(hl, cy - sphere_r * 0.7))
            p.drawLine(QPointF(hl, hb - bl), QPointF(hl, cy + sphere_r * 0.7))
            p.drawLine(QPointF(hr, ht + bl), QPointF(hr, cy - sphere_r * 0.7))
            p.drawLine(QPointF(hr, hb - bl), QPointF(hr, cy + sphere_r * 0.7))

            # Measurement ticks along telemetry lines
            p.setPen(QPen(qcol(C.PRI,max(0, telemetry_a - 5)), 0.3))
            for x in range(int(hl + bl + 10), int(cx - sphere_r * 0.9), 12):
                p.drawLine(QPointF(x, ht - 2), QPointF(x, ht + 2))
            for x in range(int(cx + sphere_r * 0.9), int(hr - bl), 12):
                p.drawLine(QPointF(x, ht - 2), QPointF(x, ht + 2))

        for bx, by, dx, dy in [(hl,ht,1,1),(hr,ht,-1,1),(hl,hb,1,-1),(hr,hb,-1,-1)]:
            # Ambient glow
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.PRI,max(0, int(self._brightness * 15)))))
            p.drawEllipse(QPointF(bx + dx * bl * 0.35, by + dy * bl * 0.35), bl * 0.5, bl * 0.5)

            # Main bracket lines — with subtle idle flicker
            _flicker = 0.85 + 0.15 * math.sin(self._tick * 0.1 + bx * 0.01 + by * 0.01)
            _bc_flick = QColor(bc); _bc_flick.setAlpha(int(bc.alpha() * _flicker))
            p.setPen(QPen(_bc_flick, 2.0))
            p.drawLine(QPointF(bx, by), QPointF(bx + dx * bl, by))
            p.drawLine(QPointF(bx, by), QPointF(bx, by + dy * bl))

            # Inner accent
            p.setPen(QPen(qcol(C.ENERGY, 80), 0.8))
            p.drawLine(QPointF(bx + dx * 8, by + dy * 8), QPointF(bx + dx * 30, by + dy * 8))
            p.drawLine(QPointF(bx + dx * 8, by + dy * 8), QPointF(bx + dx * 8, by + dy * 30))

            # Corner dot — pulsing
            _corner_pulse = 0.5 + 0.5 * math.sin(self._tick * 0.08 + bx * 0.01 + by * 0.01)
            _corner_a = int(120 + 80 * _corner_pulse)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.ENERGY,_corner_a)))
            p.drawEllipse(QPointF(bx + dx * 4, by + dy * 4), 2.5 + _corner_pulse, 2.5 + _corner_pulse)

            # Scan sweep line (rotating accent)
            _scan_angle = math.radians((self._tick * 3 + bx + by) % 360)
            _scan_len = bl * 0.5
            _scan_a = int(40 * _corner_pulse)
            if _scan_a > 3:
                p.setPen(QPen(qcol(C.ENERGY,_scan_a), 0.5))
                p.drawLine(
                    QPointF(bx, by),
                    QPointF(bx + dx * abs(math.cos(_scan_angle)) * _scan_len,
                            by + dy * abs(math.sin(_scan_angle)) * _scan_len))

            # Tick marks along bracket
            p.setPen(QPen(qcol(C.PRI, 50), 0.4))
            for ti in range(14, bl, 7):
                p.drawLine(QPointF(bx + dx * ti, by), QPointF(bx + dx * ti, by + dy * 3))
                p.drawLine(QPointF(bx, by + dy * ti), QPointF(bx + dx * 3, by + dy * ti))

            # Coordinate readout inside corner
            p.setFont(QFont("Courier New", 5))
            _cx_v = int(bx + (cx - bx) * 0.08)
            _cy_v = int(by + (cy - by) * 0.08)
            _co_a = max(0, int(self._brightness * 80))
            if _co_a > 2:
                p.setPen(QPen(qcol(C.PRI,_co_a), 0.6))
                p.drawText(QPointF(bx + dx * 52, by + dy * 4), "X:{:04d}".format(abs(int(bx)) % 9999))
                p.drawText(QPointF(bx + dx * 52, by + dy * 12), "Y:{:04d}".format(abs(int(by)) % 9999))

        # ═══ LAYER 14: Status text ════════════════════════════════════════
        sy_t = cy + fw * 0.48
        if self.muted:
            txt, col = "\u2298  MUTED",          qcol(C.MUTED_C)
        elif self.speaking:
            txt, col = "\u25cf  SPEAKING",        qcol(C.GREEN)
        elif self.state == "THINKING":
            sym = "\u25c8" if self._blink else "\u25c7"
            txt, col = f"{sym}  PROCESSING QUERY", qcol(C.ACC2)
        elif self.state == "PROCESSING":
            sym = "\u25b7" if self._blink else "\u25b6"
            txt, col = f"{sym}  EXECUTING",   qcol(C.ACC)
        elif self.state == "LISTENING":
            sym = "\u25cf" if self._blink else "\u25cb"
            txt, col = f"{sym}  LISTENING",   qcol(C.ENERGY)
        else:
            sym = "\u25cf" if self._blink else "\u25cb"
            txt, col = f"{sym}  {self.state}", qcol(C.PRI)

        # Speaking waveform directly under orb
        if self.speaking:
            sw_y = sy_t - 20
            sw_w = sphere_r * 0.5
            sw_N = 20
            sw_bw = sw_w * 2 / sw_N
            for si in range(sw_N):
                sh = random.randint(2, 14)
                sx = cx - sw_w + si * sw_bw
                sc = qcol(C.ENERGY, 150)
                p.fillRect(QRectF(sx, sw_y - sh / 2, sw_bw - 1, sh), sc)

        p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        _tc = QColor(col); _tc.setAlpha(20)
        for _ox, _oy in [(-2,0),(2,0),(0,-2),(0,2),(-1,-1),(1,1),(-1,1),(1,-1)]:
            p.setPen(QPen(_tc, 1))
            p.drawText(QRectF(_ox, sy_t + _oy, W, 18), Qt.AlignmentFlag.AlignCenter, txt)
        p.setPen(QPen(col, 1))
        p.drawText(QRectF(0, sy_t, W, 18), Qt.AlignmentFlag.AlignCenter, txt)

        # ═══ LAYER 15: Waveform ═══════════════════════════════════════════
        if self.config.waveform_style != "off":
            wy = sy_t + 26
            if self.config.waveform_style == "classic":
                N, bw = 48, 6
            elif self.config.waveform_style == "minimal":
                N, bw = 24, 8
            else:
                N, bw = 48, 6
            wx0 = (W - N * bw) / 2
            for i in range(N):
                if self.muted:
                    hgt, cl = 2, qcol(C.MUTED_C, 100)
                elif self.speaking:
                    hgt = random.randint(2, 22)
                    t   = hgt / 22
                    if t < 0.4:
                        cl = qcol(C.PRI, 180)
                    elif t < 0.75:
                        cl = qcol(C.ENERGY, 200)
                    else:
                        cl = qcol(C.GREEN, 220)
                    p.fillRect(QRectF(wx0 + i * bw - 1, wy + 22 - hgt - 3, bw + 1, hgt + 6), qcol(C.ENERGY, 25))
                elif is_active:
                    hgt = int(4 + 6 * abs(math.sin(self._tick * 0.07 + i * 0.4)))
                    cl  = qcol(C.PRI_DIM, 160)
                else:
                    hgt = int(2 + 2 * math.sin(self._tick * 0.05 + i * 0.5))
                    cl  = qcol(C.BORDER_B, 120)
                p.fillRect(QRectF(wx0 + i * bw, wy + 22 - hgt, bw - 1, hgt), cl)

        # ═══ LAYER 15b: Side telemetry ─══════════════════════════════════
        telem_a = max(0, int(self._brightness * 100))
        if telem_a > 2:
            # Left side: vertical sparkline
            spark_x = cx - sphere_r * 1.35
            spark_h = sphere_r * 0.8
            spark_cy = cy
            p.setPen(QPen(qcol(C.PRI,telem_a), 0.6))
            p.drawLine(QPointF(spark_x, spark_cy - spark_h / 2),
                       QPointF(spark_x, spark_cy + spark_h / 2))
            # Sparkline points
            p.setFont(QFont("Courier New", 5))
            p.setPen(QPen(qcol(C.PRI,max(0, telem_a - 5)), 0.5))
            p.drawText(QPointF(spark_x - 20, spark_cy - spark_h / 2 - 6), "PWR")
            for si in range(20):
                sy = spark_cy - spark_h / 2 + (spark_h / 20) * si
                sv = 8 + 6 * math.sin(self._tick * 0.03 + si * 0.5)
                p.setPen(QPen(qcol(C.ENERGY,max(0, telem_a - 2)), 0.5))
                p.drawLine(QPointF(spark_x - sv, sy), QPointF(spark_x + sv, sy))
                # Tick mark
                p.setPen(QPen(qcol(C.PRI,max(0, telem_a - 8)), 0.3))
                p.drawLine(QPointF(spark_x - 2, sy), QPointF(spark_x + 2, sy))

            # Right side: vertical sparkline
            spark_x2 = cx + sphere_r * 1.35
            p.setPen(QPen(qcol(C.PRI,telem_a), 0.6))
            p.drawLine(QPointF(spark_x2, spark_cy - spark_h / 2),
                       QPointF(spark_x2, spark_cy + spark_h / 2))
            p.setFont(QFont("Courier New", 5))
            p.setPen(QPen(qcol(C.PRI,max(0, telem_a - 5)), 0.5))
            p.drawText(QPointF(spark_x2 - 12, spark_cy - spark_h / 2 - 6), "NET")
            for si in range(20):
                sy = spark_cy - spark_h / 2 + (spark_h / 20) * si
                sv = 6 + 8 * abs(math.sin(self._tick * 0.025 + si * 0.7))
                p.setPen(QPen(qcol(C.ENERGY,max(0, telem_a - 2)), 0.5))
                p.drawLine(QPointF(spark_x2 - sv, sy), QPointF(spark_x2 + sv, sy))
                p.setPen(QPen(qcol(C.PRI,max(0, telem_a - 8)), 0.3))
                p.drawLine(QPointF(spark_x2 - 2, sy), QPointF(spark_x2 + 2, sy))

            # Left telemetry labels
            p.setFont(QFont("Courier New", 5))
            labels_left = [
                (-0.72, 0.05, "SYS {:.1f}%".format(94.2 + 2 * math.sin(self._tick * 0.01))),
                (-0.68, 0.18, "CPU  {:.0f}MHz".format(3200 + 200 * math.sin(self._tick * 0.008))),
                (-0.72, 0.31, "MEM {:.0f}MB".format(4096 + 512 * math.sin(self._tick * 0.005))),
            ]
            for dx, dy, label in labels_left:
                lx = cx + dx * sphere_r
                ly = cy + dy * sphere_r
                a = int(telem_a * (0.7 + 0.3 * math.sin(self._tick * 0.02 + dx * 5)))
                p.setPen(QPen(qcol(C.PRI,a), 0.6))
                p.drawText(QPointF(lx, ly), label)

            # Right telemetry labels
            labels_right = [
                (0.58, 0.05, "NET {:.0f}ms".format(12 + 4 * math.sin(self._tick * 0.012))),
                (0.62, 0.18, "PKT  {:.0f}/s".format(1200 + 300 * math.sin(self._tick * 0.007))),
                (0.58, 0.31, "LAT {:.0f}ms".format(2 + 1 * math.sin(self._tick * 0.015))),
            ]
            for dx, dy, label in labels_right:
                lx = cx + dx * sphere_r
                ly = cy + dy * sphere_r
                a = int(telem_a * (0.7 + 0.3 * math.sin(self._tick * 0.02 + dx * 5)))
                p.setPen(QPen(qcol(C.PRI,a), 0.6))
                p.drawText(QPointF(lx, ly), label)

        # ═══ OVERLAY: Scanlines + Vignette + Noise ════════════════════════
        # Scanlines — slow horizontal sweep
        _sweep_y = (self._tick * 1.5) % H
        for _sy in range(0, H, max(3, self._scanline_step - 1)):
            _dist = abs(_sy - _sweep_y) / H
            _sa = max(0, int(12 * (1.0 - _dist * 8)))
            if _sa > 0:
                p.fillRect(QRectF(0, _sy, W, 1), qcol(C.ENERGY, _sa))

        # Persistent faint scanlines
        for _sy in range(0, H, self._scanline_step):
            p.fillRect(QRectF(0, _sy, W, 1), qcol(C.ENERGY, 12))

        # Vignette
        _vig = QRadialGradient(QPointF(cx, cy), max(W, H) * 0.7)
        _vig_edge = qcol(C.STEEL if _is_light_theme else C.DARK, 70 if _is_light_theme else 170)
        _vig.setColorAt(0.0, qcol(C.BG, 0))
        _vig.setColorAt(0.6, qcol(C.BG, 0))
        _vig.setColorAt(1.0, _vig_edge)
        p.fillRect(self.rect(), _vig)

        # Animated noise/grain — very subtle
        if self._tick % 3 == 0:  # Update every 3 frames
            self._noise_seed = self._tick
        _n_a = 50
        for _ni in range(self._noise_count):
            _nx = random.randint(0, W)
            _ny = random.randint(0, H)
            _ns = random.uniform(0.3, 1.0)
            p.fillRect(QRectF(_nx, _ny, _ns, _ns), qcol(C.PRI, _n_a))
