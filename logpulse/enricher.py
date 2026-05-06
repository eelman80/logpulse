"""Line enrichment: attach metadata (hostname, tags, timestamp) to matched lines."""
from __future__ import annotations

import socket
import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EnrichConfig:
    include_hostname: bool = True
    include_timestamp: bool = True
    static_tags: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "EnrichConfig":
        return cls(
            include_hostname=data.get("include_hostname", True),
            include_timestamp=data.get("include_timestamp", True),
            static_tags=data.get("static_tags", {}),
        )


@dataclass
class EnrichedLine:
    raw: str
    tags: Dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"line": self.raw, **self.tags}


class LineEnricher:
    """Attach metadata tags to a raw log line."""

    def __init__(self, config: Optional[EnrichConfig] = None) -> None:
        self._cfg = config or EnrichConfig()
        self._hostname: Optional[str] = None
        if self._cfg.include_hostname:
            try:
                self._hostname = socket.gethostname()
            except OSError:
                self._hostname = "unknown"

    def enrich(self, line: str) -> EnrichedLine:
        tags: Dict[str, str] = {}
        if self._cfg.include_hostname and self._hostname:
            tags["hostname"] = self._hostname
        if self._cfg.include_timestamp:
            tags["timestamp"] = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        tags.update(self._cfg.static_tags)
        return EnrichedLine(raw=line, tags=tags)

    def enrich_many(self, lines: List[str]) -> List[EnrichedLine]:
        return [self.enrich(line) for line in lines]
