"""Alert correlation: group related alerts within a time window."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from logpulse.matcher import Alert


@dataclass
class CorrelatorConfig:
    enabled: bool = False
    window_seconds: float = 60.0
    min_group_size: int = 2
    group_by: str = "label"  # "label" or "severity"

    @classmethod
    def from_dict(cls, d: dict) -> "CorrelatorConfig":
        return cls(
            enabled=bool(d.get("enabled", False)),
            window_seconds=float(d.get("window_seconds", 60.0)),
            min_group_size=int(d.get("min_group_size", 2)),
            group_by=str(d.get("group_by", "label")),
        )


@dataclass
 class _Bucket:
    alerts: List[Alert] = field(default_factory=list)
    opened_at: float = field(default_factory=time.monotonic)


class AlertCorrelator:
    """Buffer alerts and emit correlated groups once the window closes."""

    def __init__(
        self,
        cfg: CorrelatorConfig,
        on_group: Callable[[str, List[Alert]], None],
        *,
        _now: Optional[Callable[[], float]] = None,
    ) -> None:
        self._cfg = cfg
        self._on_group = on_group
        self._now = _now or time.monotonic
        self._buckets: Dict[str, _Bucket] = {}

    def _key(self, alert: Alert) -> str:
        if self._cfg.group_by == "severity":
            return alert.severity
        return alert.label

    def feed(self, alert: Alert) -> None:
        """Accept an alert; may trigger on_group if a window has closed."""
        if not self._cfg.enabled:
            self._on_group(self._key(alert), [alert])
            return
        key = self._key(alert)
        now = self._now()
        bucket = self._buckets.get(key)
        if bucket is None:
            self._buckets[key] = _Bucket(alerts=[alert], opened_at=now)
            return
        if now - bucket.opened_at >= self._cfg.window_seconds:
            self._flush_key(key)
            self._buckets[key] = _Bucket(alerts=[alert], opened_at=now)
        else:
            bucket.alerts.append(alert)

    def flush_expired(self) -> None:
        """Emit all buckets whose window has elapsed."""
        now = self._now()
        expired = [
            k
            for k, b in self._buckets.items()
            if now - b.opened_at >= self._cfg.window_seconds
        ]
        for key in expired:
            self._flush_key(key)

    def flush_all(self) -> None:
        """Emit every open bucket regardless of age."""
        for key in list(self._buckets):
            self._flush_key(key)

    def _flush_key(self, key: str) -> None:
        bucket = self._buckets.pop(key, None)
        if bucket and len(bucket.alerts) >= self._cfg.min_group_size:
            self._on_group(key, bucket.alerts)
