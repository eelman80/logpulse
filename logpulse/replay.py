"""Replay historical log segments for testing pipelines offline."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional


@dataclass
class ReplayConfig:
    speed: float = 1.0          # multiplier; 0 = as fast as possible
    max_lines: Optional[int] = None
    start_line: int = 0         # 0-based offset into the file
    loop: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "ReplayConfig":
        return cls(
            speed=float(d.get("speed", 1.0)),
            max_lines=d.get("max_lines"),
            start_line=int(d.get("start_line", 0)),
            loop=bool(d.get("loop", False)),
        )


class LogReplayer:
    """Reads lines from a file and yields them, optionally pacing delivery."""

    def __init__(
        self,
        path: str | Path,
        cfg: Optional[ReplayConfig] = None,
        line_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._path = Path(path)
        self._cfg = cfg or ReplayConfig()
        self._callback = line_callback
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True

    def lines(self) -> Iterator[str]:
        """Yield lines from the log file according to ReplayConfig."""
        cfg = self._cfg
        while True:
            yielded = 0
            with self._path.open("r", errors="replace") as fh:
                for idx, raw in enumerate(fh):
                    if self._stopped:
                        return
                    if idx < cfg.start_line:
                        continue
                    if cfg.max_lines is not None and yielded >= cfg.max_lines:
                        return
                    line = raw.rstrip("\n")
                    if self._callback:
                        self._callback(line)
                    yield line
                    yielded += 1
                    if cfg.speed > 0:
                        time.sleep(1.0 / (cfg.speed * 1000))  # simulate ~1 ms between lines
            if not cfg.loop:
                break

    def replay_to(self, sink: Callable[[str], None]) -> int:
        """Push all lines into *sink*; returns total count of lines replayed."""
        count = 0
        for line in self.lines():
            sink(line)
            count += 1
        return count
