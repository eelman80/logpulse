"""Tests for logpulse.sampler."""
import pytest

from logpulse.sampler import LineSampler, SamplerConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sampler() -> LineSampler:
    return LineSampler(SamplerConfig(), seed=42)


# ---------------------------------------------------------------------------
# SamplerConfig validation
# ---------------------------------------------------------------------------

def test_invalid_every_nth_raises() -> None:
    with pytest.raises(ValueError, match="every_nth"):
        SamplerConfig(every_nth=0)


def test_invalid_probability_raises() -> None:
    with pytest.raises(ValueError, match="probability"):
        SamplerConfig(probability=1.5)


# ---------------------------------------------------------------------------
# every_nth
# ---------------------------------------------------------------------------

def test_every_nth_one_allows_all(sampler: LineSampler) -> None:
    results = [sampler.allow("err") for _ in range(5)]
    assert all(results)


def test_every_nth_filters_correctly() -> None:
    s = LineSampler(SamplerConfig(every_nth=3), seed=0)
    results = [s.allow("err") for _ in range(9)]
    # only positions 3, 6, 9 (1-indexed) should be True
    assert results == [False, False, True, False, False, True, False, False, True]


def test_per_label_counters_are_independent() -> None:
    s = LineSampler(SamplerConfig(every_nth=2, per_label=True), seed=0)
    # label A: calls 1,2  -> False, True
    # label B: calls 1,2  -> False, True  (own counter)
    assert s.allow("A") is False
    assert s.allow("B") is False
    assert s.allow("A") is True
    assert s.allow("B") is True


def test_global_counter_shared_across_labels() -> None:
    s = LineSampler(SamplerConfig(every_nth=2, per_label=False), seed=0)
    # shared counter: A=1(F), B=2(T)
    assert s.allow("A") is False
    assert s.allow("B") is True


# ---------------------------------------------------------------------------
# probability
# ---------------------------------------------------------------------------

def test_probability_zero_blocks_all() -> None:
    s = LineSampler(SamplerConfig(probability=0.0), seed=7)
    assert all(s.allow("x") is False for _ in range(20))


def test_probability_one_allows_all() -> None:
    s = LineSampler(SamplerConfig(probability=1.0), seed=7)
    assert all(s.allow("x") is True for _ in range(20))


def test_probability_roughly_half() -> None:
    s = LineSampler(SamplerConfig(probability=0.5), seed=99)
    allowed = sum(s.allow("x") for _ in range(1000))
    assert 350 < allowed < 650, f"Expected ~500 allowed, got {allowed}"


# ---------------------------------------------------------------------------
# reset / seen
# ---------------------------------------------------------------------------

def test_seen_increments_on_each_call() -> None:
    s = LineSampler(SamplerConfig(), seed=0)
    for i in range(1, 6):
        s.allow("lbl")
        assert s.seen("lbl") == i


def test_reset_single_label() -> None:
    s = LineSampler(SamplerConfig(every_nth=3), seed=0)
    for _ in range(3):
        s.allow("A")
    s.reset("A")
    assert s.seen("A") == 0


def test_reset_all_labels() -> None:
    s = LineSampler(SamplerConfig(), seed=0)
    s.allow("A")
    s.allow("B")
    s.reset()
    assert s.seen("A") == 0
    assert s.seen("B") == 0
