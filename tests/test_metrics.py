"""Tests for logpulse.metrics."""
import time

import pytest

from logpulse.metrics import Metrics, MetricsSnapshot


@pytest.fixture()
def m() -> Metrics:
    return Metrics()


def test_initial_snapshot_is_zero(m: Metrics) -> None:
    s = m.snapshot()
    assert s.lines_processed == 0
    assert s.lines_matched == 0
    assert s.alerts_sent == 0
    assert s.alerts_suppressed == 0
    assert s.label_counts == {}


def test_inc_lines_processed(m: Metrics) -> None:
    m.inc_lines_processed(10)
    assert m.snapshot().lines_processed == 10


def test_inc_lines_matched(m: Metrics) -> None:
    m.inc_lines_matched(3)
    assert m.snapshot().lines_matched == 3


def test_inc_alerts_sent_updates_total_and_label(m: Metrics) -> None:
    m.inc_alerts_sent("error", 2)
    m.inc_alerts_sent("warn", 1)
    s = m.snapshot()
    assert s.alerts_sent == 3
    assert s.label_counts == {"error": 2, "warn": 1}


def test_inc_alerts_sent_same_label_accumulates(m: Metrics) -> None:
    m.inc_alerts_sent("error")
    m.inc_alerts_sent("error")
    s = m.snapshot()
    assert s.label_counts["error"] == 2


def test_inc_alerts_suppressed(m: Metrics) -> None:
    m.inc_alerts_suppressed(5)
    assert m.snapshot().alerts_suppressed == 5


def test_reset_clears_all_counters(m: Metrics) -> None:
    m.inc_lines_processed(100)
    m.inc_alerts_sent("x", 4)
    m.reset()
    s = m.snapshot()
    assert s.lines_processed == 0
    assert s.alerts_sent == 0
    assert s.label_counts == {}


def test_uptime_increases_over_time(m: Metrics) -> None:
    s1 = m.snapshot()
    time.sleep(0.05)
    s2 = m.snapshot()
    assert s2.uptime_seconds > s1.uptime_seconds


def test_reset_resets_uptime(m: Metrics) -> None:
    time.sleep(0.05)
    m.reset()
    assert m.snapshot().uptime_seconds < 0.05


def test_snapshot_returns_copy_of_label_counts(m: Metrics) -> None:
    m.inc_alerts_sent("info", 1)
    s = m.snapshot()
    s.label_counts["info"] = 999  # mutate the snapshot copy
    assert m.snapshot().label_counts["info"] == 1
