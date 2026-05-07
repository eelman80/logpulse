"""Alert router: dispatch alerts to different notifiers based on label/severity rules."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol

from logpulse.matcher import Alert


class Notifier(Protocol):
    def send(self, alert: Alert) -> None:
        ...


@dataclass
class RouteRule:
    """A single routing rule.  First matching rule wins."""
    notifier: str
    label_pattern: Optional[str] = None
    severity: Optional[str] = None
    _label_re: re.Pattern = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._label_re = re.compile(self.label_pattern) if self.label_pattern else None

    def matches(self, alert: Alert) -> bool:
        if self._label_re and not self._label_re.search(alert.label):
            return False
        if self.severity and alert.severity != self.severity:
            return False
        return True


@dataclass
class RouterConfig:
    rules: List[RouteRule] = field(default_factory=list)
    default_notifier: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> "RouterConfig":
        rules = [
            RouteRule(
                notifier=r["notifier"],
                label_pattern=r.get("label_pattern"),
                severity=r.get("severity"),
            )
            for r in data.get("rules", [])
        ]
        return RouterConfig(
            rules=rules,
            default_notifier=data.get("default_notifier"),
        )


class AlertRouter:
    """Dispatch an alert to the first matching notifier, or the default."""

    def __init__(self, config: RouterConfig, notifiers: Dict[str, Notifier]) -> None:
        self._config = config
        self._notifiers = notifiers
        self._routed: int = 0
        self._dropped: int = 0

    def route(self, alert: Alert) -> bool:
        """Return True if the alert was dispatched, False if dropped."""
        for rule in self._config.rules:
            if rule.matches(alert):
                notifier = self._notifiers.get(rule.notifier)
                if notifier:
                    notifier.send(alert)
                    self._routed += 1
                    return True

        if self._config.default_notifier:
            notifier = self._notifiers.get(self._config.default_notifier)
            if notifier:
                notifier.send(alert)
                self._routed += 1
                return True

        self._dropped += 1
        return False

    @property
    def routed(self) -> int:
        return self._routed

    @property
    def dropped(self) -> int:
        return self._dropped
