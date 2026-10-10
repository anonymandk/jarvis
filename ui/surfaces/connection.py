"""Factual connection details for the current presentation client contract."""

from __future__ import annotations

import importlib

_runtime = importlib.import_module("ui._runtime")
globals().update({key: value for key, value in vars(_runtime).items() if not key.startswith("__")})


class ConnectionStatusCard(QFrame):
    """Expose connection fields only when the client supplies those facts."""

    def __init__(self, parent=None, *, compact: bool = False):
        super().__init__(parent)
        self._compact = bool(compact)
        self.setObjectName("connectionStatusCard")
        self.setAccessibleName("Estado da conexão Gemini Live")
        self._status_value = QLabel("—")
        self._rtt_value = QLabel("—")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            TOKENS.spacing["md"], TOKENS.spacing["sm"],
            TOKENS.spacing["md"], TOKENS.spacing["sm"],
        )
        layout.setSpacing(TOKENS.spacing["xs"])

        header = QHBoxLayout()
        title = QLabel("Gemini Live")
        title.setFont(QFont(UI_FONT, TOKENS.font_sizes["body"], QFont.Weight.DemiBold))
        header.addWidget(title)
        header.addStretch()
        self._connection_badge = QLabel("Conexão —")
        self._connection_badge.setAccessibleName("Estado da conexão: indisponível")
        header.addWidget(self._connection_badge)
        layout.addLayout(header)

        details = QHBoxLayout()
        details.addWidget(QLabel("RTT"))
        details.addWidget(self._rtt_value)
        details.addStretch()
        details.addWidget(QLabel("Estado"))
        details.addWidget(self._status_value)
        layout.addLayout(details)

        self._note = QLabel("O cliente atual não publica conexão ou latência.")
        self._note.setWordWrap(True)
        layout.addWidget(self._note)
        if self._compact:
            self._note.hide()
            self.setMaximumHeight(64)
            layout.setContentsMargins(
                TOKENS.spacing["sm"], TOKENS.spacing["xs"],
                TOKENS.spacing["sm"], TOKENS.spacing["xs"],
            )
            layout.setSpacing(TOKENS.spacing["xxs"])
            self.setAccessibleDescription(
                "Estado da conexão e latência não publicados pelo cliente atual."
            )
        self.refresh_theme()

    def set_connection(self, status: str | None = None, rtt_ms: float | None = None) -> None:
        if status:
            labels = {
                "connected": "Conectado", "connecting": "Conectando",
                "reconnecting": "Reconectando", "offline": "Desconectado",
                "error": "Erro",
            }
            value = labels.get(str(status).strip().lower())
            if value:
                badge_value = {
                    "connected": "Conectada", "connecting": "Conectando",
                    "reconnecting": "Reconectando", "offline": "Desconectada",
                    "error": "Com erro",
                }[str(status).strip().lower()]
                self._status_value.setText(value)
                self._connection_badge.setText(f"Conexão {badge_value.lower()}")
                self._connection_badge.setAccessibleName(f"Estado da conexão: {value}")
                self._note.setText("Estado recebido do cliente.")
        if rtt_ms is not None:
            try:
                value = float(rtt_ms)
                if value >= 0:
                    self._rtt_value.setText(f"{value:.0f} ms")
            except (TypeError, ValueError):
                pass
        self.refresh_theme()

    def clear_connection(self) -> None:
        """Return unavailable fields to their honest placeholder state."""
        self._status_value.setText("—")
        self._rtt_value.setText("—")
        self._connection_badge.setText("Conexão —")
        self._connection_badge.setAccessibleName("Estado da conexão: indisponível")
        self._note.setText("O cliente atual não publica conexão ou latência.")
        self.refresh_theme()

    def refresh_theme(self):
        self.setStyleSheet(f"""
            QFrame#connectionStatusCard {{
                background: {C.PANEL};
                border: 1px solid {C.BORDER};
                border-left: 2px solid {C.PRI};
                border-radius: {TOKENS.radii['md']}px;
            }}
        """)
        for label in self.findChildren(QLabel):
            label.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        title = self.findChild(QLabel)
        if title is not None:
            title.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        self._status_value.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self._rtt_value.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self._note.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
