"""Tests for logpulse.transformer."""
import pytest
from logpulse.transformer import TransformRule, TransformerConfig, LineTransformer


# ---------------------------------------------------------------------------
# TransformRule
# ---------------------------------------------------------------------------

def test_rule_replaces_match():
    rule = TransformRule(pattern=r"\d+", replacement="NUM")
    assert rule.apply("error 42 on line 7") == "error NUM on line NUM"


def test_rule_no_match_returns_original():
    rule = TransformRule(pattern=r"MISSING", replacement="X")
    assert rule.apply("nothing here") == "nothing here"


def test_rule_empty_replacement_removes_match():
    rule = TransformRule(pattern=r"\s+", replacement="")
    assert rule.apply("hello world") == "helloworld"


# ---------------------------------------------------------------------------
# TransformerConfig.from_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    cfg = TransformerConfig.from_dict({})
    assert cfg.enabled is True
    assert cfg.rules == []


def test_from_dict_disabled():
    cfg = TransformerConfig.from_dict({"enabled": False})
    assert cfg.enabled is False


def test_from_dict_creates_rules():
    cfg = TransformerConfig.from_dict({
        "rules": [
            {"pattern": r"\d+", "replacement": "NUM", "label": "digits"},
            {"pattern": r"ERROR", "replacement": "ERR"},
        ]
    })
    assert len(cfg.rules) == 2
    assert cfg.rules[0].label == "digits"
    assert cfg.rules[1].label == ""


# ---------------------------------------------------------------------------
# LineTransformer
# ---------------------------------------------------------------------------

@pytest.fixture()
def transformer():
    cfg = TransformerConfig.from_dict({
        "rules": [
            {"pattern": r"\d+", "replacement": "NUM"},
            {"pattern": r"ERROR", "replacement": "ERR"},
        ]
    })
    return LineTransformer(cfg)


def test_transform_applies_all_rules(transformer):
    result = transformer.transform("ERROR on line 99")
    assert result == "ERR on line NUM"


def test_transform_count_increments(transformer):
    transformer.transform("ERROR 1")
    transformer.transform("no match here")
    transformer.transform("line 2")
    # first call: 2 rules match (ERROR → ERR, 1 → NUM)
    # third call: 1 rule matches (2 → NUM)
    assert transformer.transform_count == 3


def test_transform_disabled_returns_original():
    cfg = TransformerConfig.from_dict({"enabled": False, "rules": [
        {"pattern": r".", "replacement": "X"}
    ]})
    t = LineTransformer(cfg)
    assert t.transform("hello") == "hello"


def test_no_rules_returns_original():
    cfg = TransformerConfig.from_dict({})
    t = LineTransformer(cfg)
    assert t.transform("some line") == "some line"


def test_reset_stats(transformer):
    transformer.transform("ERROR 1")
    assert transformer.transform_count > 0
    transformer.reset_stats()
    assert transformer.transform_count == 0


def test_rules_applied_in_order():
    # First rule turns 'foo' into 'bar', second rule matches 'bar'
    cfg = TransformerConfig.from_dict({
        "rules": [
            {"pattern": "foo", "replacement": "bar"},
            {"pattern": "bar", "replacement": "baz"},
        ]
    })
    t = LineTransformer(cfg)
    assert t.transform("foo") == "baz"
