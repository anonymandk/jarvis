"""Toast, popup, and presence notification components."""

from __future__ import annotations

import importlib

_runtime = importlib.import_module("ui._runtime")
globals().update({key: value for key, value in vars(_runtime).items() if not key.startswith("__")})

class ToastNotification(QWidget):
    """Floating toast notification that auto-dismisses."""

    def __init__(self, parent, message: str, toast_type: str = "info", duration: int = 4000):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(48)

        colors = {
            "info":    (C.PRI,    C.PRI_GHO),
            "success": (C.GREEN,  C.GREEN_BG),
            "warning": (C.BG,     C.ACC2),
            "error":   (C.RED,    C.RED_BG),
        }
        fg, bg = colors.get(toast_type, colors["info"])

        self.setStyleSheet(f"""
            ToastNotification {{
                background: {bg};
                border: 1px solid {fg}88;
                border-radius: {TOKENS.radii['legacy_6']}px;
            }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(TOKENS.spacing["legacy_12"], TOKENS.spacing["legacy_2"], TOKENS.spacing["legacy_12"], TOKENS.spacing["legacy_2"])
        lay.setSpacing(TOKENS.spacing["legacy_8"])

        symbols = {"info": "◈", "success": "✓", "warning": "⚠", "error": "✗"}
        sym = QLabel(symbols.get(toast_type, "◈"))
        sym.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_10"], QFont.Weight.Bold))
        sym.setStyleSheet(f"color: {fg}; background: transparent;")
        lay.addWidget(sym)

        msg = QLabel(message)
        msg.setFont(QFont(TECH_FONT, TOKENS.font_sizes["caption"]))
        message_color = C.BG if toast_type == "warning" else C.WHITE
        msg.setStyleSheet(f"color: {message_color}; background: transparent;")
        lay.addWidget(msg, stretch=1)

        close = QPushButton("✕")
        close.setFixedSize(40, 40)
        close.setAccessibleName("Dispensar notificação")
        close.setToolTip("Dispensar notificação")
        close.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_8"]))
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close_color = C.BG if toast_type == "warning" else C.TEXT_DIM
        close.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {close_color}; border: none; }}
            QPushButton:hover {{ color: {fg}; }}
            QPushButton:focus {{ border: 2px solid {fg}; }}
        """)
        close.clicked.connect(self._dismiss)
        lay.addWidget(close)

        # Opacity for fade
        self._opacity_effect = None
        try:
            from PyQt6.QtWidgets import QGraphicsOpacityEffect
            self._opacity_effect = QGraphicsOpacityEffect(self)
            self._opacity_effect.setOpacity(1.0)
            self.setGraphicsEffect(self._opacity_effect)
        except Exception:
            pass

        # Auto-dismiss timer
        QTimer.singleShot(duration, self._dismiss)

    def _dismiss(self):
        try:
            self.hide()
            self.deleteLater()
        except Exception:
            pass


class ToastManager:
    """Manages toast notification positioning."""

    _toasts: list[ToastNotification] = []

    @classmethod
    def _is_alive(cls, t) -> bool:
        """Check if a toast widget is still alive and visible."""
        try:
            return t.isVisible()
        except RuntimeError:
            return False

    @classmethod
    def show_toast(cls, parent: QWidget, message: str, toast_type: str = "info",
                   duration: int = 4000):
        try:
            toast = ToastNotification(parent, message, toast_type, duration)
            toast.setFixedWidth(min(400, parent.width() - 40))

            # Clean up dead references first
            cls._toasts = [t for t in cls._toasts if cls._is_alive(t)]

            # Position from top-right, stacking downward
            y_offset = 10
            for t in cls._toasts:
                y_offset += t.height() + 6
            toast.move(parent.width() - toast.width() - 10, y_offset)
            toast.show()
            toast.raise_()
            cls._toasts.append(toast)
        except Exception:
            pass


class PopupType(Enum):
    """Types of popups with different sizes, durations, and priorities."""
    MICRO = "micro"
    INFORMATION = "information"
    ACTION = "action"
    RESEARCH = "research"
    CRITICAL = "critical"
    PRESENCE = "presence"


