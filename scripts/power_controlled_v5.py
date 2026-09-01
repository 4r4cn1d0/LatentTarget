#!/usr/bin/env python3
"""Run exact blocked V5 pre-outcome power sensitivity simulations."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import csv
import json
import os
import sys

from src.v5_calibration import _canonical_sha256
from src.controlled_v5_power import simulate_controlled_v5_power
from src.v5_protocol_gate import file_sha256


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--episode-seeds", nargs="+", type=int, default=[8, 12, 16, 20, 24, 30]
    )
    parser.add_argument(
        "--effect-pairs",
        nargs="+",
        default=["0.10:0.15", "0.15:0.20", "0.20:0.25"],
        help="stable_DID:revision_shift pairs",
    )
    parser.add_argument("--frame-shares", default="0.333333:0.333333:0.333334")
    parser.add_argument(
        "--bank-validation",
        default=None,
        help="passed selected-bank validation JSON; required for final V5 power",
    )
    parser.add_argument("--n-sim", type=int, default=5000)
    parser.add_argument("--target-power", type=float, default=0.80)
    parser.add_argument("--alpha-each", type=float, default=0.025)
    parser.add_argument("--seed", type=int, default=20261001)
    parser.add_argument("--out-dir", default="results/v5_design/power")
    args = parser.parse_args(argv)
    if args.n_sim < 5000:
        print(
            "WARNING: fewer than 5,000 simulations is exploratory and cannot freeze V5",
            file=sys.stderr,
        )
    effects = []
    for value in args.effect_pairs:
        stable, revision = value.split(":", 1)
        effects.append((float(stable), float(revision)))
    validation_source = None
    if args.bank_validation:
        with open(args.bank_validation, "r", encoding="utf-8") as handle:
            validation = json.load(handle)
        if validation.get("pass") is not True:
            raise ValueError("final V5 power requires a passed bank validation")
        frame_shares = {
            frame: float(validation["sections"]["overall"]["shares"][frame])
            for frame in ("fairness", "risk", "expertise")
        }
        validation_source = {
            "path": os.path.abspath(args.bank_validation),
            "file_sha256": file_sha256(args.bank_validation),
            "canonical_sha256": _canonical_sha256(validation),
            "bank_sha256": validation["bank_sha256"],
            "frame_shares": frame_shares,
        }
    else:
        share_values = [float(value) for value in args.frame_shares.split(":")]
        if len(share_values) != 3:
            raise ValueError("--frame-shares requires fairness:risk:expertise")
        frame_shares = dict(zip(("fairness", "risk", "expertise"), share_values))

    rows = []
    for effect_index, (stable, revision) in enumerate(effects):
        for n_seeds in args.episode_seeds:
            rows.append(
                simulate_controlled_v5_power(
                    n_episode_seeds=n_seeds,
                    stable_did=stable,
                    revision_shift=revision,
                    n_sim=args.n_sim,
                    baseline_frame_shares=frame_shares,
                    alpha_each=args.alpha_each,
                    seed=args.seed + effect_index * 100000 + n_seeds,
                )
            )

    recommendations = {}
    complete_recommendations = {}
    for stable, revision in effects:
        key = "%.3f:%.3f" % (stable, revision)
        eligible = [
            row
            for row in rows
            if row["stable_did_seoi"] == stable
            and row["revision_shift_seoi"] == revision
            and row["joint_co_primary"]["mc_ci_lo"] >= args.target_power
        ]
        recommendations[key] = (
            min(row["n_episode_seeds"] for row in eligible) if eligible else None
        )
        complete_eligible = [
            row
            for row in rows
            if row["stable_did_seoi"] == stable
            and row["revision_shift_seoi"] == revision
            and row["complete_behavioral_pattern"]["mc_ci_lo"]
            >= args.target_power
        ]
        complete_recommendations[key] = (
            min(row["n_episode_seeds"] for row in complete_eligible)
            if complete_eligible
            else None
        )
    payload = {
        "status": (
            "pre-outcome final exact blocked V5 power sensitivity"
            if validation_source
            else "provisional power with placeholder balanced frame shares"
        ),
        "focal_model_outcomes_used": False,
        "confirmatory_outcomes_used": False,
        "selected_bank_validation_source": validation_source,
        "n_sim_requirement_met": args.n_sim >= 5000,
        "target_power_lower_mc_bound": args.target_power,
        "results": rows,
        "minimum_episode_seeds_by_effect_pair": recommendations,
        "minimum_episode_seeds_by_effect_pair_complete_pattern": complete_recommendations,
        "selection_rule": (
            "For a declared smallest-effect pair, choose the smallest listed seed "
            "count whose lower 95% Monte Carlo bound for joint co-primary power "
            "and complete-pattern power are both at least target_power; never "
            "choose the effect pair or sample size after confirmatory outcomes."
        ),
    }
    os.makedirs(args.out_dir, exist_ok=True)
    json_path = os.path.join(args.out_dir, "v5_power_sensitivity.json")
    csv_path = os.path.join(args.out_dir, "v5_power_sensitivity.csv")
    for path in (json_path, csv_path):
        if os.path.exists(path):
            raise FileExistsError("refusing to overwrite %s" % path)
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "stable_did",
                "revision_shift",
                "episode_seeds",
                "episodes",
                "generations",
                "stable_power",
                "revision_power",
                "joint_power",
                "joint_mc_ci_lo",
                "joint_mc_ci_hi",
                "complete_pattern_power",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row["stable_did_seoi"],
                    row["revision_shift_seoi"],
                    row["n_episode_seeds"],
                    row["total_confirmatory_episodes"],
                    row["total_confirmatory_generations"],
                    row["stable_co_primary"]["power"],
                    row["revision_co_primary"]["power"],
                    row["joint_co_primary"]["power"],
                    row["joint_co_primary"]["mc_ci_lo"],
                    row["joint_co_primary"]["mc_ci_hi"],
                    row["complete_behavioral_pattern"]["power"],
                ]
            )
    print("wrote %s" % json_path)
    print("wrote %s" % csv_path)
    print("recommendations: %s" % recommendations)
    print("complete-pattern recommendations: %s" % complete_recommendations)
    return 0


if __name__ == "__main__":
    sys.exit(main())
