"""Multi-line log folding: collapse continuation lines into a single event."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator, List, Optional


@dataclass
class MultilineConfig:
    """Configuration for multi-line folding."""
    start_pattern: str = r"^\S"          # line that begins a new record
    continuation_pattern: str = r"^\s+"  # lines that belong to the previous record
    max_lines: int = 50                   # hard cap per folded record
    flush_timeout_lines: int = 100        # flush pending after N unrelated lines
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "MultilineConfig":
        return cls(
            start_pattern=data.get("start_pattern", r"^\S"),
            continuation_pattern=data.get("continuation_pattern", r"^\s+"),
            max_lines=int(data.get("max_lines", 50)),
            flush_timeout_lines=int(data.get("flush_timeout_lines", 100)),
            enabled=bool(data.get("enabled", True)),
        )


@dataclass
class _Pending:
    lines: List[str] = field(default_factory=list)

    def append(self, line: str) -> None:
        self.lines.append(line)

    def flush(self) -> str:
        result = "\n".join(self.lines)
        self.lines.clear()
        return result

    @property
    def empty(self) -> bool:
        return len(self.lines) == 0


class MultilineFolder:
    """Folds continuation lines into a single logical log line."""

    def __init__(self, cfg: MultilineConfig) -> None:
        self._cfg = cfg
        self._start_re = re.compile(cfg.start_pattern)
        self._cont_re = re.compile(cfg.continuation_pattern)
        self._pending = _Pending()
        self._idle_count = 0

    def feed(self, line: str) -> Iterator[str]:
        """Feed one raw line; yield zero or more completed records."""
        if not self._cfg.enabled:
            yield line
            return

        is_start = bool(self._start_re.search(line))
        is_cont = bool(self._cont_re.search(line))

        if is_cont and not self._pending.empty:
            self._pending.append(line)
            self._idle_count = 0
            if len(self._pending.lines) >= self._cfg.max_lines:
                yield self._pending.flush()
        else:
            if not self._pending.empty:
                yield self._pending.flush()
            self._pending.append(line)
            self._idle_count = 0

    def flush(self) -> Optional[str]:
        """Flush any buffered pending record (e.g. at EOF)."""
        if not self._pending.empty:
            return self._pending.flush()
        return None
