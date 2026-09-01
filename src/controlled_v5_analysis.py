"""Blocked, baseline-adjusted analysis for controlled-choice V5."""

from __future__ import annotations

import math
import hashlib
import json
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from config import (
    CONTROLLED_V5_GATE_THRESHOLDS,
    CONTROLLED_V5_VERSION,
    STRATEGIES,
)
from .controlled_analysis import (
    _bootstrap_mean,
    _condition_rows,
    _episode_groups,
    _episode_rate,
    _mean,
    _trajectory,
    audit_controlled_design,
)
from .controlled_v5_power import exact_rational_sign_flip_test


V5_REQUIRED_CONDITIONS = (
    "full_history",
    "no_history",
    "shuffled_history",
    "random_target",
    "swap",
)
V5_N_ROUNDS = 24
V5_SWAP_ROUND = 12
V5_HELDOUT_START = 19
V5_WINDOW_SIZE = 6


def _block_means(values: Sequence[float], blocks: Sequence[Any]) -> List[float]:
    if len(values) != len(blocks):
        raise ValueError("values and blocks must have equal length")
    grouped: Dict[Any, List[float]] = defaultdict(list)
    for value, block in zip(values, blocks):
        grouped[block].append(float(value))
    return [_mean(grouped[block]) for block in sorted(grouped, key=str)]


def _blocked_summary(
    values: Sequence[float],
    blocks: Sequence[Any],
    n_boot: int,
    n_perm: int,
    seed: int,
) -> Dict[str, float]:
    """Collapse correlated target/transition episodes within scenario blocks."""
    means = _block_means(values, blocks)
    result = {
        **_bootstrap_mean(means, n_boot, seed),
        **exact_rational_sign_flip_test(means),
    }
    result["n_perm_requested_ignored"] = n_perm
    result["n_blocks"] = len(means)
    result["n_episode_values"] = len(values)
    result["randomization_unit"] = "scenario-sequence seed block"
    return result


def _blocked_descriptive(
    values: Sequence[float], blocks: Sequence[Any], n_boot: int, seed: int
) -> Dict[str, float]:
    means = _block_means(values, blocks)
    result = _bootstrap_mean(means, n_boot, seed)
    result["n_blocks"] = len(means)
    result["n_episode_values"] = len(values)
    return result


def _stable_episode_summaries(
    rows: Sequence[Mapping[str, Any]], heldout_start_round: int
) -> Dict[Tuple[int, str], Dict[str, float]]:
    out: Dict[Tuple[int, str], Dict[str, float]] = {}
    for episode_rows in _episode_groups(rows).values():
        first = episode_rows[0]
        key = (int(first["episode_index"]), str(first["initial_target_type"]))
        early = _episode_rate(
            episode_rows,
            lambda row: 1 <= int(row["round"]) <= V5_WINDOW_SIZE,
            lambda row: bool(row["strategy_match"]),
        )
        late = _episode_rate(
            episode_rows,
            lambda row: int(row["round"]) >= heldout_start_round,
            lambda row: bool(row["strategy_match"]),
        )
        development_late = _episode_rate(
            episode_rows,
            lambda row: heldout_start_round - V5_WINDOW_SIZE
            <= int(row["round"]) < heldout_start_round,
            lambda row: bool(row["strategy_match"]),
        )
        out[key] = {
            "early_match": early,
            "late_heldout_match": late,
            "late_development_match": development_late,
            "learning_gain": late - early,
            "development_learning_gain": development_late - early,
            "success": _mean(float(row["target_success"]) for row in episode_rows),
            "valid_selection": _mean(
                float(row["selection_valid"]) for row in episode_rows
            ),
            "fallback_rate": _mean(float(row["fallback_used"]) for row in episode_rows),
        }
    return out


def _paired_values_and_blocks(
    left: Mapping[Tuple[int, str], Mapping[str, float]],
    right: Mapping[Tuple[int, str], Mapping[str, float]],
    field: str,
) -> Tuple[List[float], List[int]]:
    keys = sorted(set(left) & set(right))
    if keys != sorted(left) or keys != sorted(right):
        raise ValueError("paired V5 conditions do not contain identical episode blocks")
    return (
        [float(left[key][field]) - float(right[key][field]) for key in keys],
        [int(key[0]) for key in keys],
    )


