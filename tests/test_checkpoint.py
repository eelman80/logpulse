"""Tests for logpulse.checkpoint."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from logpulse.checkpoint import CheckpointConfig, CheckpointStore


@pytest.fixture()
def store(tmp_path: Path) -> CheckpointStore:
    cfg = CheckpointConfig(path=str(tmp_path / "cp.json"), enabled=True)
    return CheckpointStore(cfg)


def test_get_unknown_path_returns_none(store: CheckpointStore) -> None:
    assert store.get("/var/log/app.log") is None


def test_save_and_get_roundtrip(store: CheckpointStore) -> None:
    store.save("/var/log/app.log", inode=42, offset=1024)
    entry = store.get("/var/log/app.log")
    assert entry is not None
    assert entry.inode == 42
    assert entry.offset == 1024


def test_checkpoint_file_is_written(store: CheckpointStore, tmp_path: Path) -> None:
    store.save("/tmp/test.log", inode=7, offset=512)
    cp_file = tmp_path / "cp.json"
    assert cp_file.exists()
    data = json.loads(cp_file.read_text())
    assert "/tmp/test.log" in data
    assert data["/tmp/test.log"]["inode"] == 7


def test_clear_removes_entry(store: CheckpointStore) -> None:
    store.save("/tmp/test.log", inode=1, offset=100)
    store.clear("/tmp/test.log")
    assert store.get("/tmp/test.log") is None


def test_clear_nonexistent_is_safe(store: CheckpointStore) -> None:
    store.clear("/no/such/file.log")  # must not raise


def test_persisted_state_survives_reload(tmp_path: Path) -> None:
    cfg = CheckpointConfig(path=str(tmp_path / "cp.json"), enabled=True)
    s1 = CheckpointStore(cfg)
    s1.save("/var/log/syslog", inode=99, offset=2048)

    s2 = CheckpointStore(cfg)  # fresh instance, same file
    entry = s2.get("/var/log/syslog")
    assert entry is not None
    assert entry.inode == 99
    assert entry.offset == 2048


def test_corrupt_checkpoint_file_starts_fresh(tmp_path: Path) -> None:
    cp_file = tmp_path / "cp.json"
    cp_file.write_text("NOT JSON")
    cfg = CheckpointConfig(path=str(cp_file), enabled=True)
    store = CheckpointStore(cfg)  # must not raise
    assert store.get("/any/path") is None


def test_disabled_store_does_not_write(tmp_path: Path) -> None:
    cfg = CheckpointConfig(path=str(tmp_path / "cp.json"), enabled=False)
    store = CheckpointStore(cfg)
    store.save("/tmp/x.log", inode=1, offset=0)
    assert not (tmp_path / "cp.json").exists()
    # get still works in-memory even when disabled
    assert store.get("/tmp/x.log") is None


def test_multiple_paths_are_independent(store: CheckpointStore) -> None:
    store.save("/a.log", inode=1, offset=10)
    store.save("/b.log", inode=2, offset=20)
    assert store.get("/a.log").offset == 10  # type: ignore[union-attr]
    assert store.get("/b.log").offset == 20  # type: ignore[union-attr]