class PopupPriority(Enum):
    """Priority levels for popup management."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class PopupConfig:
    """Configuration for each popup type."""
    type: PopupType
    width: int
    height: int
    duration: int  # milliseconds, 0 for persistent (critical)
    priority: PopupPriority
    max_active: int
    orbit_radius: int
    opacity: float


class BasePopup(QWidget):
    """Base class for all popup types."""

    def __init__(self, parent: QWidget, message: str, popup_type: PopupType):
        super().__init__(parent)
        self.popup_type = popup_type
        self.config = POPUP_CONFIGS[popup_type]

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(self.config.width, self.config.height)

        # Styling based on popup type
        bg_colors = {
            PopupType.MICRO: qss_rgba(C.PRI_GHO, 204),
            PopupType.INFORMATION: qss_rgba(C.BORDER, 170),
            PopupType.ACTION: qss_rgba(C.ACC, 21),
            PopupType.RESEARCH: qss_rgba(C.PURPLE, 21),
            PopupType.CRITICAL: qss_rgba(C.RED, 32),
        }

        border_colors = {
            PopupType.MICRO: qss_rgba(C.PRI, 68),
            PopupType.INFORMATION: qss_rgba(C.BORDER, 136),
            PopupType.ACTION: qss_rgba(C.ACC, 136),
            PopupType.RESEARCH: qss_rgba(C.PURPLE, 136),
            PopupType.CRITICAL: qss_rgba(C.RED, 204),
        }

        text_colors = {
            PopupType.MICRO: C.PRI,
            PopupType.INFORMATION: C.TEXT,
            PopupType.ACTION: C.ACC,
            PopupType.RESEARCH: C.PURPLE,
            PopupType.CRITICAL: C.RED,
        }

        bg = bg_colors.get(popup_type, qss_rgba(C.PRI_GHO, 204))
        border = border_colors.get(popup_type, qss_rgba(C.PRI, 68))
        text_color = text_colors.get(popup_type, C.WHITE)

        self.setStyleSheet(f"""
            BasePopup {{
                background: {bg};
                border: 1px solid {border};
                border-radius: {TOKENS.radii['legacy_8']}px;
            }}
        """)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(TOKENS.spacing["legacy_12"], TOKENS.spacing["legacy_8"], TOKENS.spacing["legacy_12"], TOKENS.spacing["legacy_8"])
        layout.setSpacing(TOKENS.spacing["legacy_4"])

        # Icon/symbol
        symbols = {
            PopupType.MICRO: "◈",
            PopupType.INFORMATION: "ⓘ",
            PopupType.ACTION: "⚡",
            PopupType.RESEARCH: "🔍",
            PopupType.CRITICAL: "‼",
        }
        symbol = QLabel(symbols.get(popup_type, "◈"))
        symbol.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_14"], QFont.Weight.Bold))
        symbol.setStyleSheet(f"color: {text_color}; background: transparent;")
        layout.addWidget(symbol, alignment=Qt.AlignmentFlag.AlignLeft)

        # Message
        msg_label = QLabel(message)
        msg_label.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_9"]))
        msg_label.setStyleSheet(f"color: {text_color}; background: transparent;")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label, stretch=1)

        # Close button for non-critical popups
        if popup_type != PopupType.CRITICAL:
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(40, 40)
            close_btn.setAccessibleName("Dispensar aviso")
            close_btn.setFont(QFont(TECH_FONT, TOKENS.font_sizes["legacy_8"]))
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: %s88;
                    border: none;
                }
                QPushButton:hover {
                    color: %s;
                    background: %s11;
                }
                QPushButton:focus {
                    border: 2px solid %s;
                }
            """ % (text_color, text_color, text_color, text_color))
            close_btn.clicked.connect(self._dismiss)
            layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Opacity effect for fade animations
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(self.config.opacity)
        self.setGraphicsEffect(self._opacity_effect)

        # Auto-dismiss timer (if not critical)
        if self.config.duration > 0:
            QTimer.singleShot(self.config.duration, self._dismiss)

        # Track creation time for priority management
        self._created_at = time.time()

    def _dismiss(self):
        """Dismiss the popup with fade-out animation."""
        try:
            if self._opacity_effect:
                anim = QPropertyAnimation(self._opacity_effect, b"opacity")
                anim.setDuration(TOKENS.motion_ms["legacy_300"])
                anim.setStartValue(self.config.opacity)
                anim.setEndValue(0.0)
                anim.setEasingCurve(
                    getattr(QEasingCurve.Type, TOKENS.motion_easing["emphasis"])
                )
                anim.finished.connect(self.hide)
                anim.start()

                # Actually delete after animation
                QTimer.singleShot(350, self.deleteLater)
            else:
                self.hide()
                self.deleteLater()
        except Exception:
            self.hide()
            self.deleteLater()


