"""Tests for logpulse.matcher."""

import pytest

from logpulse.matcher import Alert, Pattern, PatternMatcher


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


def test_pattern_match_positive():
    p = Pattern(label="error", regex=r"ERROR", severity="critical")
    assert p.match("2024-01-01 ERROR something broke") is not None


def test_pattern_match_negative():
    p = Pattern(label="error", regex=r"ERROR")
    assert p.match("2024-01-01 INFO all good") is None


def test_pattern_case_sensitive():
    p = Pattern(label="error", regex=r"ERROR")
    assert p.match("error lowercase") is None


# ---------------------------------------------------------------------------
# PatternMatcher.from_config
# ---------------------------------------------------------------------------


CONFIG = [
    {"label": "oom", "regex": r"Out of memory", "severity": "critical"},
    {"label": "warn", "regex": r"WARN"},
]


def test_from_config_creates_patterns():
    matcher = PatternMatcher.from_config(CONFIG)
    assert len(matcher.patterns) == 2
    assert matcher.patterns[0].label == "oom"
    assert matcher.patterns[1].severity == "warning"  # default


# ---------------------------------------------------------------------------
# PatternMatcher.check
# ---------------------------------------------------------------------------


def test_check_no_match():
    matcher = PatternMatcher.from_config(CONFIG)
    alerts = matcher.check("INFO everything is fine\n")
    assert alerts == []


def test_check_single_match():
    matcher = PatternMatcher.from_config(CONFIG)
    alerts = matcher.check("kernel: Out of memory: Kill process 1234\n")
    assert len(alerts) == 1
    assert alerts[0].label == "oom"
    assert alerts[0].severity == "critical"


def test_check_multiple_matches():
    """A line can trigger more than one pattern."""
    multi_config = [
        {"label": "a", "regex": r"FAIL"},
        {"label": "b", "regex": r"disk"},
    ]
    matcher = PatternMatcher.from_config(multi_config)
    alerts = matcher.check("FAIL: disk write error\n")
    assert len(alerts) == 2


def test_alert_str_representation():
    alert = Alert(label="oom", severity="critical", line="Out of memory\n", pattern=r"Out of memory")
    text = str(alert)
    assert "[CRITICAL]" in text
    assert "oom" in text
    assert "Out of memory" in text
