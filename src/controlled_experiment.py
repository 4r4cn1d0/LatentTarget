"""Versioned controlled-choice experiment runner.

V3 remains untouched and reproducible through :mod:`src.experiment`. This
module removes language scoring from the target and primary outcome while
retaining complete prompts, raw outputs, candidate mappings, probabilities,
random draws, and histories for audit.
"""

from __future__ import annotations

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
    make_controlled_provider,
)
from .controlled_protocol import ControlledProtocol, V4_PROTOCOL
from .controlled_target import ControlledTarget
from .focal_agent import BaseProvider
from .logging_utils import JsonlWriter, read_jsonl, write_manifest
from .scenarios import scenario_sequence
from .seeding import derive_seed


ProgressFn = Callable[[str], None]


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
)


def validate_controlled_record(record: Dict[str, Any]) -> None:
    missing = [field for field in CONTROLLED_REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError("controlled log record is missing fields: %s" % ", ".join(missing))
    candidates = record["candidates"]
    if len(candidates) != 3:
        raise ValueError("controlled record must contain exactly three candidates")
    if {candidate["frame"] for candidate in candidates} != set(STRATEGIES):
        raise ValueError("controlled candidates must contain each registered frame once")
    if {int(candidate["slot"]) for candidate in candidates} != {1, 2, 3}:
        raise ValueError("controlled candidates must occupy slots 1, 2, and 3")
    if record["selected_frame"] not in STRATEGIES:
        raise ValueError("selected frame is not registered")
    if any(record[name] not in STRATEGIES for name in (
        "hidden_target_type", "initial_target_type", "final_target_type"
    )):
        raise ValueError("record contains an unknown target type")
    selected = [
        candidate for candidate in candidates
        if int(candidate["slot"]) == int(record["selected_slot"])
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
        {"slot": int(candidate["slot"]), "message": candidate["message"]}
        for candidate in candidates
    ]
    if record["visible_candidates"] != expected_visible_candidates:
        raise ValueError("visible candidate projection is inconsistent")
    if record["target_choice"] not in {"A", "B"}:
        raise ValueError("target choice must be A or B")
    if bool(record["strategy_match"]) != (
        record["selected_frame"] == record["hidden_target_type"]
    ):
        raise ValueError("strategy_match is inconsistent with registered ground truth")
    probability = float(record["target_p_a"])
    draw = float(record["target_uniform_draw"])
    if not 0.0 <= probability <= 1.0 or not 0.0 <= draw < 1.0:
        raise ValueError("target probability or draw is outside its valid range")
    if record["target_choice"] != ("A" if draw < probability else "B"):
        raise ValueError("target choice is inconsistent with probability and draw")
    if bool(record["target_success"]) != (record["target_choice"] == "A"):
        raise ValueError("target_success is inconsistent with target choice")
    expected_history_fields = (
        {"round", "scenario_title", "selected_message", "choice"}
        if record["focal_mode"] == "spontaneous"
        else {
            "round", "scenario_title", "selected_message", "choice",
            "predicted_p_a", "candidate_messages",
        }
    )
    if any(set(entry) != expected_history_fields for entry in record["visible_history"]):
        raise ValueError("visible_history contains fields not rendered to the focal model")


@dataclass(frozen=True)
class ControlledEpisodeSpec:
    condition: ControlledCondition
    episode_index: int
    initial_target_type: str
    final_target_type: str
    n_rounds: int
    swap_round: Optional[int]
    episode_id: str

    @property
    def swaps(self) -> bool:
        return self.condition.swap and self.initial_target_type != self.final_target_type

    def active_type(self, round_index: int) -> str:
        if self.swaps and self.swap_round is not None and round_index > self.swap_round:
            return self.final_target_type
        return self.initial_target_type


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
    for condition_name in cfg.conditions:
        condition = CONTROLLED_CONDITIONS[condition_name]
        for episode_index in range(cfg.n_episode_seeds):
            for initial in STRATEGIES:
                finals = _swap_partners(initial) if condition.swap else [initial]
                for final in finals:
                    episode_id = (
                        "%s-%03d-%s-to-%s"
                        % (condition.name, episode_index, initial, final)
                        if condition.swap
                        else "%s-%03d-%s" % (condition.name, episode_index, initial)
                    )
                    specs.append(
                        ControlledEpisodeSpec(
                            condition=condition,
                            episode_index=episode_index,
                            initial_target_type=initial,
                            final_target_type=final,
                            n_rounds=cfg.n_rounds,
                            swap_round=cfg.swap_round if condition.swap else None,
                            episode_id=episode_id,
                        )
                    )
    return specs


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
) -> ControlledEpisodeResult:
    condition = spec.condition
    scenarios = scenario_sequence(spec.episode_index, spec.n_rounds, cfg.seed)
    episode_seed = derive_seed(
        cfg.seed,
        protocol.version,
        condition.name,
        spec.episode_index,
        spec.initial_target_type,
        spec.final_target_type,
    )

    own_history: List[ControlledHistoryEntry] = []
    donor_history: List[ControlledHistoryEntry] = []
    donor_episode_id: Optional[str] = None
    if condition.history_mode == "shuffled":
        if donors is None:
            raise ValueError("shuffled V4 history needs a donor registry")
        donor_episode_id, donor_history = donors.donor_for(
            spec.episode_index, spec.initial_target_type
        )

    records: List[Dict[str, Any]] = []
    for round_index in range(1, spec.n_rounds + 1):
        scenario = scenarios[round_index - 1]
        active_type = spec.active_type(round_index)
        candidates = protocol.candidate_set(
            scenario=scenario,
            episode_index=spec.episode_index,
            round_index=round_index,
            heldout_start_round=cfg.heldout_start_round,
            seed=cfg.seed,
        )
        round_seed = derive_seed(episode_seed, "focal_generation", round_index)
        # Common random numbers pair stable conditions without exposing the draw
        # to the focal provider. Condition is deliberately absent.
        target_draw_seed = derive_seed(
            cfg.seed,
            protocol.version,
            "target_draw",
            spec.episode_index,
            spec.initial_target_type,
            spec.final_target_type,
            round_index,
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
        set_next_seed = getattr(agent.provider, "set_next_seed", None)
        if callable(set_next_seed):
            set_next_seed(round_seed)
        prompt, raw, parsed, selected = agent.choose(
            scenario=scenario,
            candidates=candidates,
            history=visible_history,
            round_index=round_index,
            n_rounds=spec.n_rounds,
            show_history=condition.history_mode != "none",
            focal_mode=condition.focal_mode,
            round_seed=round_seed,
            context=(mock_context if isinstance(agent.provider, ControlledMockProvider) else {}),
            require_valid_selection=protocol.strict_selection,
        )

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
        }
        validate_controlled_record(record)
        records.append(record)

        tag_last = getattr(agent.provider, "tag_last", None)
        if callable(tag_last):
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
            "spontaneous_system_template": SPONTANEOUS_SYSTEM_TEMPLATE,
            "elicited_system_template": ELICITED_SYSTEM_TEMPLATE,
            "spontaneous_system_rendered": SPONTANEOUS_SYSTEM_TEMPLATE.format(
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
            "episode-atomic generation: records are appended only after all rounds "
            "of an episode complete; --resume skips validated complete episodes"
        ),
    }
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
) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    if not os.path.exists(manifest_path):
        raise FileNotFoundError("cannot resume without manifest %s" % manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as handle:
        existing_manifest = json.load(handle)
    if existing_manifest.get("task_version") != protocol.version:
        raise ValueError("resume manifest has a different task version")
    if existing_manifest.get("config") != cfg.as_dict():
        raise ValueError("resume config differs from the existing manifest")
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

    records = list(read_jsonl(log_path)) if os.path.exists(log_path) else []
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
    for episode_id, episode_records in by_episode.items():
        expected_rounds = spec_by_id[episode_id].n_rounds
        rounds = sorted(int(record["round"]) for record in episode_records)
        if rounds != list(range(1, expected_rounds + 1)):
            raise ValueError(
                "resume log has an incomplete episode %s; preserve it for audit and "
                "start a new run id rather than silently truncating data" % episode_id
            )
    return records, by_episode


def run_controlled_experiment(
    cfg: ControlledExperimentConfig,
    run_id: Optional[str] = None,
    provider: Optional[BaseProvider] = None,
    progress: Optional[ProgressFn] = None,
    resume: bool = False,
    protocol: ControlledProtocol = V4_PROTOCOL,
) -> ControlledExperimentResult:
    validate_controlled_config(cfg)
    specs = build_controlled_episode_specs(cfg)
    run_id = run_id or (
        "%s_%s" % (cfg.experiment_id, time.strftime("%Y%m%d_%H%M%S"))
    )
    log_path = os.path.join(cfg.out_dir, run_id + ".jsonl")
    manifest_path = os.path.join(cfg.out_dir, run_id + ".manifest.json")
    exists = os.path.exists(log_path) or os.path.exists(manifest_path)
    if exists and not resume:
        raise FileExistsError(
            "refusing to append or overwrite existing controlled run %r" % run_id
        )

    provider = provider or make_controlled_provider(cfg.model)
    agent = ControlledFocalAgent(provider)
    donors = ControlledDonorRegistry()
    if exists:
        all_records, completed = _load_resume_state(
            cfg, provider, specs, log_path, manifest_path, protocol
        )
    else:
        all_records, completed = [], {}
        write_manifest(
            manifest_path,
            _manifest_payload(cfg, provider, specs, "running", 0, 0, protocol),
        )

    for spec in specs:
        if spec.episode_id in completed and spec.condition.name == "full_history":
            donors.add(
                spec.episode_index,
                spec.initial_target_type,
                spec.episode_id,
                _history_from_records(completed[spec.episode_id]),
            )

    with JsonlWriter(
        log_path, validate=True, validator=validate_controlled_record
    ) as writer:
        for spec in specs:
            if spec.episode_id in completed:
                if progress is not None:
                    progress("resume: skipping complete episode %s" % spec.episode_id)
                continue
            result = run_controlled_episode(
                spec=spec,
                cfg=cfg,
                agent=agent,
                run_id=run_id,
                donors=donors,
                progress=progress,
                protocol=protocol,
            )
            for record in result.records:
                writer.write(record)
            all_records.extend(result.records)
            completed[spec.episode_id] = list(result.records)
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
                ),
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
            cfg, provider, specs, "completed", len(all_records), len(specs), protocol
        ),
    )
    return ControlledExperimentResult(
        log_path=log_path,
        manifest_path=manifest_path,
        n_records=len(all_records),
        n_episodes=len(specs),
        records=all_records,
        provider=provider,
    )
