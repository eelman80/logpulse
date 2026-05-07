"""Configuration loading for logpulse."""
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
from logpulse.multiline import MultilineConfig


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
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class AppConfig:
    log_path: str
    patterns: List[PatternConfig] = field(default_factory=list)
    notifiers: List[NotifierConfig] = field(default_factory=list)
    poll_interval: float = 1.0
    checkpoint_path: Optional[str] = None
    multiline: MultilineConfig = field(default_factory=MultilineConfig)


def _expand(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value))


def _sampler_from_dict(data: dict) -> SamplerConfig:
    from logpulse.sampler import SamplerConfig
    return SamplerConfig(
        every_nth=data.get("every_nth"),
        probability=data.get("probability"),
    )


def load_config(path: str) -> AppConfig:
    raw = Path(path).read_bytes()
    data: Dict[str, Any] = tomllib.loads(raw.decode())

    if "log_path" not in data:
        raise ValueError("Config must specify 'log_path'")

    patterns = [
        PatternConfig(
            label=p["label"],
            pattern=p["pattern"],
            severity=p.get("severity", "warning"),
            sampler=_sampler_from_dict(p["sampler"]) if "sampler" in p else None,
        )
        for p in data.get("patterns", [])
    ]

    notifiers = [
        NotifierConfig(
            url=_expand(n["url"]),
            timeout=float(n.get("timeout", 10.0)),
            headers=n.get("headers", {}),
        )
        for n in data.get("notifiers", [])
    ]

    multiline_data = data.get("multiline", {})
    multiline_cfg = MultilineConfig.from_dict(multiline_data)

    return AppConfig(
        log_path=_expand(data["log_path"]),
        patterns=patterns,
        notifiers=notifiers,
        poll_interval=float(data.get("poll_interval", 1.0)),
        checkpoint_path=data.get("checkpoint_path"),
        multiline=multiline_cfg,
    )