class PopupManager(QObject):
    """Manages popup creation, positioning, and lifecycle."""

    popup_created = pyqtSignal(QWidget)
    popup_destroyed = pyqtSignal(QWidget)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.parent_widget = parent
        self.active_popups: List[BasePopup] = []
        self._orbit_positions = self._calculate_orbit_positions()

    def _calculate_orbit_positions(self) -> List[QPointF]:
        """Calculate orbit positions around the center."""
        # 8 positions around a circle: top, top-right, right, bottom-right,
        # bottom, bottom-left, left, top-left
        positions = []
        center_x = self.parent_widget.width() // 2
        center_y = self.parent_widget.height() // 2

        # We'll dynamically calculate based on orbit radius when showing
        # For now, return angles that we'll use with radius
        angles = [0, 45, 90, 135, 180, 225, 270, 315]  # degrees
        for angle in angles:
            positions.append(angle)
        return positions

    def show_popup(
        self,
        message: str,
        popup_type: PopupType = PopupType.INFORMATION,
        preferred_position: Optional[int] = None
    ) -> Optional[BasePopup]:
        """Show a popup with the given message and type."""
        config = POPUP_CONFIGS[popup_type]

        # Enforce limits
        if not self._can_show_popup(popup_type):
            # Remove lowest priority popup to make room
            self._remove_lowest_priority_popup()

        # Create popup
        popup = BasePopup(self.parent_widget, message, popup_type)

        # Position it
        pos = self._get_orbit_position(popup, preferred_position)
        popup.move(int(pos.x()), int(pos.y()))

        # Show and raise
        popup.show()
        popup.raise_()

        # Track
        self.active_popups.append(popup)
        self.popup_created.emit(popup)

        # Clean up finished popups periodically
        QTimer.singleShot(1000, self._cleanup_finished_popups)

        return popup

    def _can_show_popup(self, popup_type: PopupType) -> bool:
        """Check if we can show a popup of this type given current limits."""
        config = POPUP_CONFIGS[popup_type]

        # Count active popups of this type
        type_count = sum(
            1 for p in self.active_popups
            if p.popup_type == popup_type
        )

        # Check type-specific limit
        if type_count >= config.max_active:
            return False

        # Check total limit
        if len(self.active_popups) >= 5:  # MAX_POPUPS
            return False

        # Check large popup limit (research popups are considered large)
        if popup_type == PopupType.RESEARCH:
            large_count = sum(
                1 for p in self.active_popups
                if p.popup_type == PopupType.RESEARCH
            )
            if large_count >= 2:  # MAX_LARGE_POPUPS
                return False

        return True

    def _remove_lowest_priority_popup(self):
        """Remove the lowest priority popup to make room."""
        if not self.active_popups:
            return

        # Sort by priority (lowest first) and creation time (oldest first)
        sorted_popups = sorted(
            self.active_popups,
            key=lambda p: (p.config.priority.value, p._created_at)
        )

        # Remove the lowest priority/oldest popup
        popup_to_remove = sorted_popups[0]
        popup_to_remove._dismiss()

    def _get_orbit_position(
        self,
        popup: BasePopup,
        preferred_position: Optional[int] = None
    ) -> QPointF:
        """Calculate position on orbit around the center."""
        # Get center of parent (should be AI Core area)
        center_x = self.parent_widget.width() // 2
        center_y = self.parent_widget.height() // 2

        # Use popup's config orbit radius
        radius = popup.config.orbit_radius

        # Determine angle
        if preferred_position is not None and 0 <= preferred_position < 8:
            angle_deg = preferred_position * 45  # 8 positions, 45 degrees each
        else:
            # Find least occupied position
            angle_deg = self._find_least_occupied_orbit_position() * 45

        # Convert to radians
        import math
        angle_rad = math.radians(angle_deg)

        # Calculate position
        x = center_x + radius * math.cos(angle_rad) - popup.width() // 2
        y = center_y + radius * math.sin(angle_rad) - popup.height() // 2

        return QPointF(x, y)

    def _find_least_occupied_orbit_position(self) -> int:
        """Find the orbit position with fewest popups."""
        # Simple implementation: count popups in each 45-degree segment
        position_counts = [0] * 8

        center_x = self.parent_widget.width() // 2
        center_y = self.parent_widget.height() // 2

        for popup in self.active_popups:
            try:
                if not popup.isVisible():
                    continue
            except RuntimeError:
                # Popup has been deleted, skip it
                continue

            # Calculate angle of this popup from center
            popup_center_x = popup.x() + popup.width() // 2
            popup_center_y = popup.y() + popup.height() // 2

            dx = popup_center_x - center_x
            dy = popup_center_y - center_y

            import math
            angle = math.degrees(math.atan2(dy, dx))
            if angle < 0:
                angle += 360

            position_index = int((angle // 45) % 8)
            position_counts[position_index] += 1

        # Return position with minimum count
        return position_counts.index(min(position_counts))

    def _cleanup_finished_popups(self):
        """Remove popups that are no longer visible."""
        visible_popups = []
        for p in self.active_popups:
            try:
                if p.isVisible():
                    visible_popups.append(p)
            except RuntimeError:
                # Popup has been deleted, skip it
                pass
        self.active_popups = visible_popups
        self.popup_destroyed.emit(QObject())  # Dummy signal

    def dismiss_all_popups(self):
        """Dismiss all popups immediately."""
        for popup in self.active_popups[:]:  # Copy list
            try:
                popup._dismiss()
            except RuntimeError:
                # Qt wrappers may outlive their C++ object while a tour starts.
                pass
        self.active_popups.clear()


class PresenceSystem(QObject):
    """System for proactive intelligence surfacing."""

    def __init__(self, popup_manager: PopupManager):
        super().__init__()
        self.popup_manager = popup_manager
        self._presence_tmr = QTimer()
        self._presence_tmr.timeout.connect(self._surface_presence)
        self._presence_tmr.start(15000)  # Every 15 seconds

        self._last_surface = time.time()
        self._surface_messages = [
            "Memory synchronization complete.",
            "Knowledge graph expanded.",
            "Context retrieval complete.",
            "Predictive model updated.",
            "Cross-referencing memory clusters...",
            "Building execution plan...",
            "Monitoring active systems...",
            "Research protocols standby.",
            "Systems nominal.",
            "All circuits functional.",
        ]
        self._message_index = 0

    def _surface_presence(self):
        """Surface a piece of intelligence proactively."""
        # Only surface if user hasn't interacted recently
        # For now, we'll surface periodically
        message = self._surface_messages[self._message_index]
        self._message_index = (self._message_index + 1) % len(self._surface_messages)

        self.popup_manager.show_popup(
            message,
            PopupType.MICRO
        )

    def set_active(self, active: bool):
        """Enable or disable presence system."""
        if active:
            self._presence_tmr.start()
        else:
            self._presence_tmr.stop()


POPUP_CONFIGS = {
    PopupType.MICRO: PopupConfig(
        type=PopupType.MICRO,
        width=180,
        height=50,
        duration=2500,
        priority=PopupPriority.LOW,
        max_active=5,
        orbit_radius=100,
        opacity=0.9
    ),
    PopupType.INFORMATION: PopupConfig(
        type=PopupType.INFORMATION,
        width=220,
        height=80,
        duration=6000,
        priority=PopupPriority.MEDIUM,
        max_active=5,
        orbit_radius=130,
        opacity=0.9
    ),
    PopupType.ACTION: PopupConfig(
        type=PopupType.ACTION,
        width=250,
        height=90,
        duration=8000,
        priority=PopupPriority.HIGH,
        max_active=5,
        orbit_radius=160,
        opacity=0.9
    ),
    PopupType.RESEARCH: PopupConfig(
        type=PopupType.RESEARCH,
        width=300,
        height=120,
        duration=12000,
        priority=PopupPriority.HIGH,
        max_active=2,  # Max 2 large popups
        orbit_radius=190,
        opacity=0.9
    ),
    PopupType.CRITICAL: PopupConfig(
        type=PopupType.CRITICAL,
        width=280,
        height=100,
        duration=0,  # Persistent until acknowledged
        priority=PopupPriority.CRITICAL,
        max_active=5,
        orbit_radius=160,
        opacity=0.95
    ),
    PopupType.PRESENCE: PopupConfig(
        type=PopupType.PRESENCE,
        width=200,
        height=60,
        duration=4000,  # 4 seconds
        priority=PopupPriority.LOW,
        max_active=5,
        orbit_radius=110,
        opacity=0.85
    )
}
