"""Configuration dataclasses and TOML loader for logpulse."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from logpulse.sampler import SamplerConfig
from logpulse.suppressor import SuppressorConfig


@dataclass
class PatternConfig:
    label: str
    pattern: str
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
    poll_interval: float = 1.0
    checkpoint_path: Optional[str] = None
    suppressor: SuppressorConfig = field(default_factory=SuppressorConfig)


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


def load(path: str) -> AppConfig:
    raw = Path(path).read_bytes()
    data = tomllib.loads(raw.decode())

    if "log_path" not in data:
        raise ValueError("Config missing required key: log_path")

    patterns = [
        PatternConfig(
            label=p["label"],
            pattern=p["pattern"],
            severity=p.get("severity", "warning"),
            sampler=_sampler_from_dict(p),
        )
        for p in data.get("patterns", [])
    ]

    notifiers = [
        NotifierConfig(
            url=_expand(n["url"]),
            timeout=n.get("timeout", 10.0),
            source=n.get("source"),
        )
        for n in data.get("notifiers", [])
    ]

    suppressor = SuppressorConfig.from_dict(data.get("suppressor", {}))

    return AppConfig(
        log_path=_expand(data["log_path"]),
        patterns=patterns,
        notifiers=notifiers,
        poll_interval=data.get("poll_interval", 1.0),
        checkpoint_path=data.get("checkpoint_path"),
        suppressor=suppressor,
    )
