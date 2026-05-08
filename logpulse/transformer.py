"""Line transformer: apply a sequence of regex substitutions to log lines."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TransformRule:
    pattern: str
    replacement: str
    label: str = ""
    _re: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._re = re.compile(self.pattern)

    def apply(self, line: str) -> str:
        """Return *line* with all matches replaced by *replacement*."""
        return self._re.sub(self.replacement, line)


@dataclass
class TransformerConfig:
    rules: List[TransformRule] = field(default_factory=list)
    enabled: bool = True

    @staticmethod
    def from_dict(data: dict) -> "TransformerConfig":
        enabled = data.get("enabled", True)
        rules: List[TransformRule] = [
            TransformRule(
                pattern=r["pattern"],
                replacement=r.get("replacement", ""),
                label=r.get("label", ""),
            )
            for r in data.get("rules", [])
        ]
        return TransformerConfig(rules=rules, enabled=enabled)


class LineTransformer:
    """Apply ordered transform rules to each log line."""

    def __init__(self, cfg: TransformerConfig) -> None:
        self._cfg = cfg
        self._transform_count: int = 0

    # ------------------------------------------------------------------
    def transform(self, line: str) -> str:
        """Return the transformed line.  Returns *line* unchanged when disabled."""
        if not self._cfg.enabled or not self._cfg.rules:
            return line
        result = line
        for rule in self._cfg.rules:
            new = rule.apply(result)
            if new != result:
                self._transform_count += 1
            result = new
        return result

    # ------------------------------------------------------------------
    @property
    def transform_count(self) -> int:
        """Total number of individual rule-level substitutions applied."""
        return self._transform_count

    def reset_stats(self) -> None:
        self._transform_count = 0
