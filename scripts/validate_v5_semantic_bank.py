#!/usr/bin/env python3
"""Run the frozen blind two-machine-judge semantic gate for a V5 pool."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

from src.blind_judge import CodexBlindJudge, audit_codex_artifacts
from src.controlled_v5_messages import V5MessageBank
from src.v5_semantic_validation import (
    evaluate_v5_semantic_validation,
    semantic_candidate_rows,
)


def _run_judge(rows, model, cache, artifacts, batch_size, seed, executable, timeout):
    judge = CodexBlindJudge(
        model=model,
        cache_path=cache,
        artifact_dir=artifacts,
        batch_size=batch_size,
        seed=seed,
        executable=executable,
        timeout_s=timeout,
    )
    results = judge.classify_messages(row["message"] for row in rows)
    return judge, results, audit_codex_artifacts(artifacts)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", default="data/v5/v5_candidate_pool_v1.json")
    parser.add_argument("--primary-model", default="gpt-5.6-sol")
    parser.add_argument("--sensitivity-model", default="gpt-5.6-luna")
    parser.add_argument("--batch-size", type=int, default=21)
    parser.add_argument("--seed", type=int, default=20261001)
    parser.add_argument("--codex-executable", default="codex")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--out-dir", default="results/v5_design/semantic_validation"
    )
    parser.add_argument(
        "--cache-dir", default="data/processed/v5_semantic_validation"
    )
    args = parser.parse_args(argv)
    if args.primary_model == args.sensitivity_model:
        raise ValueError("V5 semantic judges must use distinct model IDs")
    summary_path = os.path.join(args.out_dir, "summary.json")
    if os.path.exists(summary_path):
        raise FileExistsError("refusing to overwrite %s" % summary_path)
    bank = V5MessageBank.load(args.bank)
    rows = semantic_candidate_rows(bank)
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.cache_dir, exist_ok=True)
    primary = _run_judge(
        rows,
        args.primary_model,
        os.path.join(args.cache_dir, "primary_cache.jsonl"),
        os.path.join(args.out_dir, "primary_batches"),
        args.batch_size,
        args.seed,
        args.codex_executable,
        args.timeout,
    )
    sensitivity = _run_judge(
        rows,
        args.sensitivity_model,
        os.path.join(args.cache_dir, "sensitivity_cache.jsonl"),
        os.path.join(args.out_dir, "sensitivity_batches"),
        args.batch_size,
        args.seed + 1,
        args.codex_executable,
        args.timeout,
    )
    primary_judge, primary_results, primary_audit = primary
    sensitivity_judge, sensitivity_results, sensitivity_audit = sensitivity
    summary = evaluate_v5_semantic_validation(
        bank,
        primary_results,
        sensitivity_results,
        primary_judge.describe(),
        sensitivity_judge.describe(),
        primary_audit,
        sensitivity_audit,
    )
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False, allow_nan=False)
    print("PASS" if summary["pass"] else "FAIL")
    print(
        "primary accuracy %.3f; sensitivity %.3f; kappa %.3f"
        % (
            summary["primary_metrics"]["accuracy"],
            summary["sensitivity_metrics"]["accuracy"],
            summary["interjudge_kappa"],
        )
    )
    for name, passed in summary["gates"].items():
        print("  %-44s %s" % (name, "PASS" if passed else "FAIL"))
    print("wrote %s" % summary_path)
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
