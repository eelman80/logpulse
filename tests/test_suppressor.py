"""Tests for logpulse.suppressor."""
import pytest
from logpulse.suppressor import LineSuppressor, SuppressRule, SuppressorConfig


@pytest.fixture
def cfg() -> SuppressorConfig:
    return SuppressorConfig(
        rules=[
            SuppressRule(pattern=r"healthcheck", label="health"),
            SuppressRule(pattern=r"DEBUG", label="debug"),
        ],
        enabled=True,
    )


@pytest.fixture
def suppressor(cfg: SuppressorConfig) -> LineSuppressor:
    return LineSuppressor(cfg)


def test_non_matching_line_is_not_suppressed(suppressor):
    assert suppressor.should_suppress("ERROR something went wrong") is False


def test_matching_line_is_suppressed(suppressor):
    assert suppressor.should_suppress("GET /healthcheck 200") is True


def test_suppressed_count_increments(suppressor):
    suppressor.should_suppress("GET /healthcheck 200")
    suppressor.should_suppress("GET /healthcheck 200")
    assert suppressor.suppressed_count == 2


def test_last_matched_label_is_set(suppressor):
    suppressor.should_suppress("DEBUG verbose output")
    assert suppressor.last_matched_label == "debug"


def test_last_matched_label_none_when_no_match(suppressor):
    suppressor.should_suppress("INFO startup complete")
    assert suppressor.last_matched_label is None


def test_disabled_suppressor_allows_everything():
    cfg = SuppressorConfig(
        rules=[SuppressRule(pattern=r".*", label="all")],
        enabled=False,
    )
    s = LineSuppressor(cfg)
    assert s.should_suppress("anything at all") is False


def test_reset_stats_clears_count(suppressor):
    suppressor.should_suppress("GET /healthcheck 200")
    suppressor.reset_stats()
    assert suppressor.suppressed_count == 0
    assert suppressor.last_matched_label is None


def test_from_dict_creates_rules():
    data = {
        "enabled": True,
        "rules": [
            {"pattern": "TRACE", "label": "trace"},
            {"pattern": "heartbeat"},
        ],
    }
    cfg = SuppressorConfig.from_dict(data)
    assert len(cfg.rules) == 2
    assert cfg.rules[0].label == "trace"
    assert cfg.rules[1].label == "unnamed"


def test_from_dict_disabled():
    cfg = SuppressorConfig.from_dict({"enabled": False, "rules": []})
    assert cfg.enabled is False


def test_first_rule_wins(suppressor):
    # Line matches both health and debug — first rule should win
    line = "healthcheck DEBUG"
    suppressor.should_suppress(line)
    assert suppressor.last_matched_label == "health"
