"""Debouncer: suppress rapid repeated alerts and emit only after a quiet period."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional


@dataclass
class DebounceConfig:
    enabled: bool = False
    quiet_seconds: float = 5.0
    max_hold_seconds: float = 30.0

    @staticmethod
    def from_dict(d: dict) -> "DebounceConfig":
        return DebounceConfig(
            enabled=d.get("enabled", False),
            quiet_seconds=float(d.get("quiet_seconds", 5.0)),
            max_hold_seconds=float(d.get("max_hold_seconds", 30.0)),
        )


@dataclass
class _Pending:
    label: str
    last_seen: float
    first_seen: float
    count: int = 1
    payload: object = None


class AlertDebouncer:
    """Hold back repeated alerts until the signal goes quiet or the max hold
    time is exceeded, then release a single representative alert.

    Parameters
    ----------
    cfg:
        Debounce configuration.
    clock:
        Callable returning the current time in seconds (injectable for tests).
    """

    def __init__(
        self,
        cfg: DebounceConfig,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._cfg = cfg
        self._clock = clock
        self._pending: Dict[str, _Pending] = {}

    # ------------------------------------------------------------------
    def feed(self, label: str, payload: object) -> Optional[object]:
        """Feed an alert event.  Returns the payload if it should be emitted
        now, or *None* if it is being held."""
        if not self._cfg.enabled:
            return payload

        now = self._clock()
        if label in self._pending:
            p = self._pending[label]
            p.last_seen = now
            p.count += 1
            p.payload = payload
            return None

        self._pending[label] = _Pending(
            label=label, last_seen=now, first_seen=now, payload=payload
        )
        return None

    def flush(self, label: str) -> Optional[object]:
        """Force-release a held alert regardless of timing."""
        p = self._pending.pop(label, None)
        return p.payload if p else None

    def drain(self) -> list:
        """Return payloads whose quiet period or max hold has elapsed."""
        if not self._cfg.enabled:
            return []

        now = self._clock()
        ready = []
        for label, p in list(self._pending.items()):
            quiet_elapsed = (now - p.last_seen) >= self._cfg.quiet_seconds
            max_elapsed = (now - p.first_seen) >= self._cfg.max_hold_seconds
            if quiet_elapsed or max_elapsed:
                ready.append(self._pending.pop(label).payload)
        return ready

    def pending_labels(self) -> list:
        return list(self._pending.keys())
