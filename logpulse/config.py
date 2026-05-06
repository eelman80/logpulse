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
from logpulse.enricher import EnrichConfig


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


@dataclass
class AppConfig:
    log_path: str
    patterns: List[PatternConfig] = field(default_factory=list)
    notifiers: List[NotifierConfig] = field(default_factory=list)
    checkpoint_path: Optional[str] = None
    poll_interval: float = 1.0
    enrich: EnrichConfig = field(default_factory=EnrichConfig)


def _expand(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value))


def _sampler_from_dict(data: dict) -> SamplerConfig:
    return SamplerConfig(
        every_nth=data.get("every_nth"),
        probability=data.get("probability"),
    )


def load(path: str | Path) -> AppConfig:
    raw = Path(path).read_bytes()
    data: Dict[str, Any] = tomllib.loads(raw.decode())

    if "log_path" not in data:
        raise ValueError("[log_path] is required in config")

    patterns = [
        PatternConfig(
            label=p["label"],
            regex=p["regex"],
            severity=p.get("severity", "warning"),
            sampler=_sampler_from_dict(p["sampler"]) if "sampler" in p else None,
        )
        for p in data.get("patterns", [])
    ]

    notifiers = [
        NotifierConfig(url=_expand(n["url"]), timeout=n.get("timeout", 10.0))
        for n in data.get("notifiers", [])
    ]

    enrich_data = data.get("enrich", {})
    enrich = EnrichConfig.from_dict(enrich_data)

    return AppConfig(
        log_path=_expand(data["log_path"]),
        patterns=patterns,
        notifiers=notifiers,
        checkpoint_path=data.get("checkpoint_path"),
        poll_interval=data.get("poll_interval", 1.0),
        enrich=enrich,
    )
