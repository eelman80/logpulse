"""Periodic reporter that emits WindowSummary objects as Alerts."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, List

from logpulse.matcher import Alert
from logpulse.window import SlidingWindow, WindowConfig, WindowSummary


@dataclass
class ReporterConfig:
    report_interval: int = 60  # seconds between digest reports
    severity: str = "info"

    @classmethod
    def from_dict(cls, d: dict) -> "ReporterConfig":
        return cls(
            report_interval=int(d.get("report_interval", 60)),
            severity=d.get("severity", "info"),
        )


class WindowReporter:
    """Wraps a SlidingWindow and periodically converts summaries into Alerts."""

    def __init__(
        self,
        window: SlidingWindow,
        cfg: ReporterConfig,
        on_alert: Callable[[Alert], None],
    ) -> None:
        self._window = window
        self._cfg = cfg
        self._on_alert = on_alert
        self._last_report: float = time.monotonic()

    def record(self, label: str, line: str, ts: float | None = None) -> None:
        """Record a hit for *label* and emit a report if the interval elapsed."""
        self._window.record(label, ts)
        self._maybe_report()

    def _maybe_report(self, now: float | None = None) -> None:
        now = now if now is not None else time.monotonic()
        if now - self._last_report < self._cfg.report_interval:
            return
        self._last_report = now
        for summary in self._window.all_summaries(now):
            alert = self._summary_to_alert(summary)
            self._on_alert(alert)

    def force_report(self, now: float | None = None) -> List[Alert]:
        """Immediately emit alerts for all qualifying windows; returns them."""
        now = now if now is not None else time.monotonic()
        alerts: List[Alert] = []
        for summary in self._window.all_summaries(now):
            alert = self._summary_to_alert(summary)
            alerts.append(alert)
            self._on_alert(alert)
        self._last_report = now
        return alerts

    def _summary_to_alert(self, summary: WindowSummary) -> Alert:
        message = str(summary)
        return Alert(
            label=summary.label,
            line=message,
            severity=self._cfg.severity,
            pattern=f"window:{summary.label}",
        )
