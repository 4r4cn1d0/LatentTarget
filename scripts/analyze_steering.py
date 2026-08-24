#!/usr/bin/env python3
"""Analyze paired target/opposite/random/zero steering generations."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.steering_analysis import load_steering_dataframe, paired_steering_summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("--out-dir", default="results/tables")
    parser.add_argument("--fig-dir", default="results/figures")
    parser.add_argument("--n-boot", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    df = load_steering_dataframe(args.log)
    summary = paired_steering_summary(df, n_boot=args.n_boot, seed=args.seed)
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.fig_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, "steering_paired_contrasts.csv")
    json_path = os.path.join(args.out_dir, "steering_summary.json")
    fig_path = os.path.join(args.fig_dir, "fig10_steering_dose_response.png")
    import pandas as pd

    pd.DataFrame(summary).to_csv(csv_path, index=False)
    payload = {
        "source_log": args.log,
        "n_generations": int(len(df)),
        "n_source_episodes": int(df["source_episode_id"].nunique()),
        "contrasts": summary,
        "primary": (
            "At each predeclared coefficient, target direction minus zero-vector "
            "on intended_strategy_score; episode-clustered bootstrap CI."
        ),
        "warning": (
            "Keyword classifications are an engineering check. Confirm the same "
            "direction with the blind LLM judge/human audit before a causal claim."
        ),
    }
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    means = df.groupby(["coefficient", "intervention"])["intended_score"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(6.5, 4.0), dpi=150)
    styles = {
        "target": ("#1f77b4", "o"), "zero": ("#555555", "s"),
        "random": ("#ff7f0e", "^"), "opposite": ("#d62728", "v"),
    }
    for condition, group in means.groupby("intervention"):
        color, marker = styles.get(condition, (None, "o"))
        ax.plot(group["coefficient"], group["intended_score"], marker=marker,
                color=color, label=condition)
    ax.set(xlabel="steering coefficient (residual-norm units)",
           ylabel="mean score for steered strategy", ylim=(0, 1),
           title="Probe-direction steering dose response")
    ax.grid(alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(fig_path)
    plt.close(fig)
    print("wrote %s\nwrote %s\nwrote %s" % (csv_path, json_path, fig_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
