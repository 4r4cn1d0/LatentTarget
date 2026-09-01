#!/usr/bin/env python3
"""Run target-free V5 no-history pool calibration or selected-bank validation."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

from src.controlled_v5_messages import V5MessageBank
from src.hf_provider import HuggingFaceProvider
from src.v5_calibration import (
    audit_v5_calibration_schedule,
    build_v5_calibration_schedule,
    run_v5_no_history_calibration,
)
from src.v5_protocol_gate import audit_v5_calibration_plan, file_sha256


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True)
    parser.add_argument(
        "--protocol-spec",
        default=os.path.join(_bootstrap.ROOT, "docs", "v5_calibration_protocol.json"),
    )
    parser.add_argument(
        "--mode",
        choices=("pool_calibration", "selected_bank_validation"),
        required=True,
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--revision", default=None)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", default="data/calibration")
    parser.add_argument("--episode-blocks", type=int, default=None)
    parser.add_argument("--rounds", type=int, default=None)
    parser.add_argument("--heldout-start-round", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--dtype", default=None)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    with open(args.protocol_spec, "r", encoding="utf-8") as handle:
        protocol_spec = json.load(handle)
    schedule_key = (
        "pool_calibration_schedule"
        if args.mode == "pool_calibration"
        else "selected_bank_validation_schedule"
    )
    schedule_spec = protocol_spec[schedule_key]
    generation = protocol_spec["generation"]
    primary_model = protocol_spec["primary_model"]
    args.model = args.model or primary_model["id"]
    args.revision = args.revision or primary_model["revision"]
    args.episode_blocks = (
        args.episode_blocks
        if args.episode_blocks is not None
        else schedule_spec["n_episode_blocks"]
    )
    args.rounds = args.rounds if args.rounds is not None else schedule_spec["n_rounds"]
    args.heldout_start_round = (
        args.heldout_start_round
        if args.heldout_start_round is not None
        else schedule_spec["heldout_start_round"]
    )
    args.seed = args.seed if args.seed is not None else schedule_spec["seed"]
    args.dtype = args.dtype or generation["dtype"]

    bank = V5MessageBank.load(args.bank)
    if args.mode == "pool_calibration" and not bank.payload.get(
        "created_before_v5_focal_calibration"
    ):
        raise ValueError("pool calibration requires a bank authored before outcomes")
    if args.mode == "selected_bank_validation" and bank.payload.get("status") != (
        "selected_bank_pending_no_history_validation"
    ):
        raise ValueError("selected-bank validation requires a pending selected bank")
    provider = HuggingFaceProvider(
        model=args.model,
        revision=args.revision,
        temperature=generation["temperature"],
        max_tokens=generation["max_tokens"],
        device=args.device,
        dtype=args.dtype,
        capture=False,
        seed=args.seed,
        enable_thinking=generation["enable_thinking"],
        top_p=generation["top_p"],
        top_k=generation["top_k"],
        constrained_choices=tuple(generation["constrained_choices"]),
    )
    plan_audit = audit_v5_calibration_plan(
        spec=protocol_spec,
        bank=bank,
        provider=provider.describe(),
        mode=args.mode,
        n_episode_blocks=args.episode_blocks,
        n_rounds=args.rounds,
        heldout_start_round=args.heldout_start_round,
        seed=args.seed,
        repository_root=_bootstrap.ROOT,
    )
    if not plan_audit["pass"]:
        failed = sorted(
            name for name, passed in plan_audit["checks"].items() if not passed
        )
        raise ValueError(
            "planned calibration differs from frozen protocol: %s"
            % ", ".join(failed)
        )
    schedule = build_v5_calibration_schedule(
        bank,
        n_episode_blocks=args.episode_blocks,
        n_rounds=args.rounds,
        heldout_start_round=args.heldout_start_round,
        seed=args.seed,
    )
    audit = audit_v5_calibration_schedule(schedule, bank)
    print("LatentTarget V5 target-free calibration")
    print("  mode: %s" % args.mode)
    print("  model: %s @ %s" % (args.model, args.revision))
    print("  bank SHA-256: %s" % bank.sha256())
    print("  prompts: %d; target/history: absent" % len(schedule))
    print("  schedule audit: %s" % ("PASS" if audit["pass"] else "FAIL"))
    print("  frozen calibration protocol: PASS")
    if not audit["pass"]:
        raise ValueError("calibration schedule audit failed")
    if args.dry_run:
        print("DRY RUN PASSED: no model loaded and no outcomes generated")
        return 0

    result = run_v5_no_history_calibration(
        bank=bank,
        provider=provider,
        run_id=args.run_id,
        out_dir=args.out_dir,
        n_episode_blocks=args.episode_blocks,
        n_rounds=args.rounds,
        heldout_start_round=args.heldout_start_round,
        seed=args.seed,
        mode=args.mode,
        provenance={
            "protocol_path": os.path.abspath(args.protocol_spec),
            "protocol_file_sha256": file_sha256(args.protocol_spec),
            "plan_audit": plan_audit,
        },
    )
    print("wrote %d records to %s" % (len(result["records"]), result["log_path"]))
    print("manifest: %s" % result["manifest_path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
