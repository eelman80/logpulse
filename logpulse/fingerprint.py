"""Line fingerprinting: normalize log lines into stable signatures.

Useful for grouping noisy logs that differ only in dynamic values
(timestamps, IDs, hex addresses) into a single canonical fingerprint.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Optional


# Patterns that replace dynamic tokens with a stable placeholder
_DEFAULT_MASKS: List[tuple[str, str]] = [
    (r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", "<UUID>"),
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<IP>"),
    (r"\b[0-9a-fA-F]{6,}\b", "<HEX>"),
    (r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b", "<TS>"),
    (r"\b\d+\b", "<NUM>"),
]


@dataclass
class FingerprintConfig:
    enabled: bool = True
    # Extra user-supplied regex → placeholder pairs applied before defaults
    extra_masks: List[tuple[str, str]] = field(default_factory=list)
    # Hash length (chars) for the short fingerprint id
    hash_length: int = 8

    @staticmethod
    def from_dict(data: dict) -> "FingerprintConfig":
        extra_raw = data.get("extra_masks", [])
        extra = [(r["pattern"], r.get("placeholder", "<REDACTED>")) for r in extra_raw]
        return FingerprintConfig(
            enabled=data.get("enabled", True),
            extra_masks=extra,
            hash_length=int(data.get("hash_length", 8)),
        )


@dataclass
class Fingerprint:
    normalized: str
    digest: str  # short hex hash of normalized text

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.digest}:{self.normalized[:60]}"


class LineFingerprinter:
    """Normalize a raw log line and produce a stable fingerprint."""

    def __init__(self, config: Optional[FingerprintConfig] = None) -> None:
        self._cfg = config or FingerprintConfig()
        compiled: List[tuple[re.Pattern, str]] = []
        for pattern, placeholder in self._cfg.extra_masks:
            compiled.append((re.compile(pattern), placeholder))
        for pattern, placeholder in _DEFAULT_MASKS:
            compiled.append((re.compile(pattern), placeholder))
        self._masks = compiled

    def fingerprint(self, line: str) -> Fingerprint:
        """Return a Fingerprint for *line*."""
        normalized = line
        for rx, placeholder in self._masks:
            normalized = rx.sub(placeholder, normalized)
        # Collapse runs of whitespace so minor formatting changes don't diverge
        normalized = re.sub(r"\s+", " ", normalized).strip()
        digest = hashlib.sha1(normalized.encode()).hexdigest()[: self._cfg.hash_length]
        return Fingerprint(normalized=normalized, digest=digest)
