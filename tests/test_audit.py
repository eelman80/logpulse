"""Tests for logpulse.audit."""
import json
from pathlib import Path

import pytest

from logpulse.audit import AuditConfig, AuditLog
from logpulse.matcher import Alert


def _alert(label: str = "app", severity: str = "warning") -> Alert:
    return Alert(label=label, severity=severity, line="error occurred", pattern="error")


@pytest.fixture()
def audit_path(tmp_path: Path) -> Path:
    return tmp_path / "audit.jsonl"


def test_disabled_audit_writes_nothing(audit_path):
    cfg = AuditConfig(enabled=False, path=str(audit_path))
    log = AuditLog(cfg)
    log.record(_alert(), "slack", routed=True)
    assert not audit_path.exists()
    assert log.records_written == 0


def test_enabled_audit_creates_file(audit_path):
    cfg = AuditConfig(enabled=True, path=str(audit_path))
    log = AuditLog(cfg)
    log.record(_alert(), "slack", routed=True)
    assert audit_path.exists()


def test_record_contains_expected_fields(audit_path):
    cfg = AuditConfig(enabled=True, path=str(audit_path))
    log = AuditLog(cfg)
    alert = _alert(label="db", severity="critical")
    log.record(alert, "pagerduty", routed=True)
    entry = json.loads(audit_path.read_text())
    assert entry["label"] == "db"
    assert entry["severity"] == "critical"
    assert entry["notifier"] == "pagerduty"
    assert entry["routed"] is True
    assert "ts" in entry


def test_multiple_records_append(audit_path):
    cfg = AuditConfig(enabled=True, path=str(audit_path))
    log = AuditLog(cfg)
    log.record(_alert(), "slack", routed=True)
    log.record(_alert(), "slack", routed=False)
    lines = audit_path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert log.records_written == 2


def test_rotation_truncates_file(audit_path):
    cfg = AuditConfig(enabled=True, path=str(audit_path), max_bytes=10)
    log = AuditLog(cfg)
    # First write fills the file beyond max_bytes
    audit_path.write_text("x" * 20, encoding="utf-8")
    log.record(_alert(), "slack", routed=True)
    content = audit_path.read_text()
    # After rotation the old content is gone
    assert "x" * 20 not in content


def test_from_dict_defaults():
    cfg = AuditConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.path == "logpulse_audit.jsonl"
    assert cfg.max_bytes == 10 * 1024 * 1024


def test_from_dict_custom_values():
    cfg = AuditConfig.from_dict({"enabled": True, "path": "/tmp/a.jsonl", "max_bytes": 1024})
    assert cfg.enabled is True
    assert cfg.path == "/tmp/a.jsonl"
    assert cfg.max_bytes == 1024
