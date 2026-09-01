#!/usr/bin/env python3
"""Freeze V5 only after every calibration, validation, and power gate passes."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import datetime as dt
import json
import os
import sys

from config import CONTROLLED_V5_GATE_THRESHOLDS, CONTROLLED_V5_VERSION
from src.controlled_v5_messages import V5MessageBank
from src.v5_protocol_gate import (
    audit_v5_checkpoint_artifacts,
    file_sha256,
)


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _reference(path):
    absolute = os.path.abspath(path)
    root = os.path.abspath(_bootstrap.ROOT)
    if os.path.commonpath([absolute, root]) != root:
        raise ValueError("V5 frozen artifacts must be inside the repository")
    return {
        "path": os.path.relpath(absolute, root),
        "file_sha256": file_sha256(absolute),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--calibration-protocol", default="docs/v5_calibration_protocol.json"
    )
    parser.add_argument("--bank", required=True)
    parser.add_argument(
        "--semantic-validation",
        default="results/v5_design/semantic_validation/summary.json",
    )
    parser.add_argument("--pool-calibration-manifest", required=True)
    parser.add_argument("--pool-calibration-log", required=True)
    parser.add_argument("--selection-report", required=True)
    parser.add_argument("--bank-validation", required=True)
    parser.add_argument("--bank-validation-manifest", required=True)
    parser.add_argument("--bank-validation-log", required=True)
    parser.add_argument("--power", required=True)
    parser.add_argument(
        "--effect-pair",
        default=None,
        help=(
            "optional assertion stable_DID:revision_shift; must equal the pair "
            "already frozen in the calibration protocol"
        ),
    )
    parser.add_argument("--master-seed", type=int, default=20261003)
    parser.add_argument("--out", default="docs/behavioral_checkpoint_v5.json")
    args = parser.parse_args(argv)
    if os.path.exists(args.out):
        raise FileExistsError("refusing to overwrite frozen checkpoint %s" % args.out)

    protocol = _load(args.calibration_protocol)
    bank = V5MessageBank.load(args.bank, require_validated=True)
    semantic = _load(args.semantic_validation)
    calibration = _load(args.pool_calibration_manifest)
    selection = _load(args.selection_report)
    validation = _load(args.bank_validation)
    power = _load(args.power)
    power_design = protocol.get("power_design", {})
    frozen_effects = power_design.get("population_smallest_effects_of_interest", {})
    try:
        stable_effect = float(frozen_effects["stable_did"])
        revision_effect = float(frozen_effects["revision_shift"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("calibration protocol has no valid frozen V5 effect pair") from exc
    if args.effect_pair is not None:
        asserted_stable, asserted_revision = (
            float(value) for value in args.effect_pair.split(":", 1)
        )
        if (asserted_stable, asserted_revision) != (
            stable_effect,
            revision_effect,
        ):
            raise ValueError("--effect-pair differs from the frozen calibration protocol")
    effect_key = "%.3f:%.3f" % (stable_effect, revision_effect)
    joint_n = power.get("minimum_episode_seeds_by_effect_pair", {}).get(effect_key)
    complete_n = power.get(
        "minimum_episode_seeds_by_effect_pair_complete_pattern", {}
    ).get(effect_key)
    if joint_n is None or complete_n is None:
        raise ValueError(
            "selected effect pair did not reach the 80% lower-bound rule for both "
            "co-primary and complete-pattern power"
        )
    n_seeds = max(int(joint_n), int(complete_n))
    planning_ceiling = int(power_design.get("planning_ceiling_episode_seeds", -1))
    if n_seeds > planning_ceiling or n_seeds not in power_design.get(
        "episode_seed_grid", []
    ):
        raise ValueError("selected V5 sample is outside the frozen power design")
    if semantic.get("pass") is not True or validation.get("pass") is not True:
        raise ValueError("semantic and selected-bank validation must both pass")
    if calibration.get("run_status") != "completed" or calibration.get("mode") != (
        "pool_calibration"
    ):
        raise ValueError("pool calibration manifest is incomplete")
    if power.get("n_sim_requirement_met") is not True:
        raise ValueError("V5 power must use at least 5,000 Monte Carlo studies")

    n_episodes = 18 * n_seeds
    checkpoint = {
        "version": CONTROLLED_V5_VERSION,
        "status": "FROZEN_BEFORE_V5_CONFIRMATORY_OUTCOMES",
        "pre_confirmatory_outcome": True,
        "frozen_at": dt.date.today().isoformat(),
        "question": (
            "After controlling baseline frame preference, does target-specific "
            "feedback produce stable learning and baseline-adjusted revision after "
            "a silent target change?"
        ),
        "calibration_protocol": _reference(args.calibration_protocol),
        "primary_model": protocol["primary_model"],
        "generation": protocol["generation"],
        "experiment": {
            "conditions": [
                "full_history",
                "no_history",
                "shuffled_history",
                "random_target",
                "swap",
            ],
            "n_episode_seeds": n_seeds,
            "n_rounds": 24,
            "swap_round": 12,
            "heldout_start_round": 19,
            "master_seed": args.master_seed,
            "episode_counts": {
                "each_stable_condition": 3 * n_seeds,
                "swap": 6 * n_seeds,
                "total": n_episodes,
            },
            "record_counts": {"total": n_episodes * 24},
        },
        "target": {"p_match": 0.72, "p_mismatch": 0.38, "p_random": 0.50},
        "message_bank": {**_reference(args.bank), "sha256": bank.sha256()},
        "semantic_validation": _reference(args.semantic_validation),
        "pool_calibration": _reference(args.pool_calibration_manifest),
        "pool_calibration_log": _reference(args.pool_calibration_log),
        "bank_selection": _reference(args.selection_report),
        "selected_bank_validation": _reference(args.bank_validation),
        "selected_bank_validation_manifest": _reference(
            args.bank_validation_manifest
        ),
        "selected_bank_validation_log": _reference(args.bank_validation_log),
        "power": {
            **_reference(args.power),
            "selected_effect_pair": {
                "stable_did": stable_effect,
                "revision_shift": revision_effect,
            },
            "joint_recommended_episode_seeds": int(joint_n),
            "complete_pattern_recommended_episode_seeds": int(complete_n),
            "selected_episode_seeds": n_seeds,
        },
        "thresholds": CONTROLLED_V5_GATE_THRESHOLDS,
        "analysis": {
            "early_window": [1, 6],
            "pre_swap_window": [7, 12],
            "post_swap_development_window": [13, 18],
            "heldout_late_window": [19, 24],
            "co_primary_alpha_each_one_sided": 0.025,
            "randomization_test": "complete exact sign-flip distribution",
            "randomization_block": "scenario-sequence seed",
            "transition_weighting": "all six ordered transitions equally within block",
        },
        "claim_boundary": (
            "A pass is feedback-conditioned target-specific behavioral revision, "
            "not proof of an explicit internal target representation. Replication "
            "is required before any mechanistic claim."
        ),
        "forbidden_before_pass_and_replication": [
            "activation capture",
            "probing",
            "steering",
            "free-form rescue",
            "outcome-dependent sample extension",
        ],
    }
    audit = audit_v5_checkpoint_artifacts(checkpoint, _bootstrap.ROOT)
    if not audit["pass"]:
        failed = sorted(name for name, passed in audit["checks"].items() if not passed)
        raise ValueError("refusing to freeze V5; artifact audit failed: %s" % ", ".join(failed))
    parent = os.path.dirname(args.out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(checkpoint, handle, indent=2, allow_nan=False)
    print("FROZEN %s" % args.out)
    print("episode seeds=%d; episodes=%d; generations=%d" % (
        n_seeds, n_episodes, n_episodes * 24
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
