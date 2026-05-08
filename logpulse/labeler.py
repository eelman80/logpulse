"""Dynamic line labeler — attaches key/value labels to lines based on regex captures."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LabelRule:
    """A single labeling rule: apply *pattern* to a line and attach *labels*."""

    name: str
    pattern: re.Pattern
    labels: Dict[str, str]  # static labels merged with named capture groups

    def apply(self, line: str) -> Optional[Dict[str, str]]:
        """Return merged labels if *line* matches, else None."""
        m = self.pattern.search(line)
        if m is None:
            return None
        result = dict(self.labels)
        result.update({k: v for k, v in m.groupdict().items() if v is not None})
        return result


@dataclass
class LabelerConfig:
    enabled: bool = True
    rules: List[LabelRule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "LabelerConfig":
        enabled = data.get("enabled", True)
        rules: List[LabelRule] = []
        for entry in data.get("rules", []):
            name = entry["name"]
            pattern = re.compile(entry["pattern"])
            labels = {k: v for k, v in entry.items() if k not in ("name", "pattern")}
            rules.append(LabelRule(name=name, pattern=pattern, labels=labels))
        return cls(enabled=enabled, rules=rules)


class LineLabeler:
    """Attach dynamic labels to a line by running it through all configured rules."""

    def __init__(self, config: LabelerConfig) -> None:
        self._config = config

    def label(self, line: str) -> Dict[str, str]:
        """Return a dict of labels collected from all matching rules."""
        if not self._config.enabled:
            return {}
        merged: Dict[str, str] = {}
        for rule in self._config.rules:
            result = rule.apply(line)
            if result is not None:
                merged.update(result)
        return merged

    @property
    def rules(self) -> List[LabelRule]:
        return self._config.rules
