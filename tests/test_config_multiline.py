"""Tests for multiline config loading via AppConfig."""
import textwrap
import pytest
from pathlib import Path
from logpulse.config import load_config


@pytest.fixture
def toml_file(tmp_path):
    def _write(content: str) -> str:
        p = tmp_path / "cfg.toml"
        p.write_text(textwrap.dedent(content))
        return str(p)
    return _write


def test_multiline_defaults_when_section_absent(toml_file):
    path = toml_file("""
        log_path = "/var/log/app.log"
    """)
    cfg = load_config(path)
    assert cfg.multiline.enabled is True
    assert cfg.multiline.max_lines == 50


def test_multiline_enabled_false(toml_file):
    path = toml_file("""
        log_path = "/var/log/app.log"

        [multiline]
        enabled = false
    """)
    cfg = load_config(path)
    assert cfg.multiline.enabled is False


def test_multiline_custom_pattern(toml_file):
    path = toml_file("""
        log_path = "/var/log/app.log"

        [multiline]
        start_pattern = "^\\d{4}-"
        continuation_pattern = "^\\s+"
        max_lines = 20
    """)
    cfg = load_config(path)
    assert cfg.multiline.start_pattern == r"^\d{4}-"
    assert cfg.multiline.max_lines == 20


def test_multiline_flush_timeout_lines(toml_file):
    path = toml_file("""
        log_path = "/var/log/app.log"

        [multiline]
        flush_timeout_lines = 200
    """)
    cfg = load_config(path)
    assert cfg.multiline.flush_timeout_lines == 200
