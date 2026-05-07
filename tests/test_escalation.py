"""Tests for logpulse.escalation."""
import pytest
from logpulse.escalation import AlertEscalator, EscalationConfig


@pytest.fixture
def cfg() -> EscalationConfig:
    return EscalationConfig(threshold=3, window_seconds=60.0, escalated_severity="critical")


@pytest.fixture
def esc(cfg: EscalationConfig) -> AlertEscalator:
    return AlertEscalator(cfg)


# ---------------------------------------------------------------------------
# from_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    c = EscalationConfig.from_dict({})
    assert c.threshold == 5
    assert c.window_seconds == 60.0
    assert c.escalated_severity == "critical"
    assert c.enabled is True


def test_from_dict_custom_values():
    c = EscalationConfig.from_dict({"threshold": 10, "window_seconds": 30, "escalated_severity": "page"})
    assert c.threshold == 10
    assert c.window_seconds == 30.0
    assert c.escalated_severity == "page"


# ---------------------------------------------------------------------------
# record / severity escalation
# ---------------------------------------------------------------------------

def test_below_threshold_returns_original_severity(esc: AlertEscalator):
    result = esc.record("db.error", "warning", _now=0.0)
    assert result == "warning"
    result = esc.record("db.error", "warning", _now=1.0)
    assert result == "warning"


def test_at_threshold_returns_escalated_severity(esc: AlertEscalator):
    for i in range(2):
        esc.record("db.error", "warning", _now=float(i))
    result = esc.record("db.error", "warning", _now=3.0)
    assert result == "critical"


def test_different_labels_are_independent(esc: AlertEscalator):
    for i in range(3):
        esc.record("label.a", "info", _now=float(i))
    result = esc.record("label.b", "info", _now=0.0)
    assert result == "info"


def test_hits_outside_window_are_pruned(esc: AlertEscalator):
    # Two hits far in the past
    esc.record("old", "warning", _now=0.0)
    esc.record("old", "warning", _now=1.0)
    # Two hits now (window=60s, so t=0,1 are outside when now=100)
    esc.record("old", "warning", _now=100.0)
    result = esc.record("old", "warning", _now=101.0)
    # Only 2 hits in window — below threshold of 3
    assert result == "warning"


# ---------------------------------------------------------------------------
# is_escalated / reset
# ---------------------------------------------------------------------------

def test_is_escalated_true_after_threshold(esc: AlertEscalator):
    for i in range(3):
        esc.record("x", "info", _now=float(i))
    assert esc.is_escalated("x") is True


def test_is_escalated_false_for_unknown_label(esc: AlertEscalator):
    assert esc.is_escalated("nope") is False


def test_reset_clears_state(esc: AlertEscalator):
    for i in range(3):
        esc.record("y", "info", _now=float(i))
    esc.reset("y")
    assert esc.is_escalated("y") is False
    assert "y" not in esc.snapshot()


# ---------------------------------------------------------------------------
# disabled mode
# ---------------------------------------------------------------------------

def test_disabled_always_returns_original_severity():
    cfg = EscalationConfig(threshold=1, window_seconds=60.0, enabled=False)
    esc = AlertEscalator(cfg)
    result = esc.record("z", "warning", _now=0.0)
    assert result == "warning"


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------

def test_snapshot_reflects_hit_counts(esc: AlertEscalator):
    esc.record("a", "info", _now=0.0)
    esc.record("a", "info", _now=1.0)
    snap = esc.snapshot()
    assert snap["a"] == (2, False)
