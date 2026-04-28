"""Tests for logpulse.notifier."""

import json
from unittest.mock import MagicMock, patch

import pytest

from logpulse.matcher import Alert
from logpulse.notifier import WebhookNotifier, _slack_payload


SAMPLE_ALERT = Alert(
    label="oom",
    severity="critical",
    line="Out of memory: Kill process 999\n",
    pattern=r"Out of memory",
)


# ---------------------------------------------------------------------------
# _slack_payload
# ---------------------------------------------------------------------------


def test_slack_payload_contains_label():
    payload = _slack_payload(SAMPLE_ALERT)
    assert "oom" in payload["text"]


def test_slack_payload_contains_severity_emoji():
    payload = _slack_payload(SAMPLE_ALERT)
    assert ":red_circle:" in payload["text"]


def test_slack_payload_contains_source():
    payload = _slack_payload(SAMPLE_ALERT, source="/var/log/syslog")
    assert "/var/log/syslog" in payload["text"]


def test_slack_payload_no_source():
    payload = _slack_payload(SAMPLE_ALERT, source=None)
    assert "Source" not in payload["text"]


# ---------------------------------------------------------------------------
# WebhookNotifier.send
# ---------------------------------------------------------------------------


def _make_mock_response(status: int = 200):
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


@patch("logpulse.notifier.urllib.request.urlopen")
def test_send_success(mock_urlopen):
    mock_urlopen.return_value = _make_mock_response(200)
    notifier = WebhookNotifier(url="https://hooks.example.com/test")
    result = notifier.send(SAMPLE_ALERT)
    assert result is True
    mock_urlopen.assert_called_once()


@patch("logpulse.notifier.urllib.request.urlopen")
def test_send_non_200_returns_false(mock_urlopen):
    mock_urlopen.return_value = _make_mock_response(500)
    notifier = WebhookNotifier(url="https://hooks.example.com/test")
    result = notifier.send(SAMPLE_ALERT)
    assert result is False


@patch("logpulse.notifier.urllib.request.urlopen", side_effect=OSError("network down"))
def test_send_exception_returns_false(mock_urlopen):
    notifier = WebhookNotifier(url="https://hooks.example.com/test")
    result = notifier.send(SAMPLE_ALERT)
    assert result is False


@patch("logpulse.notifier.urllib.request.urlopen")
def test_send_posts_valid_json(mock_urlopen):
    mock_urlopen.return_value = _make_mock_response(200)
    notifier = WebhookNotifier(url="https://hooks.example.com/test", source="app.log")
    notifier.send(SAMPLE_ALERT)
    _, kwargs = mock_urlopen.call_args
    request_obj = mock_urlopen.call_args[0][0]
    payload = json.loads(request_obj.data.decode("utf-8"))
    assert "text" in payload
