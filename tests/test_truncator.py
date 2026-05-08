"""Tests for logpulse.truncator."""
import pytest
from logpulse.truncator import LineTruncator, TruncatorConfig, TruncationResult


@pytest.fixture()
def truncator() -> LineTruncator:
    cfg = TruncatorConfig(enabled=True, max_length=20, ellipsis="...")
    return LineTruncator(cfg)


def test_short_line_is_unchanged(truncator: LineTruncator) -> None:
    result = truncator.process("hello world")
    assert result.line == "hello world"
    assert result.truncated is False
    assert result.original_length == len("hello world")


def test_exact_length_line_is_unchanged(truncator: LineTruncator) -> None:
    line = "a" * 20
    result = truncator.process(line)
    assert result.truncated is False
    assert result.line == line


def test_long_line_is_truncated(truncator: LineTruncator) -> None:
    line = "a" * 30
    result = truncator.process(line)
    assert result.truncated is True
    assert len(result.line) == 20
    assert result.line.endswith("...")
    assert result.original_length == 30


def test_truncated_count_increments(truncator: LineTruncator) -> None:
    truncator.process("a" * 30)
    truncator.process("b" * 25)
    truncator.process("short")
    assert truncator.truncated_count == 2


def test_reset_stats(truncator: LineTruncator) -> None:
    truncator.process("a" * 30)
    assert truncator.truncated_count == 1
    truncator.reset_stats()
    assert truncator.truncated_count == 0


def test_disabled_truncator_passes_long_line() -> None:
    cfg = TruncatorConfig(enabled=False, max_length=5)
    t = LineTruncator(cfg)
    line = "this is way too long"
    result = t.process(line)
    assert result.line == line
    assert result.truncated is False


def test_from_dict_defaults() -> None:
    cfg = TruncatorConfig.from_dict({})
    assert cfg.enabled is True
    assert cfg.max_length == 4096
    assert cfg.ellipsis == "..."
    assert cfg.count_bytes is False


def test_from_dict_custom_values() -> None:
    cfg = TruncatorConfig.from_dict(
        {"enabled": False, "max_length": 512, "ellipsis": "[TRUNC]", "count_bytes": True}
    )
    assert cfg.enabled is False
    assert cfg.max_length == 512
    assert cfg.ellipsis == "[TRUNC]"
    assert cfg.count_bytes is True


def test_byte_mode_truncates_correctly() -> None:
    cfg = TruncatorConfig(enabled=True, max_length=10, ellipsis="..", count_bytes=True)
    t = LineTruncator(cfg)
    line = "abcdefghijklmno"  # 15 bytes ASCII
    result = t.process(line)
    assert result.truncated is True
    assert len(result.line.encode("utf-8")) <= 10
    assert result.line.endswith("..")


def test_byte_mode_short_line_unchanged() -> None:
    cfg = TruncatorConfig(enabled=True, max_length=100, ellipsis="...", count_bytes=True)
    t = LineTruncator(cfg)
    line = "short line"
    result = t.process(line)
    assert result.truncated is False
    assert result.line == line
