"""Tests for logpulse.config module."""
from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from logpulse.config import load, AppConfig, PatternConfig, NotifierConfig


@pytest.fixture()
def toml_file(tmp_path: Path):
    """Return a helper that writes a TOML file and returns its path."""

    def _write(content: str) -> Path:
        p = tmp_path / "logpulse.toml"
        p.write_text(textwrap.dedent(content))
        return p

    return _write


def test_load_minimal(toml_file):
    cfg = load(toml_file('log_path = "/var/log/app.log"\n'))
    assert isinstance(cfg, AppConfig)
    assert cfg.log_path == "/var/log/app.log"
    assert cfg.poll_interval == 1.0
    assert cfg.patterns == []
    assert cfg.notifier is None


def test_load_missing_log_path_raises(toml_file):
    with pytest.raises(ValueError, match="log_path"):
        load(toml_file("poll_interval = 2.0\n"))


def test_load_patterns(toml_file):
    content = """
        log_path = "/tmp/app.log"

        [[patterns]]
        label = "ERROR"
        regex = "ERROR"
        severity = "critical"
        case_sensitive = true

        [[patterns]]
        label = "warn"
        regex = "WARN"
    """
    cfg = load(toml_file(content))
    assert len(cfg.patterns) == 2
    first: PatternConfig = cfg.patterns[0]
    assert first.label == "ERROR"
    assert first.severity == "critical"
    assert first.case_sensitive is True
    second: PatternConfig = cfg.patterns[1]
    assert second.severity == "warning"  # default
    assert second.case_sensitive is False


def test_load_notifier(toml_file):
    content = """
        log_path = "/tmp/app.log"

        [notifier]
        webhook_url = "https://hooks.example.com/abc"
        timeout = 5
    """
    cfg = load(toml_file(content))
    assert isinstance(cfg.notifier, NotifierConfig)
    assert cfg.notifier.webhook_url == "https://hooks.example.com/abc"
    assert cfg.notifier.timeout == 5


def test_env_var_expansion(toml_file, monkeypatch):
    monkeypatch.setenv("LOG_DIR", "/var/log")
    cfg = load(toml_file('log_path = "$LOG_DIR/app.log"\n'))
    assert cfg.log_path == "/var/log/app.log"


def test_poll_interval_custom(toml_file):
    cfg = load(toml_file('log_path = "/tmp/x.log"\npoll_interval = 0.5\n'))
    assert cfg.poll_interval == pytest.approx(0.5)
