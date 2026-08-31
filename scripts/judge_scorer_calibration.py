#!/usr/bin/env python3
"""Apply a second blind machine judge to the target-scorer v2 corpus."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import hashlib
import json
import os
import sys

from src.blind_judge import CodexBlindJudge
from src.logging_utils import read_jsonl
from src.scorer_calibration import cohen_kappa, write_jsonl


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", default="data/calibration/target_scorer_v2_calibration.jsonl"
    )
    parser.add_argument(
        "--out", default="data/calibration/target_scorer_v2_calibration.gpt-5.6-sol.jsonl"
    )
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument(
        "--cache", default="data/calibration/target_scorer_v2_judge_cache.jsonl"
    )
    parser.add_argument(
        "--artifact-dir", default="results/target_scorer_v2/judge_batches"
    )
    parser.add_argument("--codex-executable", default="codex")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)

    rows = list(read_jsonl(args.input))
    if len(rows) != 80:
        raise ValueError("expected the frozen 80-row calibration corpus")
    judge = CodexBlindJudge(
        model=args.model,
        cache_path=args.cache,
        artifact_dir=args.artifact_dir,
        batch_size=args.batch_size,
        seed=args.seed,
        executable=args.codex_executable,
        timeout_s=args.timeout,
    )
    judged = judge.classify_messages(row["message"] for row in rows)
    output = []
    for row in rows:
        enriched = dict(row)
        enriched["second_judge"] = dict(judged[row["message"]])
        enriched["second_judge_label"] = enriched["second_judge"]["primary_strategy"]
        output.append(enriched)
    write_jsonl(args.out, output)
    raw = open(args.out, "rb").read()
    agreement = sum(
        row["reference_label"] == row["second_judge_label"] for row in output
    ) / len(output)
    manifest = {
        "input": args.input,
        "out": args.out,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "judge": judge.describe(),
        "n_rows": len(output),
        "newly_judged": judge.n_judged,
        "cache_hits": judge.n_cached,
        "reference_second_judge_agreement": agreement,
        "reference_second_judge_kappa": cohen_kappa(
            [row["reference_label"] for row in output],
            [row["second_judge_label"] for row in output],
        ),
        "blind_fields_visible_to_judge": ["sample_id", "message"],
        "warning": "Both references are machine measurements; this is not human validation.",
    }
    manifest_path = args.out[:-6] + ".manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print("agreement=%.3f  kappa=%.3f" % (
        manifest["reference_second_judge_agreement"],
        manifest["reference_second_judge_kappa"],
    ))
    print("wrote %s\nwrote %s" % (args.out, manifest_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())

