#!/usr/bin/env python3
"""Simulate an outcome-blind information-seeking positive control."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from config import TargetParams  # noqa: E402
from src.identifiability_simulation import (  # noqa: E402
    select_diagnostic_messages,
    simulate_identifiability,
)
from src.logging_utils import read_jsonl  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--figure", required=True)
    parser.add_argument("--n-per-target", type=int, default=3000)
    parser.add_argument("--n-per-swap-pair", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260901)
    args = parser.parse_args(argv)

    records = list(read_jsonl(args.log))
    with open(args.manifest, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    params = TargetParams(**manifest["config"]["target_params"])
    selected = select_diagnostic_messages(records)
    result = simulate_identifiability(
        selected,
        params,
        n_per_target=args.n_per_target,
        n_per_swap_pair=args.n_per_swap_pair,
        seed=args.seed,
    )
    result["source_log"] = args.log
    result["source_manifest"] = args.manifest

    for path in (args.out, args.figure):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7), dpi=150)
    stable = result["stable"]["accuracy_after_each_outcome"]
    axes[0].plot(range(1, len(stable) + 1), stable, marker="o", color="#1f77b4")
    axes[0].axhline(1 / 3, color="grey", ls="--", lw=1)
    axes[0].set_title("Stable target: oracle information policy")
    axes[0].set_xlabel("outcomes observed")
    axes[0].set_ylabel("target-identification accuracy")
    axes[0].set_ylim(0, 1)
    axes[0].grid(alpha=0.25)

    swap = result["swap"]["active_target_accuracy_after_each_outcome"]
    axes[1].plot(range(1, len(swap) + 1), swap, marker="o", color="#2ca02c")
    axes[1].axhline(1 / 3, color="grey", ls="--", lw=1)
    axes[1].axvline(result["swap"]["swap_after_round"] + 0.5, color="black", ls=":")
    axes[1].set_title("Silent swap: oracle information policy")
    axes[1].set_xlabel("outcomes observed")
    axes[1].set_ylabel("active-target accuracy")
    axes[1].set_ylim(0, 1)
    axes[1].grid(alpha=0.25)
    fig.suptitle("Simulator-capacity positive control (not focal-model behavior)")
    fig.tight_layout()
    fig.savefig(args.figure, bbox_inches="tight")
    plt.close(fig)

    print("stable final accuracy=%.3f" % result["stable"]["final_accuracy"])
    print("swap final accuracy=%.3f" % result["swap"]["final_target_accuracy"])
    print("wrote", args.out)
    print("wrote", args.figure)
    return 0


if __name__ == "__main__":
    sys.exit(main())
