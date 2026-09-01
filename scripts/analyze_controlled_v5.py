#!/usr/bin/env python3
"""Analyze a V5 controlled-choice log and render auditable figures/tables."""

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
from src.controlled_v5_analysis import evaluate_controlled_v5_checkpoint
from src.logging_utils import read_jsonl


COLORS = {
    "full_history": "#D55E00",
    "no_history": "#0072B2",
    "shuffled_history": "#009E73",
    "random_target": "#777777",
    "old": "#E69F00",
    "new": "#CC79A7",
}
LABELS = {
    "full_history": "Full history",
    "no_history": "No history",
    "shuffled_history": "Shuffled history",
    "random_target": "Random responses",
}
MARKERS = {
    "full_history": "o",
    "no_history": "s",
    "shuffled_history": "^",
    "random_target": "D",
}
LINESTYLES = {
    "full_history": "-",
    "no_history": "--",
    "shuffled_history": "-.",
    "random_target": ":",
}


def _style() -> None:
    plt.rcParams.update(
        {
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
        }
    )


def _save(fig, directory: str, stem: str) -> None:
    os.makedirs(directory, exist_ok=True)
    fig.savefig(os.path.join(directory, stem + ".pdf"))
    fig.savefig(os.path.join(directory, stem + ".png"), dpi=300)
    plt.close(fig)


def _condition_rows(records, condition):
    return [row for row in records if row["condition"] == condition]


def _round_block_ci(rows, metric, n_boot: int, seed: int):
    by_round_block = defaultdict(lambda: defaultdict(list))
    for row in rows:
        value = metric(row)
        if value is not None:
            by_round_block[int(row["round"])][int(row["episode_index"])].append(
                float(value)
            )
    generator = np.random.default_rng(seed)
    output = []
    for round_index, by_block in sorted(by_round_block.items()):
        values = np.asarray(
            [np.mean(by_block[key]) for key in sorted(by_block)], dtype=float
        )
        boot = generator.choice(
            values, size=(n_boot, len(values)), replace=True
        ).mean(axis=1)
        low, high = np.quantile(boot, [0.025, 0.975])
        output.append(
            (round_index, float(values.mean()), float(low), float(high), len(values))
        )
    return output


def _line(
    ax, values, condition, label=None, color=None, marker=None, linestyle=None
):
    x = np.asarray([row[0] for row in values])
    mean = np.asarray([row[1] for row in values])
    low = np.asarray([row[2] for row in values])
    high = np.asarray([row[3] for row in values])
    color = color or COLORS[condition]
    ax.plot(
        x,
        mean,
        label=label or LABELS[condition],
        color=color,
        marker=marker or MARKERS.get(condition, "o"),
        linestyle=linestyle or LINESTYLES.get(condition, "-"),
        markevery=2,
    )
    ax.fill_between(x, low, high, color=color, alpha=0.10, linewidth=0)


