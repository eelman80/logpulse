"""Tail a growing log file, detect rotation, and optionally resume via checkpoint."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Generator, Optional

from logpulse.checkpoint import CheckpointConfig, CheckpointStore


class LogTailer:
    """Yield new lines from *path*, resuming from a checkpoint when available."""

    def __init__(
        self,
        path: str,
        poll_interval: float = 0.5,
        checkpoint_config: Optional[CheckpointConfig] = None,
    ) -> None:
        self._path = path
        self._poll_interval = poll_interval
        self._fh = None
        self._inode: Optional[int] = None
        self._checkpoint = CheckpointStore(
            checkpoint_config or CheckpointConfig(enabled=False)
        )
        self._open()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _open(self) -> None:
        """Open the log file, resuming from the last checkpoint if present."""
        if self._fh:
            self._fh.close()
        self._fh = open(self._path, "r", errors="replace")  # noqa: WPS515
        stat = os.fstat(self._fh.fileno())
        self._inode = stat.st_ino
        entry = self._checkpoint.get(self._path)
        if entry and entry.inode == self._inode:
            self._fh.seek(entry.offset)
        else:
            self._fh.seek(0, 2)  # seek to end for fresh tails

    def _rotated(self) -> bool:
        """Return True if the file has been rotated (inode changed or shrunk)."""
        try:
            st = os.stat(self._path)
        except FileNotFoundError:
            return True
        if st.st_ino != self._inode:
            return True
        assert self._fh is not None
        if st.st_size < self._fh.tell():
            return True
        return False

    def _save_checkpoint(self) -> None:
        assert self._fh is not None
        assert self._inode is not None
        self._checkpoint.save(self._path, inode=self._inode, offset=self._fh.tell())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lines(self) -> Generator[str, None, None]:
        """Yield lines as they appear; handles rotation transparently."""
        assert self._fh is not None
        while True:
            line = self._fh.readline()
            if line:
                yield line.rstrip("\n")
                self._save_checkpoint()
            else:
                if self._rotated():
                    self._checkpoint.clear(self._path)
                    self._open()
                else:
                    time.sleep(self._poll_interval)

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None
