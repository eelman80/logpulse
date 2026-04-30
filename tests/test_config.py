"""Tests for logpulse.config (including sampler section)."""
from __future__ import annotations

from pathlib import Path

import pytest

from logpulse.config import load


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def toml_file(tmp_path: Path):
    def _write(content: str) -> Path:
        p = tmp_path / "cfg.toml"
        p.write_text(content, encoding="utf-8")
        return p
    return _write


MINIMAL = """
log_path = "/var/log/app.log"
[notifier]
url = "https://hooks.example.com/abc"
"""


# ---------------------------------------------------------------------------
# Existing tests (kept for regression)
# ---------------------------------------------------------------------------

def test_load_minimal(toml_file) -> None:
    cfg = load(toml_file(MINIMAL))
    assert str(cfg.log_path) == "/var/log/app.log"
    assert cfg.notifier.url == "https://hooks.example.com/abc"
    assert cfg.patterns == []


def test_load_missing_log_path_raises(toml_file) -> None:
    with pytest.raises(KeyError, match="log_path"):
        load(toml_file("[notifier]\nurl = 'http://x'\n"))


def test_load_patterns(toml_file) -> None:
    content = MINIMAL + """
[[patterns]]
label = "error"
regex = "ERROR"
severity = "critical"
"""
    cfg = load(toml_file(content))
    assert len(cfg.patterns) == 1
    assert cfg.patterns[0].label == "error"
    assert cfg.patterns[0].severity == "critical"


# ---------------------------------------------------------------------------
# Sampler section
# ---------------------------------------------------------------------------

def test_load_sampler_defaults(toml_file) -> None:
    cfg = load(toml_file(MINIMAL))
    assert cfg.sampler.every_nth == 1
    assert cfg.sampler.probability == 1.0
    assert cfg.sampler.per_label is True


def test_load_sampler_custom(toml_file) -> None:
    content = MINIMAL + """
[sampler]
every_nth = 5
probability = 0.25
per_label = false
"""
    cfg = load(toml_file(content))
    assert cfg.sampler.every_nth == 5
    assert cfg.sampler.probability == pytest.approx(0.25)
    assert cfg.sampler.per_label is False


def test_load_pattern_level_sampler_fields(toml_file) -> None:
    """Per-pattern every_nth / probability are stored on PatternConfig."""
    content = MINIMAL + """
[[patterns]]
label = "warn"
regex = "WARN"
every_nth = 10
probability = 0.5
"""
    cfg = load(toml_file(content))
    p = cfg.patterns[0]
    assert p.every_nth == 10
    assert p.probability == pytest.approx(0.5)


def test_load_notifier_missing_url_raises(toml_file) -> None:
    content = "log_path = '/tmp/x.log'\n[notifier]\ntimeout = 5\n"
    with pytest.raises(KeyError, match="notifier.url"):
        load(toml_file(content))
