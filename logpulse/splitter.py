"""Line splitter: fan-out a single alert to multiple downstream handlers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from logpulse.matcher import Alert


@dataclass
class SplitterConfig:
    """Configuration for the alert splitter."""
    enabled: bool = True
    stop_on_error: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "SplitterConfig":
        return cls(
            enabled=bool(data.get("enabled", True)),
            stop_on_error=bool(data.get("stop_on_error", False)),
        )


Handler = Callable[[Alert], None]


class AlertSplitter:
    """Fan-out an alert to multiple handlers in registration order.

    Each handler is a callable that accepts an :class:`~logpulse.matcher.Alert`.
    Errors in individual handlers are either swallowed (default) or re-raised
    depending on *stop_on_error*.
    """

    def __init__(
        self,
        config: Optional[SplitterConfig] = None,
        handlers: Optional[List[Handler]] = None,
    ) -> None:
        self._cfg = config or SplitterConfig()
        self._handlers: List[Handler] = list(handlers or [])
        self._error_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_handler(self, handler: Handler) -> None:
        """Append *handler* to the fan-out list."""
        self._handlers.append(handler)

    def dispatch(self, alert: Alert) -> int:
        """Send *alert* to every registered handler.

        Returns the number of handlers that were called successfully.
        Raises the first exception encountered when *stop_on_error* is True.
        """
        if not self._cfg.enabled:
            return 0

        success = 0
        for handler in self._handlers:
            try:
                handler(alert)
                success += 1
            except Exception:  # noqa: BLE001
                self._error_count += 1
                if self._cfg.stop_on_error:
                    raise
        return success

    @property
    def handler_count(self) -> int:
        """Number of registered handlers."""
        return len(self._handlers)

    @property
    def error_count(self) -> int:
        """Cumulative number of handler errors swallowed so far."""
        return self._error_count

    def clear(self) -> None:
        """Remove all registered handlers and reset error counter."""
        self._handlers.clear()
        self._error_count = 0
