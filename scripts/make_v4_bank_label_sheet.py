#!/usr/bin/env python3
"""Blind human-labelling sheet for the 90 V4 message-bank candidates.

Pulled from the V4 log's own `candidates` field so the sheet is exactly what
the model saw. Rows are shuffled; no frame, split, or id is visible. The
answer key is a separate file. Label each with fairness | risk | expertise |
other | unsure, then run scripts/score_labels.py --sheet <csv> --key <key>.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import csv
import json
import os
import random
import sys


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--log", default="data/raw/qwen38_27b_v4_checkpoint_20260902.jsonl")
    p.add_argument("--out", default="data/processed/v4_bank_label_sheet.csv")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--sample", type=int, default=45, help="rows to label (0 = all templates)")
    a = p.parse_args(argv)
    seen = {}
    with open(a.log, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            for c in r["candidates"]:
                # the labelling unit is the TEMPLATE (frame, split, index); candidate ids are template x scenario
                k = "%s|%s|%s" % (c["frame"], c.get("split"), c.get("template_index"))
                seen.setdefault(k, {"frame": c["frame"], "split": c.get("split"), "message": c["message"], "template": k})
    items = sorted(seen.items())
    rng = random.Random(a.seed); rng.shuffle(items)
    if a.sample and a.sample < len(items):
        items = items[: a.sample]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    key = {}
    with open(a.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(["sample_id", "message", "human_label"])
        for i, (cid, c) in enumerate(items):
            sid = "b%03d" % i; w.writerow([sid, c["message"], ""])
            key[sid] = {"candidate_id": cid, "template": c["template"], "judge_label": c["frame"], "hidden_target_type": c["frame"],
                        "split": c["split"], "classifier_name": "registered_frame", "judge_confidence": 1.0,
                        "condition": "bank", "episode_id": "bank", "round": 0, "target_choice": "", "message": c["message"]}
    with open(a.out + ".key.json", "w", encoding="utf-8") as fh:
        json.dump(key, fh, indent=2)
    counts = {}
    for _, c in items: counts[c["frame"]] = counts.get(c["frame"], 0) + 1
    print("wrote %d blind rows to %s (frames: %s; %d templates total); key: %s" % (len(items), a.out, counts, len(seen), a.out + ".key.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
