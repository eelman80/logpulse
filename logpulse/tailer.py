"""Core log tailer module for following log files and emitting new lines."""

import os
import time
from typing import Callable, Iterator, Optional


class LogTailer:
    """Tails a log file, yielding new lines as they are appended."""

    def __init__(
        self,
        filepath: str,
        poll_interval: float = 0.5,
        from_beginning: bool = False,
    ) -> None:
        self.filepath = filepath
        self.poll_interval = poll_interval
        self.from_beginning = from_beginning
        self._file = None
        self._inode: Optional[int] = None

    def _open(self) -> None:
        self._file = open(self.filepath, "r", encoding="utf-8", errors="replace")
        stat = os.stat(self.filepath)
        self._inode = stat.st_ino
        if not self.from_beginning:
            self._file.seek(0, os.SEEK_END)

    def _rotated(self) -> bool:
        """Detect if the file has been rotated (inode changed or shrunk)."""
        try:
            stat = os.stat(self.filepath)
        except FileNotFoundError:
            return True
        if stat.st_ino != self._inode:
            return True
        if self._file and stat.st_size < self._file.tell():
            return True
        return False

    def lines(self) -> Iterator[str]:
        """Yield lines from the log file indefinitely."""
        while not os.path.exists(self.filepath):
            time.sleep(self.poll_interval)

        self._open()
        try:
            while True:
                if self._rotated():
                    self._file.close()
                    time.sleep(self.poll_interval)
                    if os.path.exists(self.filepath):
                        self._open()
                    continue

                line = self._file.readline()
                if line:
                    yield line.rstrip("\n")
                else:
                    time.sleep(self.poll_interval)
        finally:
            if self._file:
                self._file.close()

    def tail(self, callback: Callable[[str], None]) -> None:
        """Convenience method: call *callback* for every new line."""
        for line in self.lines():
            callback(line)
