#!/usr/bin/env python3
"""Evaluate the frozen semantic v2 scorer on dev and sealed held-out messages."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

from config import ALL_LABELS, TargetScorerConfig
from src.logging_utils import read_jsonl
from src.scorer_calibration import cohen_kappa, confusion_metrics, write_jsonl
from src.target_simulator import make_persuasion_scorer


def _prediction(scores) -> str:
    values = dict(scores.raw_scores)
    if set(values) != set(ALL_LABELS):
        values["other"] = max(0.0, 1.0 - sum(scores[label] for label in ALL_LABELS[:3]))
    return max(ALL_LABELS, key=lambda label: (values[label], -ALL_LABELS.index(label)))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="data/calibration/target_scorer_v2_calibration.gpt-5.6-sol.jsonl",
    )
    parser.add_argument(
        "--out", default="data/calibration/target_scorer_v2_predictions.jsonl"
    )
    parser.add_argument(
        "--summary", default="results/target_scorer_v2/calibration_summary.json"
    )
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dtype", default="float16")
    args = parser.parse_args(argv)

    rows = list(read_jsonl(args.input))
    if len(rows) != 80:
        raise ValueError("expected the frozen 80-row calibration corpus")
    cfg = TargetScorerConfig(
        kind="semantic_nli_v2", device=args.device, dtype=args.dtype
    )
    scorer = make_persuasion_scorer(cfg)
    output = []
    for index, row in enumerate(rows, start=1):
        scores = scorer.score(row["message"])
        enriched = dict(row)
        enriched["semantic_scores"] = scores.as_dict()
        enriched["prediction"] = _prediction(scores)
        output.append(enriched)
        if index % 10 == 0:
            print("scored %d/%d" % (index, len(rows)), flush=True)
    write_jsonl(args.out, output)

    by_split = {
        split: confusion_metrics([row for row in output if row["split"] == split])
        for split in ("dev", "test")
    }
    hard_negatives = [
        row for row in output
        if row["split"] == "test" and "expertise_hard_negative" in row["design_tags"]
    ]
    expertise_fp_rate = (
        sum(row["prediction"] == "expertise" for row in hard_negatives) / len(hard_negatives)
        if hard_negatives else None
    )
    test = by_split["test"]
    gates = {
        "held_out_macro_f1_at_least_0.75": test["macro_f1"] >= 0.75,
        "all_held_out_class_f1_at_least_0.60": all(
            test["per_class"][label]["f1"] >= 0.60 for label in ALL_LABELS
        ),
        "held_out_fairness_recall_at_least_0.70": (
            test["per_class"]["fairness"]["recall"] >= 0.70
        ),
        "held_out_expertise_hard_negative_fp_at_most_0.15": (
            expertise_fp_rate is not None and expertise_fp_rate <= 0.15
        ),
    }
    payload = {
        "status": "machine-only calibration; not human validation",
        "scorer": scorer.describe(),
        "input": args.input,
        "predictions": args.out,
        "metrics": by_split,
        "held_out_expertise_hard_negatives_n": len(hard_negatives),
        "held_out_expertise_hard_negative_fp_rate": expertise_fp_rate,
        "gates": gates,
        "gate_pass": all(gates.values()),
        "test_opened_once_after_scorer_configuration_was_frozen": True,
        "warning": (
            "The original human gate remains unmet. Passing these gates licenses "
            "only an exploratory machine-validated experiment."
        ),
    }
    if all("second_judge_label" in row for row in output):
        payload["reference_second_judge"] = {
            "agreement": sum(
                row["reference_label"] == row["second_judge_label"] for row in output
            ) / len(output),
            "kappa": cohen_kappa(
                [row["reference_label"] for row in output],
                [row["second_judge_label"] for row in output],
            ),
            "scorer_metrics_dev": confusion_metrics(
                [row for row in output if row["split"] == "dev"],
                truth_key="second_judge_label",
            ),
            "scorer_metrics_test": confusion_metrics(
                [row for row in output if row["split"] == "test"],
                truth_key="second_judge_label",
            ),
        }
    os.makedirs(os.path.dirname(args.summary), exist_ok=True)
    with open(args.summary, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print("held-out macro-F1=%.3f  fairness recall=%.3f  hard-negative FP=%s" % (
        test["macro_f1"],
        test["per_class"]["fairness"]["recall"],
        "%.3f" % expertise_fp_rate if expertise_fp_rate is not None else "n/a",
    ))
    print("GATE: %s" % ("PASS" if payload["gate_pass"] else "FAIL"))
    print("wrote %s\nwrote %s" % (args.out, args.summary))
    return 0 if payload["gate_pass"] else 2


if __name__ == "__main__":
    sys.exit(main())

