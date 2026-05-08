"""Tests for logpulse.window_reporter."""
import pytest
from logpulse.window import WindowConfig, SlidingWindow
from logpulse.window_reporter import ReporterConfig, WindowReporter
from logpulse.matcher import Alert

NOW = 2_000.0


@pytest.fixture()
def collected():
    return []


@pytest.fixture()
def reporter(collected):
    win_cfg = WindowConfig(window_seconds=60, min_count=2)
    rep_cfg = ReporterConfig(report_interval=30, severity="warning")
    win = SlidingWindow(win_cfg)
    r = WindowReporter(win, rep_cfg, on_alert=collected.append)
    # set last_report so we control timing
    r._last_report = NOW - 100  # already overdue
    return r


def test_from_dict_defaults():
    c = ReporterConfig.from_dict({})
    assert c.report_interval == 60
    assert c.severity == "info"


def test_from_dict_custom():
    c = ReporterConfig.from_dict({"report_interval": 120, "severity": "critical"})
    assert c.report_interval == 120
    assert c.severity == "critical"


def test_force_report_returns_alerts(reporter, collected):
    reporter._window.record("err", NOW - 10)
    reporter._window.record("err", NOW - 5)
    alerts = reporter.force_report(now=NOW)
    assert len(alerts) == 1
    assert alerts[0].label == "err"


def test_force_report_calls_on_alert(reporter, collected):
    reporter._window.record("err", NOW - 10)
    reporter._window.record("err", NOW - 5)
    reporter.force_report(now=NOW)
    assert len(collected) == 1


def test_alert_severity_matches_config(reporter, collected):
    reporter._window.record("err", NOW - 10)
    reporter._window.record("err", NOW - 5)
    alerts = reporter.force_report(now=NOW)
    assert alerts[0].severity == "warning"


def test_alert_label_matches_window_label(reporter, collected):
    reporter._window.record("db_error", NOW - 10)
    reporter._window.record("db_error", NOW - 5)
    alerts = reporter.force_report(now=NOW)
    assert alerts[0].label == "db_error"


def test_no_qualifying_labels_yields_no_alerts(reporter, collected):
    # only 1 hit, min_count=2
    reporter._window.record("err", NOW - 5)
    alerts = reporter.force_report(now=NOW)
    assert alerts == []


def test_record_does_not_emit_before_interval(collected):
    win_cfg = WindowConfig(window_seconds=60, min_count=2)
    rep_cfg = ReporterConfig(report_interval=30, severity="info")
    win = SlidingWindow(win_cfg)
    r = WindowReporter(win, rep_cfg, on_alert=collected.append)
    r._last_report = NOW  # just reported
    r.record("err", "some line", ts=NOW + 1)
    r.record("err", "some line", ts=NOW + 2)
    # interval not elapsed, no alerts yet
    assert collected == []


def test_record_emits_after_interval(collected):
    win_cfg = WindowConfig(window_seconds=60, min_count=2)
    rep_cfg = ReporterConfig(report_interval=10, severity="info")
    win = SlidingWindow(win_cfg)
    r = WindowReporter(win, rep_cfg, on_alert=collected.append)
    r._last_report = NOW - 20  # overdue
    r.record("err", "line", ts=NOW)
    r.record("err", "line", ts=NOW + 0.1)
    # trigger via record at a time past interval
    r._window.record("err", NOW + 0.2)
    r._maybe_report(now=NOW + 0.3)
    assert len(collected) == 1
