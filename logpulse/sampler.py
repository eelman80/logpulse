"""Line sampler: probabilistic and nth-line sampling to reduce alert noise."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SamplerConfig:
    """Configuration for the line sampler."""

    # Keep every Nth matching line (1 = keep all, 10 = keep every 10th)
    every_nth: int = 1
    # Probability [0.0, 1.0] of keeping a line; applied after every_nth
    probability: float = 1.0
    # Independent counters per pattern label when True
    per_label: bool = True

    def __post_init__(self) -> None:
        if self.every_nth < 1:
            raise ValueError("every_nth must be >= 1")
        if not (0.0 <= self.probability <= 1.0):
            raise ValueError("probability must be between 0.0 and 1.0")


class LineSampler:
    """Decides whether a given line (identified by label) should be processed."""

    def __init__(
        self,
        config: Optional[SamplerConfig] = None,
        seed: Optional[int] = None,
    ) -> None:
        self._cfg = config or SamplerConfig()
        self._counters: dict[str, int] = {}
        self._global_counter: int = 0
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    def _counter_key(self, label: str) -> str:
        return label if self._cfg.per_label else "__global__"

    def _increment(self, label: str) -> int:
        key = self._counter_key(label)
        self._counters[key] = self._counters.get(key, 0) + 1
        return self._counters[key]

    # ------------------------------------------------------------------
    def allow(self, label: str) -> bool:
        """Return True if this occurrence should be forwarded."""
        count = self._increment(label)

        # nth-line gate
        if count % self._cfg.every_nth != 0:
            return False

        # probabilistic gate
        if self._cfg.probability < 1.0:
            if self._rng.random() >= self._cfg.probability:
                return False

        return True

    def reset(self, label: Optional[str] = None) -> None:
        """Reset counters for *label*, or all counters when label is None."""
        if label is None:
            self._counters.clear()
        else:
            key = self._counter_key(label)
            self._counters.pop(key, None)

    def seen(self, label: str) -> int:
        """Return how many times *label* has been presented so far."""
        return self._counters.get(self._counter_key(label), 0)
