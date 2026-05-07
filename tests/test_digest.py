"""Tests for logpulse.digest."""
from __future__ import annotations

import time
from typing import List
from unittest.mock import MagicMock

import pytest

from logpulse.digest import AlertDigest, DigestConfig
from logpulse.matcher import Alert


def _make_alert(label: str = "test", line: str = "error") -> Alert:
    pattern = MagicMock()
    pattern.label = label
    pattern.severity = "error"
    return Alert(pattern=pattern, line=line, source="app.log")


@pytest.fixture()
def collected() -> List[List[Alert]]:
    return []


@pytest.fixture()
def cfg() -> DigestConfig:
    return DigestConfig(enabled=True, interval_seconds=0.1, max_entries=10)


@pytest.fixture()
def digest(cfg, collected):
    d = AlertDigest(cfg, flush_callback=lambda batch: collected.append(batch))
    yield d
    d.stop()


# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    cfg = DigestConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.interval_seconds == 60.0
    assert cfg.max_entries == 100


def test_from_dict_custom():
    cfg = DigestConfig.from_dict({"enabled": True, "interval_seconds": 30, "max_entries": 50})
    assert cfg.enabled is True
    assert cfg.interval_seconds == 30.0
    assert cfg.max_entries == 50


def test_pending_count_increments(digest):
    digest.add(_make_alert())
    digest.add(_make_alert())
    assert digest.pending_count() == 2


def test_manual_flush_delivers_batch(digest, collected):
    digest.add(_make_alert("a"))
    digest.add(_make_alert("b"))
    digest.flush()
    assert len(collected) == 1
    assert len(collected[0]) == 2


def test_flush_clears_pending(digest):
    digest.add(_make_alert())
    digest.flush()
    assert digest.pending_count() == 0


def test_flush_empty_does_not_call_callback(collected):
    cfg = DigestConfig(enabled=True, interval_seconds=60.0)
    d = AlertDigest(cfg, flush_callback=lambda b: collected.append(b))
    d.flush()
    assert collected == []
    d.stop()


def test_timer_fires_automatically(collected):
    cfg = DigestConfig(enabled=True, interval_seconds=0.05)
    d = AlertDigest(cfg, flush_callback=lambda b: collected.append(b))
    d.add(_make_alert())
    time.sleep(0.2)
    d.stop()
    assert len(collected) >= 1
    assert any(len(b) == 1 for b in collected)


def test_max_entries_cap(digest):
    cfg = DigestConfig(enabled=True, interval_seconds=60.0, max_entries=3)
    collected_local: list = []
    d = AlertDigest(cfg, flush_callback=lambda b: collected_local.append(b))
    for _ in range(10):
        d.add(_make_alert())
    assert d.pending_count() == 3
    d.stop()


def test_stop_prevents_timer_flush(collected):
    cfg = DigestConfig(enabled=True, interval_seconds=0.05)
    d = AlertDigest(cfg, flush_callback=lambda b: collected.append(b))
    d.add(_make_alert())
    d.stop()
    time.sleep(0.15)
    assert collected == []
