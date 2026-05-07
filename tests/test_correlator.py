"""Tests for logpulse.correlator."""
import time
from typing import List, Tuple

import pytest

from logpulse.correlator import AlertCorrelator, CorrelatorConfig
from logpulse.matcher import Alert


def _alert(label: str = "err", severity: str = "critical", line: str = "boom") -> Alert:
    return Alert(label=label, severity=severity, line=line, pattern=".*")


@pytest.fixture()
def collected() -> List[Tuple[str, List[Alert]]]:
    return []


@pytest.fixture()
def cfg() -> CorrelatorConfig:
    return CorrelatorConfig(enabled=True, window_seconds=5.0, min_group_size=2)


def test_from_dict_defaults():
    c = CorrelatorConfig.from_dict({})
    assert c.enabled is False
    assert c.window_seconds == 60.0
    assert c.min_group_size == 2
    assert c.group_by == "label"


def test_from_dict_custom_values():
    c = CorrelatorConfig.from_dict(
        {"enabled": True, "window_seconds": 30.0, "min_group_size": 3, "group_by": "severity"}
    )
    assert c.enabled is True
    assert c.window_seconds == 30.0
    assert c.min_group_size == 3
    assert c.group_by == "severity"


def test_disabled_passes_through_immediately(collected, cfg):
    cfg.enabled = False
    t = 0.0
    cor = AlertCorrelator(cfg, lambda k, g: collected.append((k, g)), _now=lambda: t)
    cor.feed(_alert())
    assert len(collected) == 1


def test_alerts_within_window_are_buffered(collected, cfg):
    t = 0.0
    cor = AlertCorrelator(cfg, lambda k, g: collected.append((k, g)), _now=lambda: t)
    cor.feed(_alert("err"))
    cor.feed(_alert("err"))
    # window not yet expired
    assert len(collected) == 0


def test_flush_all_emits_buffered_group(collected, cfg):
    t = 0.0
    cor = AlertCorrelator(cfg, lambda k, g: collected.append((k, g)), _now=lambda: t)
    cor.feed(_alert("err"))
    cor.feed(_alert("err"))
    cor.flush_all()
    assert len(collected) == 1
    key, group = collected[0]
    assert key == "err"
    assert len(group) == 2


def test_group_below_min_size_is_dropped(collected, cfg):
    cfg.min_group_size = 3
    t = 0.0
    cor = AlertCorrelator(cfg, lambda k, g: collected.append((k, g)), _now=lambda: t)
    cor.feed(_alert("err"))
    cor.feed(_alert("err"))
    cor.flush_all()
    assert len(collected) == 0


def test_different_keys_are_independent(collected, cfg):
    t = 0.0
    cor = AlertCorrelator(cfg, lambda k, g: collected.append((k, g)), _now=lambda: t)
    cor.feed(_alert("err"))
    cor.feed(_alert("warn"))
    cor.feed(_alert("warn"))
    cor.flush_all()
    assert len(collected) == 1
    assert collected[0][0] == "warn"


def test_flush_expired_only_emits_old_buckets(collected, cfg):
    t = 0.0
    cor = AlertCorrelator(cfg, lambda k, g: collected.append((k, g)), _now=lambda: t)
    cor.feed(_alert("err"))
    cor.feed(_alert("err"))
    t = 6.0  # past the 5 s window
    cor.flush_expired()
    assert len(collected) == 1


def test_group_by_severity(collected):
    cfg = CorrelatorConfig(enabled=True, window_seconds=5.0, min_group_size=2, group_by="severity")
    t = 0.0
    cor = AlertCorrelator(cfg, lambda k, g: collected.append((k, g)), _now=lambda: t)
    cor.feed(_alert(label="a", severity="critical"))
    cor.feed(_alert(label="b", severity="critical"))
    cor.flush_all()
    assert len(collected) == 1
    assert collected[0][0] == "critical"
