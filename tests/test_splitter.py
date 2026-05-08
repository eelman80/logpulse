"""Tests for logpulse.splitter."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from logpulse.matcher import Alert
from logpulse.splitter import AlertSplitter, SplitterConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _alert(label: str = "test", line: str = "some log line") -> Alert:
    return Alert(label=label, line=line, severity="warning")


@pytest.fixture()
def splitter() -> AlertSplitter:
    return AlertSplitter()


# ---------------------------------------------------------------------------
# SplitterConfig
# ---------------------------------------------------------------------------

def test_from_dict_defaults() -> None:
    cfg = SplitterConfig.from_dict({})
    assert cfg.enabled is True
    assert cfg.stop_on_error is False


def test_from_dict_custom_values() -> None:
    cfg = SplitterConfig.from_dict({"enabled": False, "stop_on_error": True})
    assert cfg.enabled is False
    assert cfg.stop_on_error is True


# ---------------------------------------------------------------------------
# AlertSplitter
# ---------------------------------------------------------------------------

def test_empty_splitter_returns_zero(splitter: AlertSplitter) -> None:
    assert splitter.dispatch(_alert()) == 0


def test_single_handler_is_called(splitter: AlertSplitter) -> None:
    handler = MagicMock()
    splitter.add_handler(handler)
    alert = _alert()
    result = splitter.dispatch(alert)
    handler.assert_called_once_with(alert)
    assert result == 1


def test_multiple_handlers_all_called(splitter: AlertSplitter) -> None:
    h1, h2, h3 = MagicMock(), MagicMock(), MagicMock()
    for h in (h1, h2, h3):
        splitter.add_handler(h)
    alert = _alert()
    result = splitter.dispatch(alert)
    for h in (h1, h2, h3):
        h.assert_called_once_with(alert)
    assert result == 3


def test_disabled_splitter_skips_all_handlers(splitter: AlertSplitter) -> None:
    cfg = SplitterConfig(enabled=False)
    sp = AlertSplitter(config=cfg)
    handler = MagicMock()
    sp.add_handler(handler)
    result = sp.dispatch(_alert())
    handler.assert_not_called()
    assert result == 0


def test_handler_error_is_swallowed_by_default(splitter: AlertSplitter) -> None:
    bad = MagicMock(side_effect=RuntimeError("boom"))
    good = MagicMock()
    splitter.add_handler(bad)
    splitter.add_handler(good)
    result = splitter.dispatch(_alert())
    good.assert_called_once()
    assert result == 1
    assert splitter.error_count == 1


def test_stop_on_error_raises(splitter: AlertSplitter) -> None:
    cfg = SplitterConfig(stop_on_error=True)
    sp = AlertSplitter(config=cfg)
    sp.add_handler(MagicMock(side_effect=ValueError("fail")))
    sp.add_handler(MagicMock())
    with pytest.raises(ValueError, match="fail"):
        sp.dispatch(_alert())


def test_handler_count(splitter: AlertSplitter) -> None:
    assert splitter.handler_count == 0
    splitter.add_handler(MagicMock())
    splitter.add_handler(MagicMock())
    assert splitter.handler_count == 2


def test_clear_removes_handlers_and_resets_errors(splitter: AlertSplitter) -> None:
    bad = MagicMock(side_effect=RuntimeError)
    splitter.add_handler(bad)
    splitter.dispatch(_alert())  # swallowed error
    assert splitter.error_count == 1
    splitter.clear()
    assert splitter.handler_count == 0
    assert splitter.error_count == 0
