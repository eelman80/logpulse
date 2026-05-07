"""Periodic digest: batch alerts and emit a summary at a fixed interval."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List

from logpulse.matcher import Alert


@dataclass
class DigestConfig:
    enabled: bool = False
    interval_seconds: float = 60.0
    max_entries: int = 100

    @classmethod
    def from_dict(cls, data: dict) -> "DigestConfig":
        return cls(
            enabled=data.get("enabled", False),
            interval_seconds=float(data.get("interval_seconds", 60.0)),
            max_entries=int(data.get("max_entries", 100)),
        )


class AlertDigest:
    """Accumulates alerts and flushes them as a batch via a callback."""

    def __init__(
        self,
        config: DigestConfig,
        flush_callback: Callable[[List[Alert]], None],
    ) -> None:
        self._config = config
        self._callback = flush_callback
        self._lock = threading.Lock()
        self._pending: List[Alert] = []
        self._timer: threading.Timer | None = None
        self._stopped = False

    # ------------------------------------------------------------------
    def add(self, alert: Alert) -> None:
        """Add an alert to the pending batch."""
        with self._lock:
            if len(self._pending) < self._config.max_entries:
                self._pending.append(alert)
            if self._timer is None and not self._stopped:
                self._schedule()

    def flush(self) -> None:
        """Flush pending alerts immediately (thread-safe)."""
        with self._lock:
            batch = self._pending[:]
            self._pending.clear()
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        if batch:
            self._callback(batch)

    def stop(self) -> None:
        """Cancel any scheduled flush and suppress future scheduling."""
        with self._lock:
            self._stopped = True
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    # ------------------------------------------------------------------
    def _schedule(self) -> None:
        """Must be called with self._lock held."""
        self._timer = threading.Timer(
            self._config.interval_seconds, self._on_timer
        )
        self._timer.daemon = True
        self._timer.start()

    def _on_timer(self) -> None:
        with self._lock:
            self._timer = None
        self.flush()
