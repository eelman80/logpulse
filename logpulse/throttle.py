"""Alert throttling to suppress repeated notifications within a cooldown window."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ThrottleConfig:
    """Configuration for the throttle."""

    cooldown_seconds: float = 60.0
    """Minimum seconds between repeated alerts for the same pattern label."""


class AlertThrottle:
    """Tracks last-seen times for alert labels and suppresses duplicates.

    Example::

        throttle = AlertThrottle(ThrottleConfig(cooldown_seconds=30))
        if throttle.allow(alert):
            notifier.send(alert)
    """

    def __init__(self, config: Optional[ThrottleConfig] = None) -> None:
        self._config = config or ThrottleConfig()
        # label -> monotonic timestamp of last allowed notification
        self._last_sent: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allow(self, label: str) -> bool:
        """Return *True* if the alert for *label* should be forwarded.

        Side-effect: records the current time when *True* is returned.
        """
        now = time.monotonic()
        last = self._last_sent.get(label)
        if last is None or (now - last) >= self._config.cooldown_seconds:
            self._last_sent[label] = now
            return True
        return False

    def reset(self, label: str) -> None:
        """Clear the throttle state for *label* (useful in tests)."""
        self._last_sent.pop(label, None)

    def reset_all(self) -> None:
        """Clear all throttle state."""
        self._last_sent.clear()

    @property
    def cooldown_seconds(self) -> float:
        return self._config.cooldown_seconds
