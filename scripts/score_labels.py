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
import math
import os
import sys
from typing import Dict, List

import numpy as np

from config import ALL_LABELS

VALID = set(ALL_LABELS) | {"unsure"}


def _write_json(path: str, payload: dict) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


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
    p.add_argument("--out", default=None, help="optional machine-readable gate JSON")
    args = p.parse_args(argv)

    key_path = args.key or (args.sheet + ".key.json")
    with open(key_path, "r", encoding="utf-8") as fh:
        key: Dict[str, dict] = json.load(fh)

    human: Dict[str, str] = {}
    blank = 0
    bad: List[str] = []
    structural: List[str] = []
    seen = set()
    with open(args.sheet, "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sample_id = (row.get("sample_id") or "").strip()
            if sample_id in seen:
                structural.append("duplicate sample_id %r" % sample_id)
                continue
            seen.add(sample_id)
            if sample_id not in key:
                structural.append("unknown sample_id %r" % sample_id)
                continue
            if str(row.get("message", "")) != str(key[sample_id]["message"]):
                structural.append("message changed for %s" % sample_id)
            label = (row.get("human_label") or "").strip().lower()
            if not label:
                blank += 1
                continue
            if label not in VALID:
                bad.append("%s -> %r" % (sample_id, label))
                continue
            human[sample_id] = label
    missing = sorted(set(key) - seen)
    if missing:
        structural.append("missing sample_ids: %s" % ", ".join(missing))

    print("labelled %d / %d rows (%d blank)" % (len(human), len(key), blank))
    if bad:
        print("UNRECOGNISED labels (fix these, expected one of %s):" % (sorted(VALID),))
        for b in bad:
            print("  " + b)
    if structural:
        print("STRUCTURAL sheet errors (fix before scoring):")
        for issue in structural:
            print("  " + issue)
    if not human:
        print("\nNothing to score yet. Fill in the human_label column first.")
        if args.out:
            _write_json(
                args.out,
                {
                    "status": "incomplete",
                    "gate_pass": False,
                    "labelled": 0,
                    "total": len(key),
                    "blank": blank,
                    "invalid": bad,
                    "structural_issues": structural,
                },
            )
        return 1

    unsure = [s for s, l in human.items() if l == "unsure"]
    scored = [s for s, l in human.items() if l != "unsure"]
    print("marked 'unsure': %d (%.0f%%)" % (len(unsure), 100.0 * len(unsure) / max(1, len(human))))
    if len(unsure) > 0.2 * len(human):
        print("  ^ >20% unsure means the label scheme may not fit the messages. Say so in the write-up.")
    if not scored:
        print("\nNo non-`unsure` labels are available to score. Gate is BLOCKED.")
        if args.out:
            _write_json(
                args.out,
                {
                    "status": "complete_but_unscorable"
                    if blank == 0 and not bad and not structural
                    else "partial",
                    "gate_pass": False,
                    "labelled": len(human),
                    "scored": 0,
                    "total": len(key),
                    "blank": blank,
                    "invalid": bad,
                    "structural_issues": structural,
                    "unsure": len(unsure),
                },
            )
        return 1

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
    per_condition = []
    for cond in sorted({key[s]["condition"] for s in scored}):
        sub = [s for s in scored if key[s]["condition"] == cond]
        if not sub:
            continue
        hm = float(np.mean([human[s] == key[s]["hidden_target_type"] for s in sub]))
        jm = float(np.mean([key[s]["judge_label"] == key[s]["hidden_target_type"] for s in sub]))
        per_condition.append(
            {
                "condition": cond,
                "human_match_rate": hm,
                "classifier_match_rate": jm,
                "n": len(sub),
            }
        )
        print("%-20s human match=%.3f   classifier match=%.3f   (n=%d)" % (cond, hm, jm, len(sub)))
    print("\nThere is no universal 1/3 chance rate because `other` is a valid")
    print("non-matching label. This small random subsample is a measurement-validity")
    print("check; the point is direction agreement, not its exact effect size.")

    by_condition = {row["condition"]: row for row in per_condition}
    have_primary = "full_history" in by_condition and "no_history" in by_condition
    human_direction = (
        have_primary
        and by_condition["full_history"]["human_match_rate"]
        > by_condition["no_history"]["human_match_rate"]
    )
    classifier_direction = (
        have_primary
        and by_condition["full_history"]["classifier_match_rate"]
        > by_condition["no_history"]["classifier_match_rate"]
    )
    complete = blank == 0 and not bad and not structural and seen == set(key)
    unsure_ok = len(unsure) <= 0.2 * len(human)
    gate_pass = bool(
        complete
        and unsure_ok
        and math.isfinite(kappa)
        and kappa >= 0.60
        and human_direction
        and classifier_direction
    )
    print("\n--- preregistered measurement gate ---")
    print("sheet complete      : %s" % complete)
    print("unsure <= 20%%       : %s" % unsure_ok)
    print("kappa >= 0.60       : %s" % (math.isfinite(kappa) and kappa >= 0.60))
    print("direction agrees    : %s" % (human_direction and classifier_direction))
    print("GATE                : %s" % ("PASS" if gate_pass else "BLOCKED"))

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

    if args.out:
        confusion = {
            hl: {
                jl: sum(1 for x, y in zip(h, j) if x == hl and y == jl)
                for jl in labels
            }
            for hl in labels
        }
        result = {
            "status": "complete" if complete else "partial",
            "gate_pass": gate_pass,
            "sheet": args.sheet,
            "key": key_path,
            "classifier_name": key[scored[0]]["classifier_name"],
            "labelled": len(human),
            "scored": len(scored),
            "total": len(key),
            "blank": blank,
            "invalid": bad,
            "structural_issues": structural,
            "unsure": len(unsure),
            "raw_agreement": agree,
            "cohens_kappa": kappa,
            "confusion_human_rows_classifier_columns": confusion,
            "per_condition": per_condition,
            "human_full_history_advantage": human_direction,
            "classifier_full_history_advantage": classifier_direction,
            "gate_requirements": {
                "complete_sheet": complete,
                "unsure_at_most_20_percent": unsure_ok,
                "cohens_kappa_at_least_0_60": bool(
                    math.isfinite(kappa) and kappa >= 0.60
                ),
                "direction_agreement": bool(
                    human_direction and classifier_direction
                ),
            },
        }
        _write_json(args.out, result)
        print("\nwrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
