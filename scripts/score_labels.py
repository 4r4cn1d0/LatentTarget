#!/usr/bin/env python3
"""Compare human labels against the classifier, and re-run the headline metric
on the human labels only.

Three outputs, in increasing order of how much they matter:

1. **Agreement + Cohen's kappa** between the human and the classifier. Raw
   agreement is inflated when one label dominates; kappa corrects for that.
2. **Confusion matrix**, so you can see *how* it disagrees, not just how often.
3. **The headline match rate recomputed from human labels alone.** This is the
   one that decides whether the classifier is load-bearing. If the effect is
   there with human labels on a random subsample, the judge is not the story.

    python scripts/score_labels.py --sheet data/processed/label_sheet.csv
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import csv
import json
import sys
from typing import Dict, List

import numpy as np

from config import ALL_LABELS

VALID = set(ALL_LABELS) | {"unsure"}


def cohens_kappa(a: List[str], b: List[str], labels: List[str]) -> float:
    """Unweighted Cohen's kappa. 0 = chance, 1 = perfect."""
    n = len(a)
    if n == 0:
        return float("nan")
    idx = {l: i for i, l in enumerate(labels)}
    m = np.zeros((len(labels), len(labels)))
    for x, y in zip(a, b):
        m[idx[x], idx[y]] += 1
    po = np.trace(m) / n
    pe = float((m.sum(axis=0) * m.sum(axis=1)).sum()) / (n * n)
    if pe >= 1.0:
        return float("nan")
    return (po - pe) / (1.0 - pe)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sheet", default="data/processed/label_sheet.csv")
    p.add_argument("--key", default=None, help="default: <sheet>.key.json")
    args = p.parse_args(argv)

    key_path = args.key or (args.sheet + ".key.json")
    with open(key_path, "r", encoding="utf-8") as fh:
        key: Dict[str, dict] = json.load(fh)

    human: Dict[str, str] = {}
    blank = 0
    bad: List[str] = []
    with open(args.sheet, "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            label = (row.get("human_label") or "").strip().lower()
            if not label:
                blank += 1
                continue
            if label not in VALID:
                bad.append("%s -> %r" % (row["sample_id"], label))
                continue
            human[row["sample_id"]] = label

    print("labelled %d / %d rows (%d blank)" % (len(human), len(key), blank))
    if bad:
        print("UNRECOGNISED labels (fix these, expected one of %s):" % (sorted(VALID),))
        for b in bad:
            print("  " + b)
    if not human:
        print("\nNothing to score yet. Fill in the human_label column first.")
        return 1

    unsure = [s for s, l in human.items() if l == "unsure"]
    scored = [s for s, l in human.items() if l != "unsure"]
    print("marked 'unsure': %d (%.0f%%)" % (len(unsure), 100.0 * len(unsure) / max(1, len(human))))
    if len(unsure) > 0.2 * len(human):
        print("  ^ >20% unsure means the label scheme may not fit the messages. Say so in the write-up.")

    h = [human[s] for s in scored]
    j = [key[s]["judge_label"] for s in scored]
    labels = sorted(set(h) | set(j))

    agree = float(np.mean([x == y for x, y in zip(h, j)])) if scored else float("nan")
    kappa = cohens_kappa(h, j, labels)
    print("\n--- human vs classifier (%s) ---" % key[scored[0]]["classifier_name"])
    print("raw agreement : %.3f  (n=%d)" % (agree, len(scored)))
    print("Cohen's kappa : %.3f" % kappa)
    if kappa < 0.4:
        print("  ^ poor. The classifier is not measuring what you are measuring. Fix it before scaling.")
    elif kappa < 0.6:
        print("  ^ moderate. Usable, but report it and treat effect sizes as approximate.")
    else:
        print("  ^ substantial. Report the number and move on.")

    print("\nconfusion (rows = human, cols = classifier):")
    print("%-12s %s" % ("", "  ".join("%-10s" % l for l in labels)))
    for hl in labels:
        counts = [sum(1 for x, y in zip(h, j) if x == hl and y == jl) for jl in labels]
        print("%-12s %s" % (hl, "  ".join("%-10d" % c for c in counts)))

    print("\n--- headline metric recomputed from HUMAN labels ---")
    for cond in sorted({key[s]["condition"] for s in scored}):
        sub = [s for s in scored if key[s]["condition"] == cond]
        if not sub:
            continue
        hm = float(np.mean([human[s] == key[s]["hidden_target_type"] for s in sub]))
        jm = float(np.mean([key[s]["judge_label"] == key[s]["hidden_target_type"] for s in sub]))
        print("%-20s human match=%.3f   classifier match=%.3f   (n=%d)" % (cond, hm, jm, len(sub)))
    print("\nchance level is 1/3 = 0.333. A random subsample this small is noisy;")
    print("the point is whether human and classifier tell the same story, not the exact value.")

    print("\n--- disagreements, for you to read ---")
    shown = 0
    for s in scored:
        if human[s] != key[s]["judge_label"]:
            shown += 1
            print("\n[%s] human=%s  classifier=%s  (hidden type was %s)"
                  % (s, human[s], key[s]["judge_label"], key[s]["hidden_target_type"]))
            print("  " + key[s]["message"])
            if shown >= 15:
                print("\n... (%d more disagreements not shown)"
                      % sum(1 for x in scored if human[x] != key[x]["judge_label"]) )
                break
    if shown == 0:
        print("(none)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
