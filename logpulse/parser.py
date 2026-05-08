"""Structured log line parser: extracts fields from log lines via named-group regex."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ParseRule:
    name: str
    pattern: str
    _compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.pattern)

    def parse(self, line: str) -> Optional[Dict[str, str]]:
        """Return a dict of named captures, or None if the rule does not match."""
        m = self._compiled.search(line)
        if m is None:
            return None
        return {k: v for k, v in m.groupdict().items() if v is not None}


@dataclass
class ParsedLine:
    raw: str
    rule_name: Optional[str]
    fields: Dict[str, str]

    def get(self, key: str, default: str = "") -> str:
        return self.fields.get(key, default)


@dataclass
class ParserConfig:
    enabled: bool = False
    rules: List[ParseRule] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict) -> "ParserConfig":
        raw = data.get("parser", {})
        if not raw.get("enabled", False):
            return ParserConfig(enabled=False)
        rules = [
            ParseRule(name=r["name"], pattern=r["pattern"])
            for r in raw.get("rules", [])
        ]
        return ParserConfig(enabled=True, rules=rules)


class LineParser:
    """Applies the first matching ParseRule to each log line."""

    def __init__(self, cfg: ParserConfig) -> None:
        self._cfg = cfg

    def parse(self, line: str) -> ParsedLine:
        if not self._cfg.enabled:
            return ParsedLine(raw=line, rule_name=None, fields={})
        for rule in self._cfg.rules:
            fields = rule.parse(line)
            if fields is not None:
                return ParsedLine(raw=line, rule_name=rule.name, fields=fields)
        return ParsedLine(raw=line, rule_name=None, fields={})
