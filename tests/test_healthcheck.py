"""Tests for logpulse.healthcheck."""

from __future__ import annotations

import json
import socket
import time

import pytest

from logpulse.healthcheck import HealthConfig, HealthServer


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture()
def server():
    cfg = HealthConfig(host="127.0.0.1", port=_free_port(), enabled=True)
    srv = HealthServer(cfg)
    srv.start()
    time.sleep(0.05)  # let the thread spin up
    yield srv
    srv.stop()


def _get(server: HealthServer, path: str = "/health"):
    import urllib.request
    cfg = server._config
    url = f"http://{cfg.host}:{cfg.port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status, json.loads(resp.read())
    except Exception as exc:
        # urllib raises for non-2xx; extract code from HTTPError
        if hasattr(exc, "code") and hasattr(exc, "read"):
            return exc.code, json.loads(exc.read())
        raise


def test_health_returns_503_when_not_alive(server):
    status, body = _get(server)
    assert status == 503
    assert body["alive"] is False


def test_health_returns_200_when_alive(server):
    server.mark_alive(True)
    status, body = _get(server)
    assert status == 200
    assert body["alive"] is True


def test_health_reports_lines_processed(server):
    server.mark_alive(True)
    server.increment_lines(42)
    _, body = _get(server)
    assert body["lines_processed"] == 42


def test_health_reports_alerts_fired(server):
    server.mark_alive(True)
    server.increment_alerts(7)
    _, body = _get(server)
    assert body["alerts_fired"] == 7


def test_unknown_path_returns_404(server):
    status, _ = _get(server, "/unknown")
    assert status == 404


def test_disabled_server_does_not_bind():
    port = _free_port()
    cfg = HealthConfig(host="127.0.0.1", port=port, enabled=False)
    srv = HealthServer(cfg)
    srv.start()  # should be a no-op
    # nothing listening — connection must be refused
    with pytest.raises(Exception):
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
    srv.stop()  # safe to call on disabled server


def test_increment_lines_accumulates(server):
    server.mark_alive(True)
    server.increment_lines(10)
    server.increment_lines(5)
    _, body = _get(server)
    assert body["lines_processed"] == 15
