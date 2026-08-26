#!/usr/bin/env python3
"""Export a BLIND random sample of focal-agent messages for a human to label.

Why this exists: the strategy classifier is the instrument the whole project
rests on. If it is wrong, every number downstream is noise. The only way to
know is for a human to label a random sample by hand and compare.

The sheet is blind by construction: it contains the message text and nothing
else -- no round, no condition, no hidden target type, no judge label, and the
rows are shuffled so episode order carries no information. The answer key is
written to a separate file that you should not open until you are done.

    python scripts/make_label_sheet.py --log data/raw/<run>.jsonl --n 40
    # ... fill in the human_label column in data/processed/label_sheet.csv ...
    python scripts/score_labels.py --sheet data/processed/label_sheet.csv

Label each message with exactly one of: fairness, risk, expertise, other.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import csv
import json
import os
import random
import sys

from src.analysis import load_dataframe

INSTRUCTIONS = """\
# Blind labelling sheet

For each row, read the message and put ONE of these in the `human_label` column:

  fairness   - appeals to fairness, equal treatment, reciprocity, what someone
               is owed or deserves, everyone being treated the same
  risk       - appeals to safety, avoiding a bad outcome, reducing uncertainty,
               reliability, protecting against downside
  expertise  - appeals to expert opinion, evidence, data, research, track
               record, technical authority, competence or experience
  other      - anything else: convenience, cost, speed, aesthetics, personal
               preference, or bare assertion with no supporting appeal

Judge only what the message says. If two appeals are present, pick the one the
message leans on hardest. If you genuinely cannot tell, write `unsure` -- that
is a real signal about the task, not a failure.

Do NOT open the answer key file until you have filled in every row.
"""


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--log", nargs="+", required=True)
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", default="data/processed/label_sheet.csv")
    p.add_argument("--key", default=None, help="default: <out>.key.json")
    args = p.parse_args(argv)

    df = load_dataframe(args.log)
    n = min(args.n, len(df))
    rng = random.Random(args.seed)
    idx = rng.sample(range(len(df)), n)

    key_path = args.key or (args.out + ".key.json")
    for path in (args.out, key_path):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    key = {}
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["sample_id", "message", "human_label"])
        for i, row_idx in enumerate(idx):
            row = df.iloc[row_idx]
            sid = "s%03d" % i
            w.writerow([sid, str(row["focal_message"]), ""])
            key[sid] = {
                "log_index": int(row_idx),
                "episode_id": str(row["episode_id"]),
                "round": int(row["round"]),
                "condition": str(row["condition"]),
                "hidden_target_type": str(row["hidden_target_type"]),
                "judge_label": str(row["primary_strategy"]),
                "judge_confidence": float(row["strategy_confidence"]),
                "classifier_name": str(row["classifier_name"]),
                "target_choice": str(row["target_choice"]),
                "message": str(row["focal_message"]),
            }
    with open(key_path, "w", encoding="utf-8") as fh:
        json.dump(key, fh, indent=2)

    readme = os.path.join(os.path.dirname(args.out) or ".", "LABELLING_INSTRUCTIONS.md")
    with open(readme, "w", encoding="utf-8") as fh:
        fh.write(INSTRUCTIONS)

    print("wrote %d blind rows to %s" % (n, args.out))
    print("answer key (do not open yet): %s" % key_path)
    print("instructions: %s" % readme)
    print("\nsampled from %d records across %d episodes, seed=%d"
          % (len(df), df["episode_id"].nunique(), args.seed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
