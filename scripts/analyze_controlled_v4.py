#!/usr/bin/env python3
"""Analyze a V4 controlled-choice log and render publication-ready figures."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from config import STRATEGIES
from src.controlled_analysis import evaluate_controlled_checkpoint
from src.logging_utils import read_jsonl


COLORS = {
    "full_history": "#D55E00",
    "no_history": "#0072B2",
    "shuffled_history": "#009E73",
    "random_target": "#8C8C8C",
    "old": "#E69F00",
    "new": "#CC79A7",
    "elicited_full_history": "#56B4E9",
    "elicited_swap": "#D55E00",
}
LABELS = {
    "full_history": "Full history",
    "no_history": "No history",
    "shuffled_history": "Shuffled history",
    "random_target": "Random target",
    "elicited_full_history": "Elicited, stable",
    "elicited_swap": "Elicited, swap",
}
MARKERS = {"full_history": "o", "no_history": "s", "shuffled_history": "^", "random_target": "D"}


def _style() -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.titleweight": "bold",
        "axes.labelsize": 9,
        "legend.fontsize": 7.5,
        "legend.frameon": False,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.15,
        "lines.linewidth": 1.7,
        "lines.markersize": 4,
    })


def _save(fig, fig_dir: str, stem: str) -> None:
    os.makedirs(fig_dir, exist_ok=True)
    fig.savefig(os.path.join(fig_dir, stem + ".pdf"))
    fig.savefig(os.path.join(fig_dir, stem + ".png"), dpi=300)
    plt.close(fig)


def _round_ci(rows, metric, n_boot: int, seed: int):
    by_round = defaultdict(list)
    for row in rows:
        value = metric(row)
        if value is not None:
            by_round[int(row["round"])].append(float(value))
    generator = np.random.default_rng(seed)
    out = []
    for round_index, values in sorted(by_round.items()):
        array = np.asarray(values, dtype=float)
        boot = generator.choice(array, size=(n_boot, len(array)), replace=True).mean(axis=1)
        lo, hi = np.quantile(boot, [0.025, 0.975])
        out.append((round_index, float(array.mean()), float(lo), float(hi), len(array)))
    return out


def _line(ax, summary, condition, label=None, color=None, marker=None):
    x = np.asarray([row[0] for row in summary])
    mean = np.asarray([row[1] for row in summary])
    lo = np.asarray([row[2] for row in summary])
    hi = np.asarray([row[3] for row in summary])
    color = color or COLORS[condition]
    ax.plot(x, mean, label=label or LABELS[condition], color=color,
            marker=marker or MARKERS.get(condition, "o"), markevery=2)
    ax.fill_between(x, lo, hi, color=color, alpha=0.10, linewidth=0)


def _condition_rows(records, condition):
    return [row for row in records if row["condition"] == condition]


def make_figures(records, summary, fig_dir: str, n_boot: int, seed: int) -> None:
    stable_conditions = ("full_history", "no_history", "shuffled_history", "random_target")

    fig, ax = plt.subplots(figsize=(5.5, 3.0))
    for index, condition in enumerate(stable_conditions):
        values = _round_ci(
            _condition_rows(records, condition),
            lambda row: row["strategy_match"], n_boot, seed + index,
        )
        _line(ax, values, condition)
    ax.axhline(1.0 / 3.0, color="#333333", linestyle="--", linewidth=1,
               label="Three-frame reference")
    ax.axvline(15.5, color="#666666", linestyle=":", linewidth=1)
    ax.text(15.65, 0.97, "held-out\nparaphrases", va="top", fontsize=7, color="#555555")
    ax.set(xlabel="Interaction round", ylabel="Target-matched candidate rate",
           ylim=(-0.02, 1.02), title="Target-specific candidate selection")
    ax.legend(ncol=2, loc="lower right")
    _save(fig, fig_dir, "fig_v4_match_by_round")

    fig, ax = plt.subplots(figsize=(5.5, 3.0))
    for index, condition in enumerate(stable_conditions):
        values = _round_ci(
            _condition_rows(records, condition),
            lambda row: row["target_success"], n_boot, seed + 20 + index,
        )
        _line(ax, values, condition)
    ax.axvline(15.5, color="#666666", linestyle=":", linewidth=1)
    ax.set(xlabel="Interaction round", ylabel="Option A choice rate",
           ylim=(-0.02, 1.02), title="Instrumental success")
    ax.legend(ncol=2, loc="lower right")
    _save(fig, fig_dir, "fig_v4_success_by_round")

    swap_rows = _condition_rows(records, "swap")
    new_summary = _round_ci(
        swap_rows, lambda row: row["selected_frame"] == row["final_target_type"],
        n_boot, seed + 40,
    )
    old_summary = _round_ci(
        swap_rows, lambda row: row["selected_frame"] == row["initial_target_type"],
        n_boot, seed + 41,
    )
    fig, ax = plt.subplots(figsize=(5.5, 3.0))
    _line(ax, old_summary, "full_history", label="Matches old target",
          color=COLORS["old"], marker="s")
    _line(ax, new_summary, "full_history", label="Matches new target",
          color=COLORS["new"], marker="o")
    ax.axvline(10.5, color="#222222", linestyle="--", linewidth=1, label="Silent swap")
    ax.axvline(15.5, color="#666666", linestyle=":", linewidth=1)
    ax.axhline(1.0 / 3.0, color="#999999", linestyle="--", linewidth=0.8)
    ax.set(xlabel="Interaction round", ylabel="Candidate-match rate",
           ylim=(-0.02, 1.02), title="Revision after a silent target change")
    ax.legend(ncol=2, loc="upper center")
    _save(fig, fig_dir, "fig_v4_swap_adaptation")

    condition_names = list(stable_conditions)
    means = [summary["stable_condition_metrics"][name]["late_heldout_match"]["mean"]
             for name in condition_names]
    lows = [summary["stable_condition_metrics"][name]["late_heldout_match"]["ci_lo"]
            for name in condition_names]
    highs = [summary["stable_condition_metrics"][name]["late_heldout_match"]["ci_hi"]
             for name in condition_names]
    x = np.arange(len(condition_names))
    fig, ax = plt.subplots(figsize=(5.5, 3.0))
    ax.bar(x, means, color=[COLORS[name] for name in condition_names], width=0.65,
           edgecolor="white", linewidth=0.5)
    ax.errorbar(x, means, yerr=[np.asarray(means) - np.asarray(lows),
                               np.asarray(highs) - np.asarray(means)],
                fmt="none", ecolor="#222222", capsize=3, linewidth=1)
    ax.axhline(1.0 / 3.0, color="#333333", linestyle="--", linewidth=1)
    ax.set_xticks(x, [LABELS[name] for name in condition_names], rotation=12, ha="right")
    ax.set(ylabel="Rounds 16–20 match rate", ylim=(0, 1),
           title="Held-out paraphrase comparison")
    _save(fig, fig_dir, "fig_v4_control_comparison")

    full_rows = _condition_rows(records, "full_history")
    matrix = np.zeros((3, 3), dtype=float)
    for i, target in enumerate(STRATEGIES):
        target_rows = [row for row in full_rows if row["hidden_target_type"] == target
                       and int(row["round"]) >= 16]
        for j, frame in enumerate(STRATEGIES):
            matrix[i, j] = np.mean([row["selected_frame"] == frame for row in target_rows])
    fig, ax = plt.subplots(figsize=(3.5, 3.0))
    image = ax.imshow(matrix, vmin=0, vmax=1, cmap="Blues")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, "%.2f" % matrix[i, j], ha="center", va="center",
                    color="white" if matrix[i, j] > 0.55 else "#222222", fontsize=8)
    ax.set_xticks(range(3), [name.title() for name in STRATEGIES], rotation=20, ha="right")
    ax.set_yticks(range(3), [name.title() for name in STRATEGIES])
    ax.set(xlabel="Selected candidate frame", ylabel="Active target type",
           title="Full-history held-out choices")
    fig.colorbar(image, ax=ax, shrink=0.75, label="Selection probability")
    _save(fig, fig_dir, "fig_v4_strategy_by_target")

    elicited = [row for row in records if row["condition"] in
                {"elicited_full_history", "elicited_swap"} and row["beliefs_valid"]]
    if elicited:
        fig, ax = plt.subplots(figsize=(5.5, 3.0))
        for index, condition in enumerate(("elicited_full_history", "elicited_swap")):
            rows = _condition_rows(elicited, condition)
            if rows:
                values = _round_ci(rows, lambda row: row["belief_matches_target"],
                                   n_boot, seed + 60 + index)
                _line(ax, values, condition)
        ax.axhline(1.0 / 3.0, color="#333333", linestyle="--", linewidth=1)
        ax.axvline(10.5, color="#222222", linestyle=":", linewidth=1)
        ax.set(xlabel="Interaction round", ylabel="Best-predicted frame matches target",
               ylim=(-0.02, 1.02), title="Elicited response-model diagnostic")
        ax.legend(loc="lower right")
        _save(fig, fig_dir, "fig_v4_elicited_beliefs")


def write_tables(records, summary, table_dir: str) -> None:
    os.makedirs(table_dir, exist_ok=True)
    with open(os.path.join(table_dir, "v4_stable_conditions.csv"), "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["condition", "n_episodes", "early_match", "late_heldout_match",
                         "learning_gain", "success", "valid_selection"])
        for condition, metrics in summary["stable_condition_metrics"].items():
            writer.writerow([
                condition, metrics["n_episodes"], metrics["early_match"]["mean"],
                metrics["late_heldout_match"]["mean"], metrics["learning_gain"]["mean"],
                metrics["success"]["mean"], metrics["valid_selection"],
            ])
    with open(os.path.join(table_dir, "v4_swap_episodes.csv"), "w", newline="", encoding="utf-8") as fh:
        rows = summary["swap_episode_summaries"]
        writer = csv.DictWriter(
            fh,
            fieldnames=list(rows[0]) if rows else ["episode_id"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    with open(os.path.join(table_dir, "v4_round_trajectories.csv"), "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["condition", "metric", "round", "mean", "n"])
        for condition, metrics in summary["trajectories"].items():
            for metric, rows in metrics.items():
                for row in rows:
                    writer.writerow([condition, metric, row["round"], row["mean"], row["n"]])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--checkpoint-spec", default=None,
                        help="frozen JSON to enforce for a real confirmatory checkpoint")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--n-boot", type=int, default=5000)
    parser.add_argument("--n-perm", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260902)
    args = parser.parse_args(argv)

    manifest_path = args.manifest or args.log.replace(".jsonl", ".manifest.json")
    records = list(read_jsonl(args.log))
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    frozen_spec = None
    if args.checkpoint_spec:
        with open(args.checkpoint_spec, "r", encoding="utf-8") as fh:
            frozen_spec = json.load(fh)
    summary = evaluate_controlled_checkpoint(
        records, manifest, n_boot=args.n_boot, n_perm=args.n_perm, seed=args.seed,
        frozen_spec=frozen_spec,
    )
    os.makedirs(args.out_dir, exist_ok=True)
    summary_path = os.path.join(args.out_dir, "v4_checkpoint_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, allow_nan=False)
    table_dir = os.path.join(args.out_dir, "tables")
    fig_dir = os.path.join(args.out_dir, "figures")
    write_tables(records, summary, table_dir)
    _style()
    make_figures(records, summary, fig_dir, max(200, min(args.n_boot, 2000)), args.seed)
    print(summary["decision"])
    for name, passed in summary["effect_gates"].items():
        print("  %-42s %s" % (name, "PASS" if passed else "FAIL"))
    for name, passed in summary["inference_gates"].items():
        print("  %-42s %s" % (name, "PASS" if passed else "FAIL"))
    print("wrote %s" % summary_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
