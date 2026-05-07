"""Audit log: append-only structured record of every alert dispatched."""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from logpulse.matcher import Alert


@dataclass
class AuditConfig:
    enabled: bool = False
    path: str = "logpulse_audit.jsonl"
    max_bytes: int = 10 * 1024 * 1024  # 10 MiB

    @staticmethod
    def from_dict(data: dict) -> "AuditConfig":
        return AuditConfig(
            enabled=data.get("enabled", False),
            path=data.get("path", "logpulse_audit.jsonl"),
            max_bytes=int(data.get("max_bytes", 10 * 1024 * 1024)),
        )


class AuditLog:
    """Thread-safe append-only JSONL audit log."""

    def __init__(self, config: AuditConfig) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._path: Optional[Path] = Path(config.path) if config.enabled else None
        self._records_written: int = 0

    def record(self, alert: Alert, notifier_name: str, routed: bool) -> None:
        """Append one audit entry.  No-op when disabled."""
        if not self._config.enabled or self._path is None:
            return
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "label": alert.label,
            "severity": alert.severity,
            "line": alert.line,
            "pattern": alert.pattern,
            "notifier": notifier_name,
            "routed": routed,
        }
        with self._lock:
            self._rotate_if_needed()
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
            self._records_written += 1

    def _rotate_if_needed(self) -> None:
        """Truncate the file when it exceeds max_bytes (simple rotation)."""
        if self._path.exists() and self._path.stat().st_size >= self._config.max_bytes:
            self._path.write_text("", encoding="utf-8")

    @property
    def records_written(self) -> int:
        return self._records_written
