"""Tests for logpulse.window (sliding-window aggregation)."""
import pytest
from logpulse.window import WindowConfig, SlidingWindow, WindowSummary


@pytest.fixture()
def cfg() -> WindowConfig:
    return WindowConfig(enabled=True, window_seconds=60, min_count=2)


@pytest.fixture()
def win(cfg: WindowConfig) -> SlidingWindow:
    return SlidingWindow(cfg)


NOW = 1_000.0


def test_from_dict_defaults():
    c = WindowConfig.from_dict({})
    assert c.enabled is True
    assert c.window_seconds == 60
    assert c.min_count == 3


def test_from_dict_custom_values():
    c = WindowConfig.from_dict({"window_seconds": 120, "min_count": 5, "enabled": False})
    assert c.window_seconds == 120
    assert c.min_count == 5
    assert c.enabled is False


def test_below_min_count_returns_none(win):
    win.record("err", NOW)
    # only 1 hit, min_count=2
    assert win.summary("err", NOW) is None


def test_at_min_count_returns_summary(win):
    win.record("err", NOW)
    win.record("err", NOW + 1)
    s = win.summary("err", NOW + 1)
    assert s is not None
    assert s.label == "err"
    assert s.count == 2


def test_old_entries_evicted(win):
    win.record("err", NOW - 120)  # outside 60-s window
    win.record("err", NOW)
    s = win.summary("err", NOW)
    # only 1 recent entry remains
    assert s is None


def test_different_labels_are_independent(win):
    win.record("err", NOW)
    win.record("err", NOW + 1)
    win.record("warn", NOW)
    assert win.summary("err", NOW + 1) is not None
    assert win.summary("warn", NOW) is None  # only 1 hit for warn


def test_rate_per_minute_calculation():
    s = WindowSummary(label="x", count=6, window_seconds=60,
                      oldest_ts=NOW, newest_ts=NOW + 30)
    # 6 hits over 30 s => 12/min
    assert s.rate_per_minute() == 12.0


def test_rate_per_minute_zero_span():
    s = WindowSummary(label="x", count=3, window_seconds=60,
                      oldest_ts=NOW, newest_ts=NOW)
    # span=0 => returns count as float
    assert s.rate_per_minute() == 3.0


def test_summary_str_contains_label_and_count(win):
    win.record("critical", NOW)
    win.record("critical", NOW + 5)
    s = win.summary("critical", NOW + 5)
    text = str(s)
    assert "critical" in text
    assert "2" in text


def test_all_summaries_returns_qualifying_labels(win):
    win.record("a", NOW)
    win.record("a", NOW + 1)
    win.record("b", NOW)  # only 1 hit
    summaries = win.all_summaries(NOW + 1)
    labels = {s.label for s in summaries}
    assert "a" in labels
    assert "b" not in labels


def test_reset_single_label(win):
    win.record("err", NOW)
    win.record("err", NOW + 1)
    win.reset("err")
    assert win.summary("err", NOW + 1) is None


def test_reset_all(win):
    win.record("a", NOW)
    win.record("a", NOW + 1)
    win.record("b", NOW)
    win.record("b", NOW + 1)
    win.reset()
    assert win.all_summaries(NOW + 1) == []
