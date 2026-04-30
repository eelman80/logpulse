"""Rolling line buffer for context capture around matched log lines."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List


@dataclass
class BufferConfig:
    """Configuration for the rolling context buffer."""
    before: int = 3  # lines to keep before a match
    after: int = 3   # lines to emit after a match


@dataclass
class _PendingAfter:
    lines: List[str] = field(default_factory=list)
    remaining: int = 0


class ContextBuffer:
    """Maintains a rolling window of recent lines and captures context
    around matched lines.

    Usage::

        buf = ContextBuffer(BufferConfig(before=2, after=2))
        for line in stream:
            ctx = buf.feed(line, matched=pattern.match(line) is not None)
            if ctx:
                # ctx is (before_lines, matched_line, after_lines)
                handle(ctx)
    """

    def __init__(self, config: BufferConfig) -> None:
        self._cfg = config
        self._window: Deque[str] = deque(maxlen=max(config.before, 1))
        self._pending: List[_PendingAfter] = []

    # ------------------------------------------------------------------
    def feed(
        self, line: str, *, matched: bool
    ) -> List[tuple[List[str], str, List[str]]]:
        """Feed a line into the buffer.

        Returns a (possibly empty) list of completed context tuples.
        Each tuple is ``(before, matched_line, after)`` where *after* may
        be shorter than ``config.after`` if fewer lines have arrived.
        """
        results: List[tuple[List[str], str, List[str]]] = []

        # Advance pending after-contexts
        for p in self._pending:
            if p.remaining > 0:
                p.lines.append(line)
                p.remaining -= 1

        # Flush completed pending entries
        still_pending = []
        for p in self._pending:
            if p.remaining <= 0:
                # already stored matched line as first element via _PendingAfter
                results.append((p.lines[0], p.lines[1], p.lines[2:]))
            else:
                still_pending.append(p)
        self._pending = still_pending

        if matched:
            before = list(self._window)
            p = _PendingAfter(lines=[before, line], remaining=self._cfg.after)
            if self._cfg.after == 0:
                results.append((before, line, []))
            else:
                self._pending.append(p)

        self._window.append(line)
        return results

    def flush(self) -> List[tuple[List[str], str, List[str]]]:
        """Flush any pending after-contexts that haven't filled yet."""
        results = []
        for p in self._pending:
            results.append((p.lines[0], p.lines[1], p.lines[2:]))
        self._pending = []
        return results

    def reset(self) -> None:
        """Clear all internal state."""
        self._window.clear()
        self._pending.clear()
