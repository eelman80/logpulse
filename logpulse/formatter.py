"""Alert formatting utilities for logpulse notifications."""
from __future__ import annotations

import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from logpulse.matcher import Alert

SEVERITY_EMOJI = {
    "critical": "🔴",
    "error": "🟠",
    "warning": "🟡",
    "info": "🔵",
}

DEFAULT_EMOJI = "⚪"


@dataclass
class FormatConfig:
    max_line_length: int = 200
    timestamp_fmt: str = "%Y-%m-%d %H:%M:%S UTC"
    include_context: bool = True


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def format_alert(
    alert: Alert,
    source: Optional[str] = None,
    config: Optional[FormatConfig] = None,
) -> str:
    """Return a human-readable single-line summary of an alert."""
    cfg = config or FormatConfig()
    now = datetime.now(timezone.utc).strftime(cfg.timestamp_fmt)
    emoji = SEVERITY_EMOJI.get(alert.severity.lower(), DEFAULT_EMOJI)
    src_part = f" [{source}]" if source else ""
    line = _truncate(alert.line, cfg.max_line_length)
    return f"{emoji} {now}{src_part} | {alert.label} | {line}"


def format_alert_block(alert: Alert, source: Optional[str] = None) -> str:
    """Return a multi-line block suitable for verbose output or file logging."""
    now = datetime.now(timezone.utc).isoformat()
    emoji = SEVERITY_EMOJI.get(alert.severity.lower(), DEFAULT_EMOJI)
    src_line = f"  source   : {source}" if source else ""
    wrapped = textwrap.fill(alert.line, width=80, initial_indent="  ", subsequent_indent="  ")
    parts = [
        f"{emoji} ALERT",
        f"  label    : {alert.label}",
        f"  severity : {alert.severity}",
        f"  time     : {now}",
    ]
    if src_line:
        parts.append(src_line)
    parts += ["  line     :", wrapped]
    return "\n".join(parts)
