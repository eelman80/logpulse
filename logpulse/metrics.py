"""In-process counters exposed via the health-check endpoint and logs."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class MetricsSnapshot:
    lines_processed: int = 0
    lines_matched: int = 0
    alerts_sent: int = 0
    alerts_suppressed: int = 0
    uptime_seconds: float = 0.0
    label_counts: Dict[str, int] = field(default_factory=dict)


class Metrics:
    """Thread-safe counters for logpulse pipeline activity."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._start_time: float = time.monotonic()
        self._lines_processed: int = 0
        self._lines_matched: int = 0
        self._alerts_sent: int = 0
        self._alerts_suppressed: int = 0
        self._label_counts: Dict[str, int] = {}

    # --- mutators ---

    def inc_lines_processed(self, n: int = 1) -> None:
        with self._lock:
            self._lines_processed += n

    def inc_lines_matched(self, n: int = 1) -> None:
        with self._lock:
            self._lines_matched += n

    def inc_alerts_sent(self, label: str, n: int = 1) -> None:
        with self._lock:
            self._alerts_sent += n
            self._label_counts[label] = self._label_counts.get(label, 0) + n

    def inc_alerts_suppressed(self, n: int = 1) -> None:
        with self._lock:
            self._alerts_suppressed += n

    def reset(self) -> None:
        with self._lock:
            self._lines_processed = 0
            self._lines_matched = 0
            self._alerts_sent = 0
            self._alerts_suppressed = 0
            self._label_counts = {}
            self._start_time = time.monotonic()

    # --- accessors ---

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            return MetricsSnapshot(
                lines_processed=self._lines_processed,
                lines_matched=self._lines_matched,
                alerts_sent=self._alerts_sent,
                alerts_suppressed=self._alerts_suppressed,
                uptime_seconds=time.monotonic() - self._start_time,
                label_counts=dict(self._label_counts),
            )


# Module-level singleton so all components share the same counters.
global_metrics: Metrics = Metrics()