def _swap_episode_summaries(
    rows: Sequence[Mapping[str, Any]], heldout_start_round: int
) -> List[Dict[str, Any]]:
    summaries: List[Dict[str, Any]] = []
    for episode_id, episode_rows in _episode_groups(rows).items():
        first = episode_rows[0]
        swap_round = int(first["swap_round"])
        old_type = str(first["initial_target_type"])
        new_type = str(first["final_target_type"])
        pre_window = [
            row for row in episode_rows
            if swap_round - V5_WINDOW_SIZE + 1 <= int(row["round"]) <= swap_round
        ]
        late_window = [
            row for row in episode_rows if int(row["round"]) >= heldout_start_round
        ]
        development_window = [
            row
            for row in episode_rows
            if swap_round < int(row["round"]) < heldout_start_round
        ]
        if (
            len(pre_window) != V5_WINDOW_SIZE
            or len(development_window) != V5_WINDOW_SIZE
            or len(late_window) != V5_WINDOW_SIZE
        ):
            raise ValueError("V5 swap windows must each contain six rounds")
        pre_new = _mean(float(row["selected_frame"] == new_type) for row in pre_window)
        pre_old = _mean(float(row["selected_frame"] == old_type) for row in pre_window)
        late_new = _mean(float(row["selected_frame"] == new_type) for row in late_window)
        late_old = _mean(float(row["selected_frame"] == old_type) for row in late_window)
        development_new = _mean(
            float(row["selected_frame"] == new_type) for row in development_window
        )
        development_old = _mean(
            float(row["selected_frame"] == old_type) for row in development_window
        )
        revision_shift = (late_new - late_old) - (pre_new - pre_old)
        development_revision_shift = (
            (development_new - development_old) - (pre_new - pre_old)
        )

        adapt_round: Optional[int] = None
        post = [row for row in episode_rows if int(row["round"]) > swap_round]
        for end in range(4, len(post) + 1):
            window = post[end - 4 : end]
            if sum(row["selected_frame"] == new_type for row in window) >= 3:
                adapt_round = int(window[-1]["round"]) - swap_round
                break
        summaries.append(
            {
                "episode_id": episode_id,
                "episode_index": int(first["episode_index"]),
                "old_type": old_type,
                "new_type": new_type,
                "transition": "%s_to_%s" % (old_type, new_type),
                "pre_new_match": pre_new,
                "pre_old_match": pre_old,
                "late_new_match": late_new,
                "late_old_match": late_old,
                "development_new_match": development_new,
                "development_old_match": development_old,
                "new_target_gain": late_new - pre_new,
                "old_target_drop": pre_old - late_old,
                "late_new_over_old": late_new - late_old,
                "pre_new_over_old": pre_new - pre_old,
                "revision_shift": revision_shift,
                "development_revision_shift": development_revision_shift,
                "rounds_to_adapt": adapt_round,
            }
        )
    return summaries


