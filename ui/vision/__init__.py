"""Desktop vision preview window."""

from __future__ import annotations

import importlib

_runtime = importlib.import_module("ui._runtime")
globals().update({key: value for key, value in vars(_runtime).items() if not key.startswith("__")})

class VisionPreviewWindow(QWidget):
    """Small draggable live preview shown while JARVIS is using vision."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("visionPreview")
        self.setAccessibleName("JARVIS live vision preview")
        self.setFixedSize(360, 248)
        self._source = "screen"
        self._drag_origin_global = None
        self._drag_origin_pos = None
        self._has_user_position = False
        self._camera = None
        self._cv2 = None
        self._screen_capture = None
        self._screen_monitor = None
        self._graphics_quality = "medium"

        root = QVBoxLayout(self)
        root.setContentsMargins(TOKENS.spacing["legacy_1"], TOKENS.spacing["legacy_1"], TOKENS.spacing["legacy_1"], TOKENS.spacing["legacy_1"])
        root.setSpacing(TOKENS.spacing["legacy_0"])

        self._header = QWidget(self)
        self._header.setObjectName("visionPreviewHeader")
        self._header.setFixedHeight(38)
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(TOKENS.spacing["legacy_12"], TOKENS.spacing["legacy_0"], TOKENS.spacing["legacy_8"], TOKENS.spacing["legacy_0"])
        header_layout.setSpacing(TOKENS.spacing["legacy_8"])

        self._live_dot = QLabel("●", self._header)
        self._live_dot.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_8"], QFont.Weight.Medium))
        self._title = QLabel("VISION LINK", self._header)
        self._title.setFont(QFont(UI_FONT, TOKENS.font_sizes["legacy_9"], QFont.Weight.DemiBold))
        self._source_label = QLabel("SCREEN FEED", self._header)
        self._source_label.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_7"], QFont.Weight.Medium))
        header_layout.addWidget(self._live_dot)
        header_layout.addWidget(self._title)
        header_layout.addStretch(1)
        header_layout.addWidget(self._source_label)

        self._close_button = QPushButton("×", self._header)
        self._close_button.setAccessibleName("Close vision preview")
        self._close_button.setToolTip("Close live preview")
        self._close_button.setFixedSize(24, 24)
        self._close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_button.clicked.connect(self.stop)
        header_layout.addWidget(self._close_button)
        root.addWidget(self._header)

        self._frame = QLabel("INITIALIZING VISION LINK", self)
        self._frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._frame.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_8"], QFont.Weight.Medium))
        self._frame.setMinimumHeight(174)
        self._frame.setAccessibleName("Live vision image")
        root.addWidget(self._frame, stretch=1)

        self._status = QLabel("LIVE // ANALYZING", self)
        self._status.setFixedHeight(32)
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_7"], QFont.Weight.Medium))
        root.addWidget(self._status)

        for draggable in (self._header, self._live_dot, self._title, self._source_label):
            draggable.installEventFilter(self)
        if parent is not None:
            parent.installEventFilter(self)

        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._update_frame)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.stop)
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)
        self._fade = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade.setDuration(TOKENS.motion_ms["legacy_180"])
        self._fade.setEasingCurve(
            getattr(QEasingCurve.Type, TOKENS.motion_easing["standard"])
        )
        self.refresh_theme()
        self.set_graphics_quality(get_graphics_quality())

    def refresh_theme(self):
        self.setStyleSheet(f"""
            QWidget#visionPreview {{
                background: {C.BG}; border: 1px solid {C.BORDER_B}; border-radius: {TOKENS.radii['legacy_7']}px;
            }}
            QWidget#visionPreviewHeader {{
                background: {C.PANEL2}; border: none; border-bottom: 1px solid {C.BORDER};
            }}
        """)
        self._live_dot.setStyleSheet(f"color: {C.PRI}; background: transparent; border: none;")
        self._title.setStyleSheet(f"color: {C.WHITE}; background: transparent; border: none;")
        self._source_label.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        self._frame.setStyleSheet(f"color: {C.TEXT_DIM}; background: {C.DARK}; border: none;")
        self._status.setStyleSheet(
            f"color: {C.TEXT_MED}; background: {C.PANEL}; border: none; border-top: 1px solid {C.BORDER};"
        )
        self._close_button.setStyleSheet(f"""
            QPushButton {{
                color: {C.WHITE_DIM}; background: transparent; border: none; border-radius: {TOKENS.radii['legacy_4']}px;
                font-family: '{UI_FONT}'; font-size: {TOKENS.font_sizes['legacy_15']}px;
            }}
            QPushButton:hover {{ color: {C.WHITE}; background: {C.RED_BG}; }}
        """)

    def set_graphics_quality(self, quality: str):
        self._graphics_quality = _normalize_graphics_quality(quality)
        profile_ms = int(GRAPHICS_PROFILES[self._graphics_quality]["frame_ms"])
        self._frame_timer.setInterval(max(42, profile_ms * 2))

    def eventFilter(self, watched, event):
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self._clamp_to_parent)
            return False
        if watched in (self._header, self._live_dot, self._title, self._source_label):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_origin_global = event.globalPosition().toPoint()
                self._drag_origin_pos = self.pos()
                return True
            if event.type() == QEvent.Type.MouseMove and self._drag_origin_global is not None:
                if event.buttons() & Qt.MouseButton.LeftButton:
                    delta = event.globalPosition().toPoint() - self._drag_origin_global
                    self.move(self._bounded_position(self._drag_origin_pos + delta))
                    self._has_user_position = True
                    return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_origin_global = None
                self._drag_origin_pos = None
                return True
        return super().eventFilter(watched, event)

    def _bounded_position(self, position):
        parent = self.parentWidget()
        if parent is None:
            return position
        margin = 12
        max_x = max(margin, parent.width() - self.width() - margin)
        max_y = max(margin, parent.height() - self.height() - margin)
        return type(position)(
            max(margin, min(position.x(), max_x)),
            max(margin, min(position.y(), max_y)),
        )

    def _clamp_to_parent(self):
        if self.parentWidget() is not None:
            self.move(self._bounded_position(self.pos()))

    def start(self, source: str):
        self._hide_timer.stop()
        self._release_source()
        self._source = "camera" if str(source).lower().strip() == "camera" else "screen"
        self._source_label.setText(f"{self._source.upper()} FEED")
        self._status.setText("LIVE // ANALYZING")
        self._frame.setText("INITIALIZING VISION LINK")
        self._frame.setPixmap(QPixmap())

        try:
            self._open_source()
            self._frame_timer.start()
            self._update_frame()
        except Exception as exc:
            self._show_error(str(exc))

        if not self.isVisible():
            parent = self.parentWidget()
            if parent is not None and not self._has_user_position:
                self.move(self._bounded_position(
                    QPointF(parent.width() - self.width() - 24, 68).toPoint()
                ))
            else:
                self._clamp_to_parent()
            self._opacity_effect.setOpacity(0.0)
            self.show()
            self.raise_()
            self._fade.stop()
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(1.0)
            self._fade.start()
        else:
            self._clamp_to_parent()
            self.raise_()

    def finish(self, delay_ms: int = 1800):
        self._status.setText("ANALYSIS COMPLETE")
        self._hide_timer.start(max(0, int(delay_ms)))

    def stop(self):
        self._hide_timer.stop()
        self._frame_timer.stop()
        self._release_source()
        self._opacity_effect.setOpacity(1.0)
        self.hide()

    def _camera_index(self) -> int:
        try:
            data = json.loads(API_FILE.read_text(encoding="utf-8")) if API_FILE.exists() else {}
            return int(data.get("camera_index", 0))
        except Exception:
            return 0

    def _open_source(self):
        if self._source == "camera":
            import cv2
            self._cv2 = cv2
            backend = cv2.CAP_AVFOUNDATION if _OS == "Darwin" else (
                cv2.CAP_DSHOW if _OS == "Windows" else cv2.CAP_ANY
            )
            self._camera = cv2.VideoCapture(self._camera_index(), backend)
            if not self._camera.isOpened():
                self._camera.release()
                self._camera = None
                raise RuntimeError("CAMERA FEED UNAVAILABLE")
        else:
            import mss
            self._screen_capture = mss.mss()
            monitors = self._screen_capture.monitors
            self._screen_monitor = monitors[1] if len(monitors) > 1 else monitors[0]

    def _update_frame(self):
        try:
            import numpy as np
            if self._source == "camera":
                if self._camera is None:
                    return
                ok, frame = self._camera.read()
                if not ok or frame is None:
                    raise RuntimeError("CAMERA SIGNAL LOST")
                rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
            else:
                if self._screen_capture is None or self._screen_monitor is None:
                    return
                shot = self._screen_capture.grab(self._screen_monitor)
                bgra = np.asarray(shot)
                rgb = bgra[:, :, :3][:, :, ::-1].copy()

            height, width = rgb.shape[:2]
            image = QImage(rgb.data, width, height, width * 3, QImage.Format.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(image).scaled(
                self._frame.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._frame.setPixmap(pixmap)
        except Exception as exc:
            self._show_error(str(exc))

    def _show_error(self, message: str):
        self._frame_timer.stop()
        self._frame.setPixmap(QPixmap())
        self._frame.setText("VISION LINK UNAVAILABLE")
        self._status.setText(str(message or "FEED ERROR").upper()[:52])

    def _release_source(self):
        if self._camera is not None:
            try:
                self._camera.release()
            except Exception:
                pass
        self._camera = None
        self._cv2 = None
        if self._screen_capture is not None:
            try:
                self._screen_capture.close()
            except Exception:
                pass
        self._screen_capture = None
        self._screen_monitor = None

    def closeEvent(self, event):
        self._frame_timer.stop()
        self._release_source()
        event.accept()