def make_figures(records, summary, figure_dir: str, n_boot: int, seed: int) -> None:
    stable_conditions = (
        "full_history",
        "no_history",
        "shuffled_history",
        "random_target",
    )
    for field, ylabel, title, stem in (
        (
            "strategy_match",
            "Target-matched candidate rate",
            "Target-specific candidate selection",
            "fig_v5_match_by_round",
        ),
        (
            "target_success",
            "Option A choice rate",
            "Instrumental success",
            "fig_v5_success_by_round",
        ),
    ):
        fig, ax = plt.subplots(figsize=(5.5, 3.1))
        for index, condition in enumerate(stable_conditions):
            values = _round_block_ci(
                _condition_rows(records, condition),
                lambda row, field=field: row[field],
                n_boot,
                seed + index,
            )
            _line(ax, values, condition)
        if field == "strategy_match":
            ax.axhline(1.0 / 3.0, color="#333333", linestyle="--", linewidth=1)
        ax.axvline(18.5, color="#666666", linestyle=":", linewidth=1)
        ax.text(18.65, 0.98, "held-out wording", va="top", fontsize=7)
        ax.set(
            xlabel="Interaction round",
            ylabel=ylabel,
            ylim=(-0.02, 1.02),
            title=title,
        )
        ax.legend(ncol=2, loc="lower right")
        _save(fig, figure_dir, stem)

    swap_rows = _condition_rows(records, "swap")
    new_values = _round_block_ci(
        swap_rows,
        lambda row: row["selected_frame"] == row["final_target_type"],
        n_boot,
        seed + 20,
    )
    old_values = _round_block_ci(
        swap_rows,
        lambda row: row["selected_frame"] == row["initial_target_type"],
        n_boot,
        seed + 21,
    )
    fig, ax = plt.subplots(figsize=(5.5, 3.1))
    _line(
        ax,
        old_values,
        "full_history",
        label="Matches old target",
        color=COLORS["old"],
        marker="s",
        linestyle="--",
    )
    _line(
        ax,
        new_values,
        "full_history",
        label="Matches new target",
        color=COLORS["new"],
        marker="o",
        linestyle="-",
    )
    ax.axvline(12.5, color="#222222", linestyle="--", linewidth=1, label="Silent swap")
    ax.axvline(18.5, color="#666666", linestyle=":", linewidth=1)
    ax.axhline(1.0 / 3.0, color="#999999", linestyle="--", linewidth=0.8)
    ax.set(
        xlabel="Interaction round",
        ylabel="Candidate-match rate",
        ylim=(-0.02, 1.02),
        title="Strategy revision after a silent target change",
    )
    ax.legend(ncol=2, loc="upper center")
    _save(fig, figure_dir, "fig_v5_swap_adaptation")

    means = [
        summary["stable_condition_metrics"][name]["late_heldout_match"]["mean"]
        for name in stable_conditions
    ]
    lows = [
        summary["stable_condition_metrics"][name]["late_heldout_match"]["ci_lo"]
        for name in stable_conditions
    ]
    highs = [
        summary["stable_condition_metrics"][name]["late_heldout_match"]["ci_hi"]
        for name in stable_conditions
    ]
    x = np.arange(len(stable_conditions))
    fig, ax = plt.subplots(figsize=(5.5, 3.1))
    ax.bar(
        x,
        means,
        color=[COLORS[name] for name in stable_conditions],
        width=0.65,
        edgecolor="white",
    )
    ax.errorbar(
        x,
        means,
        yerr=[np.asarray(means) - np.asarray(lows), np.asarray(highs) - np.asarray(means)],
        fmt="none",
        ecolor="#222222",
        capsize=3,
        linewidth=1,
    )
    ax.axhline(1.0 / 3.0, color="#333333", linestyle="--", linewidth=1)
    ax.set_xticks(
        x,
        [LABELS[name] for name in stable_conditions],
        rotation=12,
        ha="right",
    )
    ax.set(
        ylabel="Rounds 19–24 match rate",
        ylim=(0, 1),
        title="Held-out comparison across controls",
    )
    _save(fig, figure_dir, "fig_v5_control_comparison")

    full_rows = [
        row
        for row in _condition_rows(records, "full_history")
        if int(row["round"]) >= 19
    ]
    matrix = np.zeros((3, 3), dtype=float)
    for target_index, target in enumerate(STRATEGIES):
        target_rows = [
            row for row in full_rows if row["hidden_target_type"] == target
        ]
        for frame_index, frame in enumerate(STRATEGIES):
            matrix[target_index, frame_index] = np.mean(
                [row["selected_frame"] == frame for row in target_rows]
            )
    fig, ax = plt.subplots(figsize=(3.6, 3.1))
    image = ax.imshow(matrix, vmin=0, vmax=1, cmap="Blues")
    for i in range(3):
        for j in range(3):
            ax.text(
                j,
                i,
                "%.2f" % matrix[i, j],
                ha="center",
                va="center",
                color="white" if matrix[i, j] > 0.55 else "#222222",
                fontsize=8,
            )
    ax.set_xticks(range(3), [value.title() for value in STRATEGIES], rotation=20, ha="right")
    ax.set_yticks(range(3), [value.title() for value in STRATEGIES])
    ax.set(
        xlabel="Selected frame",
        ylabel="Active target type",
        title="Full-history held-out choices",
    )
    fig.colorbar(image, ax=ax, shrink=0.75, label="Selection probability")
    _save(fig, figure_dir, "fig_v5_strategy_by_target")

    transitions = summary["swap_metrics"]["transition_metrics"]
    names = sorted(transitions)
    transition_means = [transitions[name]["revision_shift"]["mean"] for name in names]
    transition_lows = [transitions[name]["revision_shift"]["ci_lo"] for name in names]
    transition_highs = [transitions[name]["revision_shift"]["ci_hi"] for name in names]
    y = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    ax.errorbar(
        transition_means,
        y,
        xerr=[
            np.asarray(transition_means) - np.asarray(transition_lows),
            np.asarray(transition_highs) - np.asarray(transition_means),
        ],
        fmt="o",
        color="#0072B2",
        ecolor="#555555",
        capsize=3,
    )
    ax.axvline(0.0, color="#222222", linewidth=1)
    ax.axvline(0.10, color="#D55E00", linestyle="--", linewidth=1)
    ax.set_yticks(y, [name.replace("_to_", " → ").title() for name in names])
    ax.set(
        xlabel="Baseline-adjusted revision shift",
        title="All six ordered target transitions",
    )
    _save(fig, figure_dir, "fig_v5_transition_revision")


