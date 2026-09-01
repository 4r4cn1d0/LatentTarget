#!/usr/bin/env python3
"""Generate the V4 episode-level power sensitivity table and curves."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import csv
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.controlled_power import simulate_controlled_v4_power


COLORS = ["#0072B2", "#009E73", "#E69F00", "#D55E00"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode-seeds", nargs="+", type=int,
                        default=[4, 8, 12, 16, 20, 24, 30])
    parser.add_argument("--late-match", nargs="+", type=float,
                        default=[0.45, 0.50, 0.55, 0.60])
    parser.add_argument("--n-sim", type=int, default=2000)
    parser.add_argument("--target-power", type=float, default=0.80)
    parser.add_argument("--alpha-each", type=float, default=0.025)
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--out-dir", default="results/v4_design/power")
    args = parser.parse_args(argv)

    rows = []
    for effect_index, late_match in enumerate(args.late_match):
        for n in args.episode_seeds:
            rows.append(
                simulate_controlled_v4_power(
                    n_episode_seeds=n,
                    full_late_match=late_match,
                    swap_late_new_match=late_match,
                    n_sim=args.n_sim,
                    alpha_each=args.alpha_each,
                    seed=args.seed + effect_index * 10000 + n,
                )
            )

    recommendations = {}
    for late_match in args.late_match:
        eligible = [
            row for row in rows
            if row["full_late_match"] == late_match
            and row["joint_co_primary"]["mc_ci_lo"] >= args.target_power
        ]
        recommendations[str(late_match)] = (
            min(row["n_episode_seeds"] for row in eligible) if eligible else None
        )

    os.makedirs(args.out_dir, exist_ok=True)
    json_path = os.path.join(args.out_dir, "v4_power_sensitivity.json")
    csv_path = os.path.join(args.out_dir, "v4_power_sensitivity.csv")
    payload = {
        "status": "pre-data design sensitivity; no focal-model outcomes used",
        "target_power_lower_mc_bound": args.target_power,
        "results": rows,
        "minimum_episode_seeds_by_assumed_late_match": recommendations,
        "selection_rule": (
            "Choose the smallest listed seed count whose lower 95% Monte Carlo "
            "bound for joint co-primary power is at least target_power. If no "
            "plausible effect satisfies this within budget, do not call the run confirmatory."
        ),
    }
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow([
            "late_match", "episode_seeds", "stable_episodes_per_condition",
            "swap_episodes", "stable_power", "swap_power", "joint_power",
            "joint_mc_ci_lo", "joint_mc_ci_hi",
        ])
        for row in rows:
            writer.writerow([
                row["full_late_match"], row["n_episode_seeds"],
                row["stable_episodes_per_condition"], row["swap_episodes"],
                row["stable_test"]["power"], row["swap_test"]["power"],
                row["joint_co_primary"]["power"], row["joint_co_primary"]["mc_ci_lo"],
                row["joint_co_primary"]["mc_ci_hi"],
            ])

    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
        "legend.fontsize": 7.5, "legend.frameon": False,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.15,
        "savefig.dpi": 300, "savefig.bbox": "tight",
    })
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.6), sharey=True)
    metrics = (("stable_test", "Stable history"), ("swap_test", "Silent swap"),
               ("joint_co_primary", "Both co-primary"))
    for axis, (metric, title) in zip(axes, metrics):
        for index, late_match in enumerate(args.late_match):
            subset = [row for row in rows if row["full_late_match"] == late_match]
            axis.plot(
                [row["n_episode_seeds"] for row in subset],
                [row[metric]["power"] for row in subset],
                color=COLORS[index % len(COLORS)], marker=("o", "s", "^", "D")[index % 4],
                label="late match %.2f" % late_match,
            )
        axis.axhline(args.target_power, color="#222222", linestyle="--", linewidth=1)
        axis.set(title=title, xlabel="Scenario-sequence seeds", ylim=(0, 1.02))
    axes[0].set_ylabel("Simulated power")
    axes[-1].legend(loc="lower right")
    fig.tight_layout()
    pdf_path = os.path.join(args.out_dir, "fig_v4_power_sensitivity.pdf")
    png_path = os.path.join(args.out_dir, "fig_v4_power_sensitivity.png")
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=300)
    plt.close(fig)

    print("wrote %s" % json_path)
    print("wrote %s" % csv_path)
    print("recommendations: %s" % recommendations)
    return 0


if __name__ == "__main__":
    sys.exit(main())
