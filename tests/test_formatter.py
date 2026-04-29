"""Tests for logpulse.formatter."""
from __future__ import annotations

import pytest

from logpulse.formatter import (
    FormatConfig,
    _truncate,
    format_alert,
    format_alert_block,
    SEVERITY_EMOJI,
)
from logpulse.matcher import Alert


def _alert(
    label: str = "TEST",
    line: str = "something went wrong",
    severity: str = "error",
) -> Alert:
    return Alert(label=label, line=line, severity=severity)


# ---------------------------------------------------------------------------
# _truncate
# ---------------------------------------------------------------------------

def test_truncate_short_string_unchanged():
    assert _truncate("hello", 10) == "hello"


def test_truncate_long_string_adds_ellipsis():
    result = _truncate("a" * 20, 10)
    assert len(result) == 10
    assert result.endswith("...")


def test_truncate_exact_length_unchanged():
    assert _truncate("hello", 5) == "hello"


# ---------------------------------------------------------------------------
# format_alert
# ---------------------------------------------------------------------------

def test_format_alert_contains_label():
    result = format_alert(_alert(label="MYPATTERN"))
    assert "MYPATTERN" in result


def test_format_alert_contains_emoji_for_known_severity():
    for severity, emoji in SEVERITY_EMOJI.items():
        result = format_alert(_alert(severity=severity))
        assert emoji in result


def test_format_alert_unknown_severity_uses_default_emoji():
    result = format_alert(_alert(severity="verbose"))
    assert "⚪" in result


def test_format_alert_includes_source_when_provided():
    result = format_alert(_alert(), source="/var/log/app.log")
    assert "/var/log/app.log" in result


def test_format_alert_no_source_bracket_absent():
    result = format_alert(_alert(), source=None)
    assert "[" not in result


def test_format_alert_truncates_long_line():
    long_line = "x" * 300
    cfg = FormatConfig(max_line_length=50)
    result = format_alert(_alert(line=long_line), config=cfg)
    # The truncated portion should appear; full line should not
    assert long_line not in result
    assert "..." in result


# ---------------------------------------------------------------------------
# format_alert_block
# ---------------------------------------------------------------------------

def test_format_alert_block_contains_all_fields():
    alert = _alert(label="DISK", severity="critical", line="disk full")
    result = format_alert_block(alert, source="/var/log/syslog")
    assert "DISK" in result
    assert "critical" in result
    assert "/var/log/syslog" in result
    assert "disk full" in result


def test_format_alert_block_no_source_omits_source_line():
    result = format_alert_block(_alert())
    assert "source" not in result


def test_format_alert_block_is_multiline():
    result = format_alert_block(_alert())
    assert "\n" in result
