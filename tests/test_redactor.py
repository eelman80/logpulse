"""Tests for logpulse.redactor."""
import pytest

from logpulse.redactor import RedactRule, RedactorConfig, Redactor


# ---------------------------------------------------------------------------
# RedactRule
# ---------------------------------------------------------------------------

def test_redact_rule_replaces_match():
    rule = RedactRule(pattern=r"\d{4}", replacement="[NUM]")
    assert rule.apply("code 1234 here") == "code [NUM] here"


def test_redact_rule_no_match_unchanged():
    rule = RedactRule(pattern=r"\d{4}", replacement="[NUM]")
    assert rule.apply("no digits") == "no digits"


def test_redact_rule_default_replacement():
    rule = RedactRule(pattern=r"secret")
    assert rule.apply("my secret word") == "my [REDACTED] word"


# ---------------------------------------------------------------------------
# RedactorConfig.from_dict
# ---------------------------------------------------------------------------

def test_from_dict_creates_rules():
    cfg = RedactorConfig.from_dict(
        {"rules": [{"pattern": r"foo", "replacement": "[BAR]", "label": "test"}]}
    )
    assert len(cfg.rules) == 1
    assert cfg.rules[0].label == "test"
    assert cfg.enabled is True


def test_from_dict_disabled():
    cfg = RedactorConfig.from_dict({"enabled": False, "rules": []})
    assert cfg.enabled is False


def test_from_dict_default_replacement():
    cfg = RedactorConfig.from_dict({"rules": [{"pattern": r"tok"}]})
    assert cfg.rules[0].replacement == "[REDACTED]"


# ---------------------------------------------------------------------------
# Redactor — custom rules
# ---------------------------------------------------------------------------

def test_redactor_applies_custom_rule():
    cfg = RedactorConfig.from_dict(
        {"rules": [{"pattern": r"token=\S+", "replacement": "token=[REDACTED]"}]}
    )
    r = Redactor(config=cfg)
    assert r.redact("auth token=abc123 ok") == "auth token=[REDACTED] ok"


def test_redactor_disabled_returns_original():
    cfg = RedactorConfig.from_dict(
        {"enabled": False, "rules": [{"pattern": r"\d+"}]}
    )
    r = Redactor(config=cfg)
    assert r.redact("pass 1234") == "pass 1234"


def test_redactor_multiple_rules_applied_in_order():
    cfg = RedactorConfig.from_dict(
        {
            "rules": [
                {"pattern": r"foo", "replacement": "[F]"},
                {"pattern": r"bar", "replacement": "[B]"},
            ]
        }
    )
    r = Redactor(config=cfg)
    assert r.redact("foo and bar") == "[F] and [B]"


# ---------------------------------------------------------------------------
# Redactor — built-in patterns
# ---------------------------------------------------------------------------

def test_builtin_redacts_email():
    r = Redactor(include_builtins=True)
    result = r.redact("contact user@example.com now")
    assert "[EMAIL]" in result
    assert "user@example.com" not in result


def test_builtin_redacts_credit_card():
    r = Redactor(include_builtins=True)
    result = r.redact("card 4111 1111 1111 1111 charged")
    assert "[CARD]" in result


def test_no_builtins_by_default():
    r = Redactor()
    line = "email user@example.com card 4111111111111111"
    assert r.redact(line) == line
