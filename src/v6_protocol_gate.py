"""Fail-closed audits for the final V6 calibration artifact graph.

The protocol status strings are descriptive only.  V6 authorization comes from
reloading the frozen artifacts, checking their hashes, and replaying the
deterministic selection and validation transitions.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Mapping, Optional

from config import (
    CONTROLLED_V6_CALIBRATION_THRESHOLDS,
    CONTROLLED_V6_QUALITY_THRESHOLDS,
    CONTROLLED_V6_SEMANTIC_THRESHOLDS,
    CONTROLLED_V6_VERSION,
    ControlledExperimentConfig,
    ControlledTargetParams,
    ModelConfig,
)
from .controlled_experiment import build_controlled_episode_specs
from .controlled_v6_messages import (
    V6_PROVISIONAL_POOL_STATUS,
    V6_SELECTED_BANK_STATUS,
    V6TriadBank,
)
from .logging_utils import read_jsonl
from .v6_calibration import (
    V6_CALIBRATION_FOLDS,
    V6_POOL_MODE,
    V6_VALIDATION_MODE,
    audit_v6_calibration_run,
    bank_content_sha256,
    canonical_sha256,
    evaluate_v6_bank_validation,
    file_sha256,
    finalize_validated_v6_bank,
    select_v6_bank,
)
from .scenarios import V6_SCENARIO_SETS, v6_scenario_sequence


V6_CALIBRATION_PROTOCOL_VERSION = "v6-calibration-protocol-1.0"
V6_PREVALIDATION_CHECKPOINT_VERSION = "v6-prevalidation-checkpoint-1.0"
V6_FINAL_CHECKPOINT_VERSION = "v6-final-checkpoint-1.0"
V6_PREVALIDATION_CHECKPOINT_STATUS = "FROZEN_BEFORE_V6_INDEPENDENT_VALIDATION"
V6_FINAL_CHECKPOINT_STATUS = "FROZEN_BEFORE_V6_CONFIRMATORY_OUTCOMES"
V6_CONFIRMATORY_EPISODES_PER_SEED = 18


def _resolve(root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)


def _inside_root(path: str, root: str) -> bool:
    try:
        return os.path.commonpath(
            [os.path.realpath(path), os.path.realpath(root)]
        ) == os.path.realpath(root)
    except ValueError:
        return False


def v6_artifact_reference(
    path: str, repository_root: str, *, canonical_json: bool = True
) -> Dict[str, Any]:
    """Return a repository-local immutable reference for a checkpoint."""
    absolute = os.path.realpath(path)
    root = os.path.realpath(repository_root)
    if not _inside_root(absolute, root):
        raise ValueError("V6 checkpoint artifacts must be inside the repository root")
    if not os.path.isfile(absolute):
        raise FileNotFoundError(absolute)
    reference: Dict[str, Any] = {
        "path": os.path.relpath(absolute, root),
        "file_sha256": file_sha256(absolute),
    }
    if canonical_json:
        with open(absolute, "r", encoding="utf-8") as handle:
            reference["canonical_sha256"] = canonical_sha256(json.load(handle))
    return reference


def _checkpoint_reference_path(
    reference: Mapping[str, Any], repository_root: str
) -> tuple[str, bool]:
    raw_path = reference.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return "", False
    path = os.path.realpath(_resolve(repository_root, raw_path))
    return path, _inside_root(path, repository_root)


def _load_checkpoint_json_reference(
    reference: Mapping[str, Any], repository_root: str
) -> tuple[Dict[str, Any], Dict[str, bool], str]:
    path, inside = _checkpoint_reference_path(reference, repository_root)
    exists = inside and os.path.isfile(path)
    payload: Dict[str, Any] = {}
    parsed = False
    if exists:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                payload = loaded
                parsed = True
        except (OSError, ValueError, TypeError):
            pass
    checks = {
        "path_inside_root": inside,
        "exists": exists,
        "json_object": parsed,
        "file_sha256": exists
        and isinstance(reference.get("file_sha256"), str)
        and file_sha256(path) == reference.get("file_sha256"),
        "canonical_sha256": parsed
        and isinstance(reference.get("canonical_sha256"), str)
        and canonical_sha256(payload) == reference.get("canonical_sha256"),
    }
    return payload, checks, path


def _load_checkpoint_log_reference(
    reference: Mapping[str, Any], repository_root: str
) -> tuple[List[Dict[str, Any]], Dict[str, bool], str]:
    path, inside = _checkpoint_reference_path(reference, repository_root)
    exists = inside and os.path.isfile(path)
    records: List[Dict[str, Any]] = []
    parsed = False
    if exists:
        try:
            loaded = list(read_jsonl(path))
            if all(isinstance(row, dict) for row in loaded):
                records = loaded
                parsed = True
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    checks = {
        "path_inside_root": inside,
        "exists": exists,
        "jsonl_objects": parsed,
        "file_sha256": exists
        and isinstance(reference.get("file_sha256"), str)
        and file_sha256(path) == reference.get("file_sha256"),
    }
    return records, checks, path


def _prefix_checks(
    checks: Dict[str, bool], prefix: str, values: Mapping[str, bool]
) -> None:
    checks.update({"%s_%s" % (prefix, name): bool(value) for name, value in values.items()})


def v6_official_run_ids(protocol: Mapping[str, Any]) -> Dict[str, str]:
    """Read the three single-use run IDs and reject an incomplete contract."""
    values = {
        "pool_screening": protocol.get("pool_screening_schedule", {}).get(
            "official_run_id"
        ),
        "selected_bank_validation": protocol.get(
            "selected_bank_validation_schedule", {}
        ).get("official_run_id"),
        "confirmatory": protocol.get("confirmatory_design", {}).get(
            "official_run_id"
        ),
    }
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        raise ValueError("V6 protocol must freeze all three official run IDs")
    if len(set(values.values())) != len(values):
        raise ValueError("V6 official run IDs must be distinct")
    return {name: str(value) for name, value in values.items()}


def _safe_v6_official_run_ids(protocol: Mapping[str, Any]) -> Dict[str, str]:
    try:
        return v6_official_run_ids(protocol)
    except (TypeError, ValueError):
        return {}


def build_v6_confirmatory_schedule_metadata(
    protocol: Mapping[str, Any],
    bank: V6TriadBank,
    selected_episode_seeds: Optional[int] = None,
) -> Dict[str, Any]:
    """Hash every allowed full confirmatory scenario/message schedule.

    Power chooses one value from the predeclared episode-seed grid.  Freezing a
    hash for every allowed value keeps that later choice from changing any
    scenario, triad, or slot assignment while avoiding validation-dependent
    schedule generation.
    """
    design = protocol.get("confirmatory_design", {})
    power_design = protocol.get("power_design", {})
    official_run_ids = v6_official_run_ids(protocol)
    scenario_set = design.get("scenario_set")
    if scenario_set != "confirmatory":
        raise ValueError("V6 confirmatory design must use the sealed confirmatory set")
    try:
        master_seed = int(design["master_seed"])
        n_rounds = int(design["n_rounds"])
        heldout_start_round = int(design["heldout_start_round"])
        swap_round = int(design["swap_round"])
        conditions = [str(value) for value in design["conditions"]]
        target = design["target"]
        episode_seed_grid = sorted({int(value) for value in power_design["episode_seed_grid"]})
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("V6 confirmatory schedule coordinates are incomplete") from exc
    if n_rounds <= 0 or heldout_start_round < 2:
        raise ValueError("V6 confirmatory round coordinates are invalid")
    if not episode_seed_grid or episode_seed_grid[0] <= 0:
        raise ValueError("V6 power design has no positive episode-seed grid")
    if max(episode_seed_grid) != int(
        power_design.get("planning_ceiling_episode_seeds", -1)
    ):
        raise ValueError("V6 episode-seed grid does not end at its frozen ceiling")

    scenario_payload = [
        scenario.as_dict() for scenario in V6_SCENARIO_SETS[scenario_set]
    ]
    schedule_hashes: Dict[str, str] = {}
    episode_counts: Dict[str, int] = {}
    for episode_seed_count in episode_seed_grid:
        cfg = ControlledExperimentConfig(
            experiment_id="controlled_v6_checkpoint",
            n_rounds=n_rounds,
            swap_round=swap_round,
            heldout_start_round=heldout_start_round,
            n_episode_seeds=episode_seed_count,
            seed=master_seed,
            conditions=conditions,
            target_params=ControlledTargetParams(
                p_match=float(target["p_match"]),
                p_mismatch=float(target["p_mismatch"]),
                p_random=float(target["p_random"]),
            ),
            model=ModelConfig(),
        )
        specs = build_controlled_episode_specs(cfg)
        if len(specs) != V6_CONFIRMATORY_EPISODES_PER_SEED * episode_seed_count:
            raise ValueError("V6 confirmatory condition grid no longer has 18 episodes per seed")
        rows: List[Dict[str, Any]] = []
        for spec in specs:
            scenarios = v6_scenario_sequence(
                scenario_set, spec.episode_index, n_rounds, master_seed
            )
            for round_index, scenario in enumerate(scenarios, start=1):
                candidates = bank.candidate_set(
                    scenario,
                    spec.episode_index,
                    round_index,
                    heldout_start_round,
                    master_seed,
                )
                rows.append(
                    {
                        "episode_id": spec.episode_id,
                        "condition": spec.condition.name,
                        "episode_index": spec.episode_index,
                        "initial_target_type": spec.initial_target_type,
                        "final_target_type": spec.final_target_type,
                        "round": round_index,
                        "scenario_id": scenario.id,
                        "candidate_ids_by_slot": [
                            candidate.candidate_id
                            for candidate in sorted(
                                candidates, key=lambda item: item.slot
                            )
                        ],
                    }
                )
        schedule_hashes[str(episode_seed_count)] = canonical_sha256(rows)
        episode_counts[str(episode_seed_count)] = len(specs)

    metadata: Dict[str, Any] = {
        "scenario_set": scenario_set,
        "official_run_id": official_run_ids["confirmatory"],
        "scenario_set_canonical_sha256": canonical_sha256(scenario_payload),
        "n_scenarios": len(scenario_payload),
        "master_seed": master_seed,
        "n_rounds": n_rounds,
        "swap_round": swap_round,
        "heldout_start_round": heldout_start_round,
        "conditions": conditions,
        "episodes_per_seed": V6_CONFIRMATORY_EPISODES_PER_SEED,
        "episode_seed_grid": episode_seed_grid,
        "n_episodes_by_episode_seed_count": episode_counts,
        "bank_pending_sha256": bank.sha256(),
        "bank_content_sha256": bank_content_sha256(bank.payload),
        "schedule_schema": [
            "episode_index",
            "episode_id",
            "condition",
            "initial_target_type",
            "final_target_type",
            "round",
            "scenario_id",
            "candidate_ids_by_slot",
        ],
        "schedule_sha256_by_episode_seed_count": schedule_hashes,
    }
    if selected_episode_seeds is not None:
        selected_key = str(int(selected_episode_seeds))
        if selected_key not in schedule_hashes:
            raise ValueError("V6 power selected a count outside the frozen grid")
        metadata["selected_episode_seeds"] = int(selected_episode_seeds)
        metadata["selected_schedule_sha256"] = schedule_hashes[selected_key]
    metadata["contract_sha256"] = canonical_sha256(metadata)
    return metadata


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
    prevalidation_checkpoint: Optional[Mapping[str, Any]] = None,
    run_id: Optional[str] = None,
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
    official_run_ids = _safe_v6_official_run_ids(spec)
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
    prevalidation = (
        prevalidation_checkpoint
        if isinstance(prevalidation_checkpoint, Mapping)
        else {}
    )
    prevalidation_audit: Dict[str, Any] = {}
    if mode == V6_VALIDATION_MODE and prevalidation:
        prevalidation_audit = audit_v6_prevalidation_checkpoint(
            prevalidation, repository_root
        )
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
        "official_run_ids_frozen": bool(official_run_ids),
        "official_run_id": bool(official_run_ids)
        and run_id == schedule.get("official_run_id")
        == official_run_ids.get(mode),
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
        "selected_mode_prevalidation_checkpoint": mode != V6_VALIDATION_MODE
        or prevalidation_audit.get("pass") is True,
        "selected_mode_checkpoint_pending_hash": mode != V6_VALIDATION_MODE
        or prevalidation_audit.get("pending_bank_sha256") == bank.sha256(),
        "selected_mode_checkpoint_pending_content": mode != V6_VALIDATION_MODE
        or prevalidation_audit.get("pending_bank_content_sha256")
        == bank_content_sha256(bank.payload),
        "selected_mode_checkpoint_protocol": mode != V6_VALIDATION_MODE
        or prevalidation.get("calibration_protocol", {}).get(
            "canonical_sha256"
        )
        == canonical_sha256(spec),
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
        "prevalidation_checkpoint_sha256": (
            canonical_sha256(prevalidation)
            if prevalidation
            else None
        ),
    }


def build_v6_prevalidation_checkpoint(
    *,
    calibration_protocol_path: str,
    source_pool_path: str,
    semantic_validation_path: str,
    quality_validation_path: str,
    prevalidation_power_path: str,
    pool_calibration_log_path: str,
    pool_calibration_manifest_path: str,
    selection_report_path: str,
    pending_bank_path: str,
    repository_root: str,
) -> Dict[str, Any]:
    """Build and self-audit the checkpoint required before validation."""
    pool = V6TriadBank.load(source_pool_path)
    pending = V6TriadBank.load(pending_bank_path)
    with open(calibration_protocol_path, "r", encoding="utf-8") as handle:
        protocol = json.load(handle)
    with open(prevalidation_power_path, "r", encoding="utf-8") as handle:
        power = json.load(handle)
    selected_episode_seeds = power.get("selected_episode_seeds")
    checkpoint: Dict[str, Any] = {
        "checkpoint_version": V6_PREVALIDATION_CHECKPOINT_VERSION,
        "status": V6_PREVALIDATION_CHECKPOINT_STATUS,
        "independent_validation_outputs_included": False,
        "official_run_ids": v6_official_run_ids(protocol),
        "calibration_protocol": v6_artifact_reference(
            calibration_protocol_path, repository_root
        ),
        "source_pool": {
            **v6_artifact_reference(source_pool_path, repository_root),
            "bank_sha256": pool.sha256(),
            "bank_content_sha256": bank_content_sha256(pool.payload),
        },
        "semantic_validation": v6_artifact_reference(
            semantic_validation_path, repository_root
        ),
        "quality_validation": v6_artifact_reference(
            quality_validation_path, repository_root
        ),
        "prevalidation_power": v6_artifact_reference(
            prevalidation_power_path, repository_root
        ),
        "pool_calibration_log": v6_artifact_reference(
            pool_calibration_log_path, repository_root, canonical_json=False
        ),
        "pool_calibration_manifest": v6_artifact_reference(
            pool_calibration_manifest_path, repository_root
        ),
        "selection_report": v6_artifact_reference(
            selection_report_path, repository_root
        ),
        "pending_bank": {
            **v6_artifact_reference(pending_bank_path, repository_root),
            "bank_sha256": pending.sha256(),
            "bank_content_sha256": bank_content_sha256(pending.payload),
        },
        "confirmatory_schedule": build_v6_confirmatory_schedule_metadata(
            protocol, pending, selected_episode_seeds=selected_episode_seeds
        ),
    }
    audit = audit_v6_prevalidation_checkpoint(checkpoint, repository_root)
    if not audit["pass"]:
        failed = sorted(name for name, passed in audit["checks"].items() if not passed)
        raise ValueError(
            "refusing to freeze V6 pre-validation checkpoint: %s"
            % ", ".join(failed)
        )
    return checkpoint


def audit_v6_prevalidation_checkpoint(
    checkpoint: Mapping[str, Any], repository_root: str
) -> Dict[str, Any]:
    """Replay source selection and reject any edited or reselected bank."""
    checks: Dict[str, bool] = {
        "checkpoint_version": checkpoint.get("checkpoint_version")
        == V6_PREVALIDATION_CHECKPOINT_VERSION,
        "checkpoint_status": checkpoint.get("status")
        == V6_PREVALIDATION_CHECKPOINT_STATUS,
        "validation_outputs_absent": checkpoint.get(
            "independent_validation_outputs_included"
        )
        is False,
    }
    protocol, protocol_checks, _protocol_path = _load_checkpoint_json_reference(
        checkpoint.get("calibration_protocol", {}), repository_root
    )
    pool_payload, pool_checks, pool_path = _load_checkpoint_json_reference(
        checkpoint.get("source_pool", {}), repository_root
    )
    semantic, semantic_checks, _semantic_path = _load_checkpoint_json_reference(
        checkpoint.get("semantic_validation", {}), repository_root
    )
    quality, quality_checks, _quality_path = _load_checkpoint_json_reference(
        checkpoint.get("quality_validation", {}), repository_root
    )
    power, power_checks, _power_path = _load_checkpoint_json_reference(
        checkpoint.get("prevalidation_power", {}), repository_root
    )
    records, log_checks, log_path = _load_checkpoint_log_reference(
        checkpoint.get("pool_calibration_log", {}), repository_root
    )
    manifest, manifest_checks, manifest_path = _load_checkpoint_json_reference(
        checkpoint.get("pool_calibration_manifest", {}), repository_root
    )
    selection, selection_checks, _selection_path = _load_checkpoint_json_reference(
        checkpoint.get("selection_report", {}), repository_root
    )
    pending_payload, pending_checks, pending_path = _load_checkpoint_json_reference(
        checkpoint.get("pending_bank", {}), repository_root
    )
    for prefix, values in (
        ("protocol", protocol_checks),
        ("source_pool", pool_checks),
        ("semantic", semantic_checks),
        ("quality", quality_checks),
        ("prevalidation_power", power_checks),
        ("pool_log", log_checks),
        ("pool_manifest", manifest_checks),
        ("selection_report", selection_checks),
        ("pending_bank", pending_checks),
    ):
        _prefix_checks(checks, prefix, values)

    pool: Optional[V6TriadBank] = None
    pending: Optional[V6TriadBank] = None
    try:
        if pool_payload:
            pool = V6TriadBank.load(pool_path)
    except (OSError, ValueError, TypeError):
        pass
    try:
        if pending_payload:
            pending = V6TriadBank.load(pending_path)
    except (OSError, ValueError, TypeError):
        pass

    source_ref = checkpoint.get("source_pool", {})
    pending_ref = checkpoint.get("pending_bank", {})
    checks.update(
        {
            "source_pool_structural_audit": pool is not None,
            "source_pool_provisional": pool is not None
            and pool.payload.get("status") == V6_PROVISIONAL_POOL_STATUS,
            "source_pool_bank_hash": pool is not None
            and source_ref.get("bank_sha256") == pool.sha256(),
            "source_pool_content_hash": pool is not None
            and source_ref.get("bank_content_sha256")
            == bank_content_sha256(pool.payload),
            "pending_bank_structural_audit": pending is not None,
            "pending_bank_status": pending is not None
            and pending.payload.get("status")
            == "selected_bank_pending_no_history_validation",
            "pending_bank_hash": pending is not None
            and pending_ref.get("bank_sha256") == pending.sha256(),
            "pending_bank_content_hash": pending is not None
            and pending_ref.get("bank_content_sha256")
            == bank_content_sha256(pending.payload),
        }
    )

    run_audit: Dict[str, Any] = {}
    recomputed_plan: Dict[str, Any] = {}
    if pool is not None and records and manifest and protocol:
        try:
            recomputed_plan = audit_v6_calibration_plan(
                protocol,
                pool,
                manifest.get("provider", {}),
                V6_POOL_MODE,
                int(manifest.get("schedule", {}).get("seed", -1)),
                manifest.get("schedule", {}).get("n_episode_blocks"),
                repository_root,
                run_id=str(manifest.get("run_id", "")),
            )
            run_audit = audit_v6_calibration_run(
                records, manifest, pool, V6_POOL_MODE
            )
        except (KeyError, TypeError, ValueError, RuntimeError):
            pass
    checks.update(
        {
            "protocol_version": protocol.get("protocol_version")
            == V6_CALIBRATION_PROTOCOL_VERSION,
            "official_run_ids": bool(protocol)
            and bool(_safe_v6_official_run_ids(protocol))
            and checkpoint.get("official_run_ids")
            == _safe_v6_official_run_ids(protocol),
            "protocol_source_pool": pool is not None
            and protocol.get("candidate_pool", {}).get("sha256") == pool.sha256()
            and protocol.get("candidate_pool", {}).get("file_sha256")
            == source_ref.get("file_sha256"),
            "protocol_semantic_summary": bool(semantic)
            and protocol.get("semantic_validation", {}).get("canonical_sha256")
            == canonical_sha256(semantic)
            and protocol.get("semantic_validation", {}).get("file_sha256")
            == checkpoint.get("semantic_validation", {}).get("file_sha256"),
            "protocol_quality_summary": bool(quality)
            and protocol.get("quality_validation", {}).get("canonical_sha256")
            == canonical_sha256(quality)
            and protocol.get("quality_validation", {}).get("file_sha256")
            == checkpoint.get("quality_validation", {}).get("file_sha256"),
            "semantic_pass_and_pool": pool is not None
            and semantic.get("pass") is True
            and semantic.get("pool_sha256") == pool.sha256(),
            "quality_pass_and_pool": pool is not None
            and quality.get("pass") is True
            and quality.get("pool_sha256") == pool.sha256(),
            "pool_manifest_completed": manifest.get("run_status") == "completed"
            and manifest.get("mode") == V6_POOL_MODE,
            "pool_manifest_log_hash": log_checks.get("file_sha256") is True
            and manifest.get("log_file_sha256")
            == checkpoint.get("pool_calibration_log", {}).get("file_sha256"),
            "pool_plan_recomputed": recomputed_plan.get("pass") is True,
            "pool_plan_matches_manifest": bool(recomputed_plan)
            and manifest.get("frozen_protocol", {}).get("plan_audit")
            == recomputed_plan,
            "pool_run_recomputed": run_audit.get("pass") is True,
            "selection_support_pass": selection.get("support_pass") is True,
            "selection_embedded_run_audit": selection.get(
                "calibration_run_audit"
            )
            == run_audit,
            "selection_manifest_hash": manifest_checks.get("file_sha256") is True
            and selection.get("calibration_manifest_file_sha256")
            == checkpoint.get("pool_calibration_manifest", {}).get("file_sha256"),
            "selection_log_hash": log_checks.get("file_sha256") is True
            and selection.get("calibration_log_file_sha256")
            == checkpoint.get("pool_calibration_log", {}).get("file_sha256"),
        }
    )

    power_design = protocol.get("power_design", {})
    selected_episode_seeds = power.get("selected_episode_seeds")
    checks.update(
        {
            "power_pass": power.get("pass") is True
            and power.get("power_selection_pass") is True
            and power.get("null_type_i_pass") is True
            and power.get("status") == "PASS_V6_PREVALIDATION_FINITE_GRID_POWER",
            "power_outcome_independence": power.get("focal_model_outcomes_used")
            is False
            and power.get("confirmatory_outcomes_used") is False
            and power.get("selected_bank_validation_outputs_used") is False,
            "power_episode_grid": power.get("episode_seed_grid")
            == power_design.get("episode_seed_grid"),
            "power_ceiling": power.get("planning_ceiling_episode_seeds")
            == power_design.get("planning_ceiling_episode_seeds"),
            "power_simulations": power.get("minimum_simulations_per_cell")
            == power_design.get("minimum_simulations_per_cell")
            and type(power.get("n_sim_per_cell")) is int
            and power.get("n_sim_per_cell", 0)
            >= int(power_design.get("minimum_simulations_per_cell", -1))
            and power.get("n_sim_requirement_met") is True,
            "power_seed": power.get("simulation_seed")
            == power_design.get("seed"),
            "power_target": power.get("target_power_lower_mc_bound")
            == power_design.get("target_lower_mc_bound"),
            "power_population_alternatives": power.get(
                "population_alternatives"
            )
            == power_design.get("population_smallest_effects_of_interest"),
            "power_selected_count": type(selected_episode_seeds) is int
            and selected_episode_seeds
            in power_design.get("episode_seed_grid", [])
            and selected_episode_seeds
            <= int(power_design.get("planning_ceiling_episode_seeds", -1)),
        }
    )

    regenerated_pending: Optional[Dict[str, Any]] = None
    regenerated_report: Dict[str, Any] = {}
    if pool is not None and run_audit.get("pass") is True:
        try:
            regenerated_pending, regenerated_report = select_v6_bank(
                pool, records, semantic, quality
            )
            regenerated_report["calibration_run_audit"] = run_audit
            regenerated_report["calibration_manifest_file_sha256"] = file_sha256(
                manifest_path
            )
            regenerated_report["calibration_log_file_sha256"] = file_sha256(log_path)
        except (KeyError, TypeError, ValueError, RuntimeError):
            regenerated_pending = None
            regenerated_report = {}
    checks.update(
        {
            "selection_report_exactly_regenerated": bool(regenerated_report)
            and regenerated_report == selection,
            "pending_bank_exactly_regenerated": regenerated_pending is not None
            and regenerated_pending == pending_payload,
            "pending_bank_matches_selection_hash": pending is not None
            and selection.get("selected_bank_sha256") == pending.sha256(),
            "pending_content_matches_selection_hash": pending is not None
            and selection.get("selected_bank_content_sha256")
            == bank_content_sha256(pending.payload),
            "pending_source_pool_hash": pool is not None
            and pending is not None
            and pending.payload.get("source_pool_sha256") == pool.sha256(),
            "pending_semantic_hash": pending is not None
            and pending.payload.get("semantic_validation_sha256")
            == canonical_sha256(semantic),
            "pending_quality_hash": pending is not None
            and pending.payload.get("quality_validation_sha256")
            == canonical_sha256(quality),
        }
    )

    expected_schedule: Dict[str, Any] = {}
    if protocol and pending is not None:
        try:
            expected_schedule = build_v6_confirmatory_schedule_metadata(
                protocol,
                pending,
                selected_episode_seeds=selected_episode_seeds,
            )
        except (KeyError, TypeError, ValueError, RuntimeError):
            pass
    checks["confirmatory_schedule_exact"] = bool(expected_schedule) and checkpoint.get(
        "confirmatory_schedule"
    ) == expected_schedule
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "checkpoint_canonical_sha256": canonical_sha256(checkpoint),
        "pending_bank_sha256": pending.sha256() if pending is not None else None,
        "pending_bank_content_sha256": (
            bank_content_sha256(pending.payload) if pending is not None else None
        ),
        "confirmatory_schedule": expected_schedule,
        "pool_run_audit": run_audit,
    }


def build_v6_final_checkpoint(
    *,
    prevalidation_checkpoint_path: str,
    validation_summary_path: str,
    validation_log_path: str,
    validation_manifest_path: str,
    validated_bank_path: str,
    repository_root: str,
) -> Dict[str, Any]:
    """Build the confirmatory checkpoint after independent validation passes."""
    with open(prevalidation_checkpoint_path, "r", encoding="utf-8") as handle:
        prevalidation = json.load(handle)
    prevalidation_audit = audit_v6_prevalidation_checkpoint(
        prevalidation, repository_root
    )
    if not prevalidation_audit["pass"]:
        raise ValueError("V6 pre-validation checkpoint no longer passes its audit")
    final_bank = V6TriadBank.load(validated_bank_path)
    checkpoint: Dict[str, Any] = {
        "checkpoint_version": V6_FINAL_CHECKPOINT_VERSION,
        "status": V6_FINAL_CHECKPOINT_STATUS,
        "pre_confirmatory_outcomes": True,
        "prevalidation_checkpoint": v6_artifact_reference(
            prevalidation_checkpoint_path, repository_root
        ),
        "official_run_ids": json.loads(
            json.dumps(prevalidation["official_run_ids"])
        ),
        "independent_validation": v6_artifact_reference(
            validation_summary_path, repository_root
        ),
        "independent_validation_log": v6_artifact_reference(
            validation_log_path, repository_root, canonical_json=False
        ),
        "independent_validation_manifest": v6_artifact_reference(
            validation_manifest_path, repository_root
        ),
        "validated_bank": {
            **v6_artifact_reference(validated_bank_path, repository_root),
            "bank_sha256": final_bank.sha256(),
            "bank_content_sha256": bank_content_sha256(final_bank.payload),
        },
        "confirmatory_schedule": json.loads(
            json.dumps(prevalidation["confirmatory_schedule"])
        ),
    }
    audit = audit_v6_final_checkpoint(checkpoint, repository_root)
    if not audit["pass"]:
        failed = sorted(name for name, passed in audit["checks"].items() if not passed)
        raise ValueError(
            "refusing to freeze V6 final checkpoint: %s" % ", ".join(failed)
        )
    return checkpoint


def audit_v6_final_checkpoint(
    checkpoint: Mapping[str, Any], repository_root: str
) -> Dict[str, Any]:
    """Prove validation and replay pending-to-validated finalization."""
    checks: Dict[str, bool] = {
        "checkpoint_version": checkpoint.get("checkpoint_version")
        == V6_FINAL_CHECKPOINT_VERSION,
        "checkpoint_status": checkpoint.get("status") == V6_FINAL_CHECKPOINT_STATUS,
        "pre_confirmatory_outcomes": checkpoint.get("pre_confirmatory_outcomes")
        is True,
    }
    prevalidation, pre_checks, _prevalidation_path = _load_checkpoint_json_reference(
        checkpoint.get("prevalidation_checkpoint", {}), repository_root
    )
    validation, validation_checks, _validation_path = _load_checkpoint_json_reference(
        checkpoint.get("independent_validation", {}), repository_root
    )
    records, log_checks, log_path = _load_checkpoint_log_reference(
        checkpoint.get("independent_validation_log", {}), repository_root
    )
    manifest, manifest_checks, manifest_path = _load_checkpoint_json_reference(
        checkpoint.get("independent_validation_manifest", {}), repository_root
    )
    final_payload, final_checks, final_path = _load_checkpoint_json_reference(
        checkpoint.get("validated_bank", {}), repository_root
    )
    for prefix, values in (
        ("prevalidation_checkpoint", pre_checks),
        ("validation_summary", validation_checks),
        ("validation_log", log_checks),
        ("validation_manifest", manifest_checks),
        ("validated_bank", final_checks),
    ):
        _prefix_checks(checks, prefix, values)

    prevalidation_audit: Dict[str, Any] = {}
    if prevalidation:
        try:
            prevalidation_audit = audit_v6_prevalidation_checkpoint(
                prevalidation, repository_root
            )
        except (KeyError, TypeError, ValueError, RuntimeError):
            pass
    checks["prevalidation_checkpoint_recomputed"] = (
        prevalidation_audit.get("pass") is True
    )

    pending: Optional[V6TriadBank] = None
    protocol: Dict[str, Any] = {}
    if prevalidation_audit.get("pass") is True:
        pending_ref = prevalidation.get("pending_bank", {})
        pending_path, pending_inside = _checkpoint_reference_path(
            pending_ref, repository_root
        )
        protocol_ref = prevalidation.get("calibration_protocol", {})
        protocol, protocol_checks, _ = _load_checkpoint_json_reference(
            protocol_ref, repository_root
        )
        _prefix_checks(checks, "reloaded_protocol", protocol_checks)
        try:
            if pending_inside:
                pending = V6TriadBank.load(pending_path)
        except (OSError, ValueError, TypeError):
            pass
    else:
        checks.update(
            {
                "reloaded_protocol_path_inside_root": False,
                "reloaded_protocol_exists": False,
                "reloaded_protocol_json_object": False,
                "reloaded_protocol_file_sha256": False,
                "reloaded_protocol_canonical_sha256": False,
            }
        )

    manifest_proof = manifest.get("frozen_protocol", {}).get(
        "prevalidation_checkpoint", {}
    )
    checks.update(
        {
            "pending_bank_reloaded": pending is not None,
            "validation_manifest_checkpoint_binding": bool(manifest_proof)
            and manifest_proof
            == checkpoint.get("prevalidation_checkpoint", {}),
            "validation_manifest_log_hash": log_checks.get("file_sha256") is True
            and manifest.get("log_file_sha256")
            == checkpoint.get("independent_validation_log", {}).get("file_sha256"),
            "validation_summary_log_hash": log_checks.get("file_sha256") is True
            and validation.get("validation_log_file_sha256")
            == checkpoint.get("independent_validation_log", {}).get("file_sha256"),
            "validation_summary_manifest_hash": manifest_checks.get("file_sha256")
            is True
            and validation.get("validation_manifest_file_sha256")
            == checkpoint.get("independent_validation_manifest", {}).get(
                "file_sha256"
            ),
        }
    )

    recomputed_plan: Dict[str, Any] = {}
    run_audit: Dict[str, Any] = {}
    if pending is not None and protocol and manifest and records:
        try:
            recomputed_plan = audit_v6_calibration_plan(
                protocol,
                pending,
                manifest.get("provider", {}),
                V6_VALIDATION_MODE,
                int(manifest.get("schedule", {}).get("seed", -1)),
                manifest.get("schedule", {}).get("n_episode_blocks"),
                repository_root,
                prevalidation_checkpoint=prevalidation,
                run_id=str(manifest.get("run_id", "")),
            )
            run_audit = audit_v6_calibration_run(
                records, manifest, pending, V6_VALIDATION_MODE
            )
        except (KeyError, TypeError, ValueError, RuntimeError):
            pass
    checks.update(
        {
            "validation_plan_recomputed": recomputed_plan.get("pass") is True,
            "validation_plan_matches_manifest": bool(recomputed_plan)
            and manifest.get("frozen_protocol", {}).get("plan_audit")
            == recomputed_plan,
            "validation_run_recomputed": run_audit.get("pass") is True,
        }
    )

    expected_validation: Dict[str, Any] = {}
    expected_final: Dict[str, Any] = {}
    if pending is not None and run_audit.get("pass") is True:
        try:
            expected_validation = evaluate_v6_bank_validation(records, pending)
            expected_validation["calibration_run_audit"] = run_audit
            expected_validation["validation_manifest_file_sha256"] = file_sha256(
                manifest_path
            )
            expected_validation["validation_log_file_sha256"] = file_sha256(log_path)
            if expected_validation.get("pass") is True:
                expected_final = finalize_validated_v6_bank(
                    pending.payload, expected_validation
                )
        except (KeyError, TypeError, ValueError, RuntimeError):
            expected_validation = {}
            expected_final = {}
    checks.update(
        {
            "validation_pass_recomputed": expected_validation.get("pass") is True,
            "validation_summary_exactly_recomputed": bool(expected_validation)
            and validation == expected_validation,
            "validated_bank_transition_recomputed": bool(expected_final)
            and final_payload == expected_final,
        }
    )

    final_bank: Optional[V6TriadBank] = None
    try:
        if final_payload:
            final_bank = V6TriadBank.load(final_path)
    except (OSError, ValueError, TypeError):
        pass
    final_ref = checkpoint.get("validated_bank", {})
    checks.update(
        {
            "validated_bank_structural_audit": final_bank is not None,
            "validated_bank_status": final_bank is not None
            and final_bank.payload.get("status") == V6_SELECTED_BANK_STATUS,
            "validated_bank_hash": final_bank is not None
            and final_ref.get("bank_sha256") == final_bank.sha256(),
            "validated_bank_content_hash": final_bank is not None
            and final_ref.get("bank_content_sha256")
            == bank_content_sha256(final_bank.payload),
        }
    )

    expected_schedule: Dict[str, Any] = {}
    if protocol and pending is not None:
        try:
            expected_schedule = build_v6_confirmatory_schedule_metadata(
                protocol,
                pending,
                selected_episode_seeds=prevalidation.get(
                    "confirmatory_schedule", {}
                ).get("selected_episode_seeds"),
            )
        except (KeyError, TypeError, ValueError, RuntimeError):
            pass
    checks["confirmatory_schedule_matches_prevalidation"] = checkpoint.get(
        "confirmatory_schedule"
    ) == prevalidation.get("confirmatory_schedule")
    checks["official_run_ids_match_prevalidation"] = checkpoint.get(
        "official_run_ids"
    ) == prevalidation.get("official_run_ids")
    checks["confirmatory_schedule_recomputed"] = bool(expected_schedule) and checkpoint.get(
        "confirmatory_schedule"
    ) == expected_schedule
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "checkpoint_canonical_sha256": canonical_sha256(checkpoint),
        "validated_bank_sha256": (
            final_bank.sha256() if final_bank is not None else None
        ),
        "validated_bank_content_sha256": (
            bank_content_sha256(final_bank.payload)
            if final_bank is not None
            else None
        ),
        "confirmatory_schedule": expected_schedule,
        "prevalidation_checkpoint_sha256": prevalidation_audit.get(
            "checkpoint_canonical_sha256"
        ),
    }
