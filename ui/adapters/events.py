"""Translate existing JarvisClient notifications into the UI v1 envelope.

This mapper only emits facts represented by its inputs. It never infers tool
execution, connection health, latency, audio levels, or error recovery data
from log text or visual activity.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4


_STATE_ALIASES = {
    "IDLE": "idle",
    "STANDBY": "idle",
    "STANDING BY": "idle",
    "LISTENING": "listening",
    "HEARING": "listening",
    "THINKING": "processing",
    "PROCESSING": "processing",
    "EXECUTING": "processing",
    "SPEAKING": "speaking",
    "RECONNECTING": "reconnecting",
    "RECONNECT": "reconnecting",
    "ERROR": "error",
    "FAILED": "error",
    "MUTED": "muted",
    "SILENCED": "muted",
    "MICROPHONE MUTED": "muted",
}


def normalize_state(value: str) -> str | None:
    """Normalize only known UI states; unknown values have no v1 state."""
    return _STATE_ALIASES.get(str(value or "").strip().upper())


class JarvisEventMapper:
    """Build ordered v1 events from the presentation-facing client methods."""

    def __init__(
        self,
        *,
        session_id: str | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.session_id = session_id or uuid4().hex
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._sequence = 0
        self._turn_id: str | None = None
        self._turn_closed = False
        self._lock = RLock()

    def _active_turn(self, *, start_new: bool = False) -> str:
        if start_new or self._turn_id is None:
            self._turn_id = uuid4().hex
            self._turn_closed = False
        return self._turn_id

    def _envelope(self, event_type: str, payload: Mapping[str, object]) -> dict:
        with self._lock:
            timestamp = self._clock()
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            timestamp = timestamp.astimezone(timezone.utc)
            self._sequence += 1
            return {
                "v": 1,
                "type": event_type,
                "ts": timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "session_id": self.session_id,
                "seq": self._sequence,
                "payload": dict(payload),
            }

    def state(self, value: str) -> dict | None:
        normalized = normalize_state(value)
        if normalized is None:
            return None
        payload: dict[str, object] = {"state": normalized, "source": "jarvis_client"}
        if str(value).strip().lower() != normalized:
            payload["reason"] = str(value)
        return self._envelope("state", payload)

    def subtitle(self, text: str) -> dict:
        with self._lock:
            return self._envelope("transcript", {
                "speaker": "assistant",
                "text": str(text),
                "final": False,
                "turn_id": self._active_turn(),
            })

    def clear_subtitle(self) -> dict:
        with self._lock:
            turn_id = self._active_turn(start_new=True)
            return self._envelope("transcript", {
                "speaker": "assistant",
                "text": "",
                "final": True,
                "turn_id": turn_id,
                "clear": True,
            })

    def log(self, text: str) -> dict:
        """Map conversation prefixes to transcript and all other text to log."""
        with self._lock:
            message = str(text)
            for prefix, speaker in (("You: ", "user"), ("Jarvis: ", "assistant")):
                if message.startswith(prefix):
                    turn_id = self._active_turn(start_new=speaker == "user" and self._turn_closed)
                    event = self._envelope("transcript", {
                        "speaker": speaker,
                        "text": message[len(prefix):],
                        "final": True,
                        "turn_id": turn_id,
                    })
                    if speaker == "assistant":
                        self._turn_closed = True
                    return event

            level = "info"
            source = "jarvis"
            for prefix, mapped_level, mapped_source in (
                ("ERR: ", "error", "jarvis"),
                ("ERROR: ", "error", "jarvis"),
                ("WARN: ", "warning", "jarvis"),
                ("WARNING: ", "warning", "jarvis"),
                ("SYS: ", "info", "system"),
            ):
                if message.startswith(prefix):
                    level, source = mapped_level, mapped_source
                    message = message[len(prefix):]
                    break
            return self._envelope("log", {
                "level": level,
                "source": source,
                "message": message,
            })

    def client_call(self, method: str, *args) -> dict | None:
        """Map the existing engine-to-client notification methods."""
        if method == "set_state" and args:
            return self.state(str(args[0]))
        if method == "write_log" and args:
            return self.log(str(args[0]))
        if method == "show_subtitle" and args:
            return self.subtitle(str(args[0]))
        if method == "clear_subtitle":
            return self.clear_subtitle()
        return None

    def tool_call(
        self,
        *,
        call_id: str,
        name: str,
        status: str,
        started_at: str | None = None,
        duration_ms: int | None = None,
        result_summary: str | None = None,
    ) -> dict:
        """Create a tool event only when a caller supplies structured facts."""
        payload: dict[str, object] = {"id": call_id, "name": name, "status": status}
        if started_at is not None:
            payload["started_at"] = started_at
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms
        if result_summary is not None:
            payload["result_summary"] = result_summary
        return self._envelope("tool_call", payload)

    def metric(self, *, name: str, value: int | float | None, unit: str) -> dict:
        """`None` stays unavailable so consumers can render `—`."""
        return self._envelope("metric", {"name": name, "value": value, "unit": unit})

    def error(
        self,
        *,
        code: str,
        message: str,
        recoverable: bool,
        retry_after_ms: int | None = None,
    ) -> dict:
        payload: dict[str, object] = {
            "code": code,
            "message": message,
            "recoverable": recoverable,
        }
        if retry_after_ms is not None:
            payload["retry_after_ms"] = retry_after_ms
        return self._envelope("error", payload)
