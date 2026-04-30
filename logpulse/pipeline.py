"""Pipeline: wires together tailer, matcher, dedup, throttle, and notifier."""
from __future__ import annotations

import logging
import time
from typing import Optional

from logpulse.buffer import BufferConfig, ContextBuffer
from logpulse.dedup import DedupConfig, LineDeduplicator
from logpulse.formatter import FormatConfig, format_alert
from logpulse.matcher import Matcher
from logpulse.notifier import WebhookNotifier
from logpulse.tailer import LogTailer
from logpulse.throttle import AlertThrottle, ThrottleConfig

logger = logging.getLogger(__name__)


class Pipeline:
    """Coordinates all logpulse components into a single processing loop."""

    def __init__(
        self,
        tailer: LogTailer,
        matcher: Matcher,
        notifier: WebhookNotifier,
        *,
        throttle_config: Optional[ThrottleConfig] = None,
        dedup_config: Optional[DedupConfig] = None,
        format_config: Optional[FormatConfig] = None,
        buffer_config: Optional[BufferConfig] = None,
        poll_interval: float = 1.0,
    ) -> None:
        self._tailer = tailer
        self._matcher = matcher
        self._notifier = notifier
        self._throttle = AlertThrottle(throttle_config or ThrottleConfig())
        self._dedup = LineDeduplicator(dedup_config or DedupConfig())
        self._fmt = format_config or FormatConfig()
        self._buf = ContextBuffer(buffer_config or BufferConfig())
        self._poll_interval = poll_interval
        self._running = False

    # ------------------------------------------------------------------
    def run_once(self) -> int:
        """Process all currently available new lines. Returns alert count."""
        alerts_sent = 0
        new_lines = list(self._tailer.lines())

        for line in new_lines:
            if self._dedup.is_duplicate(line):
                logger.debug("Dedup suppressed: %s", line)
                continue

            alerts = self._matcher.check(line)
            for alert in alerts:
                ctx_results = self._buf.feed(line, matched=True)
                if not self._throttle.allow(alert.label):
                    logger.debug("Throttle suppressed alert: %s", alert.label)
                    continue
                context_lines: list[str] = []
                if ctx_results:
                    before, _, after = ctx_results[0]
                    context_lines = before + after
                message = format_alert(alert, self._fmt, context=context_lines)
                try:
                    self._notifier.send(message, severity=alert.severity)
                    alerts_sent += 1
                except Exception:  # noqa: BLE001
                    logger.exception("Notifier failed for alert %s", alert.label)
            else:
                self._buf.feed(line, matched=False)

        return alerts_sent

    def run(self) -> None:
        """Block and poll the log file until stop() is called."""
        self._running = True
        logger.info("Pipeline started (poll_interval=%.1fs)", self._poll_interval)
        while self._running:
            self.run_once()
            time.sleep(self._poll_interval)

    def stop(self) -> None:
        """Signal the run loop to exit after the current iteration."""
        self._running = False
        self._buf.flush()
        logger.info("Pipeline stopped")
