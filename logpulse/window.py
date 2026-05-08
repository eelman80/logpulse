"""Sliding-window rate aggregation for alert frequency reporting."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict


@dataclass
class WindowConfig:
    enabled: bool = True
    window_seconds: int = 60
    min_count: int = 3  # minimum hits in window before reporting

    @classmethod
    def from_dict(cls, d: dict) -> "WindowConfig":
        return cls(
            enabled=d.get("enabled", True),
            window_seconds=int(d.get("window_seconds", 60)),
            min_count=int(d.get("min_count", 3)),
        )


@dataclass
class WindowSummary:
    label: str
    count: int
    window_seconds: int
    oldest_ts: float
    newest_ts: float

    def rate_per_minute(self) -> float:
        span = self.newest_ts - self.oldest_ts
        if span <= 0:
            return float(self.count)
        return round(self.count / span * 60, 2)

    def __str__(self) -> str:
        return (
            f"[{self.label}] {self.count} hits in {self.window_seconds}s "
            f"(~{self.rate_per_minute()}/min)"
        )


class SlidingWindow:
    """Tracks per-label hit timestamps within a rolling time window."""

    def __init__(self, cfg: WindowConfig) -> None:
        self._cfg = cfg
        self._buckets: Dict[str, Deque[float]] = {}

    def record(self, label: str, ts: float | None = None) -> None:
        ts = ts if ts is not None else time.monotonic()
        if label not in self._buckets:
            self._buckets[label] = deque()
        self._buckets[label].append(ts)
        self._evict(label, ts)

    def _evict(self, label: str, now: float) -> None:
        cutoff = now - self._cfg.window_seconds
        dq = self._buckets[label]
        while dq and dq[0] < cutoff:
            dq.popleft()

    def summary(self, label: str, now: float | None = None) -> WindowSummary | None:
        now = now if now is not None else time.monotonic()
        self._evict(label, now)
        dq = self._buckets.get(label)
        if not dq or len(dq) < self._cfg.min_count:
            return None
        return WindowSummary(
            label=label,
            count=len(dq),
            window_seconds=self._cfg.window_seconds,
            oldest_ts=dq[0],
            newest_ts=dq[-1],
        )

    def all_summaries(self, now: float | None = None) -> list[WindowSummary]:
        now = now if now is not None else time.monotonic()
        results = []
        for label in list(self._buckets):
            s = self.summary(label, now)
            if s is not None:
                results.append(s)
        return results

    def reset(self, label: str | None = None) -> None:
        if label is None:
            self._buckets.clear()
        else:
            self._buckets.pop(label, None)
