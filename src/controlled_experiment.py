"""Versioned controlled-choice experiment runner.

V3 remains untouched and reproducible through :mod:`src.experiment`. This
module removes language scoring from the target and primary outcome while
retaining complete prompts, raw outputs, candidate mappings, probabilities,
random draws, and histories for audit.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from config import (
    CONTROLLED_CONDITIONS,
    CONTROLLED_V4_VERSION,
    ControlledCondition,
    ControlledExperimentConfig,
    STRATEGIES,
)
from .controlled_focal_agent import (
    ControlledFocalAgent,
    ControlledHistoryEntry,
    ControlledMockProvider,
    SPONTANEOUS_SYSTEM_TEMPLATE,
    ELICITED_SYSTEM_TEMPLATE,
    active_spontaneous_prompt_variant,
    active_spontaneous_template,
    build_controlled_prompt,
    make_controlled_provider,
    parse_controlled_choice,
)
from .controlled_messages import candidate_for_slot
from .controlled_protocol import ControlledProtocol, V4_PROTOCOL
from .controlled_target import ControlledTarget
from .controlled_v6_randomization import (
    v6_allocation_schedule,
    v6_regime_assignment,
)
from .file_lock import (
    require_directory_nonsymlink,
    require_regular_nonsymlink,
)
from .focal_agent import BaseProvider
from .logging_utils import (
    JsonlWriter,
    ensure_contained_directory,
    open_regular_read_descriptor,
    publish_bytes_idempotent,
    read_jsonl,
    strict_json_load,
    unlink_regular_file,
    write_manifest,
)
from .scenarios import scenario_sequence
from .seeding import derive_seed


ProgressFn = Callable[[str], None]
RoundHook = Callable[[Mapping[str, Any]], None]

ROUND_ATOMIC_RESUME_POLICY = (
    "round-atomic generation: each paid coordinate is claimed before the provider "
    "call and each row is fsynced before its claim is cleared; --resume accepts one "
    "exact trailing partial-episode prefix"
)
EPISODE_ATOMIC_RESUME_POLICY = (
    "episode-atomic generation: records are appended only after all rounds of an "
    "episode complete; --resume skips validated complete episodes"
)


def controlled_resume_policy(round_atomic: bool) -> str:
    return (
        ROUND_ATOMIC_RESUME_POLICY
        if round_atomic
        else EPISODE_ATOMIC_RESUME_POLICY
    )


ROUND_CLAIM_FIELDS: Tuple[str, ...] = (
    "kind",
    "schema_version",
    "run_id",
    "task_version",
    "condition",
    "episode_id",
    "episode_index",
    "round",
    "round_seed",
    "scenario_id",
    "candidate_ids",
    "visible_history_sha256",
)


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _strict_json_equal(left: Any, right: Any) -> bool:
    try:
        return json.dumps(
            left, sort_keys=True, separators=(",", ":"), allow_nan=False
        ) == json.dumps(
            right, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (TypeError, ValueError):
        return False


def _publish_round_claim(
    path: str,
    payload: Mapping[str, Any],
    *,
    root: Optional[str] = None,
) -> None:
    """Durably create a claim without exposing a partial canonical file."""
    data = (
        json.dumps(
            dict(payload),
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    if root is None:
        parent = os.path.dirname(path) or "."
        os.makedirs(parent, exist_ok=True)
        require_directory_nonsymlink(
            parent, label="controlled round claim parent"
        )
        require_regular_nonsymlink(
            path, label="controlled round in-flight claim", allow_missing=True
        )
        if os.path.lexists(path):
            raise FileExistsError(
                "controlled round in-flight claim already exists: %s" % path
            )
    if not publish_bytes_idempotent(path, data, mode=0o600, root=root):
        raise FileExistsError(
            "controlled round in-flight claim already exists: %s" % path
        )


def _load_round_claim(
    path: str, *, root: Optional[str] = None
) -> Dict[str, Any]:
    descriptor = open_regular_read_descriptor(
        path,
        root=root,
        label="controlled round in-flight claim",
    )
    with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
        claim = strict_json_load(handle)
    if not isinstance(claim, dict) or set(claim) != set(ROUND_CLAIM_FIELDS):
        raise ValueError("controlled round in-flight claim has an invalid schema")
    for field in (
        "kind", "schema_version", "run_id", "task_version", "condition",
        "episode_id", "scenario_id", "visible_history_sha256",
    ):
        if type(claim[field]) is not str:
            raise ValueError("controlled round in-flight claim has invalid field types")
    for field in ("episode_index", "round", "round_seed"):
        if type(claim[field]) is not int:
            raise ValueError("controlled round in-flight claim has invalid field types")
    if type(claim["candidate_ids"]) is not list or any(
        type(candidate_id) is not str for candidate_id in claim["candidate_ids"]
    ):
        raise ValueError("controlled round in-flight claim has invalid candidate IDs")
    return claim


def _record_round_claim(record: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "kind": "controlled_round_in_flight",
        "schema_version": "1.0",
        "run_id": record["run_id"],
        "task_version": record["task_version"],
        "condition": record["condition"],
        "episode_id": record["episode_id"],
        "episode_index": record["episode_index"],
        "round": record["round"],
        "round_seed": record["round_seed"],
        "scenario_id": record["scenario_id"],
        "candidate_ids": [
            candidate["candidate_id"] for candidate in record["candidates"]
        ],
        "visible_history_sha256": _canonical_sha256(record["visible_history"]),
    }


def audit_or_recover_round_claim(
    path: str,
    records: Sequence[Mapping[str, Any]],
    run_id: str,
    *,
    root: Optional[str] = None,
) -> str:
    """Clear a logged claim, or stop when a paid provider call is ambiguous."""
    try:
        claim = _load_round_claim(path, root=root)
    except FileNotFoundError:
        return "absent"
    if claim.get("run_id") != run_id:
        raise ValueError("controlled round in-flight claim belongs to another run")
    matches = [
        row
        for row in records
        if row.get("episode_id") == claim.get("episode_id")
        and row.get("round") == claim.get("round")
    ]
    if not matches:
        raise RuntimeError(
            "ambiguous in-flight paid generation for %s round %s; the provider "
            "must not be called again automatically"
            % (claim.get("episode_id"), claim.get("round"))
        )
    if len(matches) != 1 or not _strict_json_equal(
        _record_round_claim(matches[0]), claim
    ):
        raise ValueError("controlled round claim does not match its durable log row")
    unlink_regular_file(
        path,
        root=root,
        label="controlled round in-flight claim",
    )
    return "recovered"


def _clear_round_claim(
    path: str,
    expected: Mapping[str, Any],
    *,
    root: Optional[str] = None,
) -> None:
    observed = _load_round_claim(path, root=root)
    if not _strict_json_equal(observed, dict(expected)):
        raise ValueError("controlled round in-flight claim changed during generation")
    unlink_regular_file(
        path,
        root=root,
        label="controlled round in-flight claim",
    )


CONTROLLED_REQUIRED_FIELDS: Tuple[str, ...] = (
    "task_version",
    "experiment_id",
    "run_id",
    "condition",
    "focal_mode",
    "episode_id",
    "episode_index",
    "round",
    "n_rounds",
    "hidden_target_type",
    "initial_target_type",
    "final_target_type",
    "swap_condition",
    "swap_round",
    "swap_has_occurred",
    "rounds_since_swap",
    "target_mode",
    "history_mode",
    "history_source_episode_id",
    "scenario_id",
    "scenario",
    "candidate_split",
    "candidates",
    "visible_candidates",
    "focal_system_prompt",
    "focal_user_prompt",
    "focal_output_raw",
    "selection_valid",
    "beliefs_valid",
    "fallback_used",
    "parse_error",
    "selected_slot",
    "selected_candidate_id",
    "selected_message",
    "selected_frame",
    "strategy_match",
    "predicted_p_a",
    "belief_primary_slot",
    "belief_primary_frame",
    "belief_matches_target",
    "selected_prediction_brier",
    "visible_history",
    "target_p_a",
    "target_choice",
    "target_uniform_draw",
    "target_success",
    "episode_seed",
    "round_seed",
    "target_draw_seed",
    "master_seed",
    "model_name",
    "provider",
    "timestamp",
    "pair_family",
    "pair_id",
    "pair_slot",
    "allocation_seed",
    "allocation_bit",
    "assigned_regime",
    "stable_counterfactual",
    "nominal_transition",
    "generation_id",
    "replication_group_id",
    "allocation_schedule_sha256",
)


def _require_exact_type(value: Any, expected: type, field: str) -> None:
    if type(value) is not expected:
        raise ValueError(
            "controlled field %s must have exact JSON type %s"
            % (field, expected.__name__)
        )


def _require_optional_exact_type(value: Any, expected: type, field: str) -> None:
    if value is not None:
        _require_exact_type(value, expected, field)


def _validate_probability(value: Any, field: str, *, upper_open: bool = False) -> None:
    _require_exact_type(value, float, field)
    valid = 0.0 <= value < 1.0 if upper_open else 0.0 <= value <= 1.0
    if not valid:
        raise ValueError("controlled probability %s is outside its valid range" % field)


def validate_controlled_record(record: Dict[str, Any]) -> None:
    missing = [field for field in CONTROLLED_REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError("controlled log record is missing fields: %s" % ", ".join(missing))
    for field in (
        "task_version", "experiment_id", "run_id", "condition", "focal_mode",
        "episode_id", "hidden_target_type", "initial_target_type",
        "final_target_type", "target_mode", "history_mode", "scenario_id",
        "candidate_split", "focal_system_prompt", "focal_user_prompt",
        "focal_output_raw", "selected_candidate_id", "selected_message",
        "selected_frame", "target_choice", "model_name", "provider", "timestamp",
        "assigned_regime", "generation_id",
    ):
        _require_exact_type(record[field], str, field)
    for field in (
        "episode_index", "round", "n_rounds", "selected_slot", "episode_seed",
        "round_seed", "target_draw_seed", "master_seed",
    ):
        _require_exact_type(record[field], int, field)
    for field in (
        "swap_condition", "swap_has_occurred", "selection_valid", "beliefs_valid",
        "fallback_used", "strategy_match", "target_success", "stable_counterfactual",
    ):
        _require_exact_type(record[field], bool, field)
    _require_optional_exact_type(record["swap_round"], int, "swap_round")
    _require_optional_exact_type(
        record["rounds_since_swap"], int, "rounds_since_swap"
    )
    _require_optional_exact_type(
        record["history_source_episode_id"], str, "history_source_episode_id"
    )
    _require_optional_exact_type(record["parse_error"], str, "parse_error")
    for field in (
        "pair_family",
        "pair_id",
        "nominal_transition",
        "replication_group_id",
        "allocation_schedule_sha256",
    ):
        _require_optional_exact_type(record[field], str, field)
    for field in ("pair_slot", "allocation_seed", "allocation_bit"):
        _require_optional_exact_type(record[field], int, field)
    _require_optional_exact_type(
        record["belief_primary_slot"], int, "belief_primary_slot"
    )
    _require_optional_exact_type(
        record["belief_primary_frame"], str, "belief_primary_frame"
    )
    _require_optional_exact_type(
        record["belief_matches_target"], bool, "belief_matches_target"
    )
    _require_optional_exact_type(
        record["selected_prediction_brier"], float, "selected_prediction_brier"
    )
    if record["episode_index"] < 0 or record["round"] < 1 or record["n_rounds"] < 1:
        raise ValueError("controlled round/index fields are outside their valid range")
    if record["round"] > record["n_rounds"]:
        raise ValueError("controlled round exceeds n_rounds")
    if any(record[field] < 0 for field in (
        "episode_seed", "round_seed", "target_draw_seed", "master_seed"
    )):
        raise ValueError("controlled seed fields must be non-negative integers")
    if record["assigned_regime"] != record["condition"]:
        raise ValueError("assigned_regime must equal the logged condition")
    if record["stable_counterfactual"] != (
        record["condition"] == "swap_control"
    ):
        raise ValueError("stable_counterfactual is inconsistent with condition")
    if record["pair_slot"] is not None and record["pair_slot"] not in {0, 1}:
        raise ValueError("pair_slot must be 0, 1, or null")
    if record["allocation_bit"] is not None and record["allocation_bit"] not in {
        0,
        1,
    }:
        raise ValueError("allocation_bit must be 0, 1, or null")

    _require_exact_type(record["scenario"], dict, "scenario")
    _require_exact_type(record["candidates"], list, "candidates")
    _require_exact_type(record["visible_candidates"], list, "visible_candidates")
    _require_exact_type(record["visible_history"], list, "visible_history")
    candidates = record["candidates"]
    if len(candidates) != 3:
        raise ValueError("controlled record must contain exactly three candidates")
    if any(type(candidate) is not dict for candidate in candidates):
        raise ValueError("controlled candidates must be JSON objects")
    for candidate in candidates:
        _require_exact_type(candidate.get("slot"), int, "candidates[].slot")
        for field in ("frame", "candidate_id", "message"):
            _require_exact_type(candidate.get(field), str, "candidates[].%s" % field)
    if {candidate["frame"] for candidate in candidates} != set(STRATEGIES):
        raise ValueError("controlled candidates must contain each registered frame once")
    if {candidate["slot"] for candidate in candidates} != {1, 2, 3}:
        raise ValueError("controlled candidates must occupy slots 1, 2, and 3")
    if record["selected_slot"] not in {1, 2, 3}:
        raise ValueError("selected_slot must be the integer 1, 2, or 3")
    if record["selected_frame"] not in STRATEGIES:
        raise ValueError("selected frame is not registered")
    if any(record[name] not in STRATEGIES for name in (
        "hidden_target_type", "initial_target_type", "final_target_type"
    )):
        raise ValueError("record contains an unknown target type")
    selected = [
        candidate for candidate in candidates
        if candidate["slot"] == record["selected_slot"]
    ]
    if len(selected) != 1 or any(
        record[field] != selected[0][candidate_field]
        for field, candidate_field in (
            ("selected_candidate_id", "candidate_id"),
            ("selected_message", "message"),
            ("selected_frame", "frame"),
        )
    ):
        raise ValueError("selected candidate fields are inconsistent")
    expected_visible_candidates = [
        {"slot": candidate["slot"], "message": candidate["message"]}
        for candidate in candidates
    ]
    if any(
        type(candidate) is not dict
        or set(candidate) != {"slot", "message"}
        or type(candidate["slot"]) is not int
        or type(candidate["message"]) is not str
        for candidate in record["visible_candidates"]
    ):
        raise ValueError("visible candidate projection has invalid JSON types")
    if record["visible_candidates"] != expected_visible_candidates:
        raise ValueError("visible candidate projection is inconsistent")
    if record["target_choice"] not in {"A", "B"}:
        raise ValueError("target choice must be A or B")
    if record["strategy_match"] != (
        record["selected_frame"] == record["hidden_target_type"]
    ):
        raise ValueError("strategy_match is inconsistent with registered ground truth")
    _validate_probability(record["target_p_a"], "target_p_a")
    _validate_probability(
        record["target_uniform_draw"], "target_uniform_draw", upper_open=True
    )
    probability = record["target_p_a"]
    draw = record["target_uniform_draw"]
    if record["target_choice"] != ("A" if draw < probability else "B"):
        raise ValueError("target choice is inconsistent with probability and draw")
    if record["target_success"] != (record["target_choice"] == "A"):
        raise ValueError("target_success is inconsistent with target choice")
    predicted = record["predicted_p_a"]
    if predicted is not None:
        _require_exact_type(predicted, dict, "predicted_p_a")
        if set(predicted) != {"1", "2", "3"}:
            raise ValueError("predicted_p_a must contain exact slot keys 1, 2, and 3")
        for slot, value in predicted.items():
            _validate_probability(value, "predicted_p_a.%s" % slot)
    expected_history_fields = (
        {"round", "scenario_title", "selected_message", "choice"}
        if record["focal_mode"] == "spontaneous"
        else {
            "round", "scenario_title", "selected_message", "choice",
            "predicted_p_a", "candidate_messages",
        }
    )
    if any(type(entry) is not dict for entry in record["visible_history"]):
        raise ValueError("visible_history entries must be JSON objects")
    if any(set(entry) != expected_history_fields for entry in record["visible_history"]):
        raise ValueError("visible_history contains fields not rendered to the focal model")
    for entry in record["visible_history"]:
        _require_exact_type(entry["round"], int, "visible_history[].round")
        for field in ("scenario_title", "selected_message", "choice"):
            _require_exact_type(entry[field], str, "visible_history[].%s" % field)
        if record["focal_mode"] == "elicited":
            _require_exact_type(
                entry["candidate_messages"], dict,
                "visible_history[].candidate_messages",
            )
            _require_exact_type(
                entry["predicted_p_a"], dict, "visible_history[].predicted_p_a"
            )
            if set(entry["predicted_p_a"]) != {"1", "2", "3"}:
                raise ValueError("visible-history predictions have invalid slot keys")
            for slot, value in entry["predicted_p_a"].items():
                _validate_probability(
                    value, "visible_history[].predicted_p_a.%s" % slot
                )


@dataclass(frozen=True)
class ControlledEpisodeSpec:
    condition: ControlledCondition
    episode_index: int
    initial_target_type: str
    final_target_type: str
    n_rounds: int
    swap_round: Optional[int]
    episode_id: str
    pair_family: Optional[str] = None
    pair_id: Optional[str] = None
    pair_slot: Optional[int] = None
    allocation_seed: Optional[int] = None
    allocation_bit: Optional[int] = None
    assigned_regime: Optional[str] = None
    stable_counterfactual: bool = False
    nominal_transition: Optional[str] = None
    allocation_schedule_sha256: Optional[str] = None

    @property
    def swaps(self) -> bool:
        return self.condition.swap and self.initial_target_type != self.final_target_type

    def active_type(self, round_index: int) -> str:
        if self.swaps and self.swap_round is not None and round_index > self.swap_round:
            return self.final_target_type
        return self.initial_target_type


def controlled_episode_seed(
    spec: ControlledEpisodeSpec,
    cfg: ControlledExperimentConfig,
    protocol_version: str,
) -> int:
    """Return the registered episode seed used by generation and replay."""
    if spec.pair_family is not None:
        return derive_seed(
            cfg.seed,
            protocol_version,
            "randomized_branch",
            spec.pair_family,
            spec.pair_slot,
            spec.episode_index,
            spec.initial_target_type,
            spec.final_target_type,
        )
    return derive_seed(
        cfg.seed,
        protocol_version,
        spec.condition.name,
        spec.episode_index,
        spec.initial_target_type,
        spec.final_target_type,
    )


def controlled_round_identity(
    spec: ControlledEpisodeSpec,
    cfg: ControlledExperimentConfig,
    protocol_version: str,
    round_index: int,
) -> Tuple[int, int, str, Optional[str]]:
    """Return generation/draw seeds and replication IDs for one coordinate.

    Keeping this derivation in one function prevents the fail-closed replay
    audit from silently drifting away from the runtime implementation.
    """
    condition = spec.condition
    episode_seed = controlled_episode_seed(spec, cfg, protocol_version)
    if cfg.randomization_seed is not None and spec.pair_family is not None:
        if spec.pair_slot not in {0, 1}:
            raise ValueError("randomized V6 branch is missing its physical slot")
        round_seed = derive_seed(
            cfg.seed,
            protocol_version,
            "physical_slot_generation",
            spec.pair_family,
            spec.episode_index,
            spec.pair_slot,
            spec.nominal_transition,
            round_index,
        )
        generation_id = "physical-slot-%s-%03d-%d-%s-%02d" % (
            spec.pair_family,
            spec.episode_index,
            spec.pair_slot,
            spec.nominal_transition or "stable",
            round_index,
        )
        replication_group_id: Optional[str] = (
            generation_id if condition.name == "no_history" else None
        )
    else:
        round_seed = derive_seed(episode_seed, "focal_generation", round_index)
        generation_id = "%s-%02d" % (spec.episode_id, round_index)
        replication_group_id = None

    if spec.pair_family == "history_access":
        target_draw_seed = derive_seed(
            cfg.seed,
            protocol_version,
            "physical_slot_target_draw",
            spec.pair_family,
            spec.episode_index,
            spec.pair_slot,
            spec.initial_target_type,
            round_index,
        )
    elif spec.pair_family == "target_regime":
        target_draw_seed = derive_seed(
            cfg.seed,
            protocol_version,
            "physical_slot_target_draw",
            spec.pair_family,
            spec.episode_index,
            spec.pair_slot,
            spec.nominal_transition,
            round_index,
        )
    else:
        target_draw_seed = derive_seed(
            cfg.seed,
            protocol_version,
            "target_draw",
            spec.episode_index,
            spec.initial_target_type,
            spec.final_target_type,
            round_index,
        )
    return round_seed, target_draw_seed, generation_id, replication_group_id


def _swap_partners(initial: str) -> List[str]:
    if initial not in STRATEGIES:
        raise ValueError("unknown initial target type %r" % initial)
    return [target for target in STRATEGIES if target != initial]


def validate_controlled_config(cfg: ControlledExperimentConfig) -> None:
    if cfg.n_rounds < 6:
        raise ValueError("controlled V4 needs at least six rounds")
    if not 1 < cfg.swap_round < cfg.n_rounds:
        raise ValueError("swap_round must be inside the episode")
    if not cfg.swap_round < cfg.heldout_start_round <= cfg.n_rounds:
        raise ValueError("heldout rounds must begin after the silent swap")
    if cfg.n_episode_seeds < 1:
        raise ValueError("n_episode_seeds must be positive")
    if cfg.randomization_seed is not None:
        if type(cfg.randomization_seed) is not int or cfg.randomization_seed < 0:
            raise ValueError("randomization_seed must be a non-negative integer")
        required = {"full_history", "no_history", "swap", "swap_control"}
        if not required <= set(cfg.conditions):
            raise ValueError(
                "randomized V6 requires full/no-history and swap/control pairs"
            )
    elif "swap_control" in cfg.conditions:
        raise ValueError("swap_control requires prospective randomization")
    unknown = [name for name in cfg.conditions if name not in CONTROLLED_CONDITIONS]
    if unknown:
        raise ValueError("unknown controlled conditions: %s" % unknown)
    if "shuffled_history" in cfg.conditions:
        if "full_history" not in cfg.conditions:
            raise ValueError("shuffled_history requires full_history donors")
        if cfg.conditions.index("shuffled_history") < cfg.conditions.index("full_history"):
            raise ValueError("full_history must precede shuffled_history")


def build_controlled_episode_specs(
    cfg: ControlledExperimentConfig,
) -> List[ControlledEpisodeSpec]:
    validate_controlled_config(cfg)
    specs: List[ControlledEpisodeSpec] = []
    allocation_schedule = (
        v6_allocation_schedule(
            cfg.n_episode_seeds, seed=int(cfg.randomization_seed)
        )
        if cfg.randomization_seed is not None
        else None
    )
    for condition_name in cfg.conditions:
        condition = CONTROLLED_CONDITIONS[condition_name]
        for episode_index in range(cfg.n_episode_seeds):
            for initial in STRATEGIES:
                finals = (
                    _swap_partners(initial)
                    if condition.swap or condition.stable_counterfactual
                    else [initial]
                )
                for final in finals:
                    assignment = (
                        v6_regime_assignment(
                            condition.name,
                            episode_index,
                            seed=int(cfg.randomization_seed),
                        )
                        if cfg.randomization_seed is not None
                        else {
                            "pair_family": None,
                            "pair_id": None,
                            "pair_slot": None,
                            "allocation_bit": None,
                            "assigned_regime": condition.name,
                        }
                    )
                    transition_condition = (
                        condition.swap or condition.stable_counterfactual
                    )
                    episode_id = (
                        "%s-%03d-%s-to-%s"
                        % (condition.name, episode_index, initial, final)
                        if transition_condition
                        else "%s-%03d-%s" % (condition.name, episode_index, initial)
                    )
                    specs.append(
                        ControlledEpisodeSpec(
                            condition=condition,
                            episode_index=episode_index,
                            initial_target_type=initial,
                            final_target_type=final,
                            n_rounds=cfg.n_rounds,
                            swap_round=(
                                cfg.swap_round if transition_condition else None
                            ),
                            episode_id=episode_id,
                            pair_family=assignment["pair_family"],
                            pair_id=assignment["pair_id"],
                            pair_slot=assignment["pair_slot"],
                            allocation_seed=cfg.randomization_seed,
                            allocation_bit=assignment["allocation_bit"],
                            assigned_regime=condition.name,
                            stable_counterfactual=condition.stable_counterfactual,
                            nominal_transition=(
                                "%s_to_%s" % (initial, final)
                                if transition_condition
                                else None
                            ),
                            allocation_schedule_sha256=(
                                allocation_schedule["schedule_sha256"]
                                if allocation_schedule is not None
                                else None
                            ),
                        )
                    )
    if cfg.randomization_seed is None:
        return specs

    # Randomize primary episode execution order to prevent a fixed treatment
    # order from being aliased with provider/runtime drift.  Shuffled-history
    # controls remain last because they consume completed full-history donors.
    primary = [spec for spec in specs if spec.condition.name != "shuffled_history"]
    donors = [spec for spec in specs if spec.condition.name == "shuffled_history"]
    generator = np.random.Generator(
        np.random.PCG64DXSM(
            np.random.SeedSequence([int(cfg.randomization_seed), 2])
        )
    )
    order = generator.permutation(len(primary))
    return [primary[int(index)] for index in order] + donors


class ControlledDonorRegistry:
    def __init__(self) -> None:
        self._store: Dict[
            Tuple[int, str], Tuple[str, List[ControlledHistoryEntry]]
        ] = {}

    def add(
        self,
        episode_index: int,
        target_type: str,
        episode_id: str,
        history: Sequence[ControlledHistoryEntry],
    ) -> None:
        self._store[(episode_index, target_type)] = (episode_id, list(history))

    def donor_for(
        self, episode_index: int, true_type: str
    ) -> Tuple[str, List[ControlledHistoryEntry]]:
        index = STRATEGIES.index(true_type)
        for offset in (1, 2):
            key = (episode_index, STRATEGIES[(index + offset) % len(STRATEGIES)])
            if key in self._store:
                return self._store[key]
        raise KeyError("no V4 full-history donor exists for episode %d" % episode_index)


@dataclass
class ControlledEpisodeResult:
    episode_id: str
    records: List[Dict[str, Any]]
    own_history: List[ControlledHistoryEntry]


def _belief_fields(parsed, candidates, active_type: str, choice: str) -> Dict[str, Any]:
    if not parsed.beliefs_valid or parsed.predicted_p_a is None:
        return {
            "belief_primary_slot": None,
            "belief_primary_frame": None,
            "belief_matches_target": None,
            "selected_prediction_brier": None,
        }
    primary_slot = max(
        (1, 2, 3), key=lambda slot: (parsed.predicted_p_a[str(slot)], -slot)
    )
    primary_frame = next(
        candidate.frame for candidate in candidates if candidate.slot == primary_slot
    )
    selected_prediction = parsed.predicted_p_a[str(parsed.selected_slot)]
    observed = 1.0 if choice == "A" else 0.0
    return {
        "belief_primary_slot": primary_slot,
        "belief_primary_frame": primary_frame,
        "belief_matches_target": primary_frame == active_type,
        "selected_prediction_brier": float((selected_prediction - observed) ** 2),
    }


def run_controlled_episode(
    spec: ControlledEpisodeSpec,
    cfg: ControlledExperimentConfig,
    agent: ControlledFocalAgent,
    run_id: str,
    donors: Optional[ControlledDonorRegistry] = None,
    progress: Optional[ProgressFn] = None,
    protocol: ControlledProtocol = V4_PROTOCOL,
    start_round: int = 1,
    end_round: Optional[int] = None,
    own_history_prefix: Optional[Sequence[ControlledHistoryEntry]] = None,
    record_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
    before_generation: Optional[RoundHook] = None,
    after_record_durable: Optional[RoundHook] = None,
    generation_cache: Optional[Dict[str, Tuple[str, str, str]]] = None,
) -> ControlledEpisodeResult:
    condition = spec.condition
    scenarios = protocol.scenario_sequence(
        spec.episode_index, spec.n_rounds, cfg.seed
    ) or scenario_sequence(spec.episode_index, spec.n_rounds, cfg.seed)
    episode_seed = controlled_episode_seed(spec, cfg, protocol.version)

    final_round = spec.n_rounds if end_round is None else int(end_round)
    if not 1 <= start_round <= spec.n_rounds + 1:
        raise ValueError("controlled episode start_round is outside the episode")
    if not start_round - 1 <= final_round <= spec.n_rounds:
        raise ValueError("controlled episode end_round is outside the episode")
    own_history = list(own_history_prefix or [])
    if [entry.round for entry in own_history] != list(range(1, start_round)):
        raise ValueError("controlled episode history is not the exact prior-round prefix")
    donor_history: List[ControlledHistoryEntry] = []
    donor_episode_id: Optional[str] = None
    if condition.history_mode == "shuffled":
        if donors is None:
            raise ValueError("shuffled V4 history needs a donor registry")
        donor_episode_id, donor_history = donors.donor_for(
            spec.episode_index, spec.initial_target_type
        )

    records: List[Dict[str, Any]] = []
    for round_index in range(start_round, final_round + 1):
        scenario = scenarios[round_index - 1]
        active_type = spec.active_type(round_index)
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

        if condition.history_mode == "none":
            visible_history: List[ControlledHistoryEntry] = []
            history_source_episode_id = None
        elif condition.history_mode == "shuffled":
            visible_history = list(donor_history[: round_index - 1])
            history_source_episode_id = donor_episode_id
        else:
            visible_history = list(own_history)
            history_source_episode_id = spec.episode_id

        mock_context = {
            "task_version": protocol.version,
            "round_index": round_index,
            "n_rounds": spec.n_rounds,
            "episode_seed": episode_seed,
            "round_seed": round_seed,
            "focal_mode": condition.focal_mode,
            "hidden_target_type": active_type,
            "candidates": [candidate.as_dict() for candidate in candidates],
            "visible_history": [entry.mock_dict() for entry in visible_history],
            "target_params": cfg.target_params.as_dict(),
        }
        if cfg.randomization_seed is not None and condition.name == "no_history":
            # The implementation-control mock's tie breaker must respect the
            # same prompt identity as a real deterministic provider.  Hidden
            # target and randomized branch identifiers are not prompt-visible.
            mock_context["episode_seed"] = derive_seed(
                cfg.seed,
                protocol.version,
                "physical_slot_visible_prompt_identity",
                spec.pair_family,
                spec.episode_index,
                spec.pair_slot,
                round_index,
            )
        set_next_seed = getattr(agent.provider, "set_next_seed", None)
        if callable(set_next_seed):
            set_next_seed(round_seed)
        round_claim = {
            "kind": "controlled_round_in_flight",
            "schema_version": "1.0",
            "run_id": run_id,
            "task_version": protocol.version,
            "condition": condition.name,
            "episode_id": spec.episode_id,
            "episode_index": spec.episode_index,
            "round": round_index,
            "round_seed": round_seed,
            "scenario_id": scenario.id,
            "candidate_ids": [candidate.candidate_id for candidate in candidates],
            "visible_history_sha256": _canonical_sha256(
                [
                    entry.visible_dict(
                        include_predictions=condition.focal_mode == "elicited"
                    )
                    for entry in visible_history
                ]
            ),
        }
        cached_generation = (
            generation_cache.get(replication_group_id)
            if generation_cache is not None and replication_group_id is not None
            else None
        )
        generation_claimed = False
        if cached_generation is None:
            if before_generation is not None:
                before_generation(round_claim)
                generation_claimed = True
            prompt, raw, parsed, selected = agent.choose(
                scenario=scenario,
                candidates=candidates,
                history=visible_history,
                round_index=round_index,
                n_rounds=spec.n_rounds,
                show_history=condition.history_mode != "none",
                focal_mode=condition.focal_mode,
                round_seed=round_seed,
                context=(
                    mock_context
                    if isinstance(agent.provider, ControlledMockProvider)
                    else {}
                ),
                require_valid_selection=protocol.strict_selection,
            )
            if generation_cache is not None and replication_group_id is not None:
                generation_cache[replication_group_id] = (
                    prompt.system,
                    prompt.user,
                    raw,
                )
        else:
            prompt = build_controlled_prompt(
                scenario=scenario,
                candidates=candidates,
                history=visible_history,
                round_index=round_index,
                n_rounds=spec.n_rounds,
                show_history=condition.history_mode != "none",
                focal_mode=condition.focal_mode,
                context=(
                    mock_context
                    if isinstance(agent.provider, ControlledMockProvider)
                    else {}
                ),
            )
            expected_system, expected_user, raw = cached_generation
            if (prompt.system, prompt.user) != (expected_system, expected_user):
                raise RuntimeError(
                    "replication group reused across non-identical prompts"
                )
            parsed = parse_controlled_choice(raw, condition.focal_mode, round_seed)
            if protocol.strict_selection and not parsed.selection_valid:
                raise RuntimeError("cached strict V6 generation is invalid")
            selected = candidate_for_slot(candidates, parsed.selected_slot)

        target = ControlledTarget(
            hidden_type=active_type,
            mode=condition.target_mode,
            params=cfg.target_params,
        )
        response = target.respond(
            selected.frame, np.random.default_rng(target_draw_seed)
        )
        belief = _belief_fields(parsed, candidates, active_type, response.choice)
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
                str(candidate.slot): candidate.message for candidate in candidates
            },
        )
        own_history.append(history_entry)

        record: Dict[str, Any] = {
            "task_version": protocol.version,
            "experiment_id": cfg.experiment_id,
            "run_id": run_id,
            "condition": condition.name,
            "focal_mode": condition.focal_mode,
            "episode_id": spec.episode_id,
            "episode_index": spec.episode_index,
            "round": round_index,
            "n_rounds": spec.n_rounds,
            "hidden_target_type": active_type,
            "initial_target_type": spec.initial_target_type,
            "final_target_type": spec.final_target_type,
            "swap_condition": spec.swaps,
            "swap_round": spec.swap_round,
            "swap_has_occurred": bool(spec.swaps and round_index > cfg.swap_round),
            "rounds_since_swap": (
                round_index - cfg.swap_round if spec.swaps else None
            ),
            "target_mode": condition.target_mode,
            "history_mode": condition.history_mode,
            "history_source_episode_id": history_source_episode_id,
            "scenario_id": scenario.id,
            "scenario": scenario.as_dict(),
            "candidate_split": candidates[0].split,
            "candidates": [candidate.as_dict() for candidate in candidates],
            "visible_candidates": [candidate.visible_dict() for candidate in candidates],
            "focal_system_prompt": prompt.system,
            "focal_user_prompt": prompt.user,
            "focal_output_raw": raw,
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
            **belief,
            "visible_history": [
                entry.visible_dict(include_predictions=condition.focal_mode == "elicited")
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
            "model_name": getattr(agent.provider, "model", None)
            or getattr(agent.provider, "model_id", None)
            or cfg.model.model,
            "provider": agent.provider.name,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "pair_family": spec.pair_family,
            "pair_id": spec.pair_id,
            "pair_slot": spec.pair_slot,
            "allocation_seed": spec.allocation_seed,
            "allocation_bit": spec.allocation_bit,
            "assigned_regime": spec.assigned_regime or condition.name,
            "stable_counterfactual": spec.stable_counterfactual,
            "nominal_transition": spec.nominal_transition,
            "generation_id": generation_id,
            "replication_group_id": replication_group_id,
            "allocation_schedule_sha256": spec.allocation_schedule_sha256,
        }
        validate_controlled_record(record)
        if _record_round_claim(record) != round_claim:
            raise RuntimeError("controlled round claim does not bind the generated row")
        if record_sink is not None:
            record_sink(record)
        if generation_claimed and after_record_durable is not None:
            after_record_durable(round_claim)
        records.append(record)

        tag_last = getattr(agent.provider, "tag_last", None)
        if cached_generation is None and callable(tag_last):
            tag_last(
                {
                    "task_version": protocol.version,
                    "condition": condition.name,
                    "episode_id": spec.episode_id,
                    "round": round_index,
                    "hidden_target_type": active_type,
                    "initial_target_type": spec.initial_target_type,
                    "final_target_type": spec.final_target_type,
                    "selected_frame": selected.frame,
                    "strategy_match": selected.frame == active_type,
                    "candidate_split": selected.split,
                }
            )
        if progress is not None:
            progress(
                "%s round %d/%d complete"
                % (spec.episode_id, round_index, spec.n_rounds)
            )

    return ControlledEpisodeResult(
        episode_id=spec.episode_id,
        records=records,
        own_history=own_history,
    )


@dataclass
class ControlledExperimentResult:
    log_path: str
    manifest_path: str
    n_records: int
    n_episodes: int
    records: List[Dict[str, Any]]
    provider: BaseProvider


def _manifest_payload(
    cfg: ControlledExperimentConfig,
    provider: BaseProvider,
    specs: Sequence[ControlledEpisodeSpec],
    run_status: str,
    n_records: int,
    n_episodes_completed: int,
    protocol: ControlledProtocol = V4_PROTOCOL,
    round_atomic: bool = False,
) -> Dict[str, Any]:
    payload = {
        "task_version": protocol.version,
        "scientific_status": (
            "mock-only implementation control"
            if str(provider.name).startswith("mock:")
            else "real-model behavioral checkpoint"
        ),
        "run_status": run_status,
        "config": cfg.as_dict(),
        "conditions": {
            name: {
                "name": condition.name,
                "history_mode": condition.history_mode,
                "target_mode": condition.target_mode,
                "swap": condition.swap,
                "stable_counterfactual": condition.stable_counterfactual,
                "focal_mode": condition.focal_mode,
                "description": condition.description,
            }
            for name, condition in CONTROLLED_CONDITIONS.items()
            if name in cfg.conditions
        },
        "provider": provider.describe(),
        "n_records": n_records,
        "n_episodes": len(specs) if run_status == "completed" else n_episodes_completed,
        "expected_n_records": sum(spec.n_rounds for spec in specs),
        "expected_n_episodes": len(specs),
        "focal_prompt_templates": {
            "spontaneous_prompt_variant": active_spontaneous_prompt_variant(),
            "spontaneous_system_template": active_spontaneous_template(),
            "spontaneous_system_template_v4": SPONTANEOUS_SYSTEM_TEMPLATE,
            "elicited_system_template": ELICITED_SYSTEM_TEMPLATE,
            "spontaneous_system_rendered": active_spontaneous_template().format(
                n_rounds=cfg.n_rounds
            ),
            "elicited_system_rendered": ELICITED_SYSTEM_TEMPLATE.format(
                n_rounds=cfg.n_rounds
            ),
        },
        "message_banks": protocol.message_bank_manifest(),
        "message_bank_sha256": protocol.message_bank_sha256(),
        "information_boundary": (
            "real providers receive only rendered system/user prompts; registered "
            "frames and hidden types exist only in logs and mock context"
        ),
        "resume_policy": (
            controlled_resume_policy(round_atomic)
        ),
    }
    if cfg.randomization_seed is not None:
        payload["randomization_schedule"] = v6_allocation_schedule(
            cfg.n_episode_seeds, seed=cfg.randomization_seed
        )
    if protocol.version != CONTROLLED_V4_VERSION or protocol.strict_selection:
        payload["selection_policy"] = protocol.selection_policy_manifest()
        payload["message_bank_source"] = protocol.bank_source
        provenance = protocol.protocol_provenance_manifest()
        if provenance is not None:
            payload["protocol_provenance"] = provenance
    return payload


def _history_from_records(
    records: Sequence[Mapping[str, Any]],
) -> List[ControlledHistoryEntry]:
    history: List[ControlledHistoryEntry] = []
    for row in sorted(records, key=lambda item: int(item["round"])):
        history.append(
            ControlledHistoryEntry(
                round=int(row["round"]),
                scenario_id=str(row["scenario_id"]),
                scenario_title=str(row["scenario"]["title"]),
                selected_slot=int(row["selected_slot"]),
                selected_message=str(row["selected_message"]),
                selected_frame=str(row["selected_frame"]),
                choice=str(row["target_choice"]),
                predicted_p_a=(
                    {str(key): float(value) for key, value in row["predicted_p_a"].items()}
                    if row.get("predicted_p_a") is not None else None
                ),
                candidate_messages={
                    str(candidate["slot"]): str(candidate["message"])
                    for candidate in row["candidates"]
                },
            )
        )
    return history


def _load_resume_state(
    cfg: ControlledExperimentConfig,
    provider: BaseProvider,
    specs: Sequence[ControlledEpisodeSpec],
    log_path: str,
    manifest_path: str,
    protocol: ControlledProtocol = V4_PROTOCOL,
    round_atomic: bool = False,
    artifact_root: Optional[str] = None,
) -> Tuple[
    List[Dict[str, Any]],
    Dict[str, List[Dict[str, Any]]],
    Dict[str, List[Dict[str, Any]]],
]:
    if not os.path.exists(manifest_path):
        raise FileNotFoundError("cannot resume without manifest %s" % manifest_path)
    manifest_descriptor = open_regular_read_descriptor(
        manifest_path,
        root=artifact_root,
        label="controlled resume manifest",
    )
    with os.fdopen(manifest_descriptor, "r", encoding="utf-8") as handle:
        existing_manifest = strict_json_load(handle)
    if existing_manifest.get("task_version") != protocol.version:
        raise ValueError("resume manifest has a different task version")
    if existing_manifest.get("config") != cfg.as_dict():
        raise ValueError("resume config differs from the existing manifest")
    if existing_manifest.get("resume_policy") != controlled_resume_policy(round_atomic):
        raise ValueError("resume durability policy differs from the existing manifest")
    dynamic_provider_fields = {"architecture", "loaded_with", "processor"}
    existing_provider = {
        key: value for key, value in existing_manifest.get("provider", {}).items()
        if key not in dynamic_provider_fields
    }
    current_provider = {
        key: value for key, value in provider.describe().items()
        if key not in dynamic_provider_fields
    }
    if existing_provider != current_provider:
        raise ValueError("resume provider settings differ from the existing manifest")
    if existing_manifest.get("message_bank_sha256") != protocol.message_bank_sha256():
        raise ValueError("resume message bank differs from the existing manifest")
    if protocol.version != CONTROLLED_V4_VERSION or protocol.strict_selection:
        if existing_manifest.get("selection_policy") != (
            protocol.selection_policy_manifest()
        ):
            raise ValueError("resume selection policy differs from the existing manifest")
    protocol_provenance = protocol.protocol_provenance_manifest()
    if protocol_provenance is not None and existing_manifest.get(
        "protocol_provenance"
    ) != protocol_provenance:
        raise ValueError("resume protocol provenance differs from the existing manifest")

    records = (
        list(read_jsonl(log_path, root=artifact_root))
        if os.path.exists(log_path)
        else []
    )
    by_episode: Dict[str, List[Dict[str, Any]]] = {}
    keys = set()
    for record in records:
        validate_controlled_record(record)
        key = (str(record["episode_id"]), int(record["round"]))
        if key in keys:
            raise ValueError("resume log contains duplicate round key %r" % (key,))
        keys.add(key)
        by_episode.setdefault(str(record["episode_id"]), []).append(record)

    spec_by_id = {spec.episode_id: spec for spec in specs}
    unknown = sorted(set(by_episode) - set(spec_by_id))
    if unknown:
        raise ValueError("resume log contains episodes outside this config: %s" % unknown)
    if round_atomic:
        expected_coordinates = [
            (spec.episode_id, round_index)
            for spec in specs
            for round_index in range(1, spec.n_rounds + 1)
        ]
        observed_coordinates = [
            (str(record["episode_id"]), record["round"]) for record in records
        ]
        if observed_coordinates != expected_coordinates[: len(observed_coordinates)]:
            raise ValueError("resume log is not one exact official episode/round prefix")

    completed: Dict[str, List[Dict[str, Any]]] = {}
    partial: Dict[str, List[Dict[str, Any]]] = {}
    for episode_id, episode_records in by_episode.items():
        expected_rounds = spec_by_id[episode_id].n_rounds
        rounds = sorted(record["round"] for record in episode_records)
        if rounds == list(range(1, expected_rounds + 1)):
            completed[episode_id] = episode_records
        elif round_atomic and rounds == list(range(1, len(rounds) + 1)):
            partial[episode_id] = episode_records
        else:
            raise ValueError(
                "resume log has an incomplete episode %s; preserve it for audit and "
                "start a new run id rather than silently truncating data" % episode_id
            )
    if len(partial) > 1:
        raise ValueError("resume log contains more than one partial episode")
    return records, completed, partial


def run_controlled_experiment(
    cfg: ControlledExperimentConfig,
    run_id: Optional[str] = None,
    provider: Optional[BaseProvider] = None,
    progress: Optional[ProgressFn] = None,
    resume: bool = False,
    protocol: ControlledProtocol = V4_PROTOCOL,
    round_atomic: bool = False,
    in_flight_path: Optional[str] = None,
    artifact_root: Optional[str] = None,
) -> ControlledExperimentResult:
    validate_controlled_config(cfg)
    if artifact_root is not None:
        ensure_contained_directory(
            cfg.out_dir,
            artifact_root,
            label="controlled experiment output directory",
        )
    specs = build_controlled_episode_specs(cfg)
    run_id = run_id or (
        "%s_%s" % (cfg.experiment_id, time.strftime("%Y%m%d_%H%M%S"))
    )
    log_path = os.path.join(cfg.out_dir, run_id + ".jsonl")
    manifest_path = os.path.join(cfg.out_dir, run_id + ".manifest.json")
    exists = os.path.exists(log_path) or os.path.exists(manifest_path)
    if round_atomic and not in_flight_path:
        raise ValueError("round-atomic controlled runs require an in-flight claim path")
    if round_atomic and in_flight_path is not None and artifact_root is not None:
        ensure_contained_directory(
            os.path.dirname(in_flight_path) or ".",
            artifact_root,
            label="controlled round claim directory",
        )
    if exists and not resume:
        raise FileExistsError(
            "refusing to append or overwrite existing controlled run %r" % run_id
        )

    provider = provider or make_controlled_provider(cfg.model)
    agent = ControlledFocalAgent(provider)
    donors = ControlledDonorRegistry()
    if exists:
        all_records, completed, partial = _load_resume_state(
            cfg,
            provider,
            specs,
            log_path,
            manifest_path,
            protocol,
            round_atomic=round_atomic,
            artifact_root=artifact_root,
        )
        if round_atomic and in_flight_path is not None:
            audit_or_recover_round_claim(
                in_flight_path,
                all_records,
                run_id,
                root=artifact_root,
            )
    else:
        all_records, completed, partial = [], {}, {}
        if round_atomic and in_flight_path is not None and os.path.lexists(in_flight_path):
            raise FileExistsError("new controlled run has a stale in-flight claim")
        write_manifest(
            manifest_path,
            _manifest_payload(
                cfg,
                provider,
                specs,
                "running",
                0,
                0,
                protocol,
                round_atomic=round_atomic,
            ),
            root=artifact_root,
        )

    generation_cache: Dict[str, Tuple[str, str, str]] = {}
    for record in all_records:
        group = record.get("replication_group_id")
        if group is None:
            continue
        observed = (
            str(record["focal_system_prompt"]),
            str(record["focal_user_prompt"]),
            str(record["focal_output_raw"]),
        )
        previous = generation_cache.setdefault(str(group), observed)
        if previous != observed:
            raise ValueError("resume log contains divergent replicated generations")

    for spec in specs:
        if spec.episode_id in completed and spec.condition.name == "full_history":
            donors.add(
                spec.episode_index,
                spec.initial_target_type,
                spec.episode_id,
                _history_from_records(completed[spec.episode_id]),
            )

    with JsonlWriter(
        log_path,
        validate=True,
        validator=validate_controlled_record,
        root=artifact_root,
    ) as writer:
        for spec in specs:
            if spec.episode_id in completed:
                if progress is not None:
                    progress("resume: skipping complete episode %s" % spec.episode_id)
                continue
            prefix_records = partial.get(spec.episode_id, [])
            own_history_prefix = _history_from_records(prefix_records)
            result = run_controlled_episode(
                spec=spec,
                cfg=cfg,
                agent=agent,
                run_id=run_id,
                donors=donors,
                progress=progress,
                protocol=protocol,
                start_round=len(prefix_records) + 1,
                own_history_prefix=own_history_prefix,
                record_sink=(writer.write if round_atomic else None),
                before_generation=(
                    (
                        lambda claim: _publish_round_claim(
                            in_flight_path,
                            claim,
                            root=artifact_root,
                        )
                    )
                    if round_atomic and in_flight_path is not None
                    else None
                ),
                after_record_durable=(
                    (
                        lambda claim: _clear_round_claim(
                            in_flight_path,
                            claim,
                            root=artifact_root,
                        )
                    )
                    if round_atomic and in_flight_path is not None
                    else None
                ),
                generation_cache=generation_cache,
            )
            if not round_atomic:
                for record in result.records:
                    writer.write(record)
            all_records.extend(result.records)
            completed[spec.episode_id] = list(prefix_records) + list(result.records)
            partial.pop(spec.episode_id, None)
            if spec.condition.name == "full_history":
                donors.add(
                    spec.episode_index,
                    spec.initial_target_type,
                    spec.episode_id,
                    result.own_history,
                )
            write_manifest(
                manifest_path,
                _manifest_payload(
                    cfg,
                    provider,
                    specs,
                    "running",
                    len(all_records),
                    len(completed),
                    protocol,
                    round_atomic=round_atomic,
                ),
                root=artifact_root,
            )

    expected_records = sum(spec.n_rounds for spec in specs)
    if len(all_records) != expected_records:
        raise RuntimeError(
            "%s record count mismatch: expected %d, got %d"
            % (protocol.version, expected_records, len(all_records))
        )
    write_manifest(
        manifest_path,
        _manifest_payload(
            cfg,
            provider,
            specs,
            "completed",
            len(all_records),
            len(specs),
            protocol,
            round_atomic=round_atomic,
        ),
        root=artifact_root,
    )
    return ControlledExperimentResult(
        log_path=log_path,
        manifest_path=manifest_path,
        n_records=len(all_records),
        n_episodes=len(specs),
        records=all_records,
        provider=provider,
    )
