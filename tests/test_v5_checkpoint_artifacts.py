from __future__ import annotations

import json
from pathlib import Path

from config import STRATEGIES
from src.controlled_v5_messages import V5MessageBank
from src.v5_calibration import (
    _canonical_sha256,
    build_v5_calibration_schedule,
    evaluate_v5_bank_validation,
    finalize_validated_v5_bank,
    select_v5_bank,
)
from src.v5_protocol_gate import audit_v5_checkpoint_artifacts, file_sha256


ROOT = Path(__file__).parents[1]
POOL = ROOT / "data" / "v5" / "v5_candidate_pool_v1.json"


def _strict_records(bank, mode):
    records = []
    for index, row in enumerate(build_v5_calibration_schedule(bank)):
        selected = row["candidates"][index % 3]
        records.append(
            {
                **row,
                "mode": mode,
                "selection_valid": True,
                "fallback_used": False,
                "selected_frame": selected["frame"],
                "selected_pool_candidate_id": selected["pool_candidate_id"],
            }
        )
    return records


def _write(path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "path": str(path.relative_to(path.parents[1])),
        "file_sha256": file_sha256(str(path)),
    }


def test_frozen_v5_artifact_graph_passes_and_detects_corruption(tmp_path):
    pool = V5MessageBank.load(str(POOL))
    semantic = {
        "pass": True,
        "pool_sha256": pool.sha256(),
        "eligible_candidate_ids": [
            entry["candidate_id"]
            for split in pool.payload["splits"].values()
            for entries in split.values()
            for entry in entries
        ],
    }
    pending_payload, selection = select_v5_bank(
        pool, _strict_records(pool, "pool_calibration"), semantic
    )
    pending_path = tmp_path / "pending.json"
    _write(pending_path, pending_payload)
    pending = V5MessageBank.load(str(pending_path))
    validation = evaluate_v5_bank_validation(
        _strict_records(pending, "selected_bank_validation"), pending
    )
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    protocol_path = artifacts / "protocol.json"
    bank_path = artifacts / "bank.json"
    semantic_path = artifacts / "semantic.json"
    calibration_path = artifacts / "calibration.json"
    calibration_log_path = artifacts / "calibration.jsonl"
    selection_path = artifacts / "selection.json"
    validation_path = artifacts / "validation.json"
    validation_manifest_path = artifacts / "validation.manifest.json"
    validation_log_path = artifacts / "validation.jsonl"
    power_path = artifacts / "power.json"
    _write(
        protocol_path,
        {
            "protocol_version": "v5-calibration-protocol-1.0",
            "candidate_pool": {"sha256": pool.sha256()},
            "semantic_validation": {
                "canonical_sha256": _canonical_sha256(semantic)
            },
            "power_design": {
                "population_smallest_effects_of_interest": {
                    "stable_did": 0.20,
                    "revision_shift": 0.25,
                },
                "episode_seed_grid": [8, 12, 16],
                "planning_ceiling_episode_seeds": 30,
            },
        },
    )
    _write(semantic_path, semantic)
    calibration_log_path.write_text('{"choice":"1"}\n', encoding="utf-8")
    _write(
        calibration_path,
        {
            "run_status": "completed",
            "mode": "pool_calibration",
            "pool_sha256": pool.sha256(),
            "log_file_sha256": file_sha256(str(calibration_log_path)),
            "frozen_protocol": {"plan_audit": {"pass": True}},
        },
    )
    selection["calibration_run_audit"] = {"pass": True}
    selection["calibration_manifest_file_sha256"] = file_sha256(
        str(calibration_path)
    )
    selection["calibration_log_file_sha256"] = file_sha256(
        str(calibration_log_path)
    )
    _write(selection_path, selection)
    validation_log_path.write_text('{"choice":"2"}\n', encoding="utf-8")
    _write(
        validation_manifest_path,
        {
            "run_status": "completed",
            "mode": "selected_bank_validation",
            "pool_sha256": pending.sha256(),
            "log_file_sha256": file_sha256(str(validation_log_path)),
            "frozen_protocol": {"plan_audit": {"pass": True}},
        },
    )
    validation["calibration_run_audit"] = {"pass": True}
    validation["validation_manifest_file_sha256"] = file_sha256(
        str(validation_manifest_path)
    )
    validation["validation_log_file_sha256"] = file_sha256(
        str(validation_log_path)
    )
    # Finalization must include the exact enriched validation payload that is
    # later written and power-referenced.
    final_payload = finalize_validated_v5_bank(pending_payload, validation)
    _write(bank_path, final_payload)
    _write(validation_path, validation)
    _write(
        power_path,
        {
            "status": "pre-outcome final exact blocked V5 power sensitivity",
            "n_sim_requirement_met": True,
            "selected_bank_validation_source": {
                "canonical_sha256": _canonical_sha256(validation),
                "bank_sha256": validation["bank_sha256"],
            },
            "minimum_episode_seeds_by_effect_pair": {"0.200:0.250": 8},
            "minimum_episode_seeds_by_effect_pair_complete_pattern": {
                "0.200:0.250": 8
            },
        },
    )

    def ref(path):
        return {
            "path": str(path.relative_to(tmp_path)),
            "file_sha256": file_sha256(str(path)),
        }

    spec = {
        "version": "controlled-choice-v5.0",
        "status": "FROZEN_BEFORE_V5_CONFIRMATORY_OUTCOMES",
        "pre_confirmatory_outcome": True,
        "calibration_protocol": ref(protocol_path),
        "message_bank": {
            **ref(bank_path),
            "sha256": V5MessageBank.load(
                str(bank_path), require_validated=True
            ).sha256(),
        },
        "semantic_validation": ref(semantic_path),
        "pool_calibration": ref(calibration_path),
        "pool_calibration_log": ref(calibration_log_path),
        "bank_selection": ref(selection_path),
        "selected_bank_validation": ref(validation_path),
        "selected_bank_validation_manifest": ref(validation_manifest_path),
        "selected_bank_validation_log": ref(validation_log_path),
        "power": {
            **ref(power_path),
            "selected_effect_pair": {
                "stable_did": 0.20,
                "revision_shift": 0.25,
            },
        },
        "experiment": {"n_episode_seeds": 8},
    }
    audit = audit_v5_checkpoint_artifacts(spec, str(tmp_path))
    assert audit["pass"] is True
    assert all(audit["checks"].values())

    validation_log_path.write_text('{"choice":"3"}\n', encoding="utf-8")
    changed_log = audit_v5_checkpoint_artifacts(spec, str(tmp_path))
    assert changed_log["pass"] is False
    assert changed_log["checks"]["validation_log_hash"] is False
    validation_log_path.write_text('{"choice":"2"}\n', encoding="utf-8")

    power_path.write_text("{}", encoding="utf-8")
    changed = audit_v5_checkpoint_artifacts(spec, str(tmp_path))
    assert changed["pass"] is False
    assert changed["checks"]["power_file_hash"] is False
