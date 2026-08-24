#!/usr/bin/env python3
"""Print complete raw transcripts from a log, for manual inspection.

    python scripts/print_transcripts.py --log data/raw/pilot_x.jsonl --n 3
    python scripts/print_transcripts.py --log ... --episode full_history-000-risk --prompts

Episodes are selected in sorted order, never by outcome.  Use ``--random N
--seed S`` for a reproducible random sample instead.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import random
import sys
from typing import List

from src.analysis import load_dataframe


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--log", nargs="+", required=True)
    p.add_argument("--n", type=int, default=3)
    p.add_argument("--episode", nargs="*", default=None)
    p.add_argument("--condition", default=None)
    p.add_argument("--random", type=int, default=0, help="sample this many episodes at random")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--prompts", action="store_true", help="also print the full prompt for each round")
    args = p.parse_args(argv)

    df = load_dataframe(args.log)
    if args.condition:
        df = df[df["condition"] == args.condition]
    ids: List[str] = sorted(df["episode_id"].unique())
    if args.episode:
        ids = [e for e in ids if e in set(args.episode)]
    elif args.random:
        rng = random.Random(args.seed)
        ids = rng.sample(ids, min(args.random, len(ids)))
    else:
        ids = ids[: args.n]

    for eid in ids:
        g = df[df["episode_id"] == eid].sort_values("round")
        head = g.iloc[0]
        print("=" * 78)
        print("EPISODE %s" % eid)
        print("  condition   : %s (history=%s, target=%s)"
              % (head["condition"], head["history_mode"], head["target_mode"]))
        print("  hidden type : %s%s"
              % (head["initial_target_type"],
                 "" if not head["swap_condition"]
                 else "  ->  %s after round %s" % (head["final_target_type"], head["swap_round"])))
        print("  model       : %s (%s)" % (head["model_name"], head["provider"]))
        print("  seed        : %s" % head["episode_seed"])
        print("=" * 78)
        for _, row in g.iterrows():
            print("\n--- round %d / %d   [active hidden type: %s] ---"
                  % (row["round"], row["n_rounds"], row["hidden_target_type"]))
            print("scenario : %s" % row["scenario"]["title"])
            print("           A: %s   |   B: %s" % (row["scenario"]["option_a"], row["scenario"]["option_b"]))
            if args.prompts:
                print("\n[SYSTEM PROMPT]\n%s" % row["focal_system_prompt"])
                print("\n[USER PROMPT]\n%s\n" % row["focal_user_prompt"])
            print("message  : %s" % row["focal_message"])
            if str(row["focal_message_raw"]).strip() != str(row["focal_message"]).strip():
                print("raw      : %r" % row["focal_message_raw"])
            print("classifier: %s  scores=%s  conf=%.2f"
                  % (row["primary_strategy"],
                     {k: round(float(v), 2) for k, v in row["strategy_scores"].items()},
                     float(row["strategy_confidence"])))
            ts = row["target_scores"]
            print("target    : scores f=%.2f r=%.2f e=%.2f (hits=%s)  P(A)=%.3f  ->  chose %s"
                  % (ts["fairness"], ts["risk"], ts["expertise"], ts["hits"],
                     row["target_p_a"], row["target_choice"]))
            if row["displayed_choice"] != row["target_choice"]:
                print("  (agent was SHOWN: Option %s -- mismatched_feedback condition)"
                      % row["displayed_choice"])
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
