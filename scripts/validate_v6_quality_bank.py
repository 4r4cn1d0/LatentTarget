#!/usr/bin/env python3
"""Run the frozen blind two-Codex-judge quality gate for the V6 triad pool."""

from __future__ import annotations

from _bootstrap import ROOT
import argparse
import os
import sys
from typing import Iterable, Sequence

from src.blind_judge import (
    _repository_local_path,
    attest_codex_executable,
    canonical_json_sha256,
    enforce_frozen_judge_contract,
    frozen_official_runtime,
    load_frozen_judge_contract,
    publish_exact_json,
    require_v6_judge_protocol_open,
    strict_json_file_identity,
)
from src.file_lock import ExclusiveFileLock
from src.v6_quality_validation import (
    CodexQualityJudge,
    audit_quality_judge_run,
    evaluate_v6_quality_validation,
    quality_judge_contract,
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
    official_contract,
):
    message_list = [str(message) for message in messages]
    judge = CodexQualityJudge(
        model=model,
        cache_path=cache,
        artifact_dir=artifacts,
        batch_size=batch_size,
        seed=seed,
        executable=executable,
        timeout_s=timeout,
        official_contract=official_contract,
    )
    judge.score_messages(message_list)
    replay = audit_quality_judge_run(
        message_list,
        model,
        batch_size,
        seed,
        artifacts,
        cache,
        repository_root=ROOT,
        official_contract=official_contract,
    )
    return judge, replay["result_map"], replay


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", default="data/v6/v6_triad_pool_v1.json")
    parser.add_argument("--primary-model", default="gpt-5.6-sol")
    parser.add_argument("--sensitivity-model", default="gpt-5.6-luna")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261002)
    parser.add_argument("--primary-seed", type=int)
    parser.add_argument("--sensitivity-seed", type=int)
    parser.add_argument("--codex-executable", default="codex")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--out-dir", default="results/v6_design/quality_validation"
    )
    parser.add_argument(
        "--cache-dir", default="data/processed/v6_quality_validation"
    )
    parser.add_argument(
        "--judge-contract",
        default="docs/v6_calibration_protocol.json",
        help=(
            "frozen JSON path (or inline object) binding both models, both "
            "seeds, batch size, prompt version/hash, and rubric hash"
        ),
    )
    return parser


