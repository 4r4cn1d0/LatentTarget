#!/usr/bin/env python3
"""Run the frozen blind two-Codex-judge quality gate for the V6 triad pool."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import hashlib
import json
import os
import sys
from typing import Iterable, Sequence

from src.v6_quality_validation import (
    CodexQualityJudge,
    audit_quality_artifacts,
    evaluate_v6_quality_validation,
    load_v6_quality_pool,
    quality_candidate_rows,
)


def _run_judge(
    messages: Iterable[str],
    model: str,
    cache: str,
    artifacts: str,
    batch_size: int,
    seed: int,
    executable: str,
    timeout: int,
):
    judge = CodexQualityJudge(
        model=model,
        cache_path=cache,
        artifact_dir=artifacts,
        batch_size=batch_size,
        seed=seed,
        executable=executable,
        timeout_s=timeout,
    )
    results = judge.score_messages(messages)
    return judge, results, audit_quality_artifacts(artifacts)


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", default="data/v6/v6_triad_pool_v1.json")
    parser.add_argument("--primary-model", default="gpt-5.6-sol")
    parser.add_argument("--sensitivity-model", default="gpt-5.6-luna")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261002)
    parser.add_argument("--codex-executable", default="codex")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--out-dir", default="results/v6_design/quality_validation"
    )
    parser.add_argument(
        "--cache-dir", default="data/processed/v6_quality_validation"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.primary_model == args.sensitivity_model:
        raise ValueError("V6 quality judges must use distinct model IDs")
    if args.batch_size < 1:
        raise ValueError("batch size must be positive")
    if args.timeout < 1:
        raise ValueError("timeout must be positive")

    summary_path = os.path.join(args.out_dir, "summary.json")
    if os.path.exists(summary_path):
        raise FileExistsError("refusing to overwrite %s" % summary_path)

    bank = load_v6_quality_pool(args.bank)
    # This is the only object passed into either judge call. Registered frame,
    # triad, and split metadata are first joined in the evaluator below, after
    # both calls and artifact audits have completed.
    messages = [row["message"] for row in quality_candidate_rows(bank)]
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.cache_dir, exist_ok=True)

    primary_judge, primary_results, primary_audit = _run_judge(
        messages,
        args.primary_model,
        os.path.join(args.cache_dir, "primary_cache.jsonl"),
        os.path.join(args.out_dir, "primary_batches"),
        args.batch_size,
        args.seed,
        args.codex_executable,
        args.timeout,
    )
    sensitivity_judge, sensitivity_results, sensitivity_audit = _run_judge(
        messages,
        args.sensitivity_model,
        os.path.join(args.cache_dir, "sensitivity_cache.jsonl"),
        os.path.join(args.out_dir, "sensitivity_batches"),
        args.batch_size,
        args.seed + 1,
        args.codex_executable,
        args.timeout,
    )

    summary = evaluate_v6_quality_validation(
        bank,
        primary_results,
        sensitivity_results,
        primary_judge.describe(),
        sensitivity_judge.describe(),
        primary_audit,
        sensitivity_audit,
    )
    summary["pool_source_path"] = args.bank
    summary["pool_source_file_sha256"] = _file_sha256(args.bank)
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False, allow_nan=False)

    print("PASS" if summary["pass"] else "FAIL")
    print(
        "both-judge candidate pass rate %.3f; maximum triad gaps %.3f / %.3f"
        % (
            summary["both_judges_candidate_pass_rate"],
            summary["primary_metrics"][
                "maximum_within_triad_overall_quality_gap"
            ],
            summary["sensitivity_metrics"][
                "maximum_within_triad_overall_quality_gap"
            ],
        )
    )
    for name, passed in summary["gates"].items():
        print("  %-48s %s" % (name, "PASS" if passed else "FAIL"))
    print("wrote %s" % summary_path)
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
