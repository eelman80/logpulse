"""Deduplication filter: suppress identical log lines within a time window."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class DedupConfig:
    window_seconds: float = 60.0
    max_cache_size: int = 1024


@dataclass
class _Entry:
    first_seen: float
    count: int = 1


class LineDeduplicator:
    """Track recently seen log lines and report whether a line is a duplicate.

    A line is considered a duplicate when an identical line was already seen
    within *window_seconds*.  After the window expires the line is treated as
    new again.
    """

    def __init__(self, config: Optional[DedupConfig] = None) -> None:
        self._cfg = config or DedupConfig()
        self._cache: Dict[str, _Entry] = {}

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def is_duplicate(self, line: str) -> bool:
        """Return True if *line* is a duplicate within the current window."""
        key = self._hash(line)
        now = time.monotonic()
        self._evict(now)

        entry = self._cache.get(key)
        if entry is None:
            self._maybe_trim()
            self._cache[key] = _Entry(first_seen=now)
            return False

        entry.count += 1
        return True

    def seen_count(self, line: str) -> int:
        """Return how many times *line* has been seen in the current window."""
        key = self._hash(line)
        entry = self._cache.get(key)
        return entry.count if entry else 0

    def reset(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash(line: str) -> str:
        return hashlib.md5(line.encode(), usedforsecurity=False).hexdigest()

    def _evict(self, now: float) -> None:
        cutoff = now - self._cfg.window_seconds
        expired = [k for k, v in self._cache.items() if v.first_seen < cutoff]
        for k in expired:
            del self._cache[k]

    def _maybe_trim(self) -> None:
        """If cache exceeds max size, remove the oldest half."""
        if len(self._cache) < self._cfg.max_cache_size:
            return
        sorted_keys = sorted(self._cache, key=lambda k: self._cache[k].first_seen)
        for k in sorted_keys[: len(sorted_keys) // 2]:
            del self._cache[k]
