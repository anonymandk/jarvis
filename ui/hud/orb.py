"""Quiet state-driven reactor and activity visualizer for the JARVIS core."""

from __future__ import annotations

import importlib
import math

_runtime = importlib.import_module("ui._runtime")
globals().update({key: value for key, value in vars(_runtime).items() if not key.startswith("__")})


_STATE_COLOR_ROLES = {
    "idle": "TEXT_MED",
    "listening": "GREEN",
    "processing": "PURPLE",
    "speaking": "PRI",
    "reconnecting": "AMBER",
    "error": "RED",
    "muted": "TEXT_DIM",
}


class ReactorOrb(QWidget):
    """One clear JARVIS mark whose motion follows state and user preferences."""

    _ACTIVE_STATES = {"listening", "processing", "speaking", "reconnecting"}

    def __init__(self, parent=None, *, graphics_quality: str = "medium", reduced_motion: bool = False):
        super().__init__(parent)
        self.setMinimumSize(184, 184)
        self.setMaximumSize(320, 320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("JARVIS reator central")
        self._state = "idle"
        self._frame = 0
        self._quality = _normalize_graphics_quality(graphics_quality)
        self._reduced_motion = bool(reduced_motion)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._transition_timer = QTimer(self)
        self._transition_timer.setSingleShot(True)
        self._transition_timer.timeout.connect(self._finish_transition)
        self._sync_motion()

    def set_state(self, state: str) -> None:
        aliases = {
            "standing by": "idle", "initialising": "idle", "initializing": "idle",
            "thinking": "processing", "processing": "processing",
            "listening": "listening", "speaking": "speaking",
            "reconnecting": "reconnecting", "error": "error", "muted": "muted",
        }
        value = aliases.get(str(state or "").strip().lower(), "idle")
        if value == self._state:
            return
        self._state = value
        self._frame = 0
        self.setAccessibleDescription(f"Estado atual: {self._state_label(value)}")
        self._sync_motion(start_transition=True)
        self.update()

    @staticmethod
    def _state_label(state: str) -> str:
        return {
            "idle": "Em espera", "listening": "Ouvindo", "processing": "Processando",
            "speaking": "Falando", "reconnecting": "Reconectando", "error": "Erro",
            "muted": "Microfone silenciado",
        }.get(state, "Em espera")

    def set_graphics_quality(self, quality: str) -> None:
        self._quality = _normalize_graphics_quality(quality)
        self._sync_motion()
        self.update()

    def set_reduced_motion(self, enabled: bool) -> None:
        self._reduced_motion = bool(enabled)
        self._sync_motion()
        self.update()

    def _sync_motion(self, *, start_transition: bool = False) -> None:
        animate = (
            self._quality != "low"
            and not self._reduced_motion
            and self._state in self._ACTIVE_STATES
        )
        if animate:
            self._timer.setInterval(int(GRAPHICS_PROFILES[self._quality]["frame_ms"]))
            if start_transition:
                self._timer.start()
                self._transition_timer.start(TOKENS.motion_ms["state_transition"])
        else:
            self._timer.stop()
            self._transition_timer.stop()

    def _finish_transition(self) -> None:
        self._timer.stop()
        self.update()

    def _advance(self) -> None:
        self._frame = (self._frame + 1) % 240
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, self._quality != "low")
        side = min(self.width(), self.height())
        cx, cy = self.width() / 2, self.height() / 2
        radius = side * 0.35
        color = QColor(getattr(C, _STATE_COLOR_ROLES[self._state]))
        pulse = 0.0
        if self._timer.isActive():
            pulse = (math.sin(self._frame * math.tau / 120) + 1) / 2

        painter.setPen(QPen(qcol(C.BORDER_B, 1), 1))
        painter.setBrush(qcol(C.PANEL))
        painter.drawEllipse(QPointF(cx, cy), radius * 1.38, radius * 1.38)

        halo = max(0, min(255, int(16 + pulse * 18)))
        painter.setPen(QPen(qcol(color.name(), 100 + halo), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), radius * 1.22, radius * 1.22)

        core = QRadialGradient(QPointF(cx, cy), radius)
        core.setColorAt(0.0, qcol(color.name(), 54 + int(pulse * 28)))
        core.setColorAt(0.78, qcol(C.PANEL2, 255))
        core.setColorAt(1.0, qcol(C.DARK, 255))
        painter.setPen(QPen(qcol(color.name(), 210), 1.5))
        painter.setBrush(QBrush(core))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(
            QRectF(cx - radius * 1.1, cy - radius * 1.1, radius * 2.2, radius * 2.2),
            int((self._frame * 16) % 360 * 16),
            105 * 16,
        )
        painter.end()


