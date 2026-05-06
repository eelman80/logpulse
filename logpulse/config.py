"""Configuration loading for logpulse."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from logpulse.sampler import SamplerConfig
from logpulse.redactor import RedactorConfig


@dataclass
class PatternConfig:
    label: str
    regex: str
    severity: str = "warning"
    sampler: Optional[SamplerConfig] = None


@dataclass
class NotifierConfig:
    url: str
    timeout: float = 10.0
    source: Optional[str] = None


@dataclass
class AppConfig:
    log_path: str
    patterns: List[PatternConfig] = field(default_factory=list)
    notifiers: List[NotifierConfig] = field(default_factory=list)
    checkpoint_path: Optional[str] = None
    poll_interval: float = 1.0
    redactor: Optional[RedactorConfig] = None


def _expand(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value))


def _sampler_from_dict(data: Dict[str, Any]) -> Optional[SamplerConfig]:
    if "sampler" not in data:
        return None
    s = data["sampler"]
    return SamplerConfig(
        every_nth=s.get("every_nth"),
        probability=s.get("probability"),
    )


def load(path: str | Path) -> AppConfig:
    """Parse a TOML config file and return an :class:`AppConfig`."""
    with open(path, "rb") as fh:
        raw: Dict[str, Any] = tomllib.load(fh)

    if "log_path" not in raw:
        raise ValueError("Config must contain 'log_path'")

    patterns = [
        PatternConfig(
            label=p["label"],
            regex=p["regex"],
            severity=p.get("severity", "warning"),
            sampler=_sampler_from_dict(p),
        )
        for p in raw.get("patterns", [])
    ]

    notifiers = [
        NotifierConfig(
            url=n["url"],
            timeout=n.get("timeout", 10.0),
            source=n.get("source"),
        )
        for n in raw.get("notifiers", [])
    ]

    redactor: Optional[RedactorConfig] = None
    if "redactor" in raw:
        redactor = RedactorConfig.from_dict(raw["redactor"])

    return AppConfig(
        log_path=_expand(raw["log_path"]),
        patterns=patterns,
        notifiers=notifiers,
        checkpoint_path=raw.get("checkpoint_path"),
        poll_interval=raw.get("poll_interval", 1.0),
        redactor=redactor,
    )
