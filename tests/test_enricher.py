"""Tests for logpulse.enricher."""
import re
import socket
from unittest.mock import patch

import pytest

from logpulse.enricher import EnrichConfig, EnrichedLine, LineEnricher


# ---------------------------------------------------------------------------
# EnrichConfig.from_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    cfg = EnrichConfig.from_dict({})
    assert cfg.include_hostname is True
    assert cfg.include_timestamp is True
    assert cfg.static_tags == {}


def test_from_dict_custom_values():
    cfg = EnrichConfig.from_dict(
        {"include_hostname": False, "include_timestamp": False, "static_tags": {"env": "prod"}}
    )
    assert cfg.include_hostname is False
    assert cfg.include_timestamp is False
    assert cfg.static_tags == {"env": "prod"}


# ---------------------------------------------------------------------------
# LineEnricher.enrich
# ---------------------------------------------------------------------------

def test_enrich_adds_hostname():
    enricher = LineEnricher(EnrichConfig(include_hostname=True, include_timestamp=False))
    result = enricher.enrich("hello world")
    assert "hostname" in result.tags
    assert result.tags["hostname"] == socket.gethostname()


def test_enrich_no_hostname_when_disabled():
    enricher = LineEnricher(EnrichConfig(include_hostname=False, include_timestamp=False))
    result = enricher.enrich("hello")
    assert "hostname" not in result.tags


def test_enrich_adds_timestamp():
    enricher = LineEnricher(EnrichConfig(include_hostname=False, include_timestamp=True))
    result = enricher.enrich("hello")
    assert "timestamp" in result.tags
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", result.tags["timestamp"])


def test_enrich_static_tags_are_present():
    cfg = EnrichConfig(include_hostname=False, include_timestamp=False, static_tags={"env": "staging", "app": "api"})
    enricher = LineEnricher(cfg)
    result = enricher.enrich("some line")
    assert result.tags["env"] == "staging"
    assert result.tags["app"] == "api"


def test_enrich_preserves_raw_line():
    enricher = LineEnricher(EnrichConfig(include_hostname=False, include_timestamp=False))
    result = enricher.enrich("ERROR: something failed")
    assert result.raw == "ERROR: something failed"


def test_enrich_many_returns_correct_count():
    enricher = LineEnricher(EnrichConfig(include_hostname=False, include_timestamp=False))
    lines = ["line1", "line2", "line3"]
    results = enricher.enrich_many(lines)
    assert len(results) == 3
    assert [r.raw for r in results] == lines


# ---------------------------------------------------------------------------
# EnrichedLine.as_dict
# ---------------------------------------------------------------------------

def test_as_dict_contains_line_and_tags():
    el = EnrichedLine(raw="test", tags={"hostname": "box1"})
    d = el.as_dict()
    assert d["line"] == "test"
    assert d["hostname"] == "box1"


def test_hostname_fallback_on_os_error():
    with patch("socket.gethostname", side_effect=OSError("no name")):
        enricher = LineEnricher(EnrichConfig(include_hostname=True, include_timestamp=False))
    result = enricher.enrich("x")
    assert result.tags["hostname"] == "unknown"