def _run_complete_validation(
    args: argparse.Namespace,
    *,
    primary_seed: int,
    sensitivity_seed: int,
    enforced_contract,
    bank,
    pool_identity,
) -> int:
    """Execute both judges, exact replay, evaluation, and publication."""
    summary_path = os.path.join(args.out_dir, "summary.json")
    # Registered frame, triad, and split metadata are joined only after both
    # blind calls and artifact audits have completed.
    messages = [row["message"] for row in quality_candidate_rows(bank)]
    primary_judge, primary_results, primary_audit = _run_judge(
        messages,
        args.primary_model,
        os.path.join(args.cache_dir, "primary_cache.jsonl"),
        os.path.join(args.out_dir, "primary_batches"),
        args.batch_size,
        primary_seed,
        args.codex_executable,
        args.timeout,
        enforced_contract["official_contract"],
    )
    sensitivity_judge, sensitivity_results, sensitivity_audit = _run_judge(
        messages,
        args.sensitivity_model,
        os.path.join(args.cache_dir, "sensitivity_cache.jsonl"),
        os.path.join(args.out_dir, "sensitivity_batches"),
        args.batch_size,
        sensitivity_seed,
        args.codex_executable,
        args.timeout,
        enforced_contract["official_contract"],
    )

    primary_description = primary_judge.describe()
    sensitivity_description = sensitivity_judge.describe()
    for description in (primary_description, sensitivity_description):
        for field in ("cache_path", "artifact_dir"):
            if field in description:
                description[field] = _repository_local_path(
                    str(description[field]), ROOT
                )
    summary = evaluate_v6_quality_validation(
        bank,
        primary_results,
        sensitivity_results,
        primary_description,
        sensitivity_description,
        primary_audit,
        sensitivity_audit,
    )
    summary["pool_source_path"] = pool_identity["path"]
    summary["pool_source_file_sha256"] = pool_identity["file_sha256"]
    summary["pool_source_canonical_sha256"] = pool_identity[
        "canonical_sha256"
    ]
    summary["judge_contract"] = enforced_contract
    summary["raw_judge_run_manifests"] = {
        "primary": primary_audit["judge_run_manifest"],
        "sensitivity": sensitivity_audit["judge_run_manifest"],
    }
    summary["recomputed_evaluation_sha256"] = canonical_json_sha256(
        {
            key: value
            for key, value in summary.items()
            if key
            not in {
                "pool_source_path",
                "pool_source_file_sha256",
                "pool_source_canonical_sha256",
                "judge_contract",
                "raw_judge_run_manifests",
                "recomputed_evaluation_sha256",
            }
        }
    )
    published = publish_exact_json(summary_path, summary)

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
    print(("wrote" if published else "verified existing") + " %s" % summary_path)
    return 0 if summary["pass"] else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.codex_executable != "codex":
        raise ValueError(
            "official mode forbids --codex-executable overrides; use exactly 'codex'"
        )
    if args.primary_model == args.sensitivity_model:
        raise ValueError("V6 quality judges must use distinct model IDs")
    if args.batch_size < 1:
        raise ValueError("batch size must be positive")
    if args.timeout < 1:
        raise ValueError("timeout must be positive")
    primary_seed = args.seed if args.primary_seed is None else args.primary_seed
    sensitivity_seed = (
        args.seed + 1 if args.sensitivity_seed is None else args.sensitivity_seed
    )
    out_dir = (
        args.out_dir
        if os.path.isabs(args.out_dir)
        else os.path.join(ROOT, args.out_dir)
    )
    cache_dir = (
        args.cache_dir
        if os.path.isabs(args.cache_dir)
        else os.path.join(ROOT, args.cache_dir)
    )
    canonical_out_dir = _repository_local_path(out_dir, ROOT)
    canonical_cache_dir = _repository_local_path(cache_dir, ROOT)

    bank_path = (
        args.bank if os.path.isabs(args.bank) else os.path.join(ROOT, args.bank)
    )
    bank, pool_identity = strict_json_file_identity(
        bank_path,
        repository_root=ROOT,
        label="frozen V6 quality candidate pool",
    )
    if not isinstance(bank, dict):
        raise ValueError("frozen V6 quality candidate pool is not an object")
    quality_candidate_rows(bank)

    canonical_contract_path = os.path.realpath(
        os.path.join(ROOT, "docs", "v6_calibration_protocol.json")
    )
    contract_input = (
        str(args.judge_contract)
        if os.path.isabs(str(args.judge_contract))
        else os.path.join(ROOT, str(args.judge_contract))
    )
    if os.path.realpath(contract_input) != canonical_contract_path:
        raise ValueError(
            "official V6 judging requires the canonical repository protocol"
        )
    contract_payload = load_frozen_judge_contract(
        canonical_contract_path, repository_root=ROOT
    )
    require_v6_judge_protocol_open(contract_payload)
    runtime_attestation = attest_codex_executable(
        args.codex_executable,
        frozen_official_runtime(contract_payload),
    )

    enforced_contract = enforce_frozen_judge_contract(
        contract_payload,
        "quality",
        {
            "primary_model": args.primary_model,
            "sensitivity_model": args.sensitivity_model,
            "primary_seed": primary_seed,
            "sensitivity_seed": sensitivity_seed,
            "batch_size": args.batch_size,
            "canonical_out_dir": canonical_out_dir,
            "canonical_cache_dir": canonical_cache_dir,
            "candidate_pool": pool_identity,
            "codex_runtime": runtime_attestation,
        },
        quality_judge_contract(),
    )

    args.out_dir = out_dir
    args.cache_dir = cache_dir
    args.bank = bank_path
    args.codex_executable = runtime_attestation["resolved_executable"]
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.cache_dir, exist_ok=True)
    lock_path = os.path.join(args.out_dir, ".quality-validation.lock")
    with ExclusiveFileLock(
        lock_path,
        label="V6 quality validation complete run",
        metadata={"contract_sha256": enforced_contract["contract_sha256"]},
    ):
        return _run_complete_validation(
            args,
            primary_seed=primary_seed,
            sensitivity_seed=sensitivity_seed,
            enforced_contract=enforced_contract,
            bank=bank,
            pool_identity=pool_identity,
        )


if __name__ == "__main__":
    sys.exit(main())
