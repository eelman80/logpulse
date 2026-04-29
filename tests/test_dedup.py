"""Tests for logpulse.dedup.LineDeduplicator."""

from __future__ import annotations

import time

import pytest

from logpulse.dedup import DedupConfig, LineDeduplicator


@pytest.fixture()
def dedup() -> LineDeduplicator:
    return LineDeduplicator(DedupConfig(window_seconds=1.0))


def test_first_occurrence_is_not_duplicate(dedup: LineDeduplicator) -> None:
    assert dedup.is_duplicate("ERROR something went wrong") is False


def test_immediate_repeat_is_duplicate(dedup: LineDeduplicator) -> None:
    line = "ERROR something went wrong"
    dedup.is_duplicate(line)
    assert dedup.is_duplicate(line) is True


def test_different_lines_are_independent(dedup: LineDeduplicator) -> None:
    assert dedup.is_duplicate("line one") is False
    assert dedup.is_duplicate("line two") is False


def test_seen_count_increments(dedup: LineDeduplicator) -> None:
    line = "WARN disk full"
    dedup.is_duplicate(line)
    dedup.is_duplicate(line)
    dedup.is_duplicate(line)
    assert dedup.seen_count(line) == 3


def test_seen_count_unknown_line_is_zero(dedup: LineDeduplicator) -> None:
    assert dedup.seen_count("never seen") == 0


def test_line_allowed_after_window_expires(dedup: LineDeduplicator) -> None:
    cfg = DedupConfig(window_seconds=0.05)
    d = LineDeduplicator(cfg)
    line = "CRITICAL db down"
    d.is_duplicate(line)  # first — not duplicate
    time.sleep(0.1)
    assert d.is_duplicate(line) is False  # window expired → treated as new


def test_reset_clears_cache(dedup: LineDeduplicator) -> None:
    line = "INFO startup"
    dedup.is_duplicate(line)
    dedup.reset()
    assert dedup.is_duplicate(line) is False


def test_cache_trim_on_overflow() -> None:
    cfg = DedupConfig(window_seconds=60.0, max_cache_size=10)
    d = LineDeduplicator(cfg)
    for i in range(12):
        d.is_duplicate(f"unique line {i}")
    # After trimming, cache should be well below the original max
    assert len(d._cache) <= cfg.max_cache_size


def test_whitespace_differences_are_distinct(dedup: LineDeduplicator) -> None:
    assert dedup.is_duplicate("ERROR foo") is False
    assert dedup.is_duplicate("ERROR  foo") is False  # extra space
