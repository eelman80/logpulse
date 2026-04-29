"""Pipeline that wires together LogTailer, PatternMatcher, and WebhookNotifier."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from logpulse.matcher import PatternMatcher
from logpulse.notifier import WebhookNotifier
from logpulse.tailer import LogTailer

logger = logging.getLogger(__name__)


class Pipeline:
    """Continuously tail a log file, match patterns, and fire notifications."""

    def __init__(
        self,
        log_path: str | Path,
        matcher: PatternMatcher,
        notifier: WebhookNotifier,
        poll_interval: float = 1.0,
        source: Optional[str] = None,
    ) -> None:
        self.log_path = Path(log_path)
        self.matcher = matcher
        self.notifier = notifier
        self.poll_interval = poll_interval
        self.source = source or str(log_path)
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_once(self) -> int:
        """Process all currently available new lines. Returns number of alerts fired."""
        tailer = LogTailer(self.log_path)
        alerts_fired = 0
        for line in tailer.lines():
            alerts = self.matcher.check(line)
            for alert in alerts:
                try:
                    self.notifier.send(alert, source=self.source)
                    alerts_fired += 1
                except Exception as exc:  # noqa: BLE001
                    logger.error("Failed to send notification: %s", exc)
        return alerts_fired

    def run(self) -> None:
        """Block and continuously tail the log file until stopped."""
        self._running = True
        tailer = LogTailer(self.log_path)
        logger.info("Pipeline started for %s", self.log_path)
        try:
            while self._running:
                for line in tailer.lines():
                    alerts = self.matcher.check(line)
                    for alert in alerts:
                        try:
                            self.notifier.send(alert, source=self.source)
                        except Exception as exc:  # noqa: BLE001
                            logger.error("Failed to send notification: %s", exc)
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Pipeline interrupted by user.")
        finally:
            self._running = False
            logger.info("Pipeline stopped.")

    def stop(self) -> None:
        """Signal the run loop to exit."""
        self._running = False
