#!/usr/bin/env python3
"""Add an evidence-only Bayesian baseline to one or more experiment logs.

This costs no model calls. The baseline sees exactly the serialized visible
history available before each focal message. For swaps it assumes a
predeclared constant change hazard; it is *not* given the true swap round.

Example:

    python scripts/analyze_bayesian_observer.py \
        --log data/raw/myrun.jsonl --hazards 0 0.05 0.10 0.20

The primary hazard is the first value passed. The others are sensitivity
analyses and must not be searched for the prettiest result.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys
from dataclasses import asdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from config import TargetParams
from src.analysis import load_dataframe
from src.bayesian_observer import (
    augment_with_bayesian_observer,
    baseline_corrected_trajectory_gap,
)
from src.stats_utils import cluster_bootstrap_mean


def _load_design(log_paths, manifest_path=None):
    """Read target parameters/scorer half from manifests and verify agreement."""
    manifests = []
    if manifest_path:
        paths = [manifest_path]
    else:
        paths = [p[:-6] + ".manifest.json" if p.endswith(".jsonl") else p + ".manifest.json"
                 for p in log_paths]
    for path in paths:
        if not os.path.exists(path):
            raise FileNotFoundError(
                "manifest not found: %s. Pass --manifest explicitly; Bayesian "
                "likelihoods are invalid if simulator parameters are guessed." % path
            )
        with open(path, "r", encoding="utf-8") as fh:
            manifests.append(json.load(fh))
    first = manifests[0]
    params_dict = first["config"]["target_params"]
    scorer_half = first.get("target_scorer", {}).get("lexicon_half", "all")
    for m in manifests[1:]:
        if m["config"]["target_params"] != params_dict:
            raise ValueError("logs use different target parameters; analyze separately")
        if m.get("target_scorer", {}).get("lexicon_half", "all") != scorer_half:
            raise ValueError("logs use different target-scorer lexicons; analyze separately")
    return TargetParams(**params_dict), scorer_half, paths


def _curve(traj, column, n_boot, seed):
    rows = []
    sw = traj[traj["swap_condition"] & traj["rounds_since_swap"].notna()].copy()
    sw["rounds_since_swap"] = sw["rounds_since_swap"].astype(int)
    for r, group in sw.groupby("rounds_since_swap"):
        ci = cluster_bootstrap_mean(
            group[column].values, group["episode_id"].values,
            n_boot=n_boot, seed=seed,
        )
        rows.append((int(r), ci.mean, ci.lo, ci.hi))
    return rows


def _plot(primary, path, n_boot, seed):
    fig, ax = plt.subplots(figsize=(6.5, 4.0), dpi=150)
    for col, label, color, marker in (
        ("bayes_p_final", "Bayesian evidence for NEW type", "#1f77b4", "o"),
        ("behaviour_matches_final", "message uses NEW frame", "#ff7f0e", "s"),
    ):
        vals = _curve(primary, col, n_boot, seed)
        if not vals:
            continue
        x, mean, lo, hi = map(np.asarray, zip(*vals))
        ax.plot(x, mean, marker=marker, color=color, lw=1.7, ms=4, label=label)
        ax.fill_between(x, lo, hi, color=color, alpha=0.13, linewidth=0)
    ax.axvline(0.5, ls="--", lw=1.0, color="black")
    ax.text(0.65, 0.94, "silent swap", fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_xlabel("rounds since swap", fontsize=9)
    ax.set_ylabel("probability / rate", fontsize=9)
    ax.set_title("Evidence-only Bayesian observer vs. focal behaviour", fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--log", nargs="+", required=True)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--hazards", nargs="+", type=float,
                        default=[0.10, 0.0, 0.05, 0.20])
    parser.add_argument("--n-boot", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out-dir", default="results/tables")
    parser.add_argument("--fig-dir", default="results/figures")
    args = parser.parse_args(argv)

    if len(set(args.hazards)) != len(args.hazards):
        parser.error("--hazards must not contain duplicates")
    params, lexicon_half, manifest_paths = _load_design(args.log, args.manifest)
    df = load_dataframe(args.log)
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.fig_dir, exist_ok=True)

    summaries = []
    trajectories = {}
    for hazard in args.hazards:
        traj = augment_with_bayesian_observer(
            df, params=params, hazard=hazard, lexicon_half=lexicon_half
        )
        gap = baseline_corrected_trajectory_gap(
            traj, n_boot=args.n_boot, seed=args.seed
        )
        stable = traj[traj["condition"] == "full_history"]
        no_history = traj[traj["condition"] == "no_history"]
        summary = {
            "hazard": hazard,
            "full_history_bayes_accuracy": float(stable["bayes_matches_active"].mean())
            if len(stable) else None,
            "no_history_bayes_accuracy": float(no_history["bayes_matches_active"].mean())
            if len(no_history) else None,
            "swap_trajectory_gap": gap,
        }
        summaries.append(summary)
        trajectories[str(hazard)] = traj
        print(
            "hazard=%-5g  full-history accuracy=%s  gap=%s"
            % (
                hazard,
                "%.3f" % summary["full_history_bayes_accuracy"]
                if summary["full_history_bayes_accuracy"] is not None else "n/a",
                "%+.3f [%+.3f, %+.3f]" % (
                    gap["statistic"], gap["ci95"][0], gap["ci95"][1]
                ) if "statistic" in gap else "n/a",
            )
        )

    primary_hazard = args.hazards[0]
    primary = trajectories[str(primary_hazard)]
    csv_path = os.path.join(args.out_dir, "bayesian_observer_trajectory.csv")
    json_path = os.path.join(args.out_dir, "bayesian_observer_summary.json")
    fig_path = os.path.join(args.fig_dir, "fig8_bayesian_observer.png")
    primary.to_csv(csv_path, index=False)
    _plot(primary, fig_path, args.n_boot, args.seed)
    payload = {
        "primary_hazard": primary_hazard,
        "sensitivity_hazards": args.hazards[1:],
        "target_params": asdict(params),
        "target_scorer_lexicon_half": lexicon_half,
        "logs": args.log,
        "manifests": manifest_paths,
        "summaries": summaries,
        "warning": (
            "This observer is optimal only conditional on its simulator and "
            "change-hazard assumptions. It is never given the true swap round."
        ),
    }
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print("\nwrote %s\nwrote %s\nwrote %s" % (csv_path, json_path, fig_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())

