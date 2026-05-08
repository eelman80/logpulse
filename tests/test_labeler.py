"""Tests for logpulse.labeler."""
import pytest
from logpulse.labeler import LabelRule, LabelerConfig, LineLabeler
import re


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def cfg() -> LabelerConfig:
    return LabelerConfig.from_dict({
        "enabled": True,
        "rules": [
            {
                "name": "severity",
                "pattern": r"(?P<level>ERROR|WARN|INFO)",
                "source": "app",
            },
            {
                "name": "request_id",
                "pattern": r"req_id=(?P<request_id>[\w-]+)",
            },
        ],
    })


@pytest.fixture()
def labeler(cfg: LabelerConfig) -> LineLabeler:
    return LineLabeler(cfg)


# ---------------------------------------------------------------------------
# LabelRule.apply
# ---------------------------------------------------------------------------

def test_label_rule_returns_none_on_no_match():
    rule = LabelRule(name="r", pattern=re.compile(r"NOPE"), labels={})
    assert rule.apply("hello world") is None


def test_label_rule_returns_static_labels_on_match():
    rule = LabelRule(name="r", pattern=re.compile(r"ERROR"), labels={"env": "prod"})
    result = rule.apply("ERROR something bad")
    assert result == {"env": "prod"}


def test_label_rule_captures_named_groups():
    rule = LabelRule(
        name="r",
        pattern=re.compile(r"(?P<level>ERROR|WARN)"),
        labels={"source": "app"},
    )
    result = rule.apply("WARN disk full")
    assert result == {"source": "app", "level": "WARN"}


# ---------------------------------------------------------------------------
# LabelerConfig.from_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    cfg = LabelerConfig.from_dict({})
    assert cfg.enabled is True
    assert cfg.rules == []


def test_from_dict_enabled_false():
    cfg = LabelerConfig.from_dict({"enabled": False})
    assert cfg.enabled is False


def test_from_dict_creates_rules(cfg: LabelerConfig):
    assert len(cfg.rules) == 2
    assert cfg.rules[0].name == "severity"
    assert cfg.rules[1].name == "request_id"


# ---------------------------------------------------------------------------
# LineLabeler.label
# ---------------------------------------------------------------------------

def test_no_match_returns_empty(labeler: LineLabeler):
    assert labeler.label("nothing interesting here") == {}


def test_single_rule_match(labeler: LineLabeler):
    labels = labeler.label("2024-01-01 ERROR something exploded")
    assert labels["level"] == "ERROR"
    assert labels["source"] == "app"


def test_multiple_rules_merged(labeler: LineLabeler):
    labels = labeler.label("ERROR req_id=abc-123 handler failed")
    assert labels["level"] == "ERROR"
    assert labels["request_id"] == "abc-123"


def test_disabled_labeler_returns_empty(cfg: LabelerConfig):
    cfg.enabled = False
    labeler = LineLabeler(cfg)
    labels = labeler.label("ERROR req_id=abc-123 handler failed")
    assert labels == {}
