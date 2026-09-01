"""Fail-closed audits for the final V6 target-free calibration protocol."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Mapping, Optional

from config import (
    CONTROLLED_V6_CALIBRATION_THRESHOLDS,
    CONTROLLED_V6_QUALITY_THRESHOLDS,
    CONTROLLED_V6_SEMANTIC_THRESHOLDS,
    CONTROLLED_V6_VERSION,
)
from .controlled_v6_messages import V6TriadBank
from .v6_calibration import (
    V6_CALIBRATION_FOLDS,
    V6_POOL_MODE,
    V6_VALIDATION_MODE,
    canonical_sha256,
    file_sha256,
)
from .scenarios import V6_SCENARIO_SETS


V6_CALIBRATION_PROTOCOL_VERSION = "v6-calibration-protocol-1.0"


def _resolve(root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)


def _load_reference(
    reference: Mapping[str, Any], repository_root: str
) -> tuple[Dict[str, Any], bool, bool, bool]:
    path = _resolve(repository_root, str(reference.get("path", "")))
    if not os.path.isfile(path):
        return {}, False, False, False
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return (
        payload,
        True,
        file_sha256(path) == reference.get("file_sha256"),
        canonical_sha256(payload) == reference.get("canonical_sha256"),
    )


def audit_v6_calibration_plan(
    spec: Mapping[str, Any],
    bank: V6TriadBank,
    provider: Mapping[str, Any],
    mode: str,
    seed: int,
    n_episode_blocks: Optional[int],
    repository_root: str,
) -> Dict[str, Any]:
    if mode not in {V6_POOL_MODE, V6_VALIDATION_MODE}:
        raise ValueError("unknown V6 calibration mode")
    pool_ref = spec.get("candidate_pool", {})
    semantic_ref = spec.get("semantic_validation", {})
    quality_ref = spec.get("quality_validation", {})
    model = spec.get("primary_model", {})
    generation = spec.get("generation", {})
    schedule_key = (
        "pool_screening_schedule"
        if mode == V6_POOL_MODE
        else "selected_bank_validation_schedule"
    )
    schedule = spec.get(schedule_key, {})
    pool_path = _resolve(repository_root, str(pool_ref.get("path", "")))
    semantic, semantic_exists, semantic_file_ok, semantic_canonical_ok = _load_reference(
        semantic_ref, repository_root
    )
    quality, quality_exists, quality_file_ok, quality_canonical_ok = _load_reference(
        quality_ref, repository_root
    )
    pool_exists = os.path.isfile(pool_path)
    source_pool_hash = pool_ref.get("sha256")
    expected_records = int(schedule.get("n_records", -1))
    calculated_records = int(schedule.get("n_triads", -1)) * int(
        schedule.get("n_scenarios", -1)
    ) * int(schedule.get("n_slot_permutations", -1))
    expected_scenario_set = "calibration" if mode == V6_POOL_MODE else "validation"
    scenario_refs = spec.get("scenario_sets", {})
    scenario_hashes = {
        name: canonical_sha256([scenario.as_dict() for scenario in scenarios])
        for name, scenarios in V6_SCENARIO_SETS.items()
    }
    expected_triads = 20 if mode == V6_POOL_MODE else 10
    expected_records_for_mode = 1680 if mode == V6_POOL_MODE else 840
    planned_semantic_judges = list(semantic_ref.get("judges", []))
    planned_quality_judges = list(quality_ref.get("judges", []))
    observed_semantic_judges = [
        semantic.get("primary_judge", {}).get("model"),
        semantic.get("sensitivity_judge", {}).get("model"),
    ]
    observed_quality_judges = [
        quality.get("primary_judge", {}).get("model"),
        quality.get("sensitivity_judge", {}).get("model"),
    ]
    checks = {
        "protocol_version": spec.get("protocol_version")
        == V6_CALIBRATION_PROTOCOL_VERSION,
        "task_version": spec.get("task_version") == CONTROLLED_V6_VERSION,
        "pre_target_outcomes": spec.get("pre_target_outcomes") is True,
        "final_version_no_v7_rescue": spec.get("final_version_no_v7_rescue") is True,
        "machine_only_validation_declared": spec.get("machine_only_validation")
        is True
        and spec.get("human_validation") is False,
        "protocol_status": spec.get("status")
        == "SEMANTIC_AND_QUALITY_GATES_PASSED_READY_FOR_PAID_POOL_SCREENING",
        "pool_file_exists": pool_exists,
        "pool_file_hash": pool_exists
        and file_sha256(pool_path) == pool_ref.get("file_sha256"),
        "pool_canonical_hash": pool_exists
        and V6TriadBank.load(pool_path).sha256() == source_pool_hash,
        "semantic_file_exists": semantic_exists,
        "semantic_file_hash": semantic_file_ok,
        "semantic_canonical_hash": semantic_canonical_ok,
        "semantic_gate_pass": semantic.get("pass") is True
        and semantic.get("pool_sha256") == source_pool_hash,
        "semantic_judges_match_plan": planned_semantic_judges
        == observed_semantic_judges
        == ["gpt-5.6-sol", "gpt-5.6-luna"],
        "quality_file_exists": quality_exists,
        "quality_file_hash": quality_file_ok,
        "quality_canonical_hash": quality_canonical_ok,
        "quality_gate_pass": quality.get("pass") is True
        and quality.get("pool_sha256") == source_pool_hash,
        "quality_judges_match_plan": planned_quality_judges
        == observed_quality_judges
        == ["gpt-5.6-sol", "gpt-5.6-luna"],
        "semantic_thresholds": spec.get("semantic_thresholds")
        == CONTROLLED_V6_SEMANTIC_THRESHOLDS,
        "quality_thresholds": spec.get("quality_thresholds")
        == CONTROLLED_V6_QUALITY_THRESHOLDS,
        "calibration_thresholds": spec.get("calibration_thresholds")
        == CONTROLLED_V6_CALIBRATION_THRESHOLDS,
        "scenario_set_name": schedule.get("scenario_set") == expected_scenario_set,
        "scenario_count": schedule.get("n_scenarios")
        == len(V6_SCENARIO_SETS[expected_scenario_set])
        == 14,
        "scenario_hashes": all(
            scenario_refs.get(name, {}).get("canonical_sha256") == digest
            and scenario_refs.get(name, {}).get("n_scenarios")
            == len(V6_SCENARIO_SETS[name])
            for name, digest in scenario_hashes.items()
        ),
        "scenario_sets_disjoint": len(
            {
                scenario.id
                for scenarios in V6_SCENARIO_SETS.values()
                for scenario in scenarios
            }
        )
        == sum(len(scenarios) for scenarios in V6_SCENARIO_SETS.values()),
        "cross_validation_folds": spec.get("cross_validation_folds")
        == [list(pair) for pair in V6_CALIBRATION_FOLDS],
        "model_id": provider.get("model") == model.get("id"),
        "model_revision": provider.get("revision") == model.get("revision"),
        "provider_kind": provider.get("provider") == "huggingface",
        "temperature": provider.get("temperature") == generation.get("temperature"),
        "top_p": provider.get("top_p") == generation.get("top_p"),
        "top_k": provider.get("top_k") == generation.get("top_k"),
        "max_tokens": provider.get("max_tokens") == generation.get("max_tokens"),
        "dtype": provider.get("dtype") == generation.get("dtype"),
        "thinking_disabled": provider.get("enable_thinking")
        is generation.get("enable_thinking")
        is False,
        "capture_disabled": provider.get("capture")
        is generation.get("activation_capture")
        is False,
        "constrained_choices": provider.get("constrained_choices")
        == generation.get("constrained_choices")
        == ["1", "2", "3"],
        "invalid_output_aborts": generation.get("invalid_output_policy")
        == "abort; no fallback",
        "provider_seed": provider.get("torch_seed_base") == seed,
        "schedule_seed": seed == schedule.get("seed"),
        "record_count": calculated_records
        == expected_records
        == expected_records_for_mode,
        "triad_count": schedule.get("n_triads") == expected_triads,
        "all_six_slot_permutations": schedule.get("n_slot_permutations") == 6,
        "round_contract": schedule.get("n_rounds") == 24
        and schedule.get("heldout_start_round") == 19,
        "history_absent": schedule.get("history_present") is False,
        "target_absent": schedule.get("target_simulator_present") is False,
        "pool_mode_exact_source_bank": mode != V6_POOL_MODE
        or bank.sha256() == source_pool_hash,
        "selected_mode_pending_bank": mode != V6_VALIDATION_MODE
        or bank.payload.get("status")
        == "selected_bank_pending_no_history_validation",
        "selected_mode_source_pool": mode != V6_VALIDATION_MODE
        or bank.payload.get("source_pool_sha256") == source_pool_hash,
        "selected_mode_semantic_hash": mode != V6_VALIDATION_MODE
        or bank.payload.get("semantic_validation_sha256")
        == semantic_ref.get("canonical_sha256"),
        "selected_mode_quality_hash": mode != V6_VALIDATION_MODE
        or bank.payload.get("quality_validation_sha256")
        == quality_ref.get("canonical_sha256"),
        "episode_blocks_not_used_for_complete_permutation_schedules": schedule.get(
            "n_episode_blocks"
        )
        is None,
        "episode_blocks_argument_absent": n_episode_blocks is None,
        "fresh_validation_seed": spec.get("pool_screening_schedule", {}).get("seed")
        != spec.get("selected_bank_validation_schedule", {}).get("seed"),
    }
    return {
        "pass": all(checks.values()),
        "mode": mode,
        "checks": checks,
        "protocol_version": V6_CALIBRATION_PROTOCOL_VERSION,
        "bank_sha256": bank.sha256(),
        "semantic_validation_path": _resolve(
            repository_root, str(semantic_ref.get("path", ""))
        ),
        "quality_validation_path": _resolve(
            repository_root, str(quality_ref.get("path", ""))
        ),
    }
