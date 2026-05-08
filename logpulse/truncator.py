"""Line truncation and length-limiting for log lines before processing."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TruncatorConfig:
    enabled: bool = True
    max_length: int = 4096
    ellipsis: str = "..."
    count_bytes: bool = False  # if True, limit by UTF-8 byte length instead of chars

    @staticmethod
    def from_dict(data: dict) -> "TruncatorConfig":
        return TruncatorConfig(
            enabled=data.get("enabled", True),
            max_length=int(data.get("max_length", 4096)),
            ellipsis=data.get("ellipsis", "..."),
            count_bytes=bool(data.get("count_bytes", False)),
        )


@dataclass
class TruncationResult:
    line: str
    truncated: bool
    original_length: int

    def __str__(self) -> str:  # pragma: no cover
        return self.line


class LineTruncator:
    """Truncates log lines that exceed a configured maximum length."""

    def __init__(self, cfg: TruncatorConfig) -> None:
        self._cfg = cfg
        self._truncated_count: int = 0

    def process(self, line: str) -> TruncationResult:
        """Return a TruncationResult; line is unchanged if within limit."""
        if not self._cfg.enabled:
            return TruncationResult(line=line, truncated=False, original_length=len(line))

        if self._cfg.count_bytes:
            raw = line.encode("utf-8")
            original_length = len(raw)
            limit = self._cfg.max_length
            if original_length <= limit:
                return TruncationResult(line=line, truncated=False, original_length=original_length)
            ellipsis_bytes = self._cfg.ellipsis.encode("utf-8")
            keep = limit - len(ellipsis_bytes)
            truncated_line = raw[:keep].decode("utf-8", errors="ignore") + self._cfg.ellipsis
        else:
            original_length = len(line)
            limit = self._cfg.max_length
            if original_length <= limit:
                return TruncationResult(line=line, truncated=False, original_length=original_length)
            keep = limit - len(self._cfg.ellipsis)
            truncated_line = line[:keep] + self._cfg.ellipsis

        self._truncated_count += 1
        return TruncationResult(line=truncated_line, truncated=True, original_length=original_length)

    @property
    def truncated_count(self) -> int:
        return self._truncated_count

    def reset_stats(self) -> None:
        self._truncated_count = 0
