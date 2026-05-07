"""Suppressor: skip lines matching ignore patterns before alerting pipeline."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SuppressRule:
    pattern: str
    label: str = "unnamed"
    _compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.pattern)

    def matches(self, line: str) -> bool:
        return bool(self._compiled.search(line))


@dataclass
class SuppressorConfig:
    rules: List[SuppressRule] = field(default_factory=list)
    enabled: bool = True

    @staticmethod
    def from_dict(data: dict) -> "SuppressorConfig":
        enabled = data.get("enabled", True)
        rules = [
            SuppressRule(pattern=r["pattern"], label=r.get("label", "unnamed"))
            for r in data.get("rules", [])
        ]
        return SuppressorConfig(rules=rules, enabled=enabled)


class LineSuppressor:
    """Returns True if a line should be suppressed (ignored)."""

    def __init__(self, config: SuppressorConfig) -> None:
        self._config = config
        self._suppressed_count: int = 0
        self._last_matched_label: Optional[str] = None

    def should_suppress(self, line: str) -> bool:
        if not self._config.enabled:
            return False
        for rule in self._config.rules:
            if rule.matches(line):
                self._suppressed_count += 1
                self._last_matched_label = rule.label
                return True
        return False

    @property
    def suppressed_count(self) -> int:
        return self._suppressed_count

    @property
    def last_matched_label(self) -> Optional[str]:
        return self._last_matched_label

    def reset_stats(self) -> None:
        self._suppressed_count = 0
        self._last_matched_label = None
