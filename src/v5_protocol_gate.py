"""Fail-closed audits for the frozen V5 calibration protocol."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Mapping

from config import (
    CONTROLLED_V5_CALIBRATION_THRESHOLDS,
    CONTROLLED_V5_VERSION,
)
from .controlled_v5_messages import V5MessageBank
from .v5_calibration import _canonical_sha256


V5_CALIBRATION_PROTOCOL_VERSION = "v5-calibration-protocol-1.0"


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)


def audit_v5_calibration_plan(
    spec: Mapping[str, Any],
    bank: V5MessageBank,
    provider: Mapping[str, Any],
    mode: str,
    n_episode_blocks: int,
    n_rounds: int,
    heldout_start_round: int,
    seed: int,
    repository_root: str,
) -> Dict[str, Any]:
    if mode not in {"pool_calibration", "selected_bank_validation"}:
        raise ValueError("unknown V5 calibration mode")
    pool = spec.get("candidate_pool", {})
    semantic_ref = spec.get("semantic_validation", {})
    model = spec.get("primary_model", {})
    generation = spec.get("generation", {})
    schedule_key = (
        "pool_calibration_schedule"
        if mode == "pool_calibration"
        else "selected_bank_validation_schedule"
    )
    schedule = spec.get(schedule_key, {})
    semantic_path = _resolve(repository_root, str(semantic_ref.get("path", "")))
    pool_path = _resolve(repository_root, str(pool.get("path", "")))
    semantic = {}
    if os.path.isfile(semantic_path):
        with open(semantic_path, "r", encoding="utf-8") as handle:
            semantic = json.load(handle)

    bank_checks = {
        "pool_mode_exact_source_bank": mode != "pool_calibration"
        or bank.sha256() == pool.get("sha256"),
        "selected_mode_pending_bank": mode != "selected_bank_validation"
        or bank.payload.get("status")
        == "selected_bank_pending_no_history_validation",
        "selected_mode_source_pool": mode != "selected_bank_validation"
        or bank.payload.get("source_pool_sha256") == pool.get("sha256"),
        "selected_mode_semantic_hash": mode != "selected_bank_validation"
        or bank.payload.get("semantic_validation_sha256")
        == semantic_ref.get("canonical_sha256"),
    }
    checks = {
        "protocol_version": spec.get("protocol_version")
        == V5_CALIBRATION_PROTOCOL_VERSION,
        "task_version": spec.get("task_version") == CONTROLLED_V5_VERSION,
        "pre_focal_calibration": spec.get("pre_focal_calibration") is True,
        "protocol_status": spec.get("status")
        == "SEMANTIC_GATE_PASSED_READY_FOR_PAID_POOL_CALIBRATION",
        "pool_file_exists": os.path.isfile(pool_path),
        "pool_file_hash": os.path.isfile(pool_path)
        and file_sha256(pool_path) == pool.get("file_sha256"),
        "pool_canonical_hash": os.path.isfile(pool_path)
        and V5MessageBank.load(pool_path).sha256() == pool.get("sha256"),
        "semantic_file_exists": os.path.isfile(semantic_path),
        "semantic_file_hash": os.path.isfile(semantic_path)
        and file_sha256(semantic_path) == semantic_ref.get("file_sha256"),
        "semantic_canonical_hash": bool(semantic)
        and _canonical_sha256(semantic) == semantic_ref.get("canonical_sha256"),
        "semantic_gate_pass": semantic.get("pass") is True
        and semantic.get("pool_sha256") == pool.get("sha256"),
        "calibration_thresholds": spec.get("calibration_thresholds")
        == CONTROLLED_V5_CALIBRATION_THRESHOLDS,
        "model_id": provider.get("model") == model.get("id"),
        "model_revision": provider.get("revision") == model.get("revision"),
        "provider_kind": provider.get("provider") == "huggingface",
        "temperature": provider.get("temperature") == generation.get("temperature"),
        "top_p": provider.get("top_p") == generation.get("top_p"),
        "top_k": provider.get("top_k") == generation.get("top_k"),
        "max_tokens": provider.get("max_tokens") == generation.get("max_tokens"),
        "dtype": provider.get("dtype") == generation.get("dtype"),
        "thinking_disabled": provider.get("enable_thinking")
        is generation.get("enable_thinking") is False,
        "capture_disabled": provider.get("capture")
        is generation.get("activation_capture") is False,
        "constrained_choices": provider.get("constrained_choices")
        == generation.get("constrained_choices") == ["1", "2", "3"],
        "provider_seed": provider.get("torch_seed_base") == seed,
        "episode_blocks": n_episode_blocks == schedule.get("n_episode_blocks"),
        "rounds": n_rounds == schedule.get("n_rounds"),
        "heldout_start": heldout_start_round
        == schedule.get("heldout_start_round"),
        "schedule_seed": seed == schedule.get("seed"),
        "record_count": n_episode_blocks * n_rounds == schedule.get("n_records"),
        "history_absent": schedule.get("history_present") is False,
        "target_absent": schedule.get("target_simulator_present") is False,
        **bank_checks,
    }
    return {
        "pass": all(checks.values()),
        "mode": mode,
        "checks": checks,
        "protocol_version": V5_CALIBRATION_PROTOCOL_VERSION,
        "bank_sha256": bank.sha256(),
        "semantic_validation_path": semantic_path,
    }


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    return _canonical_sha256(payload)


def _read_json_reference(
    reference: Mapping[str, Any], repository_root: str
) -> tuple[Dict[str, Any], bool, bool]:
    path = _resolve(repository_root, str(reference.get("path", "")))
    if not os.path.isfile(path):
        return {}, False, False
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    hash_ok = file_sha256(path) == reference.get("file_sha256")
    return payload, True, hash_ok


def audit_v5_checkpoint_artifacts(
    spec: Mapping[str, Any], repository_root: str
) -> Dict[str, Any]:
    """Verify every pre-outcome artifact referenced by a frozen V5 checkpoint."""
    bank_ref = spec.get("message_bank", {})
    semantic_ref = spec.get("semantic_validation", {})
    calibration_ref = spec.get("pool_calibration", {})
    calibration_log_ref = spec.get("pool_calibration_log", {})
    selection_ref = spec.get("bank_selection", {})
    validation_ref = spec.get("selected_bank_validation", {})
    validation_manifest_ref = spec.get("selected_bank_validation_manifest", {})
    validation_log_ref = spec.get("selected_bank_validation_log", {})
    power_ref = spec.get("power", {})
    calibration_protocol_ref = spec.get("calibration_protocol", {})
    bank_payload, bank_exists, bank_file_ok = _read_json_reference(
        bank_ref, repository_root
    )
    semantic, semantic_exists, semantic_file_ok = _read_json_reference(
        semantic_ref, repository_root
    )
    calibration, calibration_exists, calibration_file_ok = _read_json_reference(
        calibration_ref, repository_root
    )
    selection, selection_exists, selection_file_ok = _read_json_reference(
        selection_ref, repository_root
    )
    validation, validation_exists, validation_file_ok = _read_json_reference(
        validation_ref, repository_root
    )
    validation_manifest, validation_manifest_exists, validation_manifest_file_ok = (
        _read_json_reference(validation_manifest_ref, repository_root)
    )
    power, power_exists, power_file_ok = _read_json_reference(power_ref, repository_root)
    calibration_protocol, protocol_exists, protocol_file_ok = _read_json_reference(
        calibration_protocol_ref, repository_root
    )
    calibration_log_path = _resolve(
        repository_root, str(calibration_log_ref.get("path", ""))
    )
    validation_log_path = _resolve(
        repository_root, str(validation_log_ref.get("path", ""))
    )
    calibration_log_exists = os.path.isfile(calibration_log_path)
    validation_log_exists = os.path.isfile(validation_log_path)
    calibration_log_file_ok = calibration_log_exists and (
        file_sha256(calibration_log_path) == calibration_log_ref.get("file_sha256")
    )
    validation_log_file_ok = validation_log_exists and (
        file_sha256(validation_log_path) == validation_log_ref.get("file_sha256")
    )
    bank = None
    if bank_exists:
        bank_path = _resolve(repository_root, str(bank_ref.get("path", "")))
        try:
            bank = V5MessageBank.load(bank_path, require_validated=True)
        except (OSError, ValueError):
            bank = None
    effect_pair = power_ref.get("selected_effect_pair", {})
    effect_key = None
    if effect_pair:
        effect_key = "%.3f:%.3f" % (
            float(effect_pair.get("stable_did", -1)),
            float(effect_pair.get("revision_shift", -1)),
        )
    recommended = power.get("minimum_episode_seeds_by_effect_pair", {}).get(effect_key)
    recommended_complete = power.get(
        "minimum_episode_seeds_by_effect_pair_complete_pattern", {}
    ).get(effect_key)
    selected_recommendation = (
        max(int(recommended), int(recommended_complete))
        if recommended is not None and recommended_complete is not None
        else None
    )
    validation_source = power.get("selected_bank_validation_source") or {}
    frozen_power_design = calibration_protocol.get("power_design", {})
    frozen_effect_pair = frozen_power_design.get(
        "population_smallest_effects_of_interest", {}
    )
    checks = {
        "checkpoint_frozen": spec.get("status")
        == "FROZEN_BEFORE_V5_CONFIRMATORY_OUTCOMES"
        and spec.get("pre_confirmatory_outcome") is True,
        "task_version": spec.get("version") == CONTROLLED_V5_VERSION,
        "calibration_protocol_exists": protocol_exists,
        "calibration_protocol_file_hash": protocol_file_ok,
        "calibration_protocol_match": bool(calibration_protocol)
        and calibration_protocol.get("protocol_version")
        == V5_CALIBRATION_PROTOCOL_VERSION,
        "bank_exists": bank_exists,
        "bank_file_hash": bank_file_ok,
        "bank_validated": bank is not None,
        "bank_canonical_hash": bank is not None
        and bank.sha256() == bank_ref.get("sha256"),
        "semantic_exists": semantic_exists,
        "semantic_file_hash": semantic_file_ok,
        "semantic_pass": semantic.get("pass") is True
        and semantic.get("pool_sha256") == bank_payload.get("source_pool_sha256"),
        "pool_calibration_manifest_exists": calibration_exists,
        "pool_calibration_manifest_hash": calibration_file_ok,
        "pool_calibration_completed": calibration.get("run_status") == "completed"
        and calibration.get("mode") == "pool_calibration",
        "pool_calibration_plan_audit": calibration.get("frozen_protocol", {})
        .get("plan_audit", {})
        .get("pass")
        is True,
        "pool_calibration_log_exists": calibration_log_exists,
        "pool_calibration_log_hash": calibration_log_file_ok,
        "pool_manifest_matches_log": calibration.get("log_file_sha256")
        == calibration_log_ref.get("file_sha256"),
        "pool_manifest_matches_source_bank": calibration.get("pool_sha256")
        == bank_payload.get("source_pool_sha256"),
        "selection_report_exists": selection_exists,
        "selection_report_hash": selection_file_ok,
        "selection_run_audit": selection.get("calibration_run_audit", {}).get(
            "pass"
        )
        is True,
        "selection_matches_calibration_manifest": selection.get(
            "calibration_manifest_file_sha256"
        )
        == calibration_ref.get("file_sha256"),
        "selection_matches_calibration_log": selection.get(
            "calibration_log_file_sha256"
        )
        == calibration_log_ref.get("file_sha256"),
        "selection_matches_source_pool": selection.get("source_pool_sha256")
        == bank_payload.get("source_pool_sha256"),
        "selection_matches_semantic_gate": selection.get(
            "semantic_validation_sha256"
        )
        == _canonical_sha256(semantic)
        == bank_payload.get("semantic_validation_sha256")
        if semantic
        else False,
        "selection_matches_final_bank": bool(bank_payload)
        and selection.get("selected_bank_sha256")
        == bank_payload.get("no_history_validation", {}).get(
            "pending_bank_sha256"
        ),
        "selection_content_matches_final_bank": selection.get(
            "selected_bank_content_sha256"
        )
        == _canonical_sha256(bank_payload.get("splits", {})),
        "validation_exists": validation_exists,
        "validation_file_hash": validation_file_ok,
        "validation_pass": validation.get("pass") is True,
        "validation_run_audit": validation.get("calibration_run_audit", {}).get(
            "pass"
        )
        is True,
        "validation_manifest_exists": validation_manifest_exists,
        "validation_manifest_file_hash": validation_manifest_file_ok,
        "validation_manifest_completed": validation_manifest.get("run_status")
        == "completed"
        and validation_manifest.get("mode") == "selected_bank_validation",
        "validation_manifest_plan_audit": validation_manifest.get(
            "frozen_protocol", {}
        )
        .get("plan_audit", {})
        .get("pass")
        is True,
        "validation_log_exists": validation_log_exists,
        "validation_log_hash": validation_log_file_ok,
        "validation_manifest_matches_log": validation_manifest.get(
            "log_file_sha256"
        )
        == validation_log_ref.get("file_sha256"),
        "validation_summary_matches_log": validation.get(
            "validation_log_file_sha256"
        )
        == validation_log_ref.get("file_sha256"),
        "validation_matches_final_bank": False,
        "validation_summary_matches_manifest": False,
        "validation_manifest_matches_final_bank": validation_manifest.get(
            "pool_sha256"
        )
        == bank_payload.get("no_history_validation", {}).get(
            "pending_bank_sha256"
        ),
        "validation_content_matches_final_bank": validation.get(
            "bank_content_sha256"
        )
        == _canonical_sha256(bank_payload.get("splits", {})),
        "power_exists": power_exists,
        "power_file_hash": power_file_ok,
        "power_is_final": power.get("status")
        == "pre-outcome final exact blocked V5 power sensitivity",
        "power_simulation_count": power.get("n_sim_requirement_met") is True,
        "power_uses_validation": validation_source.get("canonical_sha256")
        == _canonical_sha256(validation)
        if validation
        else False,
        "power_uses_validated_bank": validation_source.get("bank_sha256")
        == validation.get("bank_sha256"),
        "protocol_matches_source_pool": calibration_protocol.get(
            "candidate_pool", {}
        ).get("sha256")
        == bank_payload.get("source_pool_sha256"),
        "protocol_matches_semantic_gate": calibration_protocol.get(
            "semantic_validation", {}
        ).get("canonical_sha256")
        == _canonical_sha256(semantic)
        if semantic
        else False,
        "power_recommendation_matches": selected_recommendation
        == spec.get("experiment", {}).get("n_episode_seeds"),
        "power_effect_pair_frozen_before_calibration": effect_pair
        == frozen_effect_pair,
        "power_seed_count_in_frozen_grid": spec.get("experiment", {}).get(
            "n_episode_seeds"
        )
        in frozen_power_design.get("episode_seed_grid", []),
        "power_seed_count_within_frozen_ceiling": int(
            spec.get("experiment", {}).get("n_episode_seeds", -1)
        )
        <= int(frozen_power_design.get("planning_ceiling_episode_seeds", -2)),
    }
    # The final bank stores the pending-bank hash and canonical validation hash,
    # while the validation stores the stable candidate-content hash.
    if bank_payload and validation:
        checks["validation_matches_final_bank"] = (
            validation.get("bank_sha256")
            == bank_payload.get("no_history_validation", {}).get(
                "pending_bank_sha256"
            )
            and _canonical_sha256(validation)
            == bank_payload.get("no_history_validation", {}).get(
                "validation_sha256"
            )
        )
        checks["validation_summary_matches_manifest"] = (
            validation.get("validation_manifest_file_sha256")
            == validation_manifest_ref.get("file_sha256")
        )
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "checkpoint_canonical_sha256": _canonical_sha256(spec),
        "selected_effect_key": effect_key,
        "recommended_episode_seeds": recommended,
        "recommended_complete_pattern_episode_seeds": recommended_complete,
        "selected_episode_seeds": selected_recommendation,
    }
