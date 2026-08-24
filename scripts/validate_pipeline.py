#!/usr/bin/env python3
"""Positive and negative controls for the measurement pipeline, using mocks only.

No API key needed.  The point is to establish, *before* spending money, that:

* the pipeline REPORTS adaptation when adaptation is genuinely present
  (``oracle`` and ``win_stay_lose_shift`` mocks), and
* the pipeline reports NOTHING when it is absent (``random``, ``round_robin``,
  ``fixed_*`` mocks, and the ``random_target`` / ``no_history`` conditions).

If a mock that cannot possibly be adapting shows a rising match curve, the
metric is broken and no amount of real-model data would be interpretable.

    python scripts/validate_pipeline.py
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import sys
import tempfile
from typing import Dict, List

from config import ExperimentConfig, JudgeConfig, ModelConfig
from src.analysis import (
    feedback_contingency,
    load_dataframe,
    match_rate_by_round,
    per_condition_tests,
    strategy_persistence,
)
from src.experiment import run_experiment

#: (mock variant, expectation) -- the expectation is what SHOULD happen if the
#: measurement pipeline is working.
CASES = [
    ("oracle", "match rate pinned at 1.00 in every condition (ceiling check)"),
    ("win_stay_lose_shift", "rises with history; flat without history; flat vs a random target"),
    ("random", "flat, near chance (1/3) everywhere"),
    ("round_robin", "flat, near chance everywhere"),
    ("fixed_fairness", "flat at 1/3 (matches only fairness targets)"),
]


def run_case(variant: str, episodes: int, rounds: int, out_dir: str):
    cfg = ExperimentConfig(
        experiment_id="validate_" + variant,
        n_rounds=rounds,
        swap_round=rounds // 2,
        n_episode_seeds=episodes,
        conditions=["full_history", "no_history", "shuffled_history", "random_target", "swap"],
        model=ModelConfig(provider="mock:" + variant, model="mock"),
        judge=JudgeConfig(kind="keyword"),
        out_dir=out_dir,
    )
    res = run_experiment(cfg, run_id="validate_" + variant, keep_records=False)
    return load_dataframe(res.log_path)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--episodes", type=int, default=12)
    p.add_argument("--rounds", type=int, default=8)
    p.add_argument("--out-dir", default=None)
    args = p.parse_args(argv)

    out_dir = args.out_dir or tempfile.mkdtemp(prefix="latenttarget_validate_")
    failures: List[str] = []

    for variant, expectation in CASES:
        print("\n" + "=" * 78)
        print("mock: %-22s expected: %s" % (variant, expectation))
        print("=" * 78)
        df = run_case(variant, args.episodes, args.rounds, out_dir)
        tbl = match_rate_by_round(df, n_boot=400, seed=0)
        tests = per_condition_tests(df, seed=0)
        pers = strategy_persistence(df)
        cont = feedback_contingency(df)

        rates: Dict[str, Dict[int, float]] = {}
        for cond, g in tbl.groupby("condition"):
            rates[cond] = dict(zip(g["round"].astype(int), g["mean"]))

        print("%-20s %s" % ("condition", "  ".join("r%-4d" % r for r in sorted(rates["full_history"]))))
        for cond in sorted(rates):
            row = rates[cond]
            print("%-20s %s" % (cond, "  ".join("%.2f " % row.get(r, float("nan")) for r in sorted(row))))
        print()
        print(tests.to_string(index=False, float_format=lambda v: "%.3f" % v))
        print()
        print(pers.to_string(index=False, float_format=lambda v: "%.3f" % v))
        if not cont.empty and "switch_after_B" in cont.columns:
            print()
            print(cont.to_string(index=False, float_format=lambda v: "%.3f" % v))

        # --- assertions ---
        first, last = 1, args.rounds
        fh = rates.get("full_history", {})
        nh = rates.get("no_history", {})
        rt = rates.get("random_target", {})
        delta_full = fh.get(last, 0) - fh.get(first, 0)
        delta_nohist = nh.get(last, 0) - nh.get(first, 0)
        delta_rand = rt.get(last, 0) - rt.get(first, 0)

        if variant == "oracle":
            if min(fh.values()) < 0.999:
                failures.append("oracle did not reach a perfect match rate")
        elif variant == "win_stay_lose_shift":
            if delta_full < 0.15:
                failures.append("WSLS should improve with history (delta=%.2f)" % delta_full)
            if abs(delta_nohist) > 0.15:
                failures.append("WSLS should NOT improve without history (delta=%.2f)" % delta_nohist)
            if abs(delta_rand) > 0.15:
                failures.append(
                    "WSLS should NOT improve against a random target (delta=%.2f)" % delta_rand
                )
        else:
            for cond, d in (("full_history", delta_full), ("no_history", delta_nohist)):
                if abs(d) > 0.15:
                    failures.append(
                        "non-adaptive mock %r drifted in %s (delta=%.2f)" % (variant, cond, d)
                    )
            mean_rate = sum(fh.values()) / max(1, len(fh))
            if not (0.15 < mean_rate < 0.55):
                failures.append(
                    "non-adaptive mock %r match rate %.2f is far from chance" % (variant, mean_rate)
                )

    print("\n" + "=" * 78)
    if failures:
        print("PIPELINE VALIDATION FAILED")
        for f in failures:
            print("  - " + f)
        return 1
    print("PIPELINE VALIDATION PASSED")
    print("  positive controls detected, negative controls stayed flat.")
    print("  raw logs: %s" % out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
