"""Sensitive-data redaction for log lines before alerting or forwarding."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RedactRule:
    """A single redaction rule: a compiled regex and its replacement text."""

    pattern: str
    replacement: str = "[REDACTED]"
    label: str = ""
    _compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.pattern)

    def apply(self, text: str) -> str:
        """Return *text* with all matches replaced."""
        return self._compiled.sub(self.replacement, text)


@dataclass
class RedactorConfig:
    rules: List[RedactRule] = field(default_factory=list)
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "RedactorConfig":
        enabled = data.get("enabled", True)
        rules = [
            RedactRule(
                pattern=r["pattern"],
                replacement=r.get("replacement", "[REDACTED]"),
                label=r.get("label", ""),
            )
            for r in data.get("rules", [])
        ]
        return cls(rules=rules, enabled=enabled)


class Redactor:
    """Applies a sequence of :class:`RedactRule` objects to log lines."""

    # Built-in convenience patterns.
    BUILTIN_PATTERNS: List[RedactRule] = [
        RedactRule(r"(?i)(?<=password[=:\s])[^\s&]+", "[REDACTED]", "password"),
        RedactRule(r"\b(?:\d{4}[- ]?){3}\d{4}\b", "[CARD]", "credit_card"),
        RedactRule(
            r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
            "[EMAIL]",
            "email",
        ),
    ]

    def __init__(
        self,
        config: Optional[RedactorConfig] = None,
        include_builtins: bool = False,
    ) -> None:
        self._enabled = True
        rules: List[RedactRule] = []
        if include_builtins:
            rules.extend(self.BUILTIN_PATTERNS)
        if config is not None:
            self._enabled = config.enabled
            rules.extend(config.rules)
        self._rules = rules

    def redact(self, line: str) -> str:
        """Return *line* with all configured patterns replaced."""
        if not self._enabled:
            return line
        for rule in self._rules:
            line = rule.apply(line)
        return line

    def __repr__(self) -> str:  # pragma: no cover
        return f"Redactor(rules={len(self._rules)}, enabled={self._enabled})"
