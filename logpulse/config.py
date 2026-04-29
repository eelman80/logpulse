"""Configuration loader for logpulse."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass
class PatternConfig:
    label: str
    regex: str
    severity: str = "warning"
    case_sensitive: bool = False


@dataclass
class NotifierConfig:
    webhook_url: str
    timeout: int = 10


@dataclass
class AppConfig:
    log_path: str
    poll_interval: float = 1.0
    patterns: list[PatternConfig] = field(default_factory=list)
    notifier: NotifierConfig | None = None


def _expand(value: str) -> str:
    """Expand environment variables and ~ in string values."""
    return os.path.expandvars(os.path.expanduser(value))


def load(path: str | Path) -> AppConfig:
    """Load and validate configuration from a TOML file."""
    raw: dict[str, Any] = tomllib.loads(Path(path).read_text())

    log_path = _expand(raw.get("log_path", ""))
    if not log_path:
        raise ValueError("'log_path' is required in configuration")

    poll_interval = float(raw.get("poll_interval", 1.0))

    patterns: list[PatternConfig] = [
        PatternConfig(
            label=p["label"],
            regex=p["regex"],
            severity=p.get("severity", "warning"),
            case_sensitive=bool(p.get("case_sensitive", False)),
        )
        for p in raw.get("patterns", [])
    ]

    notifier: NotifierConfig | None = None
    if "notifier" in raw:
        n = raw["notifier"]
        notifier = NotifierConfig(
            webhook_url=_expand(n["webhook_url"]),
            timeout=int(n.get("timeout", 10)),
        )

    return AppConfig(
        log_path=log_path,
        poll_interval=poll_interval,
        patterns=patterns,
        notifier=notifier,
    )
