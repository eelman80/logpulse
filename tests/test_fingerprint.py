"""Tests for logpulse.fingerprint."""
import pytest

from logpulse.fingerprint import (
    Fingerprint,
    FingerprintConfig,
    LineFingerprinter,
)


@pytest.fixture()
def fp() -> LineFingerprinter:
    return LineFingerprinter()


def test_plain_line_unchanged_structure(fp: LineFingerprinter) -> None:
    result = fp.fingerprint("hello world")
    assert isinstance(result, Fingerprint)
    assert result.normalized == "hello world"


def test_uuid_is_replaced(fp: LineFingerprinter) -> None:
    line = "request 550e8400-e29b-41d4-a716-446655440000 failed"
    result = fp.fingerprint(line)
    assert "<UUID>" in result.normalized
    assert "550e8400" not in result.normalized


def test_ip_address_is_replaced(fp: LineFingerprinter) -> None:
    result = fp.fingerprint("connection from 192.168.1.42 refused")
    assert "<IP>" in result.normalized
    assert "192.168.1.42" not in result.normalized


def test_iso_timestamp_is_replaced(fp: LineFingerprinter) -> None:
    result = fp.fingerprint("2024-03-15T12:34:56Z error occurred")
    assert "<TS>" in result.normalized
    assert "2024" not in result.normalized


def test_numbers_are_replaced(fp: LineFingerprinter) -> None:
    result = fp.fingerprint("retried 3 times after 500 ms")
    assert "<NUM>" in result.normalized
    assert "500" not in result.normalized


def test_same_structure_same_digest(fp: LineFingerprinter) -> None:
    a = fp.fingerprint("user 123 logged in from 10.0.0.1")
    b = fp.fingerprint("user 456 logged in from 10.0.0.2")
    assert a.digest == b.digest
    assert a.normalized == b.normalized


def test_different_structure_different_digest(fp: LineFingerprinter) -> None:
    a = fp.fingerprint("disk full on /var")
    b = fp.fingerprint("connection refused by host")
    assert a.digest != b.digest


def test_digest_length_respects_config() -> None:
    cfg = FingerprintConfig(hash_length=12)
    fp = LineFingerprinter(cfg)
    result = fp.fingerprint("anything")
    assert len(result.digest) == 12


def test_extra_masks_applied() -> None:
    cfg = FingerprintConfig(extra_masks=[("order-\\d+", "<ORDER>")])
    fp = LineFingerprinter(cfg)
    result = fp.fingerprint("processing order-9981 done")
    assert "<ORDER>" in result.normalized
    assert "9981" not in result.normalized


def test_from_dict_defaults() -> None:
    cfg = FingerprintConfig.from_dict({})
    assert cfg.enabled is True
    assert cfg.hash_length == 8
    assert cfg.extra_masks == []


def test_from_dict_custom_values() -> None:
    cfg = FingerprintConfig.from_dict(
        {
            "enabled": False,
            "hash_length": 16,
            "extra_masks": [{"pattern": "job-\\d+", "placeholder": "<JOB>"}],
        }
    )
    assert cfg.enabled is False
    assert cfg.hash_length == 16
    assert cfg.extra_masks == [("job-\\d+", "<JOB>")]


def test_disabled_config_still_fingerprints() -> None:
    """FingerprintConfig.enabled is advisory; LineFingerprinter always works."""
    cfg = FingerprintConfig(enabled=False)
    fp = LineFingerprinter(cfg)
    result = fp.fingerprint("user 99 connected")
    assert result.digest  # non-empty