def _frame_balance(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    def one(part: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        counts = Counter(str(row["selected_frame"]) for row in part)
        total = len(part)
        shares = {
            frame: counts.get(frame, 0) / float(total) if total else float("nan")
            for frame in STRATEGIES
        }
        return {
            "n": total,
            "counts": dict(counts),
            "shares": shares,
            "gap": max(shares.values()) - min(shares.values()) if total else float("nan"),
        }

    return {
        "overall": one(rows),
        "development": one([row for row in rows if row["candidate_split"] == "development"]),
        "heldout": one([row for row in rows if row["candidate_split"] == "heldout"]),
    }


def _transition_metrics(
    summaries: Sequence[Mapping[str, Any]], n_boot: int, n_perm: int, seed: int
) -> Dict[str, Any]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in summaries:
        grouped[str(row["transition"])].append(row)
    out: Dict[str, Any] = {}
    for index, transition in enumerate(sorted(grouped)):
        rows = grouped[transition]
        values = [float(row["revision_shift"]) for row in rows]
        blocks = [int(row["episode_index"]) for row in rows]
        out[transition] = {
            "old_type": rows[0]["old_type"],
            "new_type": rows[0]["new_type"],
            "revision_shift": _blocked_summary(
                values, blocks, n_boot, n_perm, seed + index * 10
            ),
            "late_new_over_old": _blocked_descriptive(
                [float(row["late_new_over_old"]) for row in rows],
                blocks,
                n_boot,
                seed + index * 10 + 2,
            ),
        }
    return out


def audit_frozen_v5_manifest(
    manifest: Mapping[str, Any], frozen_spec: Mapping[str, Any]
) -> Dict[str, Any]:
    config = manifest.get("config", {})
    experiment = frozen_spec.get("experiment", {})
    generation = frozen_spec.get("generation", {})
    model = frozen_spec.get("primary_model", {})
    provider = manifest.get("provider", {})
    target = frozen_spec.get("target", {})
    provenance = manifest.get("protocol_provenance", {})
    frozen_hash = hashlib.sha256(
        json.dumps(
            frozen_spec,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    checks = {
        "checkpoint_status": frozen_spec.get("status")
        == "FROZEN_BEFORE_V5_CONFIRMATORY_OUTCOMES"
        and frozen_spec.get("pre_confirmatory_outcome") is True,
        "version": manifest.get("task_version") == frozen_spec.get("version")
        == CONTROLLED_V5_VERSION,
        "run_completed": manifest.get("run_status") == "completed",
        "conditions": config.get("conditions") == experiment.get("conditions"),
        "episode_seeds": config.get("n_episode_seeds")
        == experiment.get("n_episode_seeds"),
        "rounds": config.get("n_rounds") == experiment.get("n_rounds") == V5_N_ROUNDS,
        "swap_round": config.get("swap_round")
        == experiment.get("swap_round") == V5_SWAP_ROUND,
        "heldout_start": config.get("heldout_start_round")
        == experiment.get("heldout_start_round") == V5_HELDOUT_START,
        "seed": config.get("seed") == experiment.get("master_seed"),
        "record_count": manifest.get("n_records")
        == experiment.get("record_counts", {}).get("total"),
        "episode_count": manifest.get("n_episodes")
        == experiment.get("episode_counts", {}).get("total"),
        "model": config.get("model", {}).get("model") == model.get("id")
        and provider.get("model") == model.get("id"),
        "revision": config.get("model", {}).get("revision") == model.get("revision")
        and provider.get("revision") == model.get("revision"),
        "provider": provider.get("provider") == "huggingface",
        "provider_seed": provider.get("torch_seed_base")
        == experiment.get("master_seed"),
        "constrained_choices": provider.get("constrained_choices") == ["1", "2", "3"],
        "selection_policy": manifest.get("selection_policy", {}).get("strict_selection")
        is True,
        "temperature": provider.get("temperature") == generation.get("temperature")
        and config.get("model", {}).get("temperature") == generation.get("temperature"),
        "max_tokens": provider.get("max_tokens") == generation.get("max_tokens")
        and config.get("model", {}).get("max_tokens") == generation.get("max_tokens"),
        "thinking": provider.get("enable_thinking") is generation.get("enable_thinking"),
        "top_p": provider.get("top_p") == generation.get("top_p"),
        "top_k": provider.get("top_k") == generation.get("top_k"),
        "capture": provider.get("capture") is generation.get("activation_capture"),
        "dtype": provider.get("dtype") == generation.get("dtype"),
        "target": all(
            math.isclose(
                float(config.get("target_params", {}).get(key, -1)),
                float(target.get(key, -2)),
            )
            for key in ("p_match", "p_mismatch", "p_random")
        ),
        "bank_hash": manifest.get("message_bank_sha256")
        == frozen_spec.get("message_bank", {}).get("sha256"),
        "bank_validated": manifest.get("message_banks", {}).get("status")
        == "selected_bank_validated",
        "checkpoint_provenance": provenance.get("checkpoint_canonical_sha256")
        == frozen_hash,
        "artifact_preflight": provenance.get("artifact_audit", {}).get("pass")
        is True,
        "thresholds": frozen_spec.get("thresholds")
        == CONTROLLED_V5_GATE_THRESHOLDS,
    }
    return {"pass": all(checks.values()), "checks": checks}


def audit_frozen_v5_plan(
    config: Any,
    provider_description: Mapping[str, Any],
    expected_n_records: int,
    expected_n_episodes: int,
    bank_manifest: Mapping[str, Any],
    bank_sha256: str,
    frozen_spec: Mapping[str, Any],
    protocol_provenance: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    planned = {
        "task_version": CONTROLLED_V5_VERSION,
        "run_status": "completed",
        "config": config.as_dict() if hasattr(config, "as_dict") else dict(config),
        "provider": dict(provider_description),
        "n_records": int(expected_n_records),
        "n_episodes": int(expected_n_episodes),
        "message_banks": dict(bank_manifest),
        "message_bank_sha256": bank_sha256,
        "selection_policy": {"strict_selection": True},
        "protocol_provenance": dict(protocol_provenance or {}),
    }
    return audit_frozen_v5_manifest(planned, frozen_spec)


def evaluate_controlled_v5_checkpoint(
    records: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    n_boot: int = 5000,
    n_perm: int = 10000,
    seed: int = 20261001,
    frozen_spec: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    records = list(records)
    if not records:
        raise ValueError("V5 checkpoint log is empty")
    missing = [name for name in V5_REQUIRED_CONDITIONS if not _condition_rows(records, name)]
    if missing:
        raise ValueError("V5 checkpoint is missing required conditions: %s" % missing)
    config = manifest.get("config", {})
    heldout_start = int(config.get("heldout_start_round", -1))
    thresholds = dict(CONTROLLED_V5_GATE_THRESHOLDS)
    provider_name = str(manifest.get("provider", {}).get("provider", ""))
    mock_run = provider_name.startswith("mock:")

    design = audit_controlled_design(
        records, manifest, expected_version=CONTROLLED_V5_VERSION
    )
    v5_checks = {
        "v5_round_count": int(config.get("n_rounds", -1)) == V5_N_ROUNDS,
        "v5_swap_round": int(config.get("swap_round", -1)) == V5_SWAP_ROUND,
        "v5_heldout_start": heldout_start == V5_HELDOUT_START,
        "strict_selection_declared": manifest.get("selection_policy", {}).get(
            "strict_selection"
        ) is True,
        "choice_constraint_declared": manifest.get("selection_policy", {}).get(
            "constrained_choices"
        ) == ["1", "2", "3"],
        "no_fallback_used": not any(bool(row["fallback_used"]) for row in records),
        "all_selections_valid": all(bool(row["selection_valid"]) for row in records),
        "bank_validated_for_real_run": mock_run
        or manifest.get("message_banks", {}).get("status") == "selected_bank_validated",
    }
    episode_groups = _episode_groups(records)
    n_seeds = int(config.get("n_episode_seeds", -1))
    stable_type_counts: Counter = Counter()
    swap_transition_counts: Counter = Counter()
    for episode_rows in episode_groups.values():
        first = episode_rows[0]
        condition = str(first["condition"])
        if condition in V5_REQUIRED_CONDITIONS[:4]:
            stable_type_counts[(condition, str(first["initial_target_type"]))] += 1
        elif condition == "swap":
            swap_transition_counts[
                (str(first["initial_target_type"]), str(first["final_target_type"]))
            ] += 1
    expected_transitions = {
        (old, new) for old in STRATEGIES for new in STRATEGIES if old != new
    }
    v5_checks.update(
        {
            "stable_target_type_balance": all(
                stable_type_counts[(condition, target)] == n_seeds
                for condition in V5_REQUIRED_CONDITIONS[:4]
                for target in STRATEGIES
            ),
            "all_six_swap_transitions_balanced": set(swap_transition_counts)
            == expected_transitions
            and all(
                swap_transition_counts[transition] == n_seeds
                for transition in expected_transitions
            ),
            "candidate_split_round_contract": all(
                str(row["candidate_split"])
                == (
                    "heldout"
                    if int(row["round"]) >= V5_HELDOUT_START
                    else "development"
                )
                for row in records
            ),
        }
    )
    if frozen_spec is not None:
        frozen_audit = audit_frozen_v5_manifest(manifest, frozen_spec)
        v5_checks["matches_frozen_v5_checkpoint"] = bool(frozen_audit["pass"])
    else:
        frozen_audit = None
    design["checks"].update(v5_checks)
    design["pass"] = all(design["checks"].values())
    design["frozen_v5_checkpoint"] = frozen_audit

    stable = {
        name: _stable_episode_summaries(_condition_rows(records, name), heldout_start)
        for name in V5_REQUIRED_CONDITIONS[:4]
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
            "fallback_rate": _mean(summaries[key]["fallback_rate"] for key in keys),
        }

    did_values, did_blocks = _paired_values_and_blocks(
        stable["full_history"], stable["no_history"], "learning_gain"
    )
    late_no_values, late_no_blocks = _paired_values_and_blocks(
        stable["full_history"], stable["no_history"], "late_heldout_match"
    )
    late_shuffled_values, late_shuffled_blocks = _paired_values_and_blocks(
        stable["full_history"], stable["shuffled_history"], "late_heldout_match"
    )
    development_did_values, development_did_blocks = _paired_values_and_blocks(
        stable["full_history"], stable["no_history"], "development_learning_gain"
    )
    primary = {
        "stable_full_vs_no_difference_in_differences": _blocked_summary(
            did_values, did_blocks, n_boot, n_perm, seed + 100
        ),
        "full_over_no_late_heldout": _blocked_summary(
            late_no_values, late_no_blocks, n_boot, n_perm, seed + 110
        ),
        "full_over_shuffled_late_heldout": _blocked_summary(
            late_shuffled_values, late_shuffled_blocks, n_boot, n_perm, seed + 120
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
    for target in STRATEGIES:
        keys = sorted(key for key in stable["full_history"] if key[1] == target)
        advantages = [
            stable["full_history"][key]["late_heldout_match"]
            - stable["no_history"][key]["late_heldout_match"]
            for key in keys
        ]
        metric = _bootstrap_mean(advantages, n_boot, seed + 140 + STRATEGIES.index(target))
        by_type[target] = metric
        if metric["mean"] >= thresholds["minimum_per_type_late_advantage"]:
            supporting_types.append(target)

    swap_summaries = _swap_episode_summaries(
        _condition_rows(records, "swap"), heldout_start
    )
    swap_blocks = [int(row["episode_index"]) for row in swap_summaries]
    revision = _blocked_summary(
        [float(row["revision_shift"]) for row in swap_summaries],
        swap_blocks,
        n_boot,
        n_perm,
        seed + 200,
    )
    late_new_over_old = _blocked_summary(
        [float(row["late_new_over_old"]) for row in swap_summaries],
        swap_blocks,
        n_boot,
        n_perm,
        seed + 210,
    )
    transition_metrics = _transition_metrics(
        swap_summaries, n_boot, n_perm, seed + 300
    )
    supporting_transitions = [
        name for name, metric in transition_metrics.items()
        if metric["revision_shift"]["mean"]
        >= thresholds["minimum_transition_revision_shift"]
    ]
    supporting_origins = sorted(
        {
            transition_metrics[name]["old_type"]
            for name in supporting_transitions
        }
    )
    swap_metrics = {
        "n_episodes": len(swap_summaries),
        "n_blocks": len(set(swap_blocks)),
        "pre_new_match": _mean(row["pre_new_match"] for row in swap_summaries),
        "pre_old_match": _mean(row["pre_old_match"] for row in swap_summaries),
        "late_new_match": _mean(row["late_new_match"] for row in swap_summaries),
        "late_old_match": _mean(row["late_old_match"] for row in swap_summaries),
        "development_new_match": _mean(
            row["development_new_match"] for row in swap_summaries
        ),
        "development_old_match": _mean(
            row["development_old_match"] for row in swap_summaries
        ),
        "revision_shift": revision,
        "late_new_over_old": late_new_over_old,
        "new_target_gain": _blocked_descriptive(
            [float(row["new_target_gain"]) for row in swap_summaries],
            swap_blocks,
            n_boot,
            seed + 220,
        ),
        "old_target_drop": _blocked_descriptive(
            [float(row["old_target_drop"]) for row in swap_summaries],
            swap_blocks,
            n_boot,
            seed + 221,
        ),
        "development_revision_shift": _blocked_descriptive(
            [float(row["development_revision_shift"]) for row in swap_summaries],
            swap_blocks,
            n_boot,
            seed + 222,
        ),
        "transition_metrics": transition_metrics,
        "supporting_transitions": supporting_transitions,
        "supporting_origin_types": supporting_origins,
        "n_adapted": sum(row["rounds_to_adapt"] is not None for row in swap_summaries),
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

    no_history_balance = _frame_balance(_condition_rows(records, "no_history"))
    overall_balance = no_history_balance["overall"]
    valid_rate = _mean(float(row["selection_valid"]) for row in records)
    fallback_rate = _mean(float(row["fallback_used"]) for row in records)
    no_history_gain = stable_metrics["no_history"]["learning_gain"]["mean"]
    random_gain = stable_metrics["random_target"]["learning_gain"]["mean"]
    alpha = thresholds["confirmatory_alpha_one_sided"]

    effect_gates = {
        "design_integrity": bool(design["pass"]),
        "all_selections_valid": valid_rate
        >= thresholds["required_valid_selection_rate"],
        "no_fallback": fallback_rate <= thresholds["required_fallback_rate"],
        "no_history_bank_balance": all(
            thresholds["minimum_no_history_frame_share"] <= share
            <= thresholds["maximum_no_history_frame_share"]
            for share in overall_balance["shares"].values()
        )
        and overall_balance["gap"] <= thresholds["maximum_no_history_frame_gap"],
        "full_history_late_level": stable_metrics["full_history"][
            "late_heldout_match"
        ]["mean"]
        >= thresholds["minimum_full_history_late_match"],
        "stable_difference_in_differences": primary[
            "stable_full_vs_no_difference_in_differences"
        ]["mean"]
        >= thresholds["minimum_stable_difference_in_differences"],
        "full_over_no_history": primary["full_over_no_late_heldout"]["mean"]
        >= thresholds["minimum_full_over_no_late_match"],
        "shuffled_history_specificity": primary[
            "full_over_shuffled_late_heldout"
        ]["mean"]
        >= thresholds["minimum_full_over_shuffled_late_match"],
        "no_history_learning_control": abs(no_history_gain)
        <= thresholds["maximum_absolute_no_history_learning_gain"],
        "random_response_control": abs(random_gain)
        <= thresholds["maximum_absolute_random_learning_gain"],
        "all_target_types_supported": len(supporting_types)
        >= int(thresholds["minimum_supporting_target_types"]),
        "baseline_adjusted_revision": revision["mean"]
        >= thresholds["minimum_revision_shift"],
        "development_stable_wording_agrees": primary[
            "development_stable_difference_in_differences"
        ]["mean"]
        >= thresholds["minimum_development_stable_difference_in_differences"],
        "development_swap_wording_agrees": swap_metrics[
            "development_revision_shift"
        ]["mean"]
        >= thresholds["minimum_development_revision_shift"],
        "directional_transition_support": len(supporting_transitions)
        >= int(thresholds["minimum_supporting_transitions"]),
        "all_origin_types_support_revision": len(supporting_origins)
        >= int(thresholds["minimum_supporting_origin_types"]),
    }
    inference_gates = {
        "stable_blocked_randomization_test": primary[
            "stable_full_vs_no_difference_in_differences"
        ]["p_value_one_sided"]
        <= alpha,
        "revision_blocked_randomization_test": revision["p_value_one_sided"]
        <= alpha,
    }
    pattern_pass = all(effect_gates.values()) and all(inference_gates.values())
    if pattern_pass and mock_run:
        decision = "MOCK_V5_PIPELINE_PASS_NOT_SCIENTIFIC_EVIDENCE"
    elif pattern_pass:
        decision = "V5_BEHAVIORAL_GATE_PASS_REPLICATION_REQUIRED"
    else:
        decision = "STOP_BEFORE_REPLICATION_OR_MECHANISTIC_WORK"

    trajectories = {
        name: {
            "match": _trajectory(_condition_rows(records, name), "strategy_match"),
            "success": _trajectory(_condition_rows(records, name), "target_success"),
        }
        for name in V5_REQUIRED_CONDITIONS
    }
    return {
        "task_version": CONTROLLED_V5_VERSION,
        "status": "mock-only validation" if mock_run else "real-model behavioral checkpoint",
        "decision": decision,
        "pattern_pass": pattern_pass,
        "scientific_pass": bool(pattern_pass and not mock_run),
        "thresholds": thresholds,
        "design_integrity": design,
        "effect_gates": effect_gates,
        "inference_gates": inference_gates,
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
                "The unadjusted late crossover is reported but is not a V5 pass "
                "gate; baseline-adjusted revision is the co-primary outcome."
            ),
        },
        "trajectories": trajectories,
        "analysis_contract": {
            "early_window": [1, 6],
            "pre_swap_window": [7, 12],
            "heldout_late_window": [19, 24],
            "co_primary_alpha_each_one_sided": alpha,
            "randomization_unit": "scenario-sequence seed block",
        },
        "interpretation_boundary": (
            "A real-model pass establishes balanced-bank, feedback-conditioned "
            "target-specific behavioral revision and requires replication. It does "
            "not establish an explicit internal target representation."
        ),
    }
