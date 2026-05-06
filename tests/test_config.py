"""Tests for logpulse.config (including enrich section)."""
import textwrap
from pathlib import Path

import pytest

from logpulse.config import load


@pytest.fixture()
def toml_file(tmp_path):
    def _write(content: str) -> Path:
        p = tmp_path / "cfg.toml"
        p.write_text(textwrap.dedent(content))
        return p
    return _write


def _write(tmp_path, content):
    p = tmp_path / "cfg.toml"
    p.write_text(textwrap.dedent(content))
    return p


def test_load_minimal(toml_file):
    p = toml_file('log_path = "/var/log/app.log"\n')
    cfg = load(p)
    assert cfg.log_path == "/var/log/app.log"
    assert cfg.patterns == []
    assert cfg.notifiers == []


def test_load_missing_log_path_raises(toml_file):
    p = toml_file("poll_interval = 2.0\n")
    with pytest.raises(ValueError, match="log_path"):
        load(p)


def test_load_patterns(toml_file):
    p = toml_file("""
        log_path = "/tmp/x.log"
        [[patterns]]
        label = "error"
        regex = "ERROR"
        severity = "critical"
    """)
    cfg = load(p)
    assert len(cfg.patterns) == 1
    assert cfg.patterns[0].label == "error"
    assert cfg.patterns[0].severity == "critical"


def test_load_notifier(toml_file):
    p = toml_file("""
        log_path = "/tmp/x.log"
        [[notifiers]]
        url = "https://hooks.example.com/abc"
    """)
    cfg = load(p)
    assert len(cfg.notifiers) == 1
    assert cfg.notifiers[0].url == "https://hooks.example.com/abc"
    assert cfg.notifiers[0].timeout == 10.0


def test_load_enrich_defaults(toml_file):
    p = toml_file('log_path = "/tmp/x.log"\n')
    cfg = load(p)
    assert cfg.enrich.include_hostname is True
    assert cfg.enrich.include_timestamp is True
    assert cfg.enrich.static_tags == {}


def test_load_enrich_custom(toml_file):
    p = toml_file("""
        log_path = "/tmp/x.log"
        [enrich]
        include_hostname = false
        include_timestamp = false
        [enrich.static_tags]
        env = "prod"
        region = "us-east-1"
    """)
    cfg = load(p)
    assert cfg.enrich.include_hostname is False
    assert cfg.enrich.include_timestamp is False
    assert cfg.enrich.static_tags == {"env": "prod", "region": "us-east-1"}


def test_load_poll_interval(toml_file):
    p = toml_file('log_path = "/tmp/x.log"\npoll_interval = 0.5\n')
    cfg = load(p)
    assert cfg.poll_interval == pytest.approx(0.5)


def test_load_sampler_in_pattern(toml_file):
    p = toml_file("""
        log_path = "/tmp/x.log"
        [[patterns]]
        label = "warn"
        regex = "WARN"
        [patterns.sampler]
        every_nth = 5
    """)
    cfg = load(p)
    assert cfg.patterns[0].sampler is not None
    assert cfg.patterns[0].sampler.every_nth == 5
