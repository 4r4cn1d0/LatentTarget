"""Fail-closed confirmatory analysis for randomized controlled-choice V6.

V6 reuses only low-level V5 descriptive window helpers. Its causal estimands
come from prospective matched episode-seed-bundle assignments, including a
stable-old counterfactual for silent swaps. Records and manifests are never
relabelled as V5. This module performs native allocation, replication,
sealed-scenario, frozen-checkpoint, and raw-record replay audits, then routes
the co-primary estimates/tests/gates through the same helper used by power.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import stat
from collections import Counter, defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from config import (
    CONTROLLED_V6_ANALYSIS_CONFIG,
    CONTROLLED_V6_GATE_THRESHOLDS,
    CONTROLLED_V6_PAID_PREFLIGHT_RECEIPT_PATH,
    CONTROLLED_V6_RANDOMIZATION_SEED,
    CONTROLLED_V6_VERSION,
    STRATEGIES,
    ControlledExperimentConfig,
    ControlledTargetParams,
    ModelConfig,
)
from .controlled_analysis import (
    _bootstrap_mean,
    _condition_rows,
    _episode_groups,
    _mean,
    _trajectory,
    audit_controlled_design,
)
from .controlled_v5_analysis import (
    V5_HELDOUT_START,
    V5_N_ROUNDS,
    V5_SWAP_ROUND,
    V5_WINDOW_SIZE,
    _blocked_descriptive,
    _frame_balance,
    _paired_values_and_blocks,
    _stable_episode_summaries,
    _swap_episode_summaries,
    _transition_metrics,
)
from .controlled_experiment import (
    CONTROLLED_REQUIRED_FIELDS,
    ControlledDonorRegistry,
    build_controlled_episode_specs,
    controlled_episode_seed,
    controlled_round_identity,
    validate_controlled_record,
)
from .controlled_focal_agent import (
    ControlledHistoryEntry,
    build_controlled_prompt,
    parse_controlled_choice,
)
from .controlled_messages import candidate_for_slot
from .controlled_protocol import ControlledProtocol
from .controlled_target import ControlledTarget
from .controlled_v6_messages import (
    V6_SELECTED_BANK_STATUS,
    V6TriadBank,
    audit_v6_bank_payload,
)
from .controlled_v6_power import (
    V6_ALLOCATION_RNG_ROOT,
    V6_POWER_CONTRACT_SHA256,
    V6_STUDY_SCHEMA_VERSION,
    analyze_v6_bundle_study,
    exact_one_sided_bundle_randomization_test,
    reconstruct_v6_bundle_assignments,
)
from .controlled_v6_randomization import (
    V6_HISTORY_FAMILY,
    V6_SWAP_FAMILY,
    audit_v6_allocation_schedule,
    v6_allocation_schedule,
    v6_regime_assignment,
)
from .logging_utils import open_regular_read_descriptor, strict_json_load
from .scenarios import V6_CONFIRMATORY_SCENARIOS, v6_scenario_sequence
from .seeding import derive_seed
from .v6_protocol_gate import (
    V6_FINAL_CHECKPOINT_STATUS,
    audit_v6_final_checkpoint,
)


V6_REQUIRED_CONDITIONS: Tuple[str, ...] = (
    "full_history",
    "no_history",
    "shuffled_history",
    "random_target",
    "swap",
    "swap_control",
)
V6_N_ROUNDS = 24
V6_SWAP_ROUND = 12
V6_HELDOUT_START = 19
V6_WINDOW_SIZE = 6
V6_FROZEN_CHECKPOINT_STATUS = V6_FINAL_CHECKPOINT_STATUS
V6_CONFIRMATORY_SCENARIO_IDS: Tuple[str, ...] = tuple(
    scenario.id for scenario in V6_CONFIRMATORY_SCENARIOS
)
V6_CO_PRIMARY_MINIMUMS = {
    "minimum_stable_difference_in_differences": 0.10,
    "minimum_revision_shift": 0.15,
    "minimum_adjusted_new_target_gain": 0.05,
    "minimum_adjusted_old_target_drop": 0.05,
}


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


V6_CONFIRMATORY_SCENARIO_SHA256 = _canonical_sha256(
    [scenario.as_dict() for scenario in V6_CONFIRMATORY_SCENARIOS]
)


def _file_sha256(path: str, *, root: Optional[str] = None) -> str:
    digest = hashlib.sha256()
    descriptor = open_regular_read_descriptor(
        path, root=root, label="V6 analysis input"
    )
    with os.fdopen(descriptor, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_object(
    path: str,
    *,
    root: Optional[str],
    label: str,
) -> Dict[str, Any]:
    descriptor = open_regular_read_descriptor(path, root=root, label=label)
    with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
        payload = strict_json_load(handle)
    if type(payload) is not dict:
        raise ValueError("%s must be a JSON object" % label)
    return payload


def _repository_path(root: str, relative: Any) -> Optional[str]:
    """Resolve one canonical repository-relative contract path fail-closed."""
    if not isinstance(relative, str) or not relative or os.path.isabs(relative):
        return None
    if os.path.normpath(relative) != relative or relative in {".", os.pardir}:
        return None
    root = os.path.abspath(root)
    absolute = os.path.abspath(os.path.join(root, relative))
    resolved_root = os.path.realpath(root)
    resolved = os.path.realpath(absolute)
    try:
        if os.path.commonpath([root, absolute]) != root or os.path.commonpath(
            [resolved_root, resolved]
        ) != resolved_root:
            return None
    except ValueError:
        return None
    try:
        root_metadata = os.lstat(root)
    except OSError:
        return None
    if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(
        root_metadata.st_mode
    ):
        return None
    current = root
    for component in os.path.relpath(absolute, root).split(os.sep):
        current = os.path.join(current, component)
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            break
        except OSError:
            return None
        if stat.S_ISLNK(metadata.st_mode):
            return None
        if current != absolute and not stat.S_ISDIR(metadata.st_mode):
            return None
    return absolute


def _scientific_equal(observed: Any, expected: Any) -> bool:
    """Exact JSON equality, including numeric and boolean type identity."""
    if type(observed) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(observed) == set(expected) and all(
            _scientific_equal(observed[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(observed) == len(expected) and all(
            _scientific_equal(left, right)
            for left, right in zip(observed, expected)
        )
    if isinstance(expected, float):
        return math.isfinite(observed) and observed == expected
    return observed == expected


def _strict_record_schema_error(row: Mapping[str, Any]) -> Optional[str]:
    """Reject additions and type-coercible nested V6 record structures."""
    expected_keys = set(CONTROLLED_REQUIRED_FIELDS)
    observed_keys = set(row)
    if observed_keys != expected_keys:
        return "record keys differ: missing=%r unexpected=%r" % (
            sorted(expected_keys - observed_keys),
            sorted(observed_keys - expected_keys),
        )
    candidates = row.get("candidates")
    if type(candidates) is not list or any(type(item) is not dict for item in candidates):
        return "candidates must be a JSON array of objects"
    candidate_keys = {
        "slot",
        "candidate_id",
        "message",
        "frame",
        "split",
        "template_index",
    }
    if any(set(item) != candidate_keys for item in candidates):
        return "candidate objects must use the exact V6 candidate schema"
    visible_candidates = row.get("visible_candidates")
    if type(visible_candidates) is not list or any(
        type(item) is not dict or set(item) != {"slot", "message"}
        for item in visible_candidates
    ):
        return "visible candidates must use the exact focal-visible schema"
    history = row.get("visible_history")
    if type(history) is not list or any(type(item) is not dict for item in history):
        return "visible_history must be a JSON array of objects"
    expected_history_keys = {
        "round",
        "scenario_title",
        "selected_message",
        "choice",
    }
    if row.get("focal_mode") == "elicited":
        expected_history_keys |= {"predicted_p_a", "candidate_messages"}
    if any(set(item) != expected_history_keys for item in history):
        return "visible history entries must use the exact focal-visible schema"
    scenario = row.get("scenario")
    if type(scenario) is not dict or set(scenario) != {
        "id",
        "title",
        "context",
        "option_a",
        "option_b",
    }:
        return "scenario must use the exact sealed-scenario schema"
    return None


def reconcile_v6_records_against_runtime(
    records: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    cfg: ControlledExperimentConfig,
    protocol: ControlledProtocol,
    run_id: str,
    *,
    allow_complete_episode_prefix: bool = False,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Replay every outcome-bearing field from raw choices and frozen inputs.

    The JSONL's ``focal_output_raw`` is the only focal-choice input. Candidate
    identity, selected frame/message, prompt-visible history, simulator
    probability, random draw, and A/B outcome are all regenerated.  The
    returned records are the regenerated scientific rows; callers must use
    them for analysis rather than trusting duplicated convenience fields in
    the log.

    A prefix is accepted only for pre-provider resume auditing and only when it
    contains whole episodes in exact official order.
    """
    if any(type(row) is not dict for row in records):
        raise TypeError("V6 raw records must be JSON objects")
    observed_records = [dict(row) for row in records]
    specs = build_controlled_episode_specs(cfg)
    expected_total = sum(spec.n_rounds for spec in specs)
    whole_episode_prefix = (
        bool(observed_records)
        and len(observed_records) % cfg.n_rounds == 0
    )
    count_ok = (
        len(observed_records) <= expected_total and whole_episode_prefix
        if allow_complete_episode_prefix
        else len(observed_records) == expected_total
    )

    schema_errors: List[Dict[str, Any]] = []
    mismatches: List[Dict[str, Any]] = []
    mismatch_count = 0
    reconstructed: List[Dict[str, Any]] = []
    donors = ControlledDonorRegistry()
    record_index = 0
    provider = manifest.get("provider", {})
    if not isinstance(provider, Mapping):
        provider = {}
    expected_provider = provider.get("provider")
    expected_model = provider.get("model")

    def note_mismatch(
        row: Mapping[str, Any], field: str, observed: Any, expected: Any
    ) -> None:
        nonlocal mismatch_count
        mismatch_count += 1
        if len(mismatches) < 50:
            mismatches.append(
                {
                    "record_index": record_index,
                    "episode_id": str(row.get("episode_id", "")),
                    "round": row.get("round"),
                    "field": field,
                    "observed": observed,
                    "expected": expected,
                }
            )

    for spec in specs:
        if record_index >= len(observed_records):
            break
        scenarios = protocol.scenario_sequence(
            spec.episode_index, spec.n_rounds, cfg.seed
        )
        if scenarios is None or len(scenarios) != spec.n_rounds:
            raise ValueError("V6 replay protocol returned an incomplete scenario schedule")

        own_history: List[ControlledHistoryEntry] = []
        donor_history: List[ControlledHistoryEntry] = []
        donor_episode_id: Optional[str] = None
        if spec.condition.history_mode == "shuffled":
            try:
                donor_episode_id, donor_history = donors.donor_for(
                    spec.episode_index, spec.initial_target_type
                )
            except KeyError:
                donor_episode_id, donor_history = None, []

        episode_seed = controlled_episode_seed(spec, cfg, protocol.version)
        for round_index in range(1, spec.n_rounds + 1):
            if record_index >= len(observed_records):
                break
            row = observed_records[record_index]
            strict_schema_error = _strict_record_schema_error(row)
            if strict_schema_error is not None and len(schema_errors) < 50:
                schema_errors.append(
                    {
                        "record_index": record_index,
                        "episode_id": str(row.get("episode_id", "")),
                        "round": row.get("round"),
                        "error": strict_schema_error,
                    }
                )
            try:
                validate_controlled_record(row)
            except (KeyError, TypeError, ValueError) as exc:
                if len(schema_errors) < 50:
                    schema_errors.append(
                        {
                            "record_index": record_index,
                            "episode_id": str(row.get("episode_id", "")),
                            "round": row.get("round"),
                            "error": "%s: %s" % (type(exc).__name__, exc),
                        }
                    )

            scenario = scenarios[round_index - 1]
            candidates = protocol.candidate_set(
                scenario=scenario,
                episode_index=spec.episode_index,
                round_index=round_index,
                heldout_start_round=cfg.heldout_start_round,
                seed=cfg.seed,
            )
            (
                round_seed,
                target_draw_seed,
                generation_id,
                replication_group_id,
            ) = controlled_round_identity(
                spec, cfg, protocol.version, round_index
            )
            active_type = spec.active_type(round_index)

            if spec.condition.history_mode == "none":
                visible_history: List[ControlledHistoryEntry] = []
                history_source_episode_id = None
            elif spec.condition.history_mode == "shuffled":
                visible_history = list(donor_history[: round_index - 1])
                history_source_episode_id = donor_episode_id
            else:
                visible_history = list(own_history)
                history_source_episode_id = spec.episode_id

            prompt = build_controlled_prompt(
                scenario=scenario,
                candidates=candidates,
                history=visible_history,
                round_index=round_index,
                n_rounds=spec.n_rounds,
                show_history=spec.condition.history_mode != "none",
                focal_mode=spec.condition.focal_mode,
                context={},
            )
            raw_value = row.get("focal_output_raw")
            raw = raw_value if isinstance(raw_value, str) else ""
            parsed = parse_controlled_choice(raw, spec.condition.focal_mode, round_seed)
            selected = candidate_for_slot(candidates, parsed.selected_slot)
            response = ControlledTarget(
                hidden_type=active_type,
                mode=spec.condition.target_mode,
                params=cfg.target_params,
            ).respond(selected.frame, np.random.default_rng(target_draw_seed))

            belief_primary_slot = None
            belief_primary_frame = None
            belief_matches_target = None
            selected_prediction_brier = None
            if parsed.beliefs_valid and parsed.predicted_p_a is not None:
                belief_primary_slot = max(
                    (1, 2, 3),
                    key=lambda slot: (parsed.predicted_p_a[str(slot)], -slot),
                )
                belief_primary_frame = candidate_for_slot(
                    candidates, belief_primary_slot
                ).frame
                belief_matches_target = belief_primary_frame == active_type
                observed_a = 1.0 if response.choice == "A" else 0.0
                selected_prediction_brier = float(
                    (parsed.predicted_p_a[str(selected.slot)] - observed_a) ** 2
                )

            expected: Dict[str, Any] = {
                "task_version": protocol.version,
                "experiment_id": cfg.experiment_id,
                "run_id": run_id,
                "condition": spec.condition.name,
                "focal_mode": spec.condition.focal_mode,
                "episode_id": spec.episode_id,
                "episode_index": spec.episode_index,
                "round": round_index,
                "n_rounds": spec.n_rounds,
                "hidden_target_type": active_type,
                "initial_target_type": spec.initial_target_type,
                "final_target_type": spec.final_target_type,
                "swap_condition": spec.swaps,
                "swap_round": spec.swap_round,
                "swap_has_occurred": bool(
                    spec.swaps and round_index > cfg.swap_round
                ),
                "rounds_since_swap": (
                    round_index - cfg.swap_round if spec.swaps else None
                ),
                "target_mode": spec.condition.target_mode,
                "history_mode": spec.condition.history_mode,
                "history_source_episode_id": history_source_episode_id,
                "scenario_id": scenario.id,
                "scenario": scenario.as_dict(),
                "candidate_split": candidates[0].split,
                "candidates": [candidate.as_dict() for candidate in candidates],
                "visible_candidates": [
                    candidate.visible_dict() for candidate in candidates
                ],
                "focal_system_prompt": prompt.system,
                "focal_user_prompt": prompt.user,
                "selection_valid": parsed.selection_valid,
                "beliefs_valid": parsed.beliefs_valid,
                "fallback_used": parsed.fallback_used,
                "parse_error": parsed.parse_error,
                "selected_slot": selected.slot,
                "selected_candidate_id": selected.candidate_id,
                "selected_message": selected.message,
                "selected_frame": selected.frame,
                "strategy_match": selected.frame == active_type,
                "predicted_p_a": parsed.predicted_p_a,
                "belief_primary_slot": belief_primary_slot,
                "belief_primary_frame": belief_primary_frame,
                "belief_matches_target": belief_matches_target,
                "selected_prediction_brier": selected_prediction_brier,
                "visible_history": [
                    entry.visible_dict(
                        include_predictions=spec.condition.focal_mode == "elicited"
                    )
                    for entry in visible_history
                ],
                "target_p_a": response.p_a,
                "target_choice": response.choice,
                "target_uniform_draw": response.uniform_draw,
                "target_success": response.choice == "A",
                "episode_seed": episode_seed,
                "round_seed": round_seed,
                "target_draw_seed": target_draw_seed,
                "master_seed": cfg.seed,
                "model_name": expected_model,
                "provider": expected_provider,
                "pair_family": spec.pair_family,
                "pair_id": spec.pair_id,
                "pair_slot": spec.pair_slot,
                "allocation_seed": spec.allocation_seed,
                "allocation_bit": spec.allocation_bit,
                "assigned_regime": spec.assigned_regime
                or spec.condition.name,
                "stable_counterfactual": spec.stable_counterfactual,
                "nominal_transition": spec.nominal_transition,
                "generation_id": generation_id,
                "replication_group_id": replication_group_id,
                "allocation_schedule_sha256": (
                    spec.allocation_schedule_sha256
                ),
            }
            if not isinstance(raw_value, str):
                note_mismatch(row, "focal_output_raw_type", type(raw_value).__name__, "str")
            for field, expected_value in expected.items():
                observed_value = row.get(field)
                if not _scientific_equal(observed_value, expected_value):
                    note_mismatch(row, field, observed_value, expected_value)
            if not isinstance(row.get("timestamp"), str) or not row.get("timestamp"):
                note_mismatch(row, "timestamp", row.get("timestamp"), "non-empty string")

            canonical_row = dict(row)
            canonical_row.update(expected)
            reconstructed.append(canonical_row)
            history_entry = ControlledHistoryEntry(
                round=round_index,
                scenario_id=scenario.id,
                scenario_title=scenario.title,
                selected_slot=selected.slot,
                selected_message=selected.message,
                selected_frame=selected.frame,
                choice=response.choice,
                predicted_p_a=parsed.predicted_p_a,
                candidate_messages={
                    str(candidate.slot): candidate.message
                    for candidate in candidates
                },
            )
            own_history.append(history_entry)
            record_index += 1

        if spec.condition.name == "full_history" and len(own_history) == spec.n_rounds:
            donors.add(
                spec.episode_index,
                spec.initial_target_type,
                spec.episode_id,
                own_history,
            )

    checks = {
        "record_count_matches_frozen_schedule": count_ok,
        "whole_episode_prefix": whole_episode_prefix,
        "no_records_beyond_frozen_schedule": record_index == len(observed_records),
        "every_record_passes_base_schema": not schema_errors,
        "all_replayed_fields_exact": mismatch_count == 0,
        "strict_raw_choices_only": all(
            row.get("focal_output_raw") in {"1", "2", "3"}
            for row in observed_records
        ),
        "reconstructed_record_count_exact": len(reconstructed)
        == len(observed_records),
    }
    return (
        {
            "pass": all(checks.values()),
            "checks": checks,
            "allow_complete_episode_prefix": allow_complete_episode_prefix,
            "expected_total_records": expected_total,
            "observed_records": len(observed_records),
            "schema_errors": schema_errors,
            "mismatch_count": mismatch_count,
            "mismatches": mismatches,
            "reconstructed_records_canonical_sha256": _canonical_sha256(
                reconstructed
            ),
        },
        reconstructed,
    )


