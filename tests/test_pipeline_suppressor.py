"""Integration tests: Pipeline respects LineSuppressor."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

import pytest

from logpulse.matcher import Alert, AlertMatcher, Pattern
from logpulse.notifier import WebhookNotifier
from logpulse.pipeline import Pipeline
from logpulse.suppressor import LineSuppressor, SuppressRule, SuppressorConfig
from logpulse.tailer import LogTailer


@pytest.fixture
def tmp_log(tmp_path):
    p = tmp_path / "app.log"
    p.write_text("")
    return p


def _make_matcher(*labels_patterns):
    patterns = [Pattern(label=l, pattern=p, severity="error") for l, p in labels_patterns]
    return AlertMatcher(patterns)


def _make_notifier():
    n = MagicMock(spec=WebhookNotifier)
    return n


def _make_suppressor(*patterns):
    rules = [SuppressRule(pattern=p, label=p) for p in patterns]
    return LineSuppressor(SuppressorConfig(rules=rules, enabled=True))


def test_suppressed_lines_not_alerted(tmp_log):
    tmp_log.write_text("GET /healthcheck 200\nERROR boom\n")
    tailer = LogTailer(str(tmp_log), from_beginning=True)
    matcher = _make_matcher(("err", r"ERROR"))
    notifier = _make_notifier()
    suppressor = _make_suppressor(r"healthcheck")
    pipeline = Pipeline(tailer, matcher, notifier, suppressor)

    sent = pipeline.run_once()

    assert sent == 1
    assert suppressor.suppressed_count == 1
    notifier.send.assert_called_once()


def test_no_suppressor_passes_all_lines(tmp_log):
    tmp_log.write_text("GET /healthcheck 200\nERROR boom\n")
    tailer = LogTailer(str(tmp_log), from_beginning=True)
    matcher = _make_matcher(("err", r"ERROR"), ("health", r"healthcheck"))
    notifier = _make_notifier()
    pipeline = Pipeline(tailer, matcher, notifier)

    sent = pipeline.run_once()

    assert sent == 2


def test_disabled_suppressor_allows_everything(tmp_log):
    tmp_log.write_text("healthcheck\nDEBUG verbose\n")
    tailer = LogTailer(str(tmp_log), from_beginning=True)
    matcher = _make_matcher(("any", r"."))
    notifier = _make_notifier()
    cfg = SuppressorConfig(rules=[SuppressRule(pattern=r".*")], enabled=False)
    suppressor = LineSuppressor(cfg)
    pipeline = Pipeline(tailer, matcher, notifier, suppressor)

    sent = pipeline.run_once()

    assert sent == 2
    assert suppressor.suppressed_count == 0
