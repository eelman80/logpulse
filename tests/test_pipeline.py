"""Tests for logpulse.pipeline.Pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from logpulse.matcher import Alert, PatternMatcher
from logpulse.pipeline import Pipeline


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_log(tmp_path: Path) -> Path:
    p = tmp_path / "app.log"
    p.write_text("")  # create empty file
    return p


def _make_matcher(alerts: list[Alert]) -> PatternMatcher:
    matcher = MagicMock(spec=PatternMatcher)
    matcher.check.return_value = alerts
    return matcher


def _make_notifier() -> MagicMock:
    return MagicMock()


def _make_alert(label: str = "ERROR") -> Alert:
    return Alert(label=label, severity="high", line="ERROR something broke")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_run_once_no_new_lines(tmp_log: Path) -> None:
    """run_once returns 0 when there are no new lines."""
    pipeline = Pipeline(tmp_log, _make_matcher([]), _make_notifier())
    assert pipeline.run_once() == 0


def test_run_once_fires_alert_for_matching_line(tmp_log: Path) -> None:
    """run_once sends a notification for each alert returned by the matcher."""
    alert = _make_alert()
    notifier = _make_notifier()
    matcher = _make_matcher([alert])

    tmp_log.write_text("ERROR something broke\n")
    pipeline = Pipeline(tmp_log, matcher, notifier, source="myapp")

    count = pipeline.run_once()

    assert count == 1
    notifier.send.assert_called_once_with(alert, source="myapp")


def test_run_once_multiple_alerts(tmp_log: Path) -> None:
    """run_once counts all alerts across all matching lines."""
    alert = _make_alert()
    notifier = _make_notifier()
    matcher = _make_matcher([alert])

    tmp_log.write_text("ERROR one\nERROR two\n")
    pipeline = Pipeline(tmp_log, matcher, notifier)

    count = pipeline.run_once()
    assert count == 2
    assert notifier.send.call_count == 2


def test_run_once_notifier_exception_is_swallowed(tmp_log: Path) -> None:
    """run_once continues processing even if a notification fails."""
    alert = _make_alert()
    notifier = _make_notifier()
    notifier.send.side_effect = RuntimeError("webhook down")
    matcher = _make_matcher([alert])

    tmp_log.write_text("ERROR boom\n")
    pipeline = Pipeline(tmp_log, matcher, notifier)

    # Should not raise, but returns 0 because send raised
    count = pipeline.run_once()
    assert count == 0


def test_source_defaults_to_log_path(tmp_log: Path) -> None:
    """When source is not provided it defaults to the log file path string."""
    alert = _make_alert()
    notifier = _make_notifier()
    matcher = _make_matcher([alert])

    tmp_log.write_text("ERROR x\n")
    pipeline = Pipeline(tmp_log, matcher, notifier)

    pipeline.run_once()
    _, kwargs = notifier.send.call_args
    assert kwargs["source"] == str(tmp_log)


def test_stop_sets_running_false(tmp_log: Path) -> None:
    """stop() flips the internal flag so run() can exit."""
    pipeline = Pipeline(tmp_log, _make_matcher([]), _make_notifier())
    pipeline._running = True
    pipeline.stop()
    assert pipeline._running is False
