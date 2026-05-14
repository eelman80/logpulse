"""Tests for logpulse.debouncer."""
import pytest
from logpulse.debouncer import AlertDebouncer, DebounceConfig


@pytest.fixture()
def clock(monkeypatch):
    """Mutable monotonic clock."""
    t = [0.0]

    def _now():
        return t[0]

    def _advance(seconds):
        t[0] += seconds

    return _now, _advance


@pytest.fixture()
def cfg():
    return DebounceConfig(enabled=True, quiet_seconds=5.0, max_hold_seconds=30.0)


@pytest.fixture()
def deb(cfg, clock):
    now_fn, _ = clock
    return AlertDebouncer(cfg, clock=now_fn)


def test_disabled_passes_through_immediately():
    cfg = DebounceConfig(enabled=False)
    d = AlertDebouncer(cfg)
    assert d.feed("err", "payload") == "payload"


def test_first_event_is_held(deb):
    result = deb.feed("err", "payload")
    assert result is None


def test_repeated_event_still_held(deb, clock):
    _, advance = clock
    deb.feed("err", "first")
    advance(2.0)
    result = deb.feed("err", "second")
    assert result is None
    assert "err" in deb.pending_labels()


def test_drain_returns_nothing_before_quiet_period(deb, clock):
    _, advance = clock
    deb.feed("err", "payload")
    advance(3.0)
    assert deb.drain() == []


def test_drain_returns_payload_after_quiet_period(deb, clock):
    _, advance = clock
    deb.feed("err", "payload")
    advance(6.0)
    released = deb.drain()
    assert released == ["payload"]
    assert "err" not in deb.pending_labels()


def test_drain_uses_latest_payload(deb, clock):
    _, advance = clock
    deb.feed("err", "first")
    advance(2.0)
    deb.feed("err", "second")
    advance(6.0)
    released = deb.drain()
    assert released == ["second"]


def test_max_hold_forces_release(deb, clock):
    _, advance = clock
    deb.feed("err", "payload")
    # Keep refreshing so quiet period never elapses
    for _ in range(6):
        advance(4.9)
        deb.feed("err", "payload")
    advance(4.9)  # total > 30 s
    released = deb.drain()
    assert released == ["payload"]


def test_different_labels_are_independent(deb, clock):
    _, advance = clock
    deb.feed("warn", "w")
    deb.feed("err", "e")
    advance(6.0)
    released = deb.drain()
    assert len(released) == 2


def test_flush_releases_immediately(deb):
    deb.feed("err", "payload")
    result = deb.flush("err")
    assert result == "payload"
    assert "err" not in deb.pending_labels()


def test_flush_unknown_label_returns_none(deb):
    assert deb.flush("missing") is None


def test_from_dict_defaults():
    cfg = DebounceConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.quiet_seconds == 5.0
    assert cfg.max_hold_seconds == 30.0


def test_from_dict_custom_values():
    cfg = DebounceConfig.from_dict(
        {"enabled": True, "quiet_seconds": 10.0, "max_hold_seconds": 60.0}
    )
    assert cfg.enabled is True
    assert cfg.quiet_seconds == 10.0
    assert cfg.max_hold_seconds == 60.0
