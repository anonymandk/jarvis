"""Shared behavior for draggable Qt overlays."""

from __future__ import annotations

import importlib

_runtime = importlib.import_module("ui._runtime")
globals().update({key: value for key, value in vars(_runtime).items() if not key.startswith("__")})

class _OverlayBase(QWidget):
    """
    Base class for all JARVIS overlay popups.
    Provides:
      - Drag-to-move (click anywhere on the widget and drag)
      - An ✕ close button in the top-right corner
    Subclasses must call _setup_overlay_base() after building their layout,
    or call super().__init__() and use _add_close_btn(layout) manually.
    """

    def _setup_overlay_base(self, close_callback=None):
        """
        Call this once after the overlay's layout is fully built.
        Adds a floating ✕ button over the top-right corner.
        close_callback: callable to invoke on close (defaults to self.hide).
        """
        self._drag_pos = None
        self._close_cb = close_callback or self.hide

        btn = QPushButton("✕", self)
        btn.setFixedSize(22, 22)
        btn.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_9"], QFont.Weight.Bold))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C.TEXT_DIM};
                border: none;
                border-radius: {TOKENS.radii['legacy_3']}px;
            }}
            QPushButton:hover {{
                color: {C.RED};
                background: {qss_rgba(C.MUTED_C, TOKENS.opacity['close_button_tint'])};
            }}
        """)
        btn.clicked.connect(self._close_cb)
        self._close_btn = btn
        self._reposition_close_btn()

    def _reposition_close_btn(self):
        if hasattr(self, "_close_btn"):
            self._close_btn.move(self.width() - 28, 6)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_close_btn()

    def paintEvent(self, event):
        super().paintEvent(event)
        from PyQt6.QtGui import QPainter, QPen, QColor
        from PyQt6.QtCore import QPointF
        p = QPainter(self)
        p.setRenderHint(p.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bl = 16
        a = 60
        col = qcol(C.PRI, a)
        p.setPen(QPen(col, 1.2))
        for bx, by, dx, dy in [(0,0,1,1),(w,0,-1,1),(0,h,1,-1),(w,h,-1,-1)]:
            p.drawLine(QPointF(bx, by), QPointF(bx + dx * bl, by))
            p.drawLine(QPointF(bx, by), QPointF(bx, by + dy * bl))
        p.end()

    # ── Drag support ────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            # Clamp within parent bounds
            if self.parent():
                pr = self.parent().rect()
                new_pos.setX(max(0, min(new_pos.x(), pr.width()  - self.width())))
                new_pos.setY(max(0, min(new_pos.y(), pr.height() - self.height())))
            self.move(new_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)
