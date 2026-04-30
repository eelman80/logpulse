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


@dataclass
class PatternConfig:
    label: str
    regex: str
    severity: str = "warning"
    every_nth: int = 1
    probability: float = 1.0


@dataclass
class NotifierConfig:
    url: str
    timeout: float = 10.0
    source: Optional[str] = None


@dataclass
class AppConfig:
    log_path: Path
    patterns: List[PatternConfig]
    notifier: NotifierConfig
    poll_interval: float = 1.0
    sampler: SamplerConfig = field(default_factory=SamplerConfig)


def _expand(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value))


def _sampler_from_dict(raw: Dict[str, Any]) -> SamplerConfig:
    return SamplerConfig(
        every_nth=raw.get("every_nth", 1),
        probability=raw.get("probability", 1.0),
        per_label=raw.get("per_label", True),
    )


def load(path: str | Path) -> AppConfig:
    """Parse a TOML config file and return an AppConfig."""
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))

    if "log_path" not in raw:
        raise KeyError("'log_path' is required in config")

    patterns = [
        PatternConfig(
            label=p["label"],
            regex=p["regex"],
            severity=p.get("severity", "warning"),
            every_nth=p.get("every_nth", 1),
            probability=p.get("probability", 1.0),
        )
        for p in raw.get("patterns", [])
    ]

    notifier_raw = raw.get("notifier", {})
    if "url" not in notifier_raw:
        raise KeyError("'notifier.url' is required in config")
    notifier = NotifierConfig(
        url=_expand(notifier_raw["url"]),
        timeout=notifier_raw.get("timeout", 10.0),
        source=notifier_raw.get("source"),
    )

    sampler = _sampler_from_dict(raw.get("sampler", {}))

    return AppConfig(
        log_path=Path(_expand(str(raw["log_path"]))),
        patterns=patterns,
        notifier=notifier,
        poll_interval=raw.get("poll_interval", 1.0),
        sampler=sampler,
    )
