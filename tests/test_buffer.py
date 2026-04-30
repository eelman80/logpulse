"""Tests for logpulse.buffer.ContextBuffer."""
import pytest
from logpulse.buffer import BufferConfig, ContextBuffer


@pytest.fixture()
def buf() -> ContextBuffer:
    return ContextBuffer(BufferConfig(before=2, after=2))


def _feed_all(buf: ContextBuffer, lines, matched_indices):
    """Feed lines into buf; matched=True for indices in matched_indices."""
    results = []
    for i, line in enumerate(lines):
        results.extend(buf.feed(line, matched=(i in matched_indices)))
    results.extend(buf.flush())
    return results


def test_no_match_yields_nothing(buf):
    lines = ["a", "b", "c"]
    results = _feed_all(buf, lines, matched_indices=set())
    assert results == []


def test_match_at_start_has_empty_before(buf):
    lines = ["match", "after1", "after2", "after3"]
    results = _feed_all(buf, lines, matched_indices={0})
    assert len(results) == 1
    before, matched, after = results[0]
    assert matched == "match"
    assert before == []
    assert after == ["after1", "after2"]


def test_match_in_middle_captures_before_and_after(buf):
    lines = ["pre1", "pre2", "pre3", "MATCH", "post1", "post2", "post3"]
    results = _feed_all(buf, lines, matched_indices={3})
    assert len(results) == 1
    before, matched, after = results[0]
    assert matched == "MATCH"
    assert before == ["pre2", "pre3"]
    assert after == ["post1", "post2"]


def test_match_at_end_flushes_partial_after():
    buf = ContextBuffer(BufferConfig(before=1, after=3))
    lines = ["pre", "MATCH", "only_after"]
    results = _feed_all(buf, lines, matched_indices={1})
    assert len(results) == 1
    before, matched, after = results[0]
    assert matched == "MATCH"
    assert after == ["only_after"]


def test_zero_after_config():
    buf = ContextBuffer(BufferConfig(before=2, after=0))
    lines = ["a", "b", "MATCH", "c"]
    results = _feed_all(buf, lines, matched_indices={2})
    assert len(results) == 1
    before, matched, after = results[0]
    assert matched == "MATCH"
    assert after == []


def test_multiple_matches_independent(buf):
    lines = ["x", "MATCH1", "between", "MATCH2", "y", "z"]
    results = _feed_all(buf, lines, matched_indices={1, 3})
    assert len(results) == 2
    _, m1, _ = results[0]
    _, m2, _ = results[1]
    assert m1 == "MATCH1"
    assert m2 == "MATCH2"


def test_reset_clears_state(buf):
    buf.feed("pre", matched=False)
    buf.feed("MATCH", matched=True)
    buf.reset()
    # After reset, flush should return nothing
    assert buf.flush() == []
    # And window should be empty (new match at start has no before)
    results = []
    results.extend(buf.feed("NEW_MATCH", matched=True))
    results.extend(buf.feed("a", matched=False))
    results.extend(buf.feed("b", matched=False))
    results.extend(buf.flush())
    assert len(results) == 1
    before, _, _ = results[0]
    assert before == []
