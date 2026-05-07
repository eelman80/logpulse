"""Tests for logpulse.replay."""
from __future__ import annotations

import pytest
from pathlib import Path

from logpulse.replay import LogReplayer, ReplayConfig


@pytest.fixture()
def log_file(tmp_path: Path) -> Path:
    p = tmp_path / "sample.log"
    p.write_text("\n".join(f"line {i}" for i in range(10)) + "\n")
    return p


# --- ReplayConfig ---

def test_from_dict_defaults():
    cfg = ReplayConfig.from_dict({})
    assert cfg.speed == 1.0
    assert cfg.max_lines is None
    assert cfg.start_line == 0
    assert cfg.loop is False


def test_from_dict_custom():
    cfg = ReplayConfig.from_dict({"speed": "2.5", "max_lines": 5, "start_line": 3, "loop": True})
    assert cfg.speed == 2.5
    assert cfg.max_lines == 5
    assert cfg.start_line == 3
    assert cfg.loop is True


# --- LogReplayer ---

def test_replays_all_lines(log_file: Path):
    cfg = ReplayConfig(speed=0)  # as fast as possible
    replayer = LogReplayer(log_file, cfg)
    lines = list(replayer.lines())
    assert len(lines) == 10
    assert lines[0] == "line 0"
    assert lines[-1] == "line 9"


def test_max_lines_limits_output(log_file: Path):
    cfg = ReplayConfig(speed=0, max_lines=4)
    replayer = LogReplayer(log_file, cfg)
    lines = list(replayer.lines())
    assert len(lines) == 4


def test_start_line_skips_prefix(log_file: Path):
    cfg = ReplayConfig(speed=0, start_line=7)
    replayer = LogReplayer(log_file, cfg)
    lines = list(replayer.lines())
    assert len(lines) == 3
    assert lines[0] == "line 7"


def test_callback_is_called(log_file: Path):
    seen: list[str] = []
    cfg = ReplayConfig(speed=0)
    replayer = LogReplayer(log_file, cfg, line_callback=seen.append)
    list(replayer.lines())
    assert len(seen) == 10


def test_replay_to_returns_count(log_file: Path):
    cfg = ReplayConfig(speed=0)
    replayer = LogReplayer(log_file, cfg)
    received: list[str] = []
    count = replayer.replay_to(received.append)
    assert count == 10
    assert received == [f"line {i}" for i in range(10)]


def test_stop_halts_iteration(log_file: Path):
    cfg = ReplayConfig(speed=0)
    replayer = LogReplayer(log_file, cfg)
    collected: list[str] = []
    for line in replayer.lines():
        collected.append(line)
        if len(collected) == 3:
            replayer.stop()
    assert len(collected) == 3
