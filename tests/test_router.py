"""Tests for logpulse.router."""
from unittest.mock import MagicMock

import pytest

from logpulse.matcher import Alert
from logpulse.router import AlertRouter, RouteRule, RouterConfig


def _alert(label: str = "app", severity: str = "warning", line: str = "boom") -> Alert:
    return Alert(label=label, severity=severity, line=line, pattern=".*")


@pytest.fixture()
def notifiers():
    return {"slack": MagicMock(), "pagerduty": MagicMock(), "default": MagicMock()}


def test_matching_rule_dispatches_to_correct_notifier(notifiers):
    cfg = RouterConfig(
        rules=[RouteRule(notifier="pagerduty", severity="critical")],
        default_notifier="slack",
    )
    router = AlertRouter(cfg, notifiers)
    alert = _alert(severity="critical")
    assert router.route(alert) is True
    notifiers["pagerduty"].send.assert_called_once_with(alert)
    notifiers["slack"].send.assert_not_called()


def test_no_matching_rule_falls_back_to_default(notifiers):
    cfg = RouterConfig(
        rules=[RouteRule(notifier="pagerduty", severity="critical")],
        default_notifier="slack",
    )
    router = AlertRouter(cfg, notifiers)
    alert = _alert(severity="warning")
    assert router.route(alert) is True
    notifiers["slack"].send.assert_called_once_with(alert)
    notifiers["pagerduty"].send.assert_not_called()


def test_no_rule_no_default_drops_alert(notifiers):
    cfg = RouterConfig(rules=[], default_notifier=None)
    router = AlertRouter(cfg, notifiers)
    assert router.route(_alert()) is False
    assert router.dropped == 1
    assert router.routed == 0


def test_label_pattern_matches(notifiers):
    cfg = RouterConfig(
        rules=[RouteRule(notifier="slack", label_pattern="^db")],
    )
    router = AlertRouter(cfg, notifiers)
    assert router.route(_alert(label="db_errors")) is True
    notifiers["slack"].send.assert_called_once()


def test_label_pattern_no_match_uses_default(notifiers):
    cfg = RouterConfig(
        rules=[RouteRule(notifier="pagerduty", label_pattern="^db")],
        default_notifier="default",
    )
    router = AlertRouter(cfg, notifiers)
    assert router.route(_alert(label="web_errors")) is True
    notifiers["default"].send.assert_called_once()
    notifiers["pagerduty"].send.assert_not_called()


def test_first_matching_rule_wins(notifiers):
    cfg = RouterConfig(
        rules=[
            RouteRule(notifier="slack", severity="warning"),
            RouteRule(notifier="pagerduty", severity="warning"),
        ],
    )
    router = AlertRouter(cfg, notifiers)
    router.route(_alert(severity="warning"))
    notifiers["slack"].send.assert_called_once()
    notifiers["pagerduty"].send.assert_not_called()


def test_routed_counter_increments(notifiers):
    cfg = RouterConfig(default_notifier="default")
    router = AlertRouter(cfg, notifiers)
    router.route(_alert())
    router.route(_alert())
    assert router.routed == 2


def test_from_dict_creates_config():
    data = {
        "default_notifier": "slack",
        "rules": [
            {"notifier": "pagerduty", "severity": "critical", "label_pattern": "db.*"},
        ],
    }
    cfg = RouterConfig.from_dict(data)
    assert cfg.default_notifier == "slack"
    assert len(cfg.rules) == 1
    assert cfg.rules[0].notifier == "pagerduty"
    assert cfg.rules[0].severity == "critical"
