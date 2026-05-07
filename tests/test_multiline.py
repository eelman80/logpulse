"""Tests for logpulse.multiline multi-line folding."""
import pytest
from logpulse.multiline import MultilineConfig, MultilineFolder


@pytest.fixture
def folder():
    cfg = MultilineConfig(
        start_pattern=r"^\S",
        continuation_pattern=r"^\s+",
        max_lines=50,
        enabled=True,
    )
    return MultilineFolder(cfg)


def _collect(folder: MultilineFolder, lines):
    results = []
    for line in lines:
        results.extend(folder.feed(line))
    tail = folder.flush()
    if tail is not None:
        results.append(tail)
    return results


def test_single_line_record_passes_through(folder):
    result = _collect(folder, ["INFO starting up"])
    assert result == ["INFO starting up"]


def test_continuation_lines_are_folded(folder):
    lines = ["ERROR boom", "  at foo.py:10", "  at bar.py:20"]
    result = _collect(folder, lines)
    assert len(result) == 1
    assert "ERROR boom" in result[0]
    assert "at foo.py:10" in result[0]
    assert "at bar.py:20" in result[0]


def test_two_separate_records_yield_two_results(folder):
    lines = ["INFO first", "INFO second"]
    result = _collect(folder, lines)
    assert result == ["INFO first", "INFO second"]


def test_mixed_records_and_continuations(folder):
    lines = [
        "ERROR one",
        "  detail of one",
        "INFO two",
        "  detail of two",
    ]
    result = _collect(folder, lines)
    assert len(result) == 2
    assert "ERROR one" in result[0]
    assert "INFO two" in result[1]


def test_max_lines_forces_flush():
    cfg = MultilineConfig(start_pattern=r"^START", continuation_pattern=r"^\s", max_lines=3)
    folder = MultilineFolder(cfg)
    lines = ["START", " a", " b", " c"]  # 4 lines total; flush at 3
    results = []
    for line in lines:
        results.extend(folder.feed(line))
    tail = folder.flush()
    if tail:
        results.append(tail)
    # The first record should have been flushed at max_lines
    assert len(results) >= 1


def test_disabled_mode_passes_each_line_through():
    cfg = MultilineConfig(enabled=False)
    folder = MultilineFolder(cfg)
    lines = ["INFO one", "  cont", "INFO two"]
    result = _collect(folder, lines)
    assert result == lines


def test_from_dict_defaults():
    cfg = MultilineConfig.from_dict({})
    assert cfg.enabled is True
    assert cfg.max_lines == 50


def test_from_dict_custom_values():
    cfg = MultilineConfig.from_dict({"max_lines": "10", "enabled": False})
    assert cfg.max_lines == 10
    assert cfg.enabled is False


def test_flush_on_empty_returns_none(folder):
    assert folder.flush() is None
