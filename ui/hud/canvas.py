"""Reactor canvas state and animation."""

from __future__ import annotations

import importlib

_legacy = importlib.import_module("ui._legacy")
globals().update({key: value for key, value in vars(_legacy).items() if not key.startswith("__")})

from .paint import HudCanvasPaintMixin

class HudCanvas(HudCanvasPaintMixin, QWidget):
    """
    Digital Consciousness v4 — Massive Neural Core.
    Enormous central presence, connected corners,
    spherical lattice, energy pulses, sharp core.
    """
    _NODE_COUNT = 350
    _SHELL_NODES = 100
    _WAVE_COLS = 60
    _WAVE_ROWS = 35
    _RING_COUNT = 5
    _LATTICE_RINGS = 8
    _LATTICE_ARCS = 6
    def __init__(self, face_path: str, parent=None, config: HudConfig = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.config = config or HudConfig()
        self.muted    = False
        self.speaking = False
        self.state    = "INITIALISING"

        self._tick       = 0
        self._scale      = 1.0
        self._tgt_scale  = 1.0
        self._brightness = 0.6
        self._tgt_bright = 0.6
        self._last_t     = time.time()
        self._blink      = True
        self._blink_tick = 0
        self._rotation_y = 0.0
        self._rotation_x = 0.0
        self._wave_opacity = 1.0
        self._ring_angles  = [random.uniform(0, 360) for _ in range(self._RING_COUNT)]

        # Spherical lattice rotation
        self._lattice_angle = 0.0

        # Energy pulse system
        self._pulses = []
        self._next_pulse_tick = random.randint(40, 100)

        # Neural network nodes: [r, theta, phi, size, brightness, pulse_phase, cluster_id]
        self._nodes = []
        cluster_centers = [
            (0.55, 0.0, 1.2),
            (0.40, 2.0, 0.8),
            (0.70, 3.8, 2.0),
            (0.30, 5.5, 1.5),
            (0.50, 1.0, 2.5),
            (0.60, 4.5, 0.5),
            (0.45, 3.0, 1.8),
            (0.35, 0.5, 0.5),
        ]
        cluster_sizes = [70, 55, 50, 35, 60, 45, 25, 20]

        for ci, (cr, ct, cphi) in enumerate(cluster_centers):
            for _ in range(cluster_sizes[ci]):
                spread = 0.20 + ci * 0.02
                r = max(0.05, min(1.0, cr + random.gauss(0, spread)))
                theta = ct + random.gauss(0, 0.5)
                phi = max(0.3, min(math.pi - 0.3, cphi + random.gauss(0, 0.35)))
                sz = random.uniform(0.6, 2.4)
                br = random.uniform(0.3, 1.0)
                phase = random.uniform(0, 2 * math.pi)
                self._nodes.append([r, theta, phi, sz, br, phase, ci])

        while len(self._nodes) < self._NODE_COUNT:
            r = random.uniform(0.0, 1.0) ** 0.45
            theta = random.uniform(0, 2 * math.pi)
            phi = math.acos(random.uniform(-1, 1))
            sz = random.uniform(0.3, 1.2)
            br = random.uniform(0.08, 0.30)
            phase = random.uniform(0, 2 * math.pi)
            self._nodes.append([r, theta, phi, sz, br, phase, -1])

        # Pre-compute connections — denser now
        self._connections = []
        sample = self._nodes[:200]
        for i in range(len(sample)):
            for j in range(i + 1, len(sample)):
                ni, nj = sample[i], sample[j]
                same_cluster = (ni[6] == nj[6] and ni[6] >= 0)
                xi = ni[0] * math.sin(ni[2]) * math.cos(ni[1])
                yi = ni[0] * math.sin(ni[2]) * math.sin(ni[1])
                zi = ni[0] * math.cos(ni[2])
                xj = nj[0] * math.sin(nj[2]) * math.cos(nj[1])
                yj = nj[0] * math.sin(nj[2]) * math.sin(nj[1])
                zj = nj[0] * math.cos(nj[2])
                dist = math.sqrt((xi-xj)**2 + (yi-yj)**2 + (zi-zj)**2)
                threshold = 0.32 if same_cluster else 0.18
                if dist < threshold:
                    self._connections.append((i, j, dist, same_cluster))

        # Shell surface nodes
        self._shell = []
        for _ in range(self._SHELL_NODES):
            theta = random.uniform(0, 2 * math.pi)
            phi = math.acos(random.uniform(-1, 1))
            sz = random.uniform(0.2, 0.7)
            phase = random.uniform(0, 2 * math.pi)
            self._shell.append([theta, phi, sz, phase])

        # Orbital ring configs: [radius_frac, tilt_x, tilt_z, width, speed, style]
        self._orbital_rings = [
            (1.08, 0.3, 0.0, 1.6, 0.15, 0),
            (0.92, -0.2, 0.5, 0.9, -0.22, 1),
            (1.18, 0.1, -0.4, 0.7, 0.10, 2),
            (0.80, 0.6, 0.2, 1.2, -0.18, 0),
            (1.28, -0.4, 0.3, 0.5, 0.08, 3),
        ]

        # Massive secondary rings — giant, barely visible
        self._mega_rings = [
            (1.6, 0.0008, 0.5, 1.0),
            (2.2, -0.0003, 0.35, 0.8),
            (1.35, 0.0015, 0.45, 0.6),
            (2.8, 0.00015, 0.2, 0.5),
            (3.5, -0.0001, 0.12, 0.3),
        ]

        # Ambient depth particles
        self._depth_pts = []
        for _ in range(120):
            x = random.uniform(-0.6, 0.6)
            y = random.uniform(-0.5, 0.5)
            sz = random.uniform(0.2, 0.6)
            phase = random.uniform(0, 2 * math.pi)
            self._depth_pts.append([x, y, sz, phase])

        # Wave field
        self._wave_pts = []
        for row in range(self._WAVE_ROWS):
            for col in range(self._WAVE_COLS):
                nx = col / max(self._WAVE_COLS - 1, 1)
                ny = row / max(self._WAVE_ROWS - 1, 1)
                self._wave_pts.append([nx, ny, random.uniform(0, 2 * math.pi)])

        self._face_px = None
        self._load_face(face_path)

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self.set_graphics_quality(get_graphics_quality())
    def set_graphics_quality(self, quality: str):
        """Apply a graphics profile without rebuilding the HUD."""
        value = _normalize_graphics_quality(quality)
        profile = GRAPHICS_PROFILES[value]
        self._graphics_quality = value
        self._render_stride = int(profile["render_stride"])
        self._wave_stride = int(profile["wave_stride"])
        self._noise_count = int(profile["noise_count"])
        self._scanline_step = int(profile["scanline_step"])
        self._antialias = bool(profile["antialias"])
        self._tmr.setInterval(int(profile["frame_ms"]))
        if not self._tmr.isActive():
            self._tmr.start()
        self.update()
    def _load_face(self, path: str):
        try:
            from PIL import Image, ImageDraw
            import io
            img = Image.open(path).convert("RGBA")
            sz  = min(img.size)
            img = img.resize((sz, sz), Image.LANCZOS)
            mk  = Image.new("L", (sz, sz), 0)
            ImageDraw.Draw(mk).ellipse((2, 2, sz - 2, sz - 2), fill=255)
            img.putalpha(mk)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            px = QPixmap(); px.loadFromData(buf.getvalue())
            self._face_px = px
        except Exception:
            self._face_px = None
    def _step(self):
        self._tick += 1
        now = time.time()
        is_active = self.speaking or self.state in ("THINKING", "PROCESSING")

        if now - self._last_t > (0.10 if is_active else 0.45):
            if self.speaking:
                _speak_breath = 0.5 + 0.5 * math.sin(self._tick * 0.08)
                self._tgt_scale = random.uniform(1.03, 1.08) + _speak_breath * 0.04
                self._tgt_bright = random.uniform(0.85, 1.0)
            elif self.muted:
                self._tgt_scale = random.uniform(0.99, 1.01)
                self._tgt_bright = random.uniform(0.1, 0.2)
            elif is_active:
                self._tgt_scale = random.uniform(1.01, 1.05)
                self._tgt_bright = random.uniform(0.6, 0.85)
            else:
                breath = 0.5 + 0.5 * math.sin(self._tick * 0.035)
                self._tgt_scale = 1.0 + breath * 0.05
                self._tgt_bright = 0.25 + breath * 0.55
            self._last_t = now

        sp = 0.30 if is_active else 0.10
        self._scale     += (self._tgt_scale  - self._scale)     * sp
        self._brightness += (self._tgt_bright - self._brightness) * sp

        # Wave fade
        if self.speaking:
            wt = 0.0
        elif is_active:
            wt = 0.15
        else:
            wt = 1.0
        self._wave_opacity += (wt - self._wave_opacity) * 0.06

        # Rotation
        rot_speed = 0.008 if is_active else (0.002 if self.muted else 0.004)
        self._rotation_y += rot_speed
        self._rotation_x  = 0.25 + 0.05 * math.sin(self._tick * 0.003)
        self._lattice_angle += rot_speed * 0.3

        # Orbital rings
        for i, (_, _, _, _, spd, _) in enumerate(self._orbital_rings):
            mult = 2.5 if is_active else 1.0
            self._ring_angles[i] = (self._ring_angles[i] + spd * mult) % 360

        # Energy pulses
        self._next_pulse_tick -= 1
        pulse_interval = 15 if is_active else 60
        if self._next_pulse_tick <= 0 and len(self._pulses) < 10:
            if self._connections:
                conn = random.choice(self._connections)
                spd = random.uniform(0.008, 0.018)
                cidx = random.choice([0, 1, 2])
                self._pulses.append([conn[0], conn[1], 0.0, spd, cidx])
            self._next_pulse_tick = random.randint(pulse_interval // 2, pulse_interval)

        alive = []
        for pulse in self._pulses:
            pulse[2] += pulse[3]
            if pulse[2] < 1.0:
                alive.append(pulse)
        self._pulses = alive

        # Node animation
        for nd in self._nodes[::self._render_stride]:
            nd[5] += 0.04
            drift = random.gauss(0, 0.0008) * (3.0 if is_active else 1.0)
            nd[0] = max(0.05, min(1.0, nd[0] + drift))
            tb = random.uniform(0.5, 1.0) if is_active else (
                random.uniform(0.05, 0.2) if self.muted else random.uniform(0.25, 0.65))
            nd[4] += (tb - nd[4]) * 0.06

        self._blink_tick += 1
        if self._blink_tick >= 32:
            self._blink = not self._blink
            self._blink_tick = 0
        self.update()
    def _proj(self, r, theta, phi, sr, cx, cy):
        x = r * math.sin(phi) * math.cos(theta)
        y = r * math.sin(phi) * math.sin(theta)
        z = r * math.cos(phi)
        crx = math.cos(self._rotation_x); srx = math.sin(self._rotation_x)
        cry = math.cos(self._rotation_y); sry = math.sin(self._rotation_y)
        xr = x * cry - z * sry
        zr = x * sry + z * cry
        yr = y * crx - zr * srx
        z2 = y * srx + zr * crx
        return cx + xr * sr, cy - yr * sr, z2, max(0.0, min(1.0, (z2 + 1.0) / 2.0))
