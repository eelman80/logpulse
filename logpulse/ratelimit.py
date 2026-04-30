"""Rate limiter that caps the number of notifications per time window."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict


@dataclass
class RateLimitConfig:
    """Configuration for the rate limiter."""

    max_alerts: int = 10
    """Maximum number of alerts allowed within *window_seconds*."""

    window_seconds: float = 60.0
    """Rolling time window in seconds."""


class RateLimiter:
    """Per-label sliding-window rate limiter.

    Tracks alert timestamps per label and rejects new alerts once the
    *max_alerts* threshold is reached within the rolling *window_seconds*.
    """

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self._cfg = config or RateLimitConfig()
        # label -> deque of timestamps (oldest first)
        self._windows: Dict[str, Deque[float]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allow(self, label: str, *, now: float | None = None) -> bool:
        """Return *True* if the alert for *label* is within the rate limit.

        Calling this method is a side-effect: an allowed alert is recorded
        so that subsequent calls within the window count against the budget.
        """
        ts = now if now is not None else time.monotonic()
        window = self._windows.setdefault(label, deque())
        self._evict(window, ts)
        if len(window) >= self._cfg.max_alerts:
            return False
        window.append(ts)
        return True

    def remaining(self, label: str, *, now: float | None = None) -> int:
        """Return how many more alerts *label* may emit in the current window."""
        ts = now if now is not None else time.monotonic()
        window = self._windows.get(label, deque())
        self._evict(window, ts)
        return max(0, self._cfg.max_alerts - len(window))

    def reset(self, label: str | None = None) -> None:
        """Clear rate-limit state for *label*, or for all labels if *None*."""
        if label is None:
            self._windows.clear()
        else:
            self._windows.pop(label, None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict(self, window: Deque[float], now: float) -> None:
        """Remove timestamps that have fallen outside the rolling window."""
        cutoff = now - self._cfg.window_seconds
        while window and window[0] <= cutoff:
            window.popleft()