class ActivityVisualizer(QWidget):
    """A state-linked visual cue, explicitly separate from measured audio level."""

    _ACTIVE_STATES = {"listening", "processing", "speaking"}

    def __init__(self, parent=None, *, graphics_quality: str = "medium", reduced_motion: bool = False):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setAccessibleName("Atividade visual, sem nível de áudio medido")
        self._state = "idle"
        self._frame = 0
        self._quality = _normalize_graphics_quality(graphics_quality)
        self._reduced_motion = bool(reduced_motion)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._transition_timer = QTimer(self)
        self._transition_timer.setSingleShot(True)
        self._transition_timer.timeout.connect(self._finish_transition)
        self._sync_motion()

    def set_state(self, state: str) -> None:
        value = str(state or "idle").strip().lower()
        if value == "thinking":
            value = "processing"
        value = value if value in {"idle", "listening", "processing", "speaking", "muted", "error", "reconnecting"} else "idle"
        if value == self._state:
            return
        self._state = value
        self._frame = 0
        self._sync_motion(start_transition=True)
        self.update()

    def set_graphics_quality(self, quality: str) -> None:
        self._quality = _normalize_graphics_quality(quality)
        self._sync_motion()
        self.update()

    def set_reduced_motion(self, enabled: bool) -> None:
        self._reduced_motion = bool(enabled)
        self._sync_motion()
        self.update()

    def _sync_motion(self, *, start_transition: bool = False) -> None:
        animate = self._quality != "low" and not self._reduced_motion and self._state in self._ACTIVE_STATES
        if animate:
            self._timer.setInterval(int(GRAPHICS_PROFILES[self._quality]["frame_ms"]))
            if start_transition:
                self._timer.start()
                self._transition_timer.start(TOKENS.motion_ms["state_transition"])
        else:
            self._timer.stop()
            self._transition_timer.stop()

    def _finish_transition(self) -> None:
        self._timer.stop()
        self.update()

    def _advance(self) -> None:
        self._frame = (self._frame + 1) % 80
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, self._quality != "low")
        color = QColor(getattr(C, _STATE_COLOR_ROLES.get(self._state, "TEXT_MED")))
        count = 9
        gap = 7
        bar_width = 5
        total = count * bar_width + (count - 1) * gap
        start_x = (self.width() - total) / 2
        baseline = self.height() / 2
        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(count):
            if self._state in self._ACTIVE_STATES and self._timer.isActive():
                fraction = 0.25 + 0.65 * abs(math.sin((index * 0.7) + self._frame * 0.08))
            elif self._state in self._ACTIVE_STATES:
                fraction = 0.56 if index in {2, 3, 4, 5, 6} else 0.30
            else:
                fraction = 0.22
            height = max(3, (self.height() - 8) * fraction)
            color.setAlpha(190 if self._state in self._ACTIVE_STATES else 90)
            painter.setBrush(QBrush(color))
            x = start_x + index * (bar_width + gap)
            painter.drawRoundedRect(QRectF(x, baseline - height / 2, bar_width, height), 2, 2)
        painter.end()