def audit_v6_launch_receipt_payload(
    receipt: Mapping[str, Any],
    *,
    official_run_id: str,
    canonical_out_dir: str,
    checkpoint_file_sha256: str,
    checkpoint_canonical_sha256: str,
    selected_schedule_sha256: str,
    randomization_schedule_sha256: str,
    validated_bank_sha256: str,
    model_id: str,
    revision: Any,
    config: Mapping[str, Any],
    expected_focal_runtime: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Verify the immutable single-launch reservation's exact binding."""
    expected_keys = {
        "kind",
        "schema_version",
        "status",
        "official_run_id",
        "canonical_out_dir",
        "final_checkpoint_file_sha256",
        "final_checkpoint_canonical_sha256",
        "selected_schedule_sha256",
        "randomization_schedule_sha256",
        "validated_bank_sha256",
        "model",
        "config_canonical_sha256",
        "created_at_utc",
        "launch_nonce",
        "receipt_id",
    }
    if expected_focal_runtime is not None:
        expected_keys.add("focal_runtime")
    receipt_without_id = {
        key: value for key, value in receipt.items() if key != "receipt_id"
    }
    try:
        calculated_id: Optional[str] = _canonical_sha256(receipt_without_id)
    except (TypeError, ValueError):
        calculated_id = None
    timestamp = receipt.get("created_at_utc")
    canonical_timestamp = False
    if type(timestamp) is str:
        try:
            parsed_timestamp = dt.datetime.fromisoformat(timestamp)
            canonical_timestamp = (
                parsed_timestamp.tzinfo is not None
                and parsed_timestamp.utcoffset() == dt.timedelta(0)
                and timestamp.endswith("+00:00")
                and parsed_timestamp.isoformat() == timestamp
            )
        except ValueError:
            canonical_timestamp = False
    model = receipt.get("model")
    checks = {
        "top_level_schema": type(receipt) is dict
        and set(receipt) == expected_keys,
        "kind": type(receipt.get("kind")) is str
        and receipt.get("kind") == "controlled_v6_official_launch_receipt",
        "schema_version": type(receipt.get("schema_version")) is str
        and receipt.get("schema_version")
        == "2.0",
        "status": type(receipt.get("status")) is str
        and receipt.get("status") == "OFFICIAL_RUN_RESERVED",
        "official_run_id": type(receipt.get("official_run_id")) is str
        and receipt.get("official_run_id") == official_run_id,
        "canonical_out_dir": type(receipt.get("canonical_out_dir")) is str
        and receipt.get("canonical_out_dir") == canonical_out_dir,
        "checkpoint_file_sha256": type(
            receipt.get("final_checkpoint_file_sha256")
        )
        is str
        and receipt.get("final_checkpoint_file_sha256")
        == checkpoint_file_sha256,
        "checkpoint_canonical_sha256": type(
            receipt.get("final_checkpoint_canonical_sha256")
        )
        is str
        and receipt.get("final_checkpoint_canonical_sha256")
        == checkpoint_canonical_sha256,
        "selected_schedule_sha256": type(
            receipt.get("selected_schedule_sha256")
        )
        is str
        and receipt.get("selected_schedule_sha256")
        == selected_schedule_sha256,
        "randomization_schedule_sha256": type(
            receipt.get("randomization_schedule_sha256")
        )
        is str
        and receipt.get("randomization_schedule_sha256")
        == randomization_schedule_sha256,
        "validated_bank_sha256": type(
            receipt.get("validated_bank_sha256")
        )
        is str
        and receipt.get("validated_bank_sha256") == validated_bank_sha256,
        "model_schema": type(model) is dict
        and set(model) == {"id", "revision"},
        "model": type(model) is dict
        and _scientific_equal(
            model, {"id": model_id, "revision": revision}
        ),
        "focal_runtime": (
            "focal_runtime" not in receipt
            if expected_focal_runtime is None
            else type(receipt.get("focal_runtime")) is dict
            and _scientific_equal(
                receipt.get("focal_runtime"), dict(expected_focal_runtime)
            )
        ),
        "config_canonical_sha256": type(
            receipt.get("config_canonical_sha256")
        )
        is str
        and receipt.get("config_canonical_sha256")
        == _canonical_sha256(config),
        "created_at_utc": canonical_timestamp,
        "launch_nonce": type(receipt.get("launch_nonce")) is str
        and re.fullmatch(r"[0-9a-f]{64}", receipt["launch_nonce"])
        is not None,
        "receipt_id": type(receipt.get("receipt_id")) is str
        and receipt.get("receipt_id") == calculated_id,
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "receipt_id": calculated_id,
    }


def _replay_runtime_from_checkpoint(
    manifest: Mapping[str, Any],
    frozen_spec: Mapping[str, Any],
    checkpoint_root: str,
    checkpoint_audit: Mapping[str, Any],
) -> Tuple[ControlledExperimentConfig, ControlledProtocol, str]:
    """Build a no-provider replay runtime from the audited final checkpoint."""
    contract = checkpoint_audit.get("analysis_contract", {})
    if not isinstance(contract, Mapping):
        raise ValueError("V6 checkpoint audit has no analysis contract")
    experiment = contract.get("experiment", {})
    model = contract.get("primary_model", {})
    target = contract.get("target", {})
    if not all(isinstance(value, Mapping) for value in (experiment, model, target)):
        raise ValueError("V6 analysis contract is incomplete")

    bank_reference = frozen_spec.get("validated_bank", {})
    if not isinstance(bank_reference, Mapping):
        raise ValueError("V6 final checkpoint has no validated-bank reference")
    bank_path = _repository_path(checkpoint_root, bank_reference.get("path"))
    if bank_path is None or not os.path.isfile(bank_path):
        raise ValueError("V6 validated-bank path is not a frozen repository file")
    bank_payload = _load_json_object(
        bank_path,
        root=checkpoint_root,
        label="V6 validated bank",
    )
    bank_audit = audit_v6_bank_payload(bank_payload)
    if bank_audit.get("pass") is not True:
        failed = sorted(
            name
            for name, passed in bank_audit.get("checks", {}).items()
            if not passed
        )
        raise ValueError("invalid V6 triad bank: %s" % ", ".join(failed))
    bank = V6TriadBank(payload=bank_payload, source_path=bank_path)
    if bank.sha256() != contract.get("message_bank", {}).get("sha256"):
        raise ValueError("V6 replay bank differs from the analysis contract")
    if bank.manifest().get("status") != V6_SELECTED_BANK_STATUS:
        raise ValueError("V6 replay bank is not independently validated")

    config_payload = manifest.get("config", {})
    config_model = (
        config_payload.get("model", {})
        if isinstance(config_payload, Mapping)
        else {}
    )
    if not isinstance(config_model, Mapping):
        config_model = {}
    canonical_out_dir = _repository_path(
        checkpoint_root, experiment.get("canonical_out_dir")
    )
    if canonical_out_dir is None:
        raise ValueError("V6 canonical output directory is invalid")
    cfg = ControlledExperimentConfig(
        experiment_id=str(config_payload.get("experiment_id", "")),
        n_rounds=int(experiment["n_rounds"]),
        swap_round=int(experiment["swap_round"]),
        heldout_start_round=int(experiment["heldout_start_round"]),
        n_episode_seeds=int(experiment["n_episode_seeds"]),
        seed=int(experiment["master_seed"]),
        randomization_seed=int(experiment["randomization_seed"]),
        conditions=[str(value) for value in experiment["conditions"]],
        target_params=ControlledTargetParams(
            p_match=float(target["p_match"]),
            p_mismatch=float(target["p_mismatch"]),
            p_random=float(target["p_random"]),
        ),
        model=ModelConfig(
            provider=str(config_model.get("provider", "")),
            model=str(model.get("id", "")),
            revision=model.get("revision"),
            temperature=float(config_model.get("temperature", 0.0)),
            max_tokens=int(config_model.get("max_tokens", 0)),
        ),
        out_dir=canonical_out_dir,
    )
    protocol = ControlledProtocol(
        version=CONTROLLED_V6_VERSION,
        candidate_builder=bank.candidate_set,
        bank_manifest_builder=bank.manifest,
        bank_hash_builder=bank.sha256,
        strict_selection=True,
        constrained_choices=("1", "2", "3"),
        bank_source=bank_path,
        scenario_sequence_builder=lambda episode_index, n_rounds, seed: (
            v6_scenario_sequence(
                "confirmatory", episode_index, n_rounds, seed
            )
        ),
    )
    return cfg, protocol, str(contract.get("official_run_id", ""))


def _v6_thresholds() -> Dict[str, float]:
    """Return the frozen V6 gates, rejecting accidental V5 threshold reuse."""
    thresholds = dict(CONTROLLED_V6_GATE_THRESHOLDS)
    drift = {
        key: thresholds.get(key)
        for key, expected in V6_CO_PRIMARY_MINIMUMS.items()
        if thresholds.get(key) != expected
    }
    if drift:
        expected = ", ".join(
            "%s=%s" % (key, value)
            for key, value in V6_CO_PRIMARY_MINIMUMS.items()
        )
        raise ValueError(
            "CONTROLLED_V6_GATE_THRESHOLDS drifted from the frozen "
            "confirmatory contract (%s); observed %r" % (expected, drift)
        )
    return thresholds


def _float_equal(left: Any, right: Any) -> bool:
    return (
        type(left) is float
        and type(right) is float
        and math.isfinite(left)
        and math.isfinite(right)
        and left == right
    )


def _scenario_contract_from_spec(
    frozen_spec: Mapping[str, Any],
) -> Tuple[Any, Any, Any]:
    experiment = frozen_spec.get("experiment", {})
    if not isinstance(experiment, Mapping):
        experiment = {}
    return (
        experiment.get("scenario_set", frozen_spec.get("scenario_set")),
        experiment.get("scenario_ids", frozen_spec.get("scenario_ids")),
        experiment.get(
            "scenario_set_canonical_sha256",
            frozen_spec.get("scenario_set_canonical_sha256"),
        ),
    )


def audit_frozen_v6_manifest(
    manifest: Mapping[str, Any],
    frozen_spec: Mapping[str, Any],
    repository_root: Optional[str],
    checkpoint_file_sha256: Optional[str] = None,
    log_path: Optional[str] = None,
    log_file_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """Audit a completed V6 run against its pre-outcome checkpoint.

    The canonical checkpoint hash is compared against the immutable provenance
    embedded by the runner.  This function does not rewrite either object or
    route through the V5 manifest audit.
    """
    thresholds = _v6_thresholds()
    checkpoint_audit: Dict[str, Any] = {}
    if repository_root:
        try:
            checkpoint_audit = audit_v6_final_checkpoint(
                frozen_spec, repository_root
            )
        except (KeyError, OSError, TypeError, ValueError, RuntimeError):
            checkpoint_audit = {}
    contract = checkpoint_audit.get("analysis_contract", {})
    if not isinstance(contract, Mapping):
        contract = {}
    config = manifest.get("config", {})
    if not isinstance(config, Mapping):
        config = {}
    experiment = contract.get("experiment", {})
    if not isinstance(experiment, Mapping):
        experiment = {}
    generation = contract.get("generation", {})
    if not isinstance(generation, Mapping):
        generation = {}
    model = contract.get("primary_model", {})
    if not isinstance(model, Mapping):
        model = {}
    provider = manifest.get("provider", {})
    if not isinstance(provider, Mapping):
        provider = {}
    target = contract.get("target", {})
    if not isinstance(target, Mapping):
        target = {}
    analysis = contract.get("analysis", {})
    if not isinstance(analysis, Mapping):
        analysis = {}
    provenance = manifest.get("protocol_provenance", {})
    if not isinstance(provenance, Mapping):
        provenance = {}
    config_model = config.get("model", {})
    if not isinstance(config_model, Mapping):
        config_model = {}
    config_target = config.get("target_params", {})
    if not isinstance(config_target, Mapping):
        config_target = {}
    record_counts = experiment.get("record_counts", {})
    if not isinstance(record_counts, Mapping):
        record_counts = {}
    episode_counts = experiment.get("episode_counts", {})
    if not isinstance(episode_counts, Mapping):
        episode_counts = {}
    selection_policy = manifest.get("selection_policy", {})
    if not isinstance(selection_policy, Mapping):
        selection_policy = {}
    bank_manifest = manifest.get("message_banks", {})
    if not isinstance(bank_manifest, Mapping):
        bank_manifest = {}

    provider_name = str(provider.get("provider", ""))
    mock_run = provider_name.startswith("mock:")
    scenario_set, scenario_ids, scenario_hash = _scenario_contract_from_spec(
        contract
    )
    frozen_hash = _canonical_sha256(frozen_spec)
    contract_hash = (
        _canonical_sha256(
            {key: value for key, value in contract.items() if key != "contract_sha256"}
        )
        if contract
        else None
    )
    checkpoint_proof = provenance.get("v6_final_checkpoint", {})
    if not isinstance(checkpoint_proof, Mapping):
        checkpoint_proof = {}

    canonical_out_dir = experiment.get("canonical_out_dir")
    launch_receipt_relative = experiment.get("launch_receipt_path")
    expected_log_relative = (
        os.path.join(str(canonical_out_dir), "%s.jsonl" % contract.get("official_run_id"))
        if isinstance(canonical_out_dir, str)
        and isinstance(contract.get("official_run_id"), str)
        else None
    )
    completed_log = manifest.get("completed_log", {})
    if not isinstance(completed_log, Mapping):
        completed_log = {}
    receipt_reference = manifest.get("official_launch_receipt", {})
    if not isinstance(receipt_reference, Mapping):
        receipt_reference = {}

    canonical_out_path = None
    receipt_path = None
    actual_log_path = None
    receipt_payload: Dict[str, Any] = {}
    receipt_file_sha256 = None
    if repository_root:
        canonical_out_path = _repository_path(
            repository_root, canonical_out_dir
        )
        receipt_path = _repository_path(
            repository_root, launch_receipt_relative
        )
        if log_path is not None:
            try:
                log_descriptor = open_regular_read_descriptor(
                    log_path,
                    root=repository_root,
                    label="completed V6 log",
                )
            except (FileNotFoundError, OSError, TypeError, ValueError):
                actual_log_path = None
            else:
                os.close(log_descriptor)
                actual_log_path = os.path.abspath(log_path)
        if receipt_path is not None and os.path.isfile(receipt_path):
            try:
                loaded_receipt = _load_json_object(
                    receipt_path,
                    root=repository_root,
                    label="V6 official launch receipt",
                )
                receipt_payload = loaded_receipt
                receipt_file_sha256 = _file_sha256(
                    receipt_path, root=repository_root
                )
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                receipt_payload = {}
    receipt_audit = audit_v6_launch_receipt_payload(
        receipt_payload,
        official_run_id=str(contract.get("official_run_id", "")),
        canonical_out_dir=str(canonical_out_dir or ""),
        checkpoint_file_sha256=str(checkpoint_file_sha256 or ""),
        checkpoint_canonical_sha256=frozen_hash,
        selected_schedule_sha256=str(
            experiment.get("full_schedule_sha256", "")
        ),
        randomization_schedule_sha256=str(
            experiment.get("randomization_schedule_sha256", "")
        ),
        validated_bank_sha256=str(
            contract.get("message_bank", {}).get("sha256", "")
        ),
        model_id=str(model.get("id", "")),
        revision=model.get("revision"),
        config=config,
        expected_focal_runtime=(
            contract.get("focal_runtime")
            if isinstance(contract.get("focal_runtime"), Mapping)
            else None
        ),
    )

    def provider_generation_matches(
        provider_key: str, generation_key: Optional[str] = None
    ) -> bool:
        generation_key = generation_key or provider_key
        if generation_key not in generation:
            return False
        return mock_run or provider.get(provider_key) == generation.get(
            generation_key
        )

    checks = {
        "checkpoint_status": contract.get("status")
        == V6_FROZEN_CHECKPOINT_STATUS
        and frozen_spec.get("pre_confirmatory_outcomes") is True,
        "version": manifest.get("task_version") == contract.get("version")
        == CONTROLLED_V6_VERSION,
        "experiment_id": config.get("experiment_id")
        == "controlled_v6_checkpoint",
        "run_completed": manifest.get("run_status") == "completed",
        "conditions": list(config.get("conditions", []))
        == list(experiment.get("conditions", []))
        == list(V6_REQUIRED_CONDITIONS),
        "episode_seeds": config.get("n_episode_seeds")
        == experiment.get("n_episode_seeds"),
        "rounds": config.get("n_rounds")
        == experiment.get("n_rounds")
        == V6_N_ROUNDS,
        "swap_round": config.get("swap_round")
        == experiment.get("swap_round")
        == V6_SWAP_ROUND,
        "heldout_start": config.get("heldout_start_round")
        == experiment.get("heldout_start_round")
        == V6_HELDOUT_START,
        "seed": config.get("seed") == experiment.get("master_seed"),
        "randomization_seed": config.get("randomization_seed")
        == experiment.get("randomization_seed")
        == CONTROLLED_V6_RANDOMIZATION_SEED,
        "randomization_schedule": isinstance(
            manifest.get("randomization_schedule"), Mapping
        )
        and manifest.get("randomization_schedule", {}).get("schedule_sha256")
        == experiment.get("randomization_schedule_sha256"),
        "record_count": manifest.get("n_records") == record_counts.get("total"),
        "episode_count": manifest.get("n_episodes")
        == episode_counts.get("total"),
        "model": config_model.get("model") == model.get("id")
        and provider.get("model") == model.get("id"),
        "revision": config_model.get("revision") == model.get("revision")
        and provider.get("revision") == model.get("revision"),
        "provider": (
            config_model.get("provider") == provider_name
            if mock_run
            else provider_name == "huggingface"
        ),
        "provider_seed": mock_run
        or provider.get("torch_seed_base") == experiment.get("master_seed"),
        "strict_choice_policy": selection_policy
        == {
            "strict_selection": True,
            "constrained_choices": ["1", "2", "3"],
            "invalid_output_policy": "abort episode; no fallback",
        },
        "frozen_generation_choice_policy": generation.get(
            "constrained_choices"
        )
        == ["1", "2", "3"]
        and generation.get("invalid_output_policy") == "abort; no fallback",
        "provider_constrained_choices": mock_run
        or provider.get("constrained_choices") == ["1", "2", "3"],
        "temperature": config_model.get("temperature")
        == generation.get("temperature")
        and provider_generation_matches("temperature"),
        "max_tokens": config_model.get("max_tokens")
        == generation.get("max_tokens")
        and provider_generation_matches("max_tokens"),
        "thinking": provider_generation_matches("enable_thinking"),
        "top_p": provider_generation_matches("top_p"),
        "top_k": provider_generation_matches("top_k"),
        "capture": provider_generation_matches("capture", "activation_capture"),
        "dtype": provider_generation_matches("dtype"),
        "target": all(
            _float_equal(config_target.get(key), target.get(key))
            for key in ("p_match", "p_mismatch", "p_random")
        ),
        "bank_hash": manifest.get("message_bank_sha256")
        == contract.get("message_bank", {}).get("sha256"),
        "bank_validated": bank_manifest.get("status")
        == V6_SELECTED_BANK_STATUS,
        "checkpoint_provenance_present": bool(checkpoint_proof),
        "checkpoint_provenance": checkpoint_proof.get("canonical_sha256")
        == frozen_hash,
        "checkpoint_file_hash": isinstance(checkpoint_file_sha256, str)
        and checkpoint_proof.get("file_sha256") == checkpoint_file_sha256,
        "artifact_preflight": checkpoint_audit.get("pass") is True,
        "analysis_contract_exact": checkpoint_audit.get("analysis_contract")
        == frozen_spec.get("analysis_contract")
        and contract.get("contract_sha256") == contract_hash,
        "thresholds": contract.get("thresholds") == thresholds,
        "analysis_settings": _scientific_equal(
            analysis, CONTROLLED_V6_ANALYSIS_CONFIG
        ),
        "analysis_output_directory": analysis.get("canonical_out_dir")
        == CONTROLLED_V6_ANALYSIS_CONFIG["canonical_out_dir"],
        "paid_preflight_paths": experiment.get("paid_preflight_report_path")
        == "results/v6_design/confirmatory_paid_preflight.json"
        and experiment.get("paid_preflight_receipt_path")
        == CONTROLLED_V6_PAID_PREFLIGHT_RECEIPT_PATH,
        "scenario_set": scenario_set == "confirmatory",
        "scenario_ids": list(scenario_ids or [])
        == list(V6_CONFIRMATORY_SCENARIO_IDS),
        "scenario_hash": scenario_hash == V6_CONFIRMATORY_SCENARIO_SHA256,
        "single_official_run": experiment.get("single_official_run") is True,
        "outcome_blind_freeze": contract.get("outcome_blind_freeze") is True,
        "canonical_output_directory": canonical_out_path is not None
        and os.path.realpath(str(config.get("out_dir", "")))
        == canonical_out_path,
        "actual_log_at_canonical_path": actual_log_path is not None
        and canonical_out_path is not None
        and actual_log_path
        == os.path.realpath(
            os.path.join(
                canonical_out_path, "%s.jsonl" % contract.get("official_run_id")
            )
        ),
        "completed_log_path": completed_log.get("path")
        == expected_log_relative,
        "completed_log_hash": isinstance(log_file_sha256, str)
        and completed_log.get("file_sha256") == log_file_sha256,
        "completed_log_record_count": completed_log.get("n_records")
        == record_counts.get("total"),
        "launch_receipt_path": receipt_path is not None
        and receipt_reference.get("path") == launch_receipt_relative,
        "launch_receipt_file_hash": isinstance(receipt_file_sha256, str)
        and receipt_reference.get("file_sha256") == receipt_file_sha256,
        "launch_receipt_id": receipt_reference.get("receipt_id")
        == receipt_audit.get("receipt_id"),
        "launch_receipt_binding": receipt_audit.get("pass") is True,
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "checkpoint_canonical_sha256": frozen_hash,
        "confirmatory_scenario_canonical_sha256": (
            V6_CONFIRMATORY_SCENARIO_SHA256
        ),
        "final_checkpoint_artifact_audit": checkpoint_audit,
        "analysis_contract_sha256": contract_hash,
        "launch_receipt_audit": receipt_audit,
        "completed_log": dict(completed_log),
    }


def _audit_sealed_scenarios(
    records: Sequence[Mapping[str, Any]], manifest: Mapping[str, Any]
) -> Dict[str, Any]:
    sealed_by_id = {
        scenario.id: scenario.as_dict() for scenario in V6_CONFIRMATORY_SCENARIOS
    }
    observed_ids = {str(row.get("scenario_id", "")) for row in records}
    config = manifest.get("config", {})
    if not isinstance(config, Mapping):
        config = {}
    n_rounds = int(config.get("n_rounds", -1))
    master_seed = int(config.get("seed", -1))
    schedule_mismatches: List[Dict[str, Any]] = []
    payload_mismatches: List[Dict[str, Any]] = []

    expected_by_episode: Dict[int, List[Any]] = {}
    if n_rounds > 0:
        for row in records:
            episode_index = int(row.get("episode_index", -1))
            if episode_index not in expected_by_episode:
                expected_by_episode[episode_index] = v6_scenario_sequence(
                    "confirmatory", episode_index, n_rounds, master_seed
                )
            round_index = int(row.get("round", -1))
            expected = (
                expected_by_episode[episode_index][round_index - 1]
                if 1 <= round_index <= n_rounds
                else None
            )
            if expected is None or str(row.get("scenario_id", "")) != expected.id:
                schedule_mismatches.append(
                    {
                        "episode_id": str(row.get("episode_id", "")),
                        "episode_index": episode_index,
                        "round": round_index,
                        "observed": str(row.get("scenario_id", "")),
                        "expected": expected.id if expected is not None else None,
                    }
                )
            scenario_id = str(row.get("scenario_id", ""))
            if row.get("scenario") != sealed_by_id.get(scenario_id):
                payload_mismatches.append(
                    {
                        "episode_id": str(row.get("episode_id", "")),
                        "round": round_index,
                        "scenario_id": scenario_id,
                    }
                )

    checks = {
        "sealed_confirmatory_scenario_ids_only": observed_ids
        <= set(V6_CONFIRMATORY_SCENARIO_IDS),
        "all_sealed_confirmatory_scenarios_observed": observed_ids
        == set(V6_CONFIRMATORY_SCENARIO_IDS),
        "sealed_scenario_payloads_exact": not payload_mismatches,
        "sealed_scenario_schedule_exact": not schedule_mismatches,
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "scenario_set": "confirmatory",
        "expected_ids": list(V6_CONFIRMATORY_SCENARIO_IDS),
        "observed_ids": sorted(observed_ids),
        "canonical_sha256": V6_CONFIRMATORY_SCENARIO_SHA256,
        "schedule_mismatches": schedule_mismatches,
        "payload_mismatches": payload_mismatches,
    }


def _audit_full_confirmatory_schedule(
    records: Sequence[Mapping[str, Any]],
    frozen_spec: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Reconstruct the exact schedule hash frozen before outcomes existed."""
    contract = (
        frozen_spec.get("analysis_contract", {})
        if isinstance(frozen_spec, Mapping)
        else {}
    )
    experiment = contract.get("experiment", {}) if isinstance(contract, Mapping) else {}
    expected = (
        experiment.get("full_schedule_sha256")
        if isinstance(experiment, Mapping)
        else None
    )
    ordered = list(records)
    rows: List[Dict[str, Any]] = []
    keys: List[Tuple[str, int]] = []
    for row in ordered:
        episode_index = int(row.get("episode_index", -1))
        round_index = int(row.get("round", -1))
        keys.append((str(row.get("episode_id", "")), round_index))
        candidates = row.get("candidates", [])
        candidate_ids = []
        if isinstance(candidates, list):
            candidate_ids = [
                str(candidate.get("candidate_id", ""))
                for candidate in sorted(
                    (item for item in candidates if isinstance(item, Mapping)),
                    key=lambda item: int(item.get("slot", -1)),
                )
            ]
        rows.append(
            {
                "episode_id": str(row.get("episode_id", "")),
                "condition": str(row.get("condition", "")),
                "episode_index": episode_index,
                "initial_target_type": str(row.get("initial_target_type", "")),
                "final_target_type": str(row.get("final_target_type", "")),
                "pair_family": row.get("pair_family"),
                "pair_id": row.get("pair_id"),
                "pair_slot": row.get("pair_slot"),
                "allocation_bit": row.get("allocation_bit"),
                "assigned_regime": row.get("assigned_regime"),
                "stable_counterfactual": row.get("stable_counterfactual"),
                "nominal_transition": row.get("nominal_transition"),
                "round": round_index,
                "scenario_id": str(row.get("scenario_id", "")),
                "candidate_ids_by_slot": candidate_ids,
            }
        )
    observed = _canonical_sha256(rows)
    checks = {
        "schedule_coordinates_unique": len(keys) == len(set(keys)),
        "three_candidates_each_round": all(
            len(row["candidate_ids_by_slot"]) == 3 for row in rows
        ),
        "frozen_schedule_hash_present": isinstance(expected, str),
        "full_schedule_hash_exact": isinstance(expected, str) and observed == expected,
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "expected_sha256": expected,
        "observed_sha256": observed,
        "n_rows": len(rows),
    }


def _bundle_means(
    values: Sequence[float], blocks: Sequence[Any]
) -> List[float]:
    if len(values) != len(blocks):
        raise ValueError("values and randomized bundle ids must have equal length")
    grouped: Dict[Any, List[float]] = defaultdict(list)
    for value, block in zip(values, blocks):
        grouped[block].append(float(value))
    return [_mean(grouped[block]) for block in sorted(grouped, key=str)]


def _randomized_bundle_summary(
    values: Sequence[float],
    blocks: Sequence[Any],
    n_boot: int,
    n_perm: int,
    seed: int,
    *,
    family: str,
) -> Dict[str, Any]:
    """Analyze prospectively randomized matched bundle contrasts.

    The exact sign enumeration is licensed here by the frozen within-bundle
    treatment assignment.  It tests the Fisher sharp null of no effect on any
    bundle; the mean and bootstrap interval are descriptive effect summaries,
    not a model-based population-average test.
    """
    means = _bundle_means(values, blocks)
    integer_scale = {
        V6_HISTORY_FAMILY: 18,
        V6_SWAP_FAMILY: 36,
    }.get(family)
    if integer_scale is None:
        raise ValueError("unknown V6 randomization family %r" % family)
    result: Dict[str, Any] = {
        **_bootstrap_mean(means, n_boot, seed),
        **exact_one_sided_bundle_randomization_test(
            means, integer_scale=integer_scale
        ),
    }
    result.update(
        {
            "n_perm_requested_ignored": n_perm,
            "n_randomized_bundles": len(means),
            "n_episode_values": len(values),
            "randomization_family": family,
            "randomization_unit": "episode-seed bundle",
            "test": "exact within-bundle treatment-label randomization",
            "null_hypothesis": "Fisher sharp null of no treatment effect",
            "mean_interval_role": "descriptive cluster bootstrap",
        }
    )
    return result


def _identical_fields(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> bool:
    if not rows:
        return False
    first = rows[0]
    return all(
        all(_scientific_equal(row.get(field), first.get(field)) for field in fields)
        for row in rows[1:]
    )


def _audit_v6_replication(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Enforce deterministic prompt identities used by the power model."""
    no_groups: Dict[Tuple[int, int], List[Mapping[str, Any]]] = defaultdict(list)
    for row in records:
        condition = str(row.get("condition", ""))
        episode_index = int(row.get("episode_index", -1))
        round_index = int(row.get("round", -1))
        if condition == "no_history":
            no_groups[(episode_index, round_index)].append(row)

    prompt_output_fields = (
        "scenario_id",
        "candidates",
        "visible_candidates",
        "focal_system_prompt",
        "focal_user_prompt",
        "focal_output_raw",
        "selected_slot",
        "selected_candidate_id",
        "selected_message",
        "selected_frame",
    )
    no_failures: List[Any] = []
    for key, rows in sorted(no_groups.items()):
        types = {str(row.get("initial_target_type", "")) for row in rows}
        if (
            len(rows) != len(STRATEGIES)
            or types != set(STRATEGIES)
            or any(row.get("visible_history") != [] for row in rows)
            or not _identical_fields(
                rows,
                prompt_output_fields
                + ("round_seed", "generation_id", "replication_group_id"),
            )
        ):
            no_failures.append(key)

    checks = {
        "no_history_target_rows_identical": not no_failures and bool(no_groups),
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "no_history_failures": no_failures,
        "n_unique_no_history_choices": len(no_groups),
    }


def _unique_no_history_rows(
    records: Sequence[Mapping[str, Any]],
) -> List[Mapping[str, Any]]:
    groups: Dict[Tuple[int, int], List[Mapping[str, Any]]] = defaultdict(list)
    for row in _condition_rows(records, "no_history"):
        groups[(int(row["episode_index"]), int(row["round"]))].append(row)
    return [groups[key][0] for key in sorted(groups)]


def v6_records_to_bundle_study(
    records: Sequence[Mapping[str, Any]],
    n_episode_seeds: int,
) -> Dict[str, Any]:
    """Adapt audited confirmatory rows to the frozen power-analysis schema.

    This is the sole real-data adapter for the estimand, exact-test, and
    complete-gate implementation shared with every prospective simulation.
    """
    if type(n_episode_seeds) is not int or n_episode_seeds < 1:
        raise ValueError("V6 bundle-study adapter needs a positive bundle count")
    grouped: Dict[Tuple[str, int, str, str], List[Mapping[str, Any]]] = (
        defaultdict(list)
    )
    for row in records:
        grouped[
            (
                str(row.get("condition", "")),
                int(row.get("episode_index", -1)),
                str(row.get("initial_target_type", "")),
                str(row.get("final_target_type", "")),
            )
        ].append(row)

    def trajectory(
        condition: str,
        bundle_index: int,
        initial: str,
        final: str,
    ) -> Dict[str, Any]:
        rows = sorted(
            grouped.get((condition, bundle_index, initial, final), []),
            key=lambda row: int(row.get("round", -1)),
        )
        if len(rows) != V6_N_ROUNDS or [
            int(row.get("round", -1)) for row in rows
        ] != list(range(1, V6_N_ROUNDS + 1)):
            raise ValueError(
                "V6 bundle-study trajectory is incomplete: %s/%d/%s/%s"
                % (condition, bundle_index, initial, final)
            )
        return {
            "frames": [str(row.get("selected_frame", "")) for row in rows],
            "target_outcomes": [
                int(str(row.get("target_choice", "")) == "A") for row in rows
            ],
        }

    assignments = reconstruct_v6_bundle_assignments(
        n_episode_seeds, study_index=0
    )
    bundles: List[Dict[str, Any]] = []
    for expected in assignments:
        bundle_index = int(expected["bundle_index"])
        stable_slots: List[Dict[str, Any]] = []
        for condition, slot in (
            ("full_history", int(expected["stable_full_slot"])),
            ("no_history", 1 - int(expected["stable_full_slot"])),
        ):
            stable_slots.append(
                {
                    "slot": slot,
                    "condition": condition,
                    "target_trajectories": {
                        target: trajectory(
                            condition, bundle_index, target, target
                        )
                        for target in STRATEGIES
                    },
                }
            )

        transition_slots: List[Dict[str, Any]] = []
        for condition, label, slot in (
            ("swap", "silent_swap", int(expected["swap_slot"])),
            (
                "swap_control",
                "stable_old",
                1 - int(expected["swap_slot"]),
            ),
        ):
            transition_slots.append(
                {
                    "slot": slot,
                    "condition": label,
                    "transitions": {
                        "%s->%s" % (old, new): trajectory(
                            condition, bundle_index, old, new
                        )
                        for old in STRATEGIES
                        for new in STRATEGIES
                        if old != new
                    },
                }
            )

        relevant = [
            row
            for row in records
            if int(row.get("episode_index", -1)) == bundle_index
            and str(row.get("condition", ""))
            in {
                "full_history",
                "no_history",
                "random_target",
                "swap",
                "swap_control",
            }
        ]
        bundles.append(
            {
                "bundle_index": bundle_index,
                "stable_full_slot": int(expected["stable_full_slot"]),
                "swap_slot": int(expected["swap_slot"]),
                "stable_slots": stable_slots,
                "transition_slots": transition_slots,
                "random_target_controls": {
                    target: trajectory(
                        "random_target", bundle_index, target, target
                    )
                    for target in STRATEGIES
                },
                "selection_valid": bool(relevant)
                and all(row.get("selection_valid") is True for row in relevant),
                "fallback_used": any(
                    row.get("fallback_used") is True for row in relevant
                ),
            }
        )

    unique_no = [
        frame
        for bundle in bundles
        for frame in bundle["stable_slots"][
            next(
                index
                for index, slot in enumerate(bundle["stable_slots"])
                if slot["condition"] == "no_history"
            )
        ]["target_trajectories"][STRATEGIES[0]]["frames"]
    ]
    frame_total = float(len(unique_no))
    return {
        "schema_version": V6_STUDY_SCHEMA_VERSION,
        "study_index": 0,
        "allocation_rng_root": V6_ALLOCATION_RNG_ROOT,
        "n_episode_seeds": n_episode_seeds,
        "baseline_frame_shares": {
            frame: unique_no.count(frame) / frame_total for frame in STRATEGIES
        },
        "planning_scenario": None,
        "null_profile_id": None,
        "assignments": assignments,
        "bundles": bundles,
    }


def _audit_v6_randomization(
    records: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    frozen_spec: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    config = manifest.get("config", {})
    if not isinstance(config, Mapping):
        config = {}
    n_seeds = config.get("n_episode_seeds")
    allocation_seed = config.get("randomization_seed")
    expected: Dict[str, Any] = {}
    if type(n_seeds) is int and type(allocation_seed) is int and n_seeds > 0:
        try:
            expected = v6_allocation_schedule(n_seeds, seed=allocation_seed)
        except ValueError:
            expected = {}
    observed = manifest.get("randomization_schedule")
    observed_audit = (
        audit_v6_allocation_schedule(observed)
        if isinstance(observed, Mapping)
        else {"pass": False, "checks": {"schedule_present": False}}
    )
    contract = (
        frozen_spec.get("analysis_contract", {})
        if isinstance(frozen_spec, Mapping)
        else {}
    )
    experiment = contract.get("experiment", {}) if isinstance(contract, Mapping) else {}
    expected_hash = (
        experiment.get("randomization_schedule_sha256")
        if isinstance(experiment, Mapping)
        else None
    )
    row_failures: List[Dict[str, Any]] = []
    schedule_hash = expected.get("schedule_sha256")
    for row in records:
        condition = str(row.get("condition", ""))
        episode_index = int(row.get("episode_index", -1))
        try:
            assignment = v6_regime_assignment(
                condition, episode_index, seed=int(allocation_seed)
            )
        except (TypeError, ValueError):
            row_failures.append(
                {"episode_id": row.get("episode_id"), "round": row.get("round")}
            )
            continue
        expected_fields = {
            **assignment,
            "allocation_seed": allocation_seed,
            "allocation_schedule_sha256": schedule_hash,
            "stable_counterfactual": condition == "swap_control",
            "nominal_transition": (
                "%s_to_%s"
                % (row.get("initial_target_type"), row.get("final_target_type"))
                if condition in {"swap", "swap_control"}
                else None
            ),
        }
        if any(
            not _scientific_equal(row.get(key), value)
            for key, value in expected_fields.items()
        ):
            row_failures.append(
                {"episode_id": row.get("episode_id"), "round": row.get("round")}
            )
    checks = {
        "frozen_randomization_seed": allocation_seed
        == CONTROLLED_V6_RANDOMIZATION_SEED,
        "manifest_schedule_exact": bool(expected)
        and isinstance(observed, Mapping)
        and _scientific_equal(dict(observed), expected),
        "manifest_schedule_replays": observed_audit.get("pass") is True,
        "checkpoint_schedule_hash_exact": isinstance(expected_hash, str)
        and expected_hash == schedule_hash,
        "all_record_assignments_exact": not row_failures,
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "expected_schedule": expected,
        "manifest_schedule_audit": observed_audit,
        "row_failures": row_failures,
    }


def _adjusted_swap_episode_summaries(
    swap_rows: Sequence[Mapping[str, Any]],
    control_rows: Sequence[Mapping[str, Any]],
    heldout_start_round: int,
) -> List[Dict[str, Any]]:
    treated = {
        (int(row["episode_index"]), str(row["transition"])): row
        for row in _swap_episode_summaries(swap_rows, heldout_start_round)
    }
    control = {
        (int(row["episode_index"]), str(row["transition"])): row
        for row in _swap_episode_summaries(control_rows, heldout_start_round)
    }
    if set(treated) != set(control):
        raise ValueError("swap and stable-counterfactual transition grids differ")
    out: List[Dict[str, Any]] = []
    for key in sorted(treated):
        swap = treated[key]
        stable = control[key]
        adjusted_new = float(swap["new_target_gain"]) - float(
            stable["new_target_gain"]
        )
        adjusted_old = float(swap["old_target_drop"]) - float(
            stable["old_target_drop"]
        )
        out.append(
            {
                **swap,
                "stable_counterfactual_new_target_gain": float(
                    stable["new_target_gain"]
                ),
                "stable_counterfactual_old_target_drop": float(
                    stable["old_target_drop"]
                ),
                "adjusted_new_target_gain": adjusted_new,
                "adjusted_old_target_drop": adjusted_old,
                "adjusted_revision_shift": adjusted_new + adjusted_old,
                "adjusted_development_revision_shift": float(
                    swap["development_revision_shift"]
                )
                - float(stable["development_revision_shift"]),
            }
        )
    return out


def _estimand_reuse_audit(
    records: Sequence[Mapping[str, Any]], manifest: Mapping[str, Any]
) -> Dict[str, Any]:
    """Audit the limited V5 descriptive-helper reuse in redesigned V6."""
    helpers = (
        _stable_episode_summaries,
        _paired_values_and_blocks,
        _swap_episode_summaries,
        _blocked_descriptive,
    )
    checks = {
        "v5_descriptive_helpers_reused": all(
            helper.__module__ == "src.controlled_v5_analysis" for helper in helpers
        ),
        "exact_v5_round_contract_preserved": V5_N_ROUNDS == V6_N_ROUNDS,
        "exact_v5_swap_contract_preserved": V5_SWAP_ROUND == V6_SWAP_ROUND,
        "exact_v5_heldout_contract_preserved": (
            V5_HELDOUT_START == V6_HELDOUT_START
        ),
        "exact_v5_window_contract_preserved": V5_WINDOW_SIZE == V6_WINDOW_SIZE,
        "manifest_remains_v6": manifest.get("task_version")
        == CONTROLLED_V6_VERSION,
        "records_remain_v6": {
            str(row.get("task_version", "")) for row in records
        }
        == {CONTROLLED_V6_VERSION},
        "manifest_rewritten_as_v5": False,
        "records_rewritten_as_v5": False,
    }
    pass_checks = [
        value
        for name, value in checks.items()
        if name not in {"manifest_rewritten_as_v5", "records_rewritten_as_v5"}
    ]
    return {
        "pass": all(pass_checks)
        and checks["manifest_rewritten_as_v5"] is False
        and checks["records_rewritten_as_v5"] is False,
        "checks": checks,
        "source_module": "src.controlled_v5_analysis",
        "preserved_estimands": [
            "stable full-vs-no-history difference-in-differences",
            "within-episode new-frame gain and old-frame drop components",
        ],
        "v6_estimand_changes": [
            "prospectively randomized history-access bundle contrast",
            "swap-minus-stable-counterfactual adjusted new-frame gain",
            "swap-minus-stable-counterfactual adjusted old-frame drop",
        ],
        "randomization_unit": "episode-seed bundle",
    }


def evaluate_controlled_v6_checkpoint(
    records: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    n_boot: int = int(CONTROLLED_V6_ANALYSIS_CONFIG["n_boot"]),
    n_perm: int = int(CONTROLLED_V6_ANALYSIS_CONFIG["n_perm"]),
    seed: int = int(CONTROLLED_V6_ANALYSIS_CONFIG["seed"]),
    frozen_spec: Optional[Mapping[str, Any]] = None,
    checkpoint_root: Optional[str] = None,
    checkpoint_file_sha256: Optional[str] = None,
    log_path: Optional[str] = None,
    log_file_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate the fixed V6 confirmatory pattern and all diagnostics.

    ``frozen_spec`` is mandatory for a valid confirmatory result.  It remains an
    optional Python argument only so malformed/unprovenanced inputs can receive
    a machine-readable invalid-input status and complete diagnostics.
    """
    if (
        type(n_boot) is not int
        or type(n_perm) is not int
        or type(seed) is not int
        or n_boot <= 0
        or n_perm <= 0
    ):
        raise ValueError("V6 analysis counts and seed must be exact positive integers")
    original_records = list(records)
    if not original_records:
        raise ValueError("V6 checkpoint log is empty")
    thresholds = _v6_thresholds()
    config = manifest.get("config", {})
    if not isinstance(config, Mapping):
        config = {}
    heldout_start = int(config.get("heldout_start_round", -1))
    provider_name = str(manifest.get("provider", {}).get("provider", ""))
    mock_run = provider_name.startswith("mock:")

    if frozen_spec is None:
        frozen_audit = {
            "pass": False,
            "checks": {
                "checkpoint_spec_supplied": False,
                "checkpoint_provenance_present": bool(
                    manifest.get("protocol_provenance")
                ),
            },
            "checkpoint_canonical_sha256": None,
            "confirmatory_scenario_canonical_sha256": (
                V6_CONFIRMATORY_SCENARIO_SHA256
            ),
            "final_checkpoint_artifact_audit": {},
        }
    else:
        frozen_audit = audit_frozen_v6_manifest(
            manifest,
            frozen_spec,
            checkpoint_root,
            checkpoint_file_sha256,
            log_path,
            log_file_sha256,
        )

    replay_audit: Dict[str, Any] = {
        "pass": False,
        "checks": {"frozen_replay_runtime_available": False},
        "mismatches": [],
        "schema_errors": [],
    }
    records = original_records
    if (
        frozen_spec is not None
        and checkpoint_root
        and frozen_audit.get("final_checkpoint_artifact_audit", {}).get("pass")
        is True
    ):
        try:
            replay_cfg, replay_protocol, replay_run_id = (
                _replay_runtime_from_checkpoint(
                    manifest,
                    frozen_spec,
                    checkpoint_root,
                    frozen_audit["final_checkpoint_artifact_audit"],
                )
            )
            replay_audit, reconstructed = reconcile_v6_records_against_runtime(
                original_records,
                manifest,
                replay_cfg,
                replay_protocol,
                replay_run_id,
            )
            if len(reconstructed) == len(original_records):
                records = reconstructed
        except (KeyError, OSError, TypeError, ValueError, RuntimeError) as exc:
            replay_audit = {
                "pass": False,
                "checks": {"frozen_replay_runtime_available": False},
                "mismatches": [],
                "schema_errors": [],
                "error": "%s: %s" % (type(exc).__name__, exc),
            }

    missing = [
        name for name in V6_REQUIRED_CONDITIONS if not _condition_rows(records, name)
    ]
    if missing:
        raise ValueError("V6 checkpoint is missing required conditions: %s" % missing)

    audit_records = original_records
    try:
        design = audit_controlled_design(
            audit_records, manifest, expected_version=CONTROLLED_V6_VERSION
        )
    except (KeyError, TypeError, ValueError) as exc:
        design = audit_controlled_design(
            records, manifest, expected_version=CONTROLLED_V6_VERSION
        )
        design["checks"]["raw_design_record_shape"] = False
        design["raw_design_audit_error"] = "%s: %s" % (
            type(exc).__name__,
            exc,
        )
        design["pass"] = False
    scenario_audit = _audit_sealed_scenarios(audit_records, manifest)
    full_schedule_audit = _audit_full_confirmatory_schedule(
        audit_records, frozen_spec
    )
    estimand_audit = _estimand_reuse_audit(audit_records, manifest)
    randomization_audit = _audit_v6_randomization(
        audit_records, manifest, frozen_spec
    )
    replication_audit = _audit_v6_replication(audit_records)
    episode_groups = _episode_groups(audit_records)
    n_seeds = int(config.get("n_episode_seeds", -1))
    shared_bundle_summary: Optional[Dict[str, Any]] = None
    shared_bundle_audit: Dict[str, Any]
    try:
        shared_study = v6_records_to_bundle_study(audit_records, n_seeds)
        shared_bundle_summary = analyze_v6_bundle_study(shared_study)
        shared_bundle_audit = {
            "pass": True,
            "analysis_helper": "controlled_v6_power.analyze_v6_bundle_study",
            "power_contract_sha256": V6_POWER_CONTRACT_SHA256,
            "n_bundles": shared_bundle_summary["n_bundles"],
        }
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        shared_bundle_audit = {
            "pass": False,
            "analysis_helper": "controlled_v6_power.analyze_v6_bundle_study",
            "power_contract_sha256": V6_POWER_CONTRACT_SHA256,
            "error": "%s: %s" % (type(exc).__name__, exc),
        }
    stable_type_counts: Counter = Counter()
    swap_transition_counts: Counter = Counter()
    swap_control_transition_counts: Counter = Counter()
    for episode_rows in episode_groups.values():
        first = episode_rows[0]
        condition = str(first["condition"])
        if condition in V6_REQUIRED_CONDITIONS[:4]:
            stable_type_counts[(condition, str(first["initial_target_type"]))] += 1
        elif condition == "swap":
            swap_transition_counts[
                (str(first["initial_target_type"]), str(first["final_target_type"]))
            ] += 1
        elif condition == "swap_control":
            swap_control_transition_counts[
                (str(first["initial_target_type"]), str(first["final_target_type"]))
            ] += 1
    expected_transitions = {
        (old, new) for old in STRATEGIES for new in STRATEGIES if old != new
    }
    selection_policy = manifest.get("selection_policy", {})
    if not isinstance(selection_policy, Mapping):
        selection_policy = {}
    frozen_contract = (
        frozen_spec.get("analysis_contract", {})
        if isinstance(frozen_spec, Mapping)
        else {}
    )
    synthetic_analysis_fixture = bool(
        isinstance(frozen_spec, Mapping)
        and frozen_spec.get("synthetic_analysis_fixture") is True
    )
    runtime_analysis_parameters = {
        "n_boot": n_boot,
        "n_perm": n_perm,
        "seed": seed,
    }
    expected_analysis_parameters = {
        key: CONTROLLED_V6_ANALYSIS_CONFIG[key]
        for key in ("n_boot", "n_perm", "seed")
    }
    runtime_analysis_parameters_match = _scientific_equal(
        runtime_analysis_parameters, expected_analysis_parameters
    )
    official_run_id = (
        frozen_contract.get("official_run_id")
        if isinstance(frozen_contract, Mapping)
        else None
    )
    v6_checks = {
        "v6_gate_thresholds_frozen": all(
            thresholds[key] == value
            for key, value in V6_CO_PRIMARY_MINIMUMS.items()
        ),
        "analysis_runtime_parameters_frozen": (
            runtime_analysis_parameters_match or synthetic_analysis_fixture
        ),
        "v6_round_count": int(config.get("n_rounds", -1)) == V6_N_ROUNDS,
        "v6_swap_round": int(config.get("swap_round", -1)) == V6_SWAP_ROUND,
        "v6_heldout_start": heldout_start == V6_HELDOUT_START,
        "exact_six_condition_contract": list(config.get("conditions", []))
        == list(V6_REQUIRED_CONDITIONS),
        "strict_selection_declared": selection_policy.get("strict_selection")
        is True,
        "choice_constraint_declared": selection_policy.get("constrained_choices")
        == ["1", "2", "3"],
        "invalid_output_aborts_declared": selection_policy.get(
            "invalid_output_policy"
        )
        == "abort episode; no fallback",
        "selected_slots_strict": all(
            int(row.get("selected_slot", -1)) in (1, 2, 3)
            for row in audit_records
        ),
        "no_fallback_used": not any(
            bool(row.get("fallback_used")) for row in audit_records
        ),
        "all_selections_valid": all(
            bool(row.get("selection_valid")) for row in audit_records
        ),
        "single_official_run_id": isinstance(official_run_id, str)
        and {str(row.get("run_id", "")) for row in audit_records}
        == {official_run_id},
        "validated_v6_bank": manifest.get("message_banks", {}).get("status")
        == V6_SELECTED_BANK_STATUS,
        "stable_target_type_balance": all(
            stable_type_counts[(condition, target)] == n_seeds
            for condition in V6_REQUIRED_CONDITIONS[:4]
            for target in STRATEGIES
        ),
        "all_six_ordered_swap_transitions_balanced": set(swap_transition_counts)
        == expected_transitions
        and all(
            swap_transition_counts[transition] == n_seeds
            for transition in expected_transitions
        ),
        "all_six_stable_counterfactual_transitions_balanced": set(
            swap_control_transition_counts
        )
        == expected_transitions
        and all(
            swap_control_transition_counts[transition] == n_seeds
            for transition in expected_transitions
        ),
        "candidate_split_round_contract": all(
            str(row.get("candidate_split", ""))
            == (
                "heldout"
                if int(row.get("round", -1)) >= V6_HELDOUT_START
                else "development"
            )
            for row in audit_records
        ),
        **scenario_audit["checks"],
        **full_schedule_audit["checks"],
        "v6_randomization_schedule_valid": bool(randomization_audit["pass"]),
        "deterministic_replication_contract_valid": bool(
            replication_audit["pass"]
        ),
        "shared_power_analysis_adapter_valid": bool(
            shared_bundle_audit["pass"]
        ),
        "v5_descriptive_helpers_reused_without_version_rewrite": bool(
            estimand_audit["pass"]
        ),
    }
    completed_log = manifest.get("completed_log", {})
    if not isinstance(completed_log, Mapping):
        completed_log = {}
    v6_checks.update(
        {
            "raw_record_replay_exact": replay_audit.get("pass") is True,
            "completed_log_reconstructed_hash": completed_log.get(
                "reconstructed_records_canonical_sha256"
            )
            == replay_audit.get("reconstructed_records_canonical_sha256"),
        }
    )
    v6_checks["matches_frozen_v6_checkpoint"] = bool(frozen_audit["pass"])
    design["checks"].update(v6_checks)
    design["pass"] = all(design["checks"].values())
    design["frozen_v6_checkpoint"] = frozen_audit
    design["sealed_confirmatory_scenarios"] = scenario_audit
    design["full_confirmatory_schedule"] = full_schedule_audit
    design["v5_estimand_reuse"] = estimand_audit
    design["prospective_randomization"] = randomization_audit
    design["deterministic_replication"] = replication_audit
    design["shared_power_analysis"] = shared_bundle_audit
    design["raw_record_replay"] = replay_audit

    stable = {
        name: _stable_episode_summaries(
            _condition_rows(records, name), heldout_start
        )
        for name in V6_REQUIRED_CONDITIONS[:4]
    }
    stable_metrics: Dict[str, Any] = {}
    for condition_index, (name, summaries) in enumerate(stable.items()):
        keys = sorted(summaries)
        blocks = [key[0] for key in keys]
        stable_metrics[name] = {
            "n_episodes": len(keys),
            "n_blocks": len(set(blocks)),
            "early_match": _blocked_descriptive(
                [summaries[key]["early_match"] for key in keys],
                blocks,
                n_boot,
                seed + condition_index * 20,
            ),
            "late_heldout_match": _blocked_descriptive(
                [summaries[key]["late_heldout_match"] for key in keys],
                blocks,
                n_boot,
                seed + condition_index * 20 + 1,
            ),
            "late_development_match": _blocked_descriptive(
                [summaries[key]["late_development_match"] for key in keys],
                blocks,
                n_boot,
                seed + condition_index * 20 + 2,
            ),
            "learning_gain": _blocked_descriptive(
                [summaries[key]["learning_gain"] for key in keys],
                blocks,
                n_boot,
                seed + condition_index * 20 + 3,
            ),
            "development_learning_gain": _blocked_descriptive(
                [summaries[key]["development_learning_gain"] for key in keys],
                blocks,
                n_boot,
                seed + condition_index * 20 + 5,
            ),
            "success": _blocked_descriptive(
                [summaries[key]["success"] for key in keys],
                blocks,
                n_boot,
                seed + condition_index * 20 + 4,
            ),
            "valid_selection": _mean(
                summaries[key]["valid_selection"] for key in keys
            ),
            "fallback_rate": _mean(
                summaries[key]["fallback_rate"] for key in keys
            ),
        }

    did_values, did_blocks = _paired_values_and_blocks(
        stable["full_history"], stable["no_history"], "learning_gain"
    )
    late_no_values, late_no_blocks = _paired_values_and_blocks(
        stable["full_history"], stable["no_history"], "late_heldout_match"
    )
    late_shuffled_values, late_shuffled_blocks = _paired_values_and_blocks(
        stable["full_history"],
        stable["shuffled_history"],
        "late_heldout_match",
    )
    development_did_values, development_did_blocks = _paired_values_and_blocks(
        stable["full_history"],
        stable["no_history"],
        "development_learning_gain",
    )
    primary = {
        "stable_full_vs_no_difference_in_differences": _randomized_bundle_summary(
            did_values,
            did_blocks,
            n_boot,
            n_perm,
            seed + 100,
            family=V6_HISTORY_FAMILY,
        ),
        "full_over_no_late_heldout": _blocked_descriptive(
            late_no_values, late_no_blocks, n_boot, seed + 110
        ),
        "full_over_shuffled_late_heldout": _blocked_descriptive(
            late_shuffled_values,
            late_shuffled_blocks,
            n_boot,
            seed + 120,
        ),
        "development_stable_difference_in_differences": _blocked_descriptive(
            development_did_values,
            development_did_blocks,
            n_boot,
            seed + 130,
        ),
    }

    by_type: Dict[str, Any] = {}
    supporting_types: List[str] = []
    for target_name in STRATEGIES:
        keys = sorted(
            key for key in stable["full_history"] if key[1] == target_name
        )
        advantages = [
            stable["full_history"][key]["late_heldout_match"]
            - stable["no_history"][key]["late_heldout_match"]
            for key in keys
        ]
        metric = _bootstrap_mean(
            advantages,
            n_boot,
            seed + 140 + STRATEGIES.index(target_name),
        )
        by_type[target_name] = metric
        if metric["mean"] >= thresholds["minimum_per_type_late_advantage"]:
            supporting_types.append(target_name)

    swap_summaries = _adjusted_swap_episode_summaries(
        _condition_rows(records, "swap"),
        _condition_rows(records, "swap_control"),
        heldout_start,
    )
    swap_blocks = [int(row["episode_index"]) for row in swap_summaries]
    revision = _randomized_bundle_summary(
        [float(row["adjusted_revision_shift"]) for row in swap_summaries],
        swap_blocks,
        n_boot,
        n_perm,
        seed + 200,
        family=V6_SWAP_FAMILY,
    )
    adjusted_new_gain = _blocked_descriptive(
        [float(row["adjusted_new_target_gain"]) for row in swap_summaries],
        swap_blocks,
        n_boot,
        seed + 220,
    )
    adjusted_old_drop = _blocked_descriptive(
        [float(row["adjusted_old_target_drop"]) for row in swap_summaries],
        swap_blocks,
        n_boot,
        seed + 221,
    )
    late_new_over_old = _blocked_descriptive(
        [float(row["late_new_over_old"]) for row in swap_summaries],
        swap_blocks,
        n_boot,
        seed + 210,
    )
    grouped_transitions: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in swap_summaries:
        grouped_transitions[str(row["transition"])].append(row)
    transition_metrics: Dict[str, Any] = {}
    for transition_index, transition in enumerate(sorted(grouped_transitions)):
        rows = grouped_transitions[transition]
        transition_metrics[transition] = {
            "old_type": rows[0]["old_type"],
            "new_type": rows[0]["new_type"],
            "adjusted_revision_shift": _bootstrap_mean(
                [float(row["adjusted_revision_shift"]) for row in rows],
                n_boot,
                seed + 300 + transition_index,
            ),
            "adjusted_new_target_gain": _bootstrap_mean(
                [float(row["adjusted_new_target_gain"]) for row in rows],
                n_boot,
                seed + 320 + transition_index,
            ),
            "adjusted_old_target_drop": _bootstrap_mean(
                [float(row["adjusted_old_target_drop"]) for row in rows],
                n_boot,
                seed + 340 + transition_index,
            ),
        }
    supporting_transitions = [
        name
        for name, metric in transition_metrics.items()
        if metric["adjusted_revision_shift"]["mean"]
        >= thresholds["minimum_transition_revision_shift"]
    ]
    supporting_origins = sorted(
        {transition_metrics[name]["old_type"] for name in supporting_transitions}
    )
    swap_metrics = {
        "n_transition_pairs": len(swap_summaries),
        "n_randomized_bundles": len(set(swap_blocks)),
        "pre_new_match": _mean(row["pre_new_match"] for row in swap_summaries),
        "pre_old_match": _mean(row["pre_old_match"] for row in swap_summaries),
        "late_new_match": _mean(row["late_new_match"] for row in swap_summaries),
        "late_old_match": _mean(row["late_old_match"] for row in swap_summaries),
        "revision_shift": revision,
        "adjusted_new_target_gain": adjusted_new_gain,
        "adjusted_old_target_drop": adjusted_old_drop,
        "late_new_over_old": late_new_over_old,
        "development_revision_shift": _blocked_descriptive(
            [
                float(row["adjusted_development_revision_shift"])
                for row in swap_summaries
            ],
            swap_blocks,
            n_boot,
            seed + 222,
        ),
        "transition_metrics": transition_metrics,
        "supporting_transitions": supporting_transitions,
        "supporting_origin_types": supporting_origins,
        "n_adapted": sum(
            row["rounds_to_adapt"] is not None for row in swap_summaries
        ),
        "median_rounds_to_adapt": (
            float(
                np.median(
                    [
                        row["rounds_to_adapt"]
                        for row in swap_summaries
                        if row["rounds_to_adapt"] is not None
                    ]
                )
            )
            if any(row["rounds_to_adapt"] is not None for row in swap_summaries)
            else None
        ),
    }

    no_history_balance = _frame_balance(_unique_no_history_rows(records))
    overall_balance = no_history_balance["overall"]
    valid_rate = _mean(
        float(row.get("selection_valid", False)) for row in audit_records
    )
    fallback_rate = _mean(
        float(row.get("fallback_used", False)) for row in audit_records
    )
    no_history_gain = stable_metrics["no_history"]["learning_gain"]["mean"]
    random_gain = stable_metrics["random_target"]["learning_gain"]["mean"]
    alpha = thresholds["confirmatory_alpha_one_sided"]

    shared_agreement = False
    if shared_bundle_summary is not None:
        shared_agreement = all(
            math.isclose(float(left), float(right), abs_tol=1e-12)
            for left, right in (
                (
                    primary[
                        "stable_full_vs_no_difference_in_differences"
                    ]["mean"],
                    shared_bundle_summary["stable"],
                ),
                (revision["mean"], shared_bundle_summary["revision"]),
                (
                    adjusted_new_gain["mean"],
                    shared_bundle_summary["adjusted_new_gain"],
                ),
                (
                    adjusted_old_drop["mean"],
                    shared_bundle_summary["adjusted_old_drop"],
                ),
                (
                    late_new_over_old["mean"],
                    shared_bundle_summary["late_swap_new_minus_old"],
                ),
            )
        )
        shared_agreement = shared_agreement and math.isclose(
            float(
                primary[
                    "stable_full_vs_no_difference_in_differences"
                ]["p_value_one_sided"]
            ),
            float(
                shared_bundle_summary["stable_test"]["p_value_one_sided"]
            ),
            abs_tol=1e-15,
        ) and math.isclose(
            float(revision["p_value_one_sided"]),
            float(
                shared_bundle_summary["revision_test"]["p_value_one_sided"]
            ),
            abs_tol=1e-15,
        )
    design["checks"]["shared_power_analysis_exact_agreement"] = (
        shared_agreement
    )
    design["pass"] = all(design["checks"].values())

    shared_effect = (
        shared_bundle_summary["effect_gates"]
        if shared_bundle_summary is not None
        else {}
    )
    shared_inference = (
        shared_bundle_summary["inference_gates"]
        if shared_bundle_summary is not None
        else {}
    )

    effect_gates = {
        "design_integrity": bool(design["pass"]),
        "all_selections_valid": shared_effect.get(
            "all_selections_valid"
        ) is True,
        "no_fallback": shared_effect.get("zero_fallback") is True,
        "no_history_bank_balance": shared_effect.get(
            "no_history_frame_balance"
        ) is True,
        "no_history_learning_control": shared_effect.get(
            "no_history_learning_control"
        ) is True,
        "random_response_control": shared_effect.get(
            "random_target_learning_control"
        ) is True,
        "full_history_late_level": shared_effect.get(
            "full_history_late_level"
        ) is True,
        "full_over_no_history": shared_effect.get("full_over_no_late")
        is True,
        "all_target_types_supported": shared_effect.get(
            "all_target_types_supported"
        ) is True,
        "stable_difference_in_differences": shared_effect.get("stable")
        is True,
        "swap_vs_stable_adjusted_revision": shared_effect.get("revision")
        is True,
        "adjusted_new_target_gain": shared_effect.get(
            "adjusted_new_gain"
        ) is True,
        "adjusted_old_target_drop": shared_effect.get(
            "adjusted_old_drop"
        ) is True,
        "late_new_target_crossover": shared_effect.get(
            "late_swap_new_minus_old"
        ) is True,
        "directional_transition_support": shared_effect.get(
            "directional_transition_support"
        ) is True,
        "all_origin_types_support_revision": shared_effect.get(
            "all_origin_types_support_revision"
        ) is True,
    }
    diagnostic_gates = {
        "full_history_learning_gain": stable_metrics["full_history"][
            "learning_gain"
        ]["mean"]
        >= thresholds["minimum_full_history_learning_gain"],
        "shuffled_history_specificity": primary[
            "full_over_shuffled_late_heldout"
        ]["mean"]
        >= thresholds["minimum_full_over_shuffled_late_match"],
        "development_stable_wording_agrees": primary[
            "development_stable_difference_in_differences"
        ]["mean"]
        >= thresholds["minimum_development_stable_difference_in_differences"],
        "development_swap_wording_agrees": swap_metrics[
            "development_revision_shift"
        ]["mean"]
        >= thresholds["minimum_development_revision_shift"],
    }
    inference_gates = {
        "stable_exact_bundle_randomization_test": shared_inference.get(
            "stable_exact_one_sided"
        ) is True,
        "revision_exact_bundle_randomization_test": shared_inference.get(
            "revision_exact_one_sided"
        ) is True,
    }
    pattern_pass = all(effect_gates.values()) and all(inference_gates.values())
    input_valid = bool(design["pass"])
    if not input_valid:
        status = "invalid V6 confirmatory input"
        decision = "ALLOCATION_OR_PROVENANCE_INVALID"
    elif pattern_pass and mock_run:
        status = "mock-only V6 validation"
        decision = "MOCK_V6_PIPELINE_PASS_NOT_SCIENTIFIC_EVIDENCE"
    elif mock_run:
        status = "mock-only V6 validation"
        decision = "MOCK_V6_PIPELINE_PATTERN_FAIL"
    elif pattern_pass:
        status = "real-model V6 confirmatory checkpoint"
        decision = "VALID_POSITIVE_REPLICATION_REQUIRED"
    else:
        status = "real-model V6 confirmatory checkpoint"
        if not all(inference_gates.values()):
            decision = "VALID_NEGATIVE_SIGNIFICANCE"
        else:
            decision = "VALID_DISCORDANT_COMPONENT_PATTERN"

    trajectories = {
        name: {
            "match": _trajectory(
                _condition_rows(records, name), "strategy_match"
            ),
            "success": _trajectory(
                _condition_rows(records, name), "target_success"
            ),
        }
        for name in V6_REQUIRED_CONDITIONS
    }
    return {
        "task_version": CONTROLLED_V6_VERSION,
        "status": status,
        "decision": decision,
        "input_valid": input_valid,
        "pattern_pass": pattern_pass,
        "scientific_pass": bool(pattern_pass and not mock_run),
        "thresholds": thresholds,
        "design_integrity": design,
        "effect_gates": effect_gates,
        "inference_gates": inference_gates,
        "diagnostic_gates_nonconfirmatory": diagnostic_gates,
        "shared_power_analysis_summary": shared_bundle_summary,
        "valid_selection_rate": valid_rate,
        "fallback_rate": fallback_rate,
        "no_history_frame_balance": no_history_balance,
        "stable_condition_metrics": stable_metrics,
        "primary_contrasts": primary,
        "late_advantage_by_target_type": by_type,
        "supporting_target_types": supporting_types,
        "swap_metrics": swap_metrics,
        "swap_episode_summaries": swap_summaries,
        "secondary_diagnostics": {
            "late_new_exceeds_old": late_new_over_old["mean"] > 0.0,
            "late_new_over_old": late_new_over_old,
            "note": (
                "The late new-over-old crossover is a component magnitude gate; "
                "the co-primary randomized outcome is the swap-minus-stable "
                "adjusted revision contrast."
            ),
        },
        "trajectories": trajectories,
        "analysis_contract": {
            "early_window": [1, 6],
            "pre_swap_window": [7, 12],
            "heldout_late_window": [19, 24],
            "conditions": list(V6_REQUIRED_CONDITIONS),
            "ordered_transitions": sorted(
                "%s_to_%s" % transition for transition in expected_transitions
            ),
            "co_primary_alpha_each_one_sided": alpha,
            "randomization_unit": "episode-seed bundle",
            "randomization_seed": CONTROLLED_V6_RANDOMIZATION_SEED,
            "randomization_null": "Fisher sharp null of no bundle effect",
            "shared_power_analysis_helper": (
                "controlled_v6_power.analyze_v6_bundle_study"
            ),
            "power_contract_sha256": V6_POWER_CONTRACT_SHA256,
            "mean_intervals": "descriptive episode-bundle bootstrap",
            "scenario_set": "confirmatory",
            "scenario_ids": list(V6_CONFIRMATORY_SCENARIO_IDS),
            "scenario_set_canonical_sha256": (
                V6_CONFIRMATORY_SCENARIO_SHA256
            ),
            "outcome_triggered_behavior": False,
            "adaptive_actions": [],
            "reporting_policy": (
                "all fixed diagnostics are reported regardless of sign"
            ),
        },
        "analysis_execution": {
            **runtime_analysis_parameters,
            "matches_frozen_parameters": runtime_analysis_parameters_match,
            "canonical_out_dir": CONTROLLED_V6_ANALYSIS_CONFIG[
                "canonical_out_dir"
            ],
            "figure_bootstrap": json.loads(
                json.dumps(CONTROLLED_V6_ANALYSIS_CONFIG["figure_bootstrap"])
            ),
        },
        "interpretation_boundary": (
            "A real-model V6 pass rejects the two Fisher sharp no-effect nulls "
            "under prospective matched-bundle randomization and meets the frozen "
            "directional component gates for this model, bank, simulator, and "
            "schedule. It requires a separately frozen replication. A valid "
            "negative or discordant component pattern cannot trigger redesign, "
            "threshold relaxation, sample extension, or mechanistic rescue. The "
            "study tests registered-frame behavioral adaptation, not an explicit "
            "internal target representation or unseen-scenario generalization."
        ),
    }
