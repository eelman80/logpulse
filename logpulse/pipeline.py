"""Pipeline: wire tailer → suppressor → matcher → notifier."""
from __future__ import annotations

import logging
import time
from typing import Optional

from logpulse.matcher import AlertMatcher
from logpulse.notifier import WebhookNotifier
from logpulse.suppressor import LineSuppressor, SuppressorConfig
from logpulse.tailer import LogTailer

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(
        self,
        tailer: LogTailer,
        matcher: AlertMatcher,
        notifier: WebhookNotifier,
        suppressor: Optional[LineSuppressor] = None,
        poll_interval: float = 1.0,
    ) -> None:
        self._tailer = tailer
        self._matcher = matcher
        self._notifier = notifier
        self._suppressor = suppressor or LineSuppressor(SuppressorConfig(enabled=False))
        self._poll_interval = poll_interval
        self._running = False

    def run_once(self) -> int:
        """Process all currently available new lines. Returns count of alerts sent."""
        alerts_sent = 0
        for line in self._tailer.tail():
            if self._suppressor.should_suppress(line):
                logger.debug("Suppressed line (label=%s)", self._suppressor.last_matched_label)
                continue
            alerts = self._matcher.check(line)
            for alert in alerts:
                try:
                    self._notifier.send(alert)
                    alerts_sent += 1
                except Exception as exc:  # pragma: no cover
                    logger.error("Notifier error: %s", exc)
        return alerts_sent

    def run(self) -> None:
        self._running = True
        logger.info("Pipeline started (poll_interval=%.1fs)", self._poll_interval)
        while self._running:
            self.run_once()
            time.sleep(self._poll_interval)

    def stop(self) -> None:
        self._running = False
        logger.info(
            "Pipeline stopped. Total suppressed lines: %d",
            self._suppressor.suppressed_count,
        )
