"""Tests for logpulse.ratelimit."""
import pytest

from logpulse.ratelimit import RateLimitConfig, RateLimiter


@pytest.fixture()
def limiter() -> RateLimiter:
    """Rate limiter allowing 3 alerts per 60-second window."""
    return RateLimiter(RateLimitConfig(max_alerts=3, window_seconds=60.0))


def test_first_alert_is_allowed(limiter: RateLimiter) -> None:
    assert limiter.allow("error", now=0.0) is True


def test_allows_up_to_max(limiter: RateLimiter) -> None:
    for i in range(3):
        assert limiter.allow("error", now=float(i)) is True


def test_exceeding_max_is_rejected(limiter: RateLimiter) -> None:
    for i in range(3):
        limiter.allow("error", now=float(i))
    assert limiter.allow("error", now=3.0) is False


def test_different_labels_are_independent(limiter: RateLimiter) -> None:
    for i in range(3):
        limiter.allow("error", now=float(i))
    # "warn" has its own budget
    assert limiter.allow("warn", now=3.0) is True


def test_alert_allowed_after_window_expires(limiter: RateLimiter) -> None:
    for i in range(3):
        limiter.allow("error", now=float(i))
    # 61 seconds later the window has fully rolled over
    assert limiter.allow("error", now=61.0) is True


def test_partial_window_expiry(limiter: RateLimiter) -> None:
    """Only timestamps outside the window are evicted."""
    limiter.allow("error", now=0.0)   # will expire at t=60
    limiter.allow("error", now=30.0)  # will expire at t=90
    limiter.allow("error", now=50.0)  # will expire at t=110
    # At t=61 the first entry is gone → 2 remain → one slot free
    assert limiter.allow("error", now=61.0) is True
    # Now 3 entries remain (30, 50, 61) → next is rejected
    assert limiter.allow("error", now=61.5) is False


def test_remaining_decrements(limiter: RateLimiter) -> None:
    assert limiter.remaining("error", now=0.0) == 3
    limiter.allow("error", now=0.0)
    assert limiter.remaining("error", now=0.0) == 2


def test_remaining_resets_after_window(limiter: RateLimiter) -> None:
    for i in range(3):
        limiter.allow("error", now=float(i))
    assert limiter.remaining("error", now=0.0) == 0
    assert limiter.remaining("error", now=61.0) == 3


def test_reset_single_label(limiter: RateLimiter) -> None:
    limiter.allow("error", now=0.0)
    limiter.reset("error")
    assert limiter.remaining("error", now=0.0) == 3


def test_reset_all_labels(limiter: RateLimiter) -> None:
    limiter.allow("error", now=0.0)
    limiter.allow("warn", now=0.0)
    limiter.reset()
    assert limiter.remaining("error", now=0.0) == 3
    assert limiter.remaining("warn", now=0.0) == 3
