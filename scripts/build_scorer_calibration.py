#!/usr/bin/env python3
"""Build the fixed 80-message, outcome-free target-scorer v2 corpus."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import hashlib
import json
import os
import sys
from collections import Counter

from src.logging_utils import read_jsonl
from src.scorer_calibration import (
    CALIBRATION_SEED,
    CALIBRATION_VERSION,
    build_calibration_rows,
    write_jsonl,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--existing-log",
        default="data/processed/qwen38_27b_gonogo_20260826.codex-judge.jsonl",
    )
    parser.add_argument(
        "--out", default="data/calibration/target_scorer_v2_calibration.jsonl"
    )
    parser.add_argument("--seed", type=int, default=CALIBRATION_SEED)
    args = parser.parse_args(argv)

    rows = build_calibration_rows(read_jsonl(args.existing_log), seed=args.seed)
    write_jsonl(args.out, rows)
    raw = open(args.out, "rb").read()
    counts = Counter((row["reference_label"], row["split"]) for row in rows)
    source_counts = Counter(row["source"] for row in rows)
    manifest = {
        "calibration_version": CALIBRATION_VERSION,
        "seed": args.seed,
        "source_log": args.existing_log,
        "out": args.out,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "n_rows": len(rows),
        "counts_by_label_split": {
            "%s/%s" % key: value for key, value in sorted(counts.items())
        },
        "counts_by_source": dict(sorted(source_counts.items())),
        "information_excluded": [
            "target choice",
            "target probability",
            "hidden target type",
            "condition",
            "round",
            "scenario",
        ],
        "warning": (
            "Reference labels are machine-derived, not human gold labels. Existing "
            "messages use the blind GPT judge label; controlled messages use their "
            "prewritten intended construct."
        ),
    }
    manifest_path = args.out[:-6] + ".manifest.json"
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print("wrote %s (%d rows; sha256 %s)" % (args.out, len(rows), manifest["sha256"]))
    print("wrote %s" % manifest_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

