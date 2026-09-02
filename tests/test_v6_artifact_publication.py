from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from src.logging_utils import publish_json_idempotent


ROOT = Path(__file__).parents[1]
SCRIPTS = str(ROOT / "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_select_v6_bank_recovers_after_report_only_publication(
    monkeypatch, tmp_path
):
    module = importlib.import_module("scripts.select_v6_bank")
    pool = object()
    monkeypatch.setattr(module.V6TriadBank, "load", lambda path: pool)
    monkeypatch.setattr(module, "read_jsonl", lambda path: iter(()))
    monkeypatch.setattr(
        module,
        "audit_v6_calibration_run",
        lambda *args: {"pass": True, "checks": {"exact": True}},
    )
    monkeypatch.setattr(module, "file_sha256", lambda path: "a" * 64)
    monkeypatch.setattr(
        module,
        "select_v6_bank",
        lambda *args: ({"bank": "selected"}, {"pass": True}),
    )
    manifest = tmp_path / "pool.manifest.json"
    semantic = tmp_path / "semantic.json"
    quality = tmp_path / "quality.json"
    _write_json(manifest, {"log_file_sha256": "a" * 64})
    _write_json(semantic, {})
    _write_json(quality, {})
    report_path = tmp_path / "selection.json"
    bank_path = tmp_path / "pending.json"
    expected_report = {
        "pass": True,
        "calibration_run_audit": {
            "pass": True,
            "checks": {"exact": True},
        },
        "calibration_manifest_file_sha256": "a" * 64,
        "calibration_log_file_sha256": "a" * 64,
    }
    publish_json_idempotent(str(report_path), expected_report)
    argv = [
        "--pool",
        str(tmp_path / "pool.json"),
        "--calibration-log",
        str(tmp_path / "pool.jsonl"),
        "--calibration-manifest",
        str(manifest),
        "--semantic-validation",
        str(semantic),
        "--quality-validation",
        str(quality),
        "--bank-out",
        str(bank_path),
        "--report-out",
        str(report_path),
    ]
    assert module.main(argv) == 0
    assert json.loads(bank_path.read_text()) == {"bank": "selected"}
    assert module.main(argv) == 0

    report_path.write_text('{"pass": false}', encoding="utf-8")
    with pytest.raises(FileExistsError, match="non-identical"):
        module.main(argv)


def test_freeze_checkpoint_is_create_once_and_idempotent(monkeypatch, tmp_path):
    module = importlib.import_module("scripts.freeze_v6_validation_checkpoint")
    monkeypatch.setattr(
        module,
        "build_v6_prevalidation_checkpoint",
        lambda **kwargs: {
            "pending_bank": {"bank_sha256": "b" * 64},
            "official_run_ids": {"selected_bank_validation": "validation-1"},
        },
    )
    output = tmp_path / "checkpoint.json"
    argv = [
        "--source-pool",
        "pool",
        "--semantic-validation",
        "semantic",
        "--quality-validation",
        "quality",
        "--prevalidation-power",
        "power",
        "--pool-calibration-log",
        "log",
        "--pool-calibration-manifest",
        "manifest",
        "--selection-report",
        "selection",
        "--pending-bank",
        "bank",
        "--out",
        str(output),
    ]
    assert module.main(argv) == 0
    first = output.read_bytes()
    assert module.main(argv) == 0
    assert output.read_bytes() == first
    output.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError, match="non-identical"):
        module.main(argv)


def test_finalize_v6_bank_recovers_after_validation_summary_only(
    monkeypatch, tmp_path
):
    module = importlib.import_module("scripts.finalize_v6_bank")
    pending = SimpleNamespace(
        payload={"pending": True},
        sha256=lambda: "p" * 64,
    )
    monkeypatch.setattr(module.V6TriadBank, "load", lambda path: pending)
    monkeypatch.setattr(
        module,
        "audit_v6_prevalidation_checkpoint",
        lambda *args: {
            "pass": True,
            "checks": {"exact": True},
            "pending_bank_sha256": "p" * 64,
        },
    )
    monkeypatch.setattr(module, "read_jsonl", lambda path: iter(()))
    monkeypatch.setattr(
        module, "v6_artifact_reference", lambda *args: {"sha256": "c" * 64}
    )
    monkeypatch.setattr(
        module,
        "audit_v6_calibration_run",
        lambda *args: {"pass": True, "checks": {"exact": True}},
    )
    monkeypatch.setattr(module, "file_sha256", lambda path: "d" * 64)
    monkeypatch.setattr(
        module,
        "evaluate_v6_bank_validation",
        lambda *args: {"pass": True, "metric": 1.0},
    )
    monkeypatch.setattr(
        module,
        "finalize_validated_v6_bank",
        lambda *args: {"bank": "final"},
    )
    monkeypatch.setattr(
        module,
        "build_v6_final_checkpoint",
        lambda **kwargs: {"status": "FINAL", "bank": "e" * 64},
    )
    checkpoint = tmp_path / "prevalidation.json"
    manifest = tmp_path / "validation.manifest.json"
    _write_json(
        checkpoint,
        {
            "official_run_ids": {"selected_bank_validation": "validation-1"}
        },
    )
    _write_json(
        manifest,
        {
            "run_id": "validation-1",
            "frozen_protocol": {
                "prevalidation_checkpoint": {"sha256": "c" * 64}
            },
            "log_file_sha256": "d" * 64,
        },
    )
    validation_out = tmp_path / "validation.json"
    final_bank = tmp_path / "final-bank.json"
    final_checkpoint = tmp_path / "final-checkpoint.json"
    expected_validation = {
        "pass": True,
        "metric": 1.0,
        "calibration_run_audit": {
            "pass": True,
            "checks": {"exact": True},
        },
        "validation_manifest_file_sha256": "d" * 64,
        "validation_log_file_sha256": "d" * 64,
    }
    publish_json_idempotent(str(validation_out), expected_validation)
    argv = [
        "--pending-bank",
        str(tmp_path / "pending.json"),
        "--pre-validation-checkpoint",
        str(checkpoint),
        "--validation-log",
        str(tmp_path / "validation.jsonl"),
        "--validation-manifest",
        str(manifest),
        "--validation-out",
        str(validation_out),
        "--final-bank-out",
        str(final_bank),
        "--final-checkpoint-out",
        str(final_checkpoint),
    ]
    assert module.main(argv) == 0
    assert json.loads(final_bank.read_text()) == {"bank": "final"}
    assert json.loads(final_checkpoint.read_text())["status"] == "FINAL"
    assert module.main(argv) == 0

    final_bank.write_text('{"bank":"foreign"}', encoding="utf-8")
    with pytest.raises(FileExistsError, match="non-identical"):
        module.main(argv)
