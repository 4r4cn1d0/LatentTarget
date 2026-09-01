from __future__ import annotations

import json
from pathlib import Path

from src.controlled_v6_messages import V6TriadBank
from src.v6_calibration import V6_POOL_MODE, canonical_sha256, file_sha256
from src.v6_protocol_gate import audit_v6_calibration_plan


ROOT = Path(__file__).parents[1]
POOL = ROOT / "data" / "v6" / "v6_triad_pool_v1.json"
PROTOCOL = ROOT / "docs" / "v6_calibration_protocol.json"
POOL_RUN_ID = "v6_pool_screening_qwen38_27b_20260902"
VALIDATION_RUN_ID = "v6_bank_validation_qwen38_27b_20260902"
CONFIRMATORY_RUN_ID = "qwen38_27b_v6_confirmatory_20260902"


def _write_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _passing_fixture(tmp_path):
    bank = V6TriadBank.load(str(POOL))
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    semantic = {
        "pass": True,
        "pool_sha256": bank.sha256(),
        "primary_judge": {"model": "gpt-5.6-sol"},
        "sensitivity_judge": {"model": "gpt-5.6-luna"},
    }
    quality = json.loads(json.dumps(semantic))
    semantic_path = tmp_path / "semantic.json"
    quality_path = tmp_path / "quality.json"
    _write_json(semantic_path, semantic)
    _write_json(quality_path, quality)
    spec["status"] = "SEMANTIC_AND_QUALITY_GATES_PASSED_READY_FOR_PAID_POOL_SCREENING"
    spec["pool_screening_schedule"]["official_run_id"] = POOL_RUN_ID
    spec["selected_bank_validation_schedule"][
        "official_run_id"
    ] = VALIDATION_RUN_ID
    spec["confirmatory_design"]["official_run_id"] = CONFIRMATORY_RUN_ID
    for name, path, payload in (
        ("semantic_validation", semantic_path, semantic),
        ("quality_validation", quality_path, quality),
    ):
        spec[name].update(
            {
                "path": str(path),
                "file_sha256": file_sha256(str(path)),
                "canonical_sha256": canonical_sha256(payload),
            }
        )
    provider = {
        "provider": "huggingface",
        "model": spec["primary_model"]["id"],
        "revision": spec["primary_model"]["revision"],
        "temperature": 0.0,
        "top_p": 0.8,
        "top_k": 20,
        "max_tokens": 2,
        "dtype": "bfloat16",
        "enable_thinking": False,
        "capture": False,
        "constrained_choices": ["1", "2", "3"],
        "torch_seed_base": 20262001,
    }
    return bank, spec, provider


def test_v6_pool_plan_audit_passes_only_exact_frozen_contract(tmp_path):
    bank, spec, provider = _passing_fixture(tmp_path)
    result = audit_v6_calibration_plan(
        spec,
        bank,
        provider,
        V6_POOL_MODE,
        20262001,
        None,
        str(ROOT),
        run_id=POOL_RUN_ID,
    )
    assert result["pass"] is True
    assert all(result["checks"].values())

    wrong_run = audit_v6_calibration_plan(
        spec,
        bank,
        provider,
        V6_POOL_MODE,
        20262001,
        None,
        str(ROOT),
        run_id="reselected-run-id",
    )
    assert wrong_run["pass"] is False
    assert wrong_run["checks"]["official_run_id"] is False


def test_v6_pool_plan_audit_fails_scenario_or_legacy_block_override(tmp_path):
    bank, spec, provider = _passing_fixture(tmp_path)
    spec["scenario_sets"]["calibration"]["canonical_sha256"] = "tampered"
    result = audit_v6_calibration_plan(
        spec,
        bank,
        provider,
        V6_POOL_MODE,
        20262001,
        24,
        str(ROOT),
        run_id=POOL_RUN_ID,
    )
    assert result["pass"] is False
    assert result["checks"]["scenario_hashes"] is False
    assert result["checks"]["episode_blocks_argument_absent"] is False
