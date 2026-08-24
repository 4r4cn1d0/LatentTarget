#!/usr/bin/env python3
"""Generate pre-data power/sensitivity tables for the planned real-model run."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.power_analysis import simulate_behavior_power, simulate_swap_gap_power


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode-seeds", nargs="+", type=int,
                        default=[4, 8, 12, 16, 20])
    parser.add_argument("--behavior-effects", nargs="+", type=float,
                        default=[0.10, 0.15, 0.20, 0.25])
    parser.add_argument("--swap-effects", nargs="+", type=float,
                        default=[0.3, 0.5, 0.7])
    parser.add_argument("--n-sim", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20250819)
    parser.add_argument("--out-dir", default="results/tables")
    parser.add_argument("--fig-dir", default="results/figures")
    args = parser.parse_args(argv)

    behavior = []
    swap = []
    for i, effect in enumerate(args.behavior_effects):
        for n in args.episode_seeds:
            behavior.append(simulate_behavior_power(
                n, effect, n_sim=args.n_sim, seed=args.seed + i * 1000 + n
            ))
    for i, effect in enumerate(args.swap_effects):
        for n in args.episode_seeds:
            swap.append(simulate_swap_gap_power(
                n, effect, n_sim=args.n_sim, seed=args.seed + 10000 + i * 1000 + n
            ))

    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.fig_dir, exist_ok=True)
    json_path = os.path.join(args.out_dir, "power_sensitivity.json")
    csv_path = os.path.join(args.out_dir, "power_sensitivity.csv")
    fig_path = os.path.join(args.fig_dir, "fig_power_sensitivity.png")
    payload = {
        "status": "design sensitivity; no real-model observations used",
        "behavior_primary": behavior,
        "swap_mechanistic": swap,
        "assumptions": {
            "independent_unit": "episode",
            "behavior_test": "paired full-history vs no-history change contrast",
            "behavior_episode_random_intercept_sd_logit": 0.55,
            "swap_test": "episode-level standardized trajectory gap",
            "alpha": 0.05,
            "warning": (
                "Use an unblinded pilot to estimate variance, then freeze the main "
                "sample size before examining main-run outcomes."
            ),
        },
    }
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    with open(csv_path, "w", encoding="utf-8") as fh:
        fh.write("analysis,effect,n_episode_seeds,n_episodes,power\n")
        for row in behavior:
            fh.write("behavior,%.3f,%d,%d,%.4f\n" % (
                row["late_match_increase"], row["n_episode_seeds"],
                row["episodes_per_condition"], row["power"],
            ))
        for row in swap:
            fh.write("swap_gap,%.3f,%d,%d,%.4f\n" % (
                row["standardized_gap"], row["n_episode_seeds"],
                row["swap_episodes"], row["power"],
            ))

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), dpi=150)
    for effect in args.behavior_effects:
        subset = [row for row in behavior if row["late_match_increase"] == effect]
        axes[0].plot([r["episodes_per_condition"] for r in subset],
                     [r["power"] for r in subset], marker="o", label="+%.0f pp" % (100 * effect))
    for effect in args.swap_effects:
        subset = [row for row in swap if row["standardized_gap"] == effect]
        axes[1].plot([r["swap_episodes"] for r in subset],
                     [r["power"] for r in subset], marker="o", label="d=%.1f" % effect)
    for ax, title, xlabel in (
        (axes[0], "Primary behavioural contrast", "episodes per stable condition"),
        (axes[1], "Mechanistic swap-gap sensitivity", "counterbalanced swap episodes"),
    ):
        ax.axhline(0.8, color="black", ls="--", lw=1)
        ax.set(title=title, xlabel=xlabel, ylabel="simulated power", ylim=(0, 1))
        ax.grid(alpha=0.25)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(fig_path)
    plt.close(fig)
    print("wrote %s\nwrote %s\nwrote %s" % (json_path, csv_path, fig_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
