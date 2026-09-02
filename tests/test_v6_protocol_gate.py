from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import src.v6_protocol_gate as v6_protocol_gate_module
from config import (
    CONTROLLED_V6_ANALYSIS_CONFIG,
    CONTROLLED_V6_PAID_PREFLIGHT_RECEIPT_PATH,
)
from src.controlled_v6_messages import V6TriadBank
from src.v6_calibration import V6_POOL_MODE, canonical_sha256, file_sha256
from src.v6_protocol_gate import (
    audit_v6_calibration_plan,
    build_v6_analysis_contract,
    build_v6_confirmatory_schedule_metadata,
)


ROOT = Path(__file__).parents[1]
POOL = ROOT / "data" / "v6" / "v6_triad_pool_v1.json"
PROTOCOL = ROOT / "docs" / "v6_calibration_protocol.json"
POOL_RUN_ID = "v6_pool_screening_qwen38_27b_20260902"
VALIDATION_RUN_ID = "v6_bank_validation_qwen38_27b_20260902"
CONFIRMATORY_RUN_ID = "qwen38_27b_v6_confirmatory_20260902"


def _write_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _passing_fixture(tmp_path, monkeypatch):
    bank = V6TriadBank.load(str(POOL))
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    semantic = {
        "pass": True,
        "pool_sha256": bank.sha256(),
        "primary_judge": {"model": "gpt-5.6-sol"},
        "sensitivity_judge": {"model": "gpt-5.6-luna"},
        "judge_contract": {
            **spec["semantic_validation"]["judge_contract"],
            "kind": "semantic",
            "enforced": True,
        },
    }
    quality = json.loads(json.dumps(semantic))
    quality["judge_contract"] = {
        **spec["quality_validation"]["judge_contract"],
        "kind": "quality",
        "enforced": True,
    }
    monkeypatch.setattr(
        v6_protocol_gate_module,
        "audit_v6_semantic_validation_summary",
        lambda summary, _pool, _root: {
            "ok": True,
            "pass": summary.get("pass") is True,
            "recomputed_evaluation_sha256": "synthetic-semantic",
        },
    )
    monkeypatch.setattr(
        v6_protocol_gate_module,
        "audit_v6_quality_validation_summary",
        lambda summary, _pool, _root: {
            "ok": True,
            "pass": summary.get("pass") is True,
            "recomputed_evaluation_sha256": "synthetic-quality",
        },
    )
    semantic_path = tmp_path / "semantic.json"
    quality_path = tmp_path / "quality.json"
    _write_json(semantic_path, semantic)
    _write_json(quality_path, quality)
    # These plan-audit tests deliberately synthesize judge artifacts outside
    # the repository. Keep that test seam explicit while production reads
    # remain repository-root anchored.
    real_read_rooted_json = v6_protocol_gate_module._read_rooted_json_object

    def read_fixture_json(path, repository_root, *, label):
        if Path(path) in {semantic_path, quality_path}:
            raw = Path(path).read_bytes()
            return json.loads(raw), raw
        return real_read_rooted_json(path, repository_root, label=label)

    monkeypatch.setattr(
        v6_protocol_gate_module,
        "_read_rooted_json_object",
        read_fixture_json,
    )
    canonical_measurement_paths = deepcopy(
        v6_protocol_gate_module.V6_CANONICAL_MEASUREMENT_PATHS
    )
    canonical_measurement_paths["semantic"]["summary"] = str(semantic_path)
    canonical_measurement_paths["quality"]["summary"] = str(quality_path)
    monkeypatch.setattr(
        v6_protocol_gate_module,
        "V6_CANONICAL_MEASUREMENT_PATHS",
        canonical_measurement_paths,
    )
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


def test_v6_pool_plan_audit_passes_only_exact_frozen_contract(
    tmp_path, monkeypatch
):
    bank, spec, provider = _passing_fixture(tmp_path, monkeypatch)
    result = audit_v6_calibration_plan(
        spec,
        bank,
        provider,
        V6_POOL_MODE,
        20262001,
        None,
        str(ROOT),
        run_id=POOL_RUN_ID,
        require_runtime_evidence=False,
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
        require_runtime_evidence=False,
    )
    assert wrong_run["pass"] is False
    assert wrong_run["checks"]["official_run_id"] is False


def test_v6_pool_plan_audit_fails_scenario_or_legacy_block_override(
    tmp_path, monkeypatch
):
    bank, spec, provider = _passing_fixture(tmp_path, monkeypatch)
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
        require_runtime_evidence=False,
    )
    assert result["pass"] is False
    assert result["checks"]["scenario_hashes"] is False
    assert result["checks"]["episode_blocks_argument_absent"] is False


def test_v6_protocol_freezes_analysis_and_paid_preflight_receipt(
    tmp_path, monkeypatch
):
    bank, spec, provider = _passing_fixture(tmp_path, monkeypatch)
    result = audit_v6_calibration_plan(
        spec,
        bank,
        provider,
        V6_POOL_MODE,
        20262001,
        None,
        str(ROOT),
        run_id=POOL_RUN_ID,
        require_runtime_evidence=False,
    )
    assert result["checks"]["analysis_contract"] is True
    assert spec["analysis"] == CONTROLLED_V6_ANALYSIS_CONFIG
    assert spec["confirmatory_design"]["paid_preflight_receipt_path"] == (
        CONTROLLED_V6_PAID_PREFLIGHT_RECEIPT_PATH
    )
    assert v6_protocol_gate_module.V6_CANONICAL_RUN_PATHS["confirmatory"][
        "preflight_receipt"
    ] == CONTROLLED_V6_PAID_PREFLIGHT_RECEIPT_PATH


def test_v6_protocol_rejects_type_coerced_analysis_or_preflight_path_drift(
    tmp_path, monkeypatch
):
    bank, spec, provider = _passing_fixture(tmp_path, monkeypatch)
    spec["analysis"]["n_boot"] = True
    spec["confirmatory_design"]["paid_preflight_receipt_path"] = (
        "results/v6_design/launch_receipts/alternate.json"
    )
    result = audit_v6_calibration_plan(
        spec,
        bank,
        provider,
        V6_POOL_MODE,
        20262001,
        None,
        str(ROOT),
        run_id=POOL_RUN_ID,
        require_runtime_evidence=False,
    )
    assert result["pass"] is False
    assert result["checks"]["analysis_contract"] is False
    assert result["checks"]["confirmatory_paid_preflight_paths"] is False


def test_v6_final_analysis_contract_carries_exact_frozen_runtime(
    tmp_path, monkeypatch
):
    bank, spec, _provider = _passing_fixture(tmp_path, monkeypatch)
    schedule = build_v6_confirmatory_schedule_metadata(
        spec, bank, selected_episode_seeds=12
    )
    contract = build_v6_analysis_contract(spec, bank, schedule)
    assert contract["analysis"] == CONTROLLED_V6_ANALYSIS_CONFIG
    assert contract["experiment"]["paid_preflight_receipt_path"] == (
        CONTROLLED_V6_PAID_PREFLIGHT_RECEIPT_PATH
    )
    drifted = deepcopy(spec)
    drifted["analysis"]["seed"] = True
    try:
        build_v6_analysis_contract(drifted, bank, schedule)
    except ValueError as exc:
        assert "analysis settings differ" in str(exc)
    else:  # pragma: no cover - fail loudly if the strict type gate regresses
        raise AssertionError("type-coerced V6 analysis contract was accepted")
