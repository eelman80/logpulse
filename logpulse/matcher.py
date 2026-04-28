"""Pattern matching engine for log lines."""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Pattern:
    """A compiled pattern with associated alert label and severity."""

    label: str
    regex: str
    severity: str = "warning"  # info | warning | critical
    _compiled: Optional[re.Pattern] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.regex)

    def match(self, line: str) -> Optional[re.Match]:
        """Return a regex Match object if *line* matches, else None."""
        return self._compiled.search(line)


@dataclass
class Alert:
    """Represents a single matched alert."""

    label: str
    severity: str
    line: str
    pattern: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.label}: {self.line.rstrip()}"


class PatternMatcher:
    """Checks log lines against a collection of :class:`Pattern` objects."""

    def __init__(self, patterns: List[Pattern]) -> None:
        self.patterns = patterns

    @classmethod
    def from_config(cls, config: List[dict]) -> "PatternMatcher":
        """Build a :class:`PatternMatcher` from a list of config dicts.

        Each dict must have *label* and *regex* keys; *severity* is optional.
        """
        patterns = [
            Pattern(
                label=entry["label"],
                regex=entry["regex"],
                severity=entry.get("severity", "warning"),
            )
            for entry in config
        ]
        return cls(patterns)

    def check(self, line: str) -> List[Alert]:
        """Return all :class:`Alert` objects triggered by *line*."""
        alerts: List[Alert] = []
        for pattern in self.patterns:
            if pattern.match(line):
                alerts.append(
                    Alert(
                        label=pattern.label,
                        severity=pattern.severity,
                        line=line,
                        pattern=pattern.regex,
                    )
                )
        return alerts
