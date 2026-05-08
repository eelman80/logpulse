"""Tests for logpulse.parser."""
import pytest
from logpulse.parser import LineParser, ParseRule, ParserConfig, ParsedLine


NGINX_PATTERN = (
    r'(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) \S+" (?P<status>\d+)'
)


@pytest.fixture()
def cfg() -> ParserConfig:
    return ParserConfig(
        enabled=True,
        rules=[
            ParseRule(name="nginx", pattern=NGINX_PATTERN),
            ParseRule(name="syslog", pattern=r"(?P<level>ERROR|WARN|INFO) (?P<msg>.*)"),
        ],
    )


@pytest.fixture()
def parser(cfg: ParserConfig) -> LineParser:
    return LineParser(cfg)


def test_nginx_line_extracts_fields(parser: LineParser) -> None:
    line = '1.2.3.4 - - [01/Jan/2024:00:00:00 +0000] "GET /health HTTP/1.1" 200'
    result = parser.parse(line)
    assert result.rule_name == "nginx"
    assert result.get("ip") == "1.2.3.4"
    assert result.get("method") == "GET"
    assert result.get("path") == "/health"
    assert result.get("status") == "200"


def test_syslog_line_uses_fallback_rule(parser: LineParser) -> None:
    line = "ERROR something went wrong"
    result = parser.parse(line)
    assert result.rule_name == "syslog"
    assert result.get("level") == "ERROR"
    assert result.get("msg") == "something went wrong"


def test_unmatched_line_returns_empty_fields(parser: LineParser) -> None:
    line = "totally unstructured log line"
    result = parser.parse(line)
    assert result.rule_name is None
    assert result.fields == {}
    assert result.raw == line


def test_get_missing_key_returns_default(parser: LineParser) -> None:
    line = "ERROR oops"
    result = parser.parse(line)
    assert result.get("nonexistent", "fallback") == "fallback"


def test_disabled_parser_skips_all_rules() -> None:
    cfg = ParserConfig(enabled=False, rules=[ParseRule(name="r", pattern=r"(?P<x>\w+)")])
    p = LineParser(cfg)
    result = p.parse("hello")
    assert result.rule_name is None
    assert result.fields == {}


def test_from_dict_disabled_when_absent() -> None:
    cfg = ParserConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.rules == []


def test_from_dict_creates_rules() -> None:
    data = {
        "parser": {
            "enabled": True,
            "rules": [
                {"name": "simple", "pattern": r"(?P<code>\d+)"},
            ],
        }
    }
    cfg = ParserConfig.from_dict(data)
    assert cfg.enabled is True
    assert len(cfg.rules) == 1
    assert cfg.rules[0].name == "simple"


def test_parse_rule_returns_none_on_no_match() -> None:
    rule = ParseRule(name="r", pattern=r"(?P<num>\d+)")
    assert rule.parse("no digits here? nope.") is None


def test_parse_rule_returns_dict_on_match() -> None:
    rule = ParseRule(name="r", pattern=r"(?P<num>\d+)")
    result = rule.parse("error code 42 occurred")
    assert result == {"num": "42"}
