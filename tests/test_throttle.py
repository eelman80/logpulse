"""Tests for logpulse.throttle."""

from __future__ import annotations

import time

import pytest

from logpulse.throttle import AlertThrottle, ThrottleConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _throttle(cooldown: float = 60.0) -> AlertThrottle:
    return AlertThrottle(ThrottleConfig(cooldown_seconds=cooldown))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_first_alert_is_allowed():
    t = _throttle()
    assert t.allow("ERROR") is True


def test_immediate_repeat_is_suppressed():
    t = _throttle(cooldown=60.0)
    t.allow("ERROR")  # first — allowed
    assert t.allow("ERROR") is False


def test_different_labels_are_independent():
    t = _throttle(cooldown=60.0)
    t.allow("ERROR")
    # A different label should still be allowed
    assert t.allow("WARN") is True


def test_alert_allowed_after_cooldown(monkeypatch):
    """Simulate time passing beyond the cooldown window."""
    base = 1_000.0
    monkeypatch.setattr(time, "monotonic", lambda: base)

    t = _throttle(cooldown=10.0)
    t.allow("ERROR")  # record base time

    # Advance clock past the cooldown
    monkeypatch.setattr(time, "monotonic", lambda: base + 11.0)
    assert t.allow("ERROR") is True


def test_alert_still_suppressed_within_cooldown(monkeypatch):
    base = 1_000.0
    monkeypatch.setattr(time, "monotonic", lambda: base)

    t = _throttle(cooldown=10.0)
    t.allow("ERROR")

    # Advance clock but stay within the cooldown
    monkeypatch.setattr(time, "monotonic", lambda: base + 5.0)
    assert t.allow("ERROR") is False


def test_reset_clears_single_label():
    t = _throttle(cooldown=60.0)
    t.allow("ERROR")
    t.reset("ERROR")
    assert t.allow("ERROR") is True


def test_reset_all_clears_everything():
    t = _throttle(cooldown=60.0)
    t.allow("ERROR")
    t.allow("WARN")
    t.reset_all()
    assert t.allow("ERROR") is True
    assert t.allow("WARN") is True


def test_cooldown_seconds_property():
    t = _throttle(cooldown=42.0)
    assert t.cooldown_seconds == 42.0