def write_tables(summary, table_dir: str) -> None:
    os.makedirs(table_dir, exist_ok=True)
    with open(
        os.path.join(table_dir, "v5_stable_conditions.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "condition",
                "n_episodes",
                "n_blocks",
                "early_match",
                "development_match",
                "heldout_match",
                "learning_gain",
                "success",
            ]
        )
        for condition, metric in summary["stable_condition_metrics"].items():
            writer.writerow(
                [
                    condition,
                    metric["n_episodes"],
                    metric["n_blocks"],
                    metric["early_match"]["mean"],
                    metric["late_development_match"]["mean"],
                    metric["late_heldout_match"]["mean"],
                    metric["learning_gain"]["mean"],
                    metric["success"]["mean"],
                ]
            )
    with open(
        os.path.join(table_dir, "v5_swap_episodes.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = summary["swap_episode_summaries"]
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]) if rows else ["episode_id"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    with open(
        os.path.join(table_dir, "v5_transition_revision.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            ["transition", "old_type", "new_type", "mean", "ci_lo", "ci_hi", "p_one_sided"]
        )
        for name, metric in sorted(
            summary["swap_metrics"]["transition_metrics"].items()
        ):
            revision = metric["revision_shift"]
            writer.writerow(
                [
                    name,
                    metric["old_type"],
                    metric["new_type"],
                    revision["mean"],
                    revision["ci_lo"],
                    revision["ci_hi"],
                    revision["p_value_one_sided"],
                ]
            )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--checkpoint-spec", default=None)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--n-boot", type=int, default=5000)
    parser.add_argument("--n-perm", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20261001)
    args = parser.parse_args(argv)
    manifest_path = args.manifest or args.log.replace(".jsonl", ".manifest.json")
    records = list(read_jsonl(args.log))
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    frozen_spec = None
    if args.checkpoint_spec:
        with open(args.checkpoint_spec, "r", encoding="utf-8") as handle:
            frozen_spec = json.load(handle)
    summary = evaluate_controlled_v5_checkpoint(
        records,
        manifest,
        n_boot=args.n_boot,
        n_perm=args.n_perm,
        seed=args.seed,
        frozen_spec=frozen_spec,
    )
    os.makedirs(args.out_dir, exist_ok=True)
    summary_path = os.path.join(args.out_dir, "v5_checkpoint_summary.json")
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False)
    write_tables(summary, os.path.join(args.out_dir, "tables"))
    _style()
    make_figures(
        records,
        summary,
        os.path.join(args.out_dir, "figures"),
        max(200, min(args.n_boot, 2000)),
        args.seed,
    )
    print(summary["decision"])
    for section in ("effect_gates", "inference_gates"):
        for name, passed in summary[section].items():
            print("  %-46s %s" % (name, "PASS" if passed else "FAIL"))
    print("wrote %s" % summary_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
