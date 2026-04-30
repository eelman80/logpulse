"""Simple health-check endpoint that reports pipeline liveness via HTTP."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Optional


@dataclass
class HealthConfig:
    host: str = "127.0.0.1"
    port: int = 9090
    enabled: bool = True


class _Handler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that serves /health as JSON."""

    get_status: Callable[[], dict]  # injected by HealthServer

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return

        payload = self.get_status()
        body = json.dumps(payload).encode()
        status = 200 if payload.get("alive") else 503
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args, **kwargs) -> None:  # silence access logs
        pass


class HealthServer:
    """Runs a background HTTP server exposing /health."""

    def __init__(self, config: HealthConfig) -> None:
        self._config = config
        self._alive: bool = False
        self._lines_processed: int = 0
        self._alerts_fired: int = 0
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # State mutators called by the pipeline
    # ------------------------------------------------------------------

    def mark_alive(self, alive: bool = True) -> None:
        self._alive = alive

    def increment_lines(self, n: int = 1) -> None:
        self._lines_processed += n

    def increment_alerts(self, n: int = 1) -> None:
        self._alerts_fired += n

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if not self._config.enabled:
            return

        handler_cls = type(
            "BoundHandler",
            (_Handler,),
            {"get_status": lambda _self: self._status()},
        )
        self._server = HTTPServer((self._config.host, self._config.port), handler_cls)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()

    def _status(self) -> dict:
        return {
            "alive": self._alive,
            "lines_processed": self._lines_processed,
            "alerts_fired": self._alerts_fired,
        }
