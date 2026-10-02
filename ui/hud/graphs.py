"""Metric bars and sparklines."""

from __future__ import annotations

import importlib

_legacy = importlib.import_module("ui._legacy")
globals().update({key: value for key, value in vars(_legacy).items() if not key.startswith("__")})

class MetricBar(QWidget):

    def __init__(self, label: str, color: str = C.PRI, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0       # 0–100
        self._text  = "--"
        self.setFixedHeight(38)
        self.setMinimumWidth(80)

    def set_value(self, pct: float, text: str):
        self._value = max(0.0, min(100.0, pct))
        self._text  = text
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        p.setBrush(QBrush(qcol(C.PANEL2)))
        p.setPen(QPen(qcol(C.BORDER_A), 1))
        p.drawRoundedRect(QRectF(1, 1, W - 2, H - 2), 4, 4)

        bar_h   = 4
        bar_y   = H - bar_h - 5
        bar_w   = W - 12
        bar_x   = 6
        fill_w  = int(bar_w * self._value / 100)

        p.setBrush(QBrush(qcol(C.BAR_BG)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2, 2)

        if self._value > 85:
            bar_col = qcol(C.TEXT_MED)
        elif self._value > 65:
            bar_col = qcol(C.TEXT_MED)
        else:
            bar_col = qcol(self._color)

        if fill_w > 0:
            p.setBrush(QBrush(bar_col))
            p.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 2, 2)

        p.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(8, 5, 50, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._label)

        p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        p.setPen(QPen(bar_col if self._text != "--" else qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(0, 4, W - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._text)


class SparklineBar(QWidget):
    """Compact metric row with label, sparkline, and value."""

    def __init__(self, label: str, color: str = C.TEXT_MED, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = "0"
        self._unit = ""
        self._history = [0.0] * 30
        self.setFixedHeight(28)

    def set_value(self, value: str, pct: float = 0.0, unit: str = ""):
        """Update value and sparkline. pct is 0-1 for the bar height."""
        self._value = value
        self._unit = unit
        self._history.append(max(0.0, min(1.0, pct)))
        if len(self._history) > 30:
            self._history = self._history[-30:]
        self.update()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient
        from PyQt6.QtCore import QPointF
        W, H = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Label (left)
        p.setFont(QFont("Courier New", 6, QFont.Weight.Bold))
        p.setPen(QColor(C.TEXT_DIM))
        label_w = 44
        p.drawText(0, 0, label_w, H, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._label)

        # Sparkline (middle)
        spark_x = label_w + 2
        spark_w = W - label_w - 60
        spark_h = H - 6
        spark_y = 3

        col = QColor(self._color)
        col_dim = QColor(self._color)
        col_dim.setAlpha(40)

        # Fill area under curve
        if len(self._history) > 1:
            from PyQt6.QtGui import QPainterPath
            path = QPainterPath()
            step = spark_w / (len(self._history) - 1)
            for i, v in enumerate(self._history):
                x = spark_x + i * step
                y = spark_y + spark_h * (1 - v)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            # Close path for fill
            fill = QPainterPath(path)
            fill.lineTo(spark_x + spark_w, spark_y + spark_h)
            fill.lineTo(spark_x, spark_y + spark_h)
            fill.closeSubpath()
            fill_col = QColor(self._color)
            fill_col.setAlpha(15)
            p.fillPath(fill, fill_col)
            # Stroke line
            p.setPen(QPen(col, 1.2))
            p.drawPath(path)

        # Value (right)
        p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        p.setPen(QColor(C.WHITE))
        val_x = W - 55
        val_w = 35
        p.drawText(val_x, 0, val_w, H, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, self._value)
        # Unit
        p.setFont(QFont("Courier New", 6))
        p.setPen(QColor(C.TEXT_DIM))
        p.drawText(val_x + val_w + 2, 0, 18, H, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._unit)

        p.end()
