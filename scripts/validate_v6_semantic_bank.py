#!/usr/bin/env python3
"""Run the frozen blind two-machine-judge semantic gate for a V6 pool."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import hashlib
import json
import os
import sys
from typing import Iterable, Sequence

from src.blind_judge import CodexBlindJudge, audit_codex_artifacts
from src.v6_semantic_validation import (
    evaluate_v6_semantic_validation,
    load_v6_semantic_pool,
    semantic_candidate_rows,
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
    """Run one blind judge with message text as the only caller-supplied data."""
    judge = CodexBlindJudge(
        model=model,
        cache_path=cache,
        artifact_dir=artifacts,
        batch_size=batch_size,
        seed=seed,
        executable=executable,
        timeout_s=timeout,
    )
    results = judge.classify_messages(messages)
    return judge, results, audit_codex_artifacts(artifacts)


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
    parser.add_argument("--seed", type=int, default=20261001)
    parser.add_argument("--codex-executable", default="codex")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--out-dir", default="results/v6_design/semantic_validation"
    )
    parser.add_argument(
        "--cache-dir", default="data/processed/v6_semantic_validation"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.primary_model == args.sensitivity_model:
        raise ValueError("V6 semantic judges must use distinct model IDs")
    if args.batch_size < 1:
        raise ValueError("batch size must be positive")
    if args.timeout < 1:
        raise ValueError("timeout must be positive")

    summary_path = os.path.join(args.out_dir, "summary.json")
    if os.path.exists(summary_path):
        raise FileExistsError("refusing to overwrite %s" % summary_path)

    pool = load_v6_semantic_pool(args.bank)
    rows = semantic_candidate_rows(pool)
    blind_messages = [row["message"] for row in rows]
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.cache_dir, exist_ok=True)
    primary = _run_judge(
        blind_messages,
        args.primary_model,
        os.path.join(args.cache_dir, "primary_cache.jsonl"),
        os.path.join(args.out_dir, "primary_batches"),
        args.batch_size,
        args.seed,
        args.codex_executable,
        args.timeout,
    )
    sensitivity = _run_judge(
        blind_messages,
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
    summary = evaluate_v6_semantic_validation(
        pool,
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
    kappa = summary["interjudge_kappa"]
    kappa_text = "undefined" if kappa is None else "%.3f" % kappa
    print(
        "primary accuracy %.3f; sensitivity %.3f; kappa %s"
        % (
            summary["primary_metrics"]["accuracy"],
            summary["sensitivity_metrics"]["accuracy"],
            kappa_text,
        )
    )
    print(
        "eligible triads: development %d; heldout %d"
        % (
            summary["eligible_counts"]["development"],
            summary["eligible_counts"]["heldout"],
        )
    )
    for name, passed in summary["gates"].items():
        print("  %-44s %s" % (name, "PASS" if passed else "FAIL"))
    print("wrote %s" % summary_path)
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
