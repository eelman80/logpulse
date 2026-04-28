"""Tests for logpulse.tailer.LogTailer."""

import os
import tempfile
import threading
import time

import pytest

from logpulse.tailer import LogTailer


@pytest.fixture()
def tmp_log(tmp_path):
    log_file = tmp_path / "app.log"
    log_file.write_text("existing line\n")
    return str(log_file)


def _collect_lines(tailer: LogTailer, results: list, count: int) -> None:
    """Collect *count* lines then stop (runs in a thread)."""
    for line in tailer.lines():
        results.append(line)
        if len(results) >= count:
            break


def test_tail_new_lines(tmp_log):
    tailer = LogTailer(tmp_log, poll_interval=0.05, from_beginning=False)
    results = []
    t = threading.Thread(target=_collect_lines, args=(tailer, results, 2), daemon=True)
    t.start()

    time.sleep(0.1)
    with open(tmp_log, "a") as f:
        f.write("line one\nline two\n")

    t.join(timeout=3)
    assert results == ["line one", "line two"]


def test_tail_from_beginning(tmp_log):
    tailer = LogTailer(tmp_log, poll_interval=0.05, from_beginning=True)
    results = []
    t = threading.Thread(target=_collect_lines, args=(tailer, results, 1), daemon=True)
    t.start()
    t.join(timeout=3)
    assert results == ["existing line"]


def test_rotation_detected(tmp_path):
    log_file = tmp_path / "rotate.log"
    log_file.write_text("before rotation\n")

    tailer = LogTailer(str(log_file), poll_interval=0.05, from_beginning=False)
    results = []
    t = threading.Thread(target=_collect_lines, args=(tailer, results, 1), daemon=True)
    t.start()

    time.sleep(0.1)
    # Simulate rotation: remove and recreate
    os.remove(str(log_file))
    time.sleep(0.1)
    log_file.write_text("after rotation\n")

    t.join(timeout=4)
    assert "after rotation" in results


def test_callback_interface(tmp_log):
    tailer = LogTailer(tmp_log, poll_interval=0.05, from_beginning=True)
    seen = []

    def _cb(line: str) -> None:
        seen.append(line)
        if len(seen) >= 1:
            raise StopIteration  # break out of tail loop

    with pytest.raises(StopIteration):
        tailer.tail(_cb)

    assert seen == ["existing line"]
