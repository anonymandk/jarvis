"""Simple in-process metrics collector for ARGUS.

No external dependencies required.

This module intentionally keeps the surface area small so it can be used
from performance-sensitive audio loops without heavy locking.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ToolMetric:
    name: str
    count: int = 0
    success: int = 0
    failure: int = 0
    total_latency_s: float = 0.0

    def record(self, ok: bool, latency_s: float) -> None:
        self.count += 1
        if ok:
            self.success += 1
        else:
            self.failure += 1
        self.total_latency_s += float(latency_s)

    @property
    def avg_latency_s(self) -> float:
        return self.total_latency_s / self.count if self.count else 0.0


@dataclass
class MetricsCollector:
    tool_calls: Dict[str, ToolMetric] = field(default_factory=dict)
    live_reconnect_attempts: int = 0
    live_reconnect_success: int = 0
    audio_loop_latency_s_total: float = 0.0
    audio_loop_latency_samples: int = 0

    def record_tool_call(self, name: str, ok: bool, latency_s: float) -> None:
        m = self.tool_calls.get(name)
        if m is None:
            m = ToolMetric(name=name)
            self.tool_calls[name] = m
        m.record(ok=ok, latency_s=latency_s)

    def record_reconnect_attempt(self) -> None:
        self.live_reconnect_attempts += 1

    def record_reconnect_success(self) -> None:
        self.live_reconnect_success += 1

    def record_audio_latency(self, latency_s: float) -> None:
        self.audio_loop_latency_s_total += float(latency_s)
        self.audio_loop_latency_samples += 1

    def snapshot(self) -> dict:
        return {
            "tool_calls": {
                name: {
                    "count": m.count,
                    "success": m.success,
                    "failure": m.failure,
                    "avg_latency_s": m.avg_latency_s,
                }
                for name, m in self.tool_calls.items()
            },
            "live_reconnect_attempts": self.live_reconnect_attempts,
            "live_reconnect_success": self.live_reconnect_success,
            "audio_loop_avg_latency_s": (
                self.audio_loop_latency_s_total / self.audio_loop_latency_samples
                if self.audio_loop_latency_samples
                else 0.0
            ),
        }


metrics = MetricsCollector()


class Timer:
    def __init__(self) -> None:
        self._t0: Optional[float] = None
        self._t1: Optional[float] = None

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._t1 = time.perf_counter()

    @property
    def elapsed_s(self) -> float:
        if self._t0 is None or self._t1 is None:
            return 0.0
        return self._t1 - self._t0
