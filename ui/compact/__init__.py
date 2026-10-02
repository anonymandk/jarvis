"""Floating compact-mode widget."""

from __future__ import annotations

import importlib

_legacy = importlib.import_module("ui._legacy")
globals().update({key: value for key, value in vars(_legacy).items() if not key.startswith("__")})

class CompactModeWidget(QWidget):
    """Small floating circular arc reactor widget for compact mode."""

    expand_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(80, 80)

        self._tick = 0
        self._ring_angle = 0.0
        self._state = "LISTENING"
        self._drag_pos = None

        ThemeManager.add_listener(lambda _: self.update())
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(30)

    def set_state(self, state: str):
        self._state = state

    def _step(self):
        self._tick += 1
        speed = 2.0 if self._state in ("SPEAKING", "THINKING") else 0.5
        self._ring_angle = (self._ring_angle + speed) % 360
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        r = min(W, H) / 2 - 4

        # Background circle
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(qcol(C.DARK, 220)))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Outer ring
        p.setPen(QPen(qcol(C.PRI, 120), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Rotating arcs
        rect = QRectF(cx - r + 4, cy - r + 4, (r - 4) * 2, (r - 4) * 2)
        is_active = self._state in ("SPEAKING", "THINKING", "PROCESSING")
        alpha = 200 if is_active else 100
        p.setPen(QPen(qcol(C.ENERGY, alpha), 2))
        for i in range(3):
            start = int((self._ring_angle + i * 120) * 16)
            p.drawArc(rect, start, 60 * 16)

        # Core glow
        core_r = r * 0.3
        grad = QRadialGradient(QPointF(cx, cy), core_r)
        glow_a = 180 if is_active else 80
        grad.setColorAt(0, qcol(C.ENERGY, glow_a))
        grad.setColorAt(1, qcol(C.PRI, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # State indicator dot
        state_col = {
            "LISTENING": C.GREEN, "SPEAKING": C.PRI,
            "THINKING": C.ACC, "PROCESSING": C.PURPLE,
        }.get(self._state, C.TEXT_DIM)
        p.setBrush(QBrush(qcol(state_col)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy + r - 10), 4, 4)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if self._drag_pos:
            # If barely moved, treat as click → expand
            delta = event.globalPosition().toPoint() - self.frameGeometry().topLeft() - self._drag_pos
            if abs(delta.x()) < 5 and abs(delta.y()) < 5:
                self.expand_requested.emit()
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        self.expand_requested.emit()
