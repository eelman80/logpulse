"""Persist and restore log file read positions across restarts."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class CheckpointConfig:
    path: str = ".logpulse_checkpoint.json"
    enabled: bool = True


@dataclass
class _Entry:
    inode: int
    offset: int


class CheckpointStore:
    """Read/write file-position checkpoints keyed by log path."""

    def __init__(self, config: CheckpointConfig) -> None:
        self._config = config
        self._store: Dict[str, _Entry] = {}
        if config.enabled:
            self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, log_path: str, inode: int, offset: int) -> None:
        """Persist the current read position for *log_path*."""
        if not self._config.enabled:
            return
        self._store[log_path] = _Entry(inode=inode, offset=offset)
        self._flush()

    def get(self, log_path: str) -> Optional[_Entry]:
        """Return the last saved position for *log_path*, or ``None``."""
        return self._store.get(log_path)

    def clear(self, log_path: str) -> None:
        """Remove the checkpoint for *log_path* (e.g. after rotation)."""
        if log_path in self._store:
            del self._store[log_path]
            if self._config.enabled:
                self._flush()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        p = Path(self._config.path)
        if not p.exists():
            return
        try:
            raw = json.loads(p.read_text())
            for log_path, data in raw.items():
                self._store[log_path] = _Entry(
                    inode=data["inode"], offset=data["offset"]
                )
        except (json.JSONDecodeError, KeyError, OSError):
            # Corrupt or unreadable checkpoint — start fresh.
            self._store = {}

    def _flush(self) -> None:
        data = {
            k: {"inode": v.inode, "offset": v.offset}
            for k, v in self._store.items()
        }
        tmp = self._config.path + ".tmp"
        try:
            Path(tmp).write_text(json.dumps(data, indent=2))
            os.replace(tmp, self._config.path)
        except OSError:
            pass  # Non-fatal; we'll retry on the next save.
