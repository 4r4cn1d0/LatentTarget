#!/usr/bin/env python3
"""Run final V6 target-free pool screening or selected-bank validation."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

from src.controlled_v6_messages import V6TriadBank
from src.hf_provider import HuggingFaceProvider
from src.v6_calibration import (
    V6_POOL_MODE,
    V6_VALIDATION_MODE,
    audit_v6_pool_schedule,
    audit_v6_validation_schedule,
    build_v6_pool_schedule,
    build_v6_validation_schedule,
    file_sha256,
    run_v6_target_free_calibration,
)
from src.v6_protocol_gate import (
    audit_v6_calibration_plan,
    audit_v6_prevalidation_checkpoint,
    v6_artifact_reference,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True)
    parser.add_argument(
        "--protocol-spec",
        default=os.path.join(_bootstrap.ROOT, "docs", "v6_calibration_protocol.json"),
    )
    parser.add_argument(
        "--mode", choices=(V6_POOL_MODE, V6_VALIDATION_MODE), required=True
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--revision", default=None)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", default="data/calibration")
    parser.add_argument("--episode-blocks", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--dtype", default=None)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--pre-validation-checkpoint",
        default=None,
        help="required immutable artifact graph for selected-bank validation",
    )
    args = parser.parse_args(argv)

    with open(args.protocol_spec, "r", encoding="utf-8") as handle:
        spec = json.load(handle)
    schedule_key = (
        "pool_screening_schedule"
        if args.mode == V6_POOL_MODE
        else "selected_bank_validation_schedule"
    )
    schedule_spec = spec[schedule_key]
    official_run_id = schedule_spec.get("official_run_id")
    if not isinstance(official_run_id, str) or args.run_id != official_run_id:
        raise ValueError(
            "V6 run-id must equal the single official run-id frozen in the protocol"
        )
    generation = spec["generation"]
    primary_model = spec["primary_model"]
    model = args.model or primary_model["id"]
    revision = args.revision or primary_model["revision"]
    seed = args.seed if args.seed is not None else int(schedule_spec["seed"])
    # V6 enumerates complete triad × scenario × permutation schedules, so an
    # episode-block count is deliberately absent (JSON null).  Retain the CLI
    # option only as a rejected compatibility surface; it must not alter the
    # frozen schedule.
    episode_blocks = args.episode_blocks
    dtype = args.dtype or generation["dtype"]
    bank = V6TriadBank.load(args.bank)
    prevalidation_checkpoint = None
    prevalidation_reference = None
    if args.mode == V6_VALIDATION_MODE:
        if args.pre_validation_checkpoint is None:
            raise ValueError(
                "selected-bank validation requires a frozen pre-validation checkpoint"
            )
        with open(args.pre_validation_checkpoint, "r", encoding="utf-8") as handle:
            prevalidation_checkpoint = json.load(handle)
        prevalidation_audit = audit_v6_prevalidation_checkpoint(
            prevalidation_checkpoint, _bootstrap.ROOT
        )
        if not prevalidation_audit["pass"]:
            failed = sorted(
                name
                for name, passed in prevalidation_audit["checks"].items()
                if not passed
            )
            raise ValueError(
                "V6 pre-validation checkpoint audit failed: %s"
                % ", ".join(failed)
            )
        if prevalidation_audit.get("pending_bank_sha256") != bank.sha256():
            raise ValueError("validation bank differs from the frozen pending bank")
        prevalidation_reference = v6_artifact_reference(
            args.pre_validation_checkpoint, _bootstrap.ROOT
        )
    elif args.pre_validation_checkpoint is not None:
        raise ValueError("pool screening must not consume a validation checkpoint")
    if args.mode == V6_POOL_MODE and not bank.payload.get(
        "candidate_text_authored_before_v6_focal_calibration"
    ):
        raise ValueError("pool screening requires a bank authored before outcomes")
    if args.mode == V6_VALIDATION_MODE and bank.payload.get("status") != (
        "selected_bank_pending_no_history_validation"
    ):
        raise ValueError("selected-bank validation requires a pending selected bank")
    provider = HuggingFaceProvider(
        model=model,
        revision=revision,
        temperature=generation["temperature"],
        max_tokens=generation["max_tokens"],
        device=args.device,
        dtype=dtype,
        capture=False,
        seed=seed,
        enable_thinking=generation["enable_thinking"],
        top_p=generation["top_p"],
        top_k=generation["top_k"],
        constrained_choices=tuple(generation["constrained_choices"]),
    )
    plan_audit = audit_v6_calibration_plan(
        spec=spec,
        bank=bank,
        provider=provider.describe(),
        mode=args.mode,
        seed=seed,
        n_episode_blocks=episode_blocks,
        repository_root=_bootstrap.ROOT,
        prevalidation_checkpoint=prevalidation_checkpoint,
        run_id=args.run_id,
    )
    if not plan_audit["pass"]:
        failed = sorted(
            name for name, passed in plan_audit["checks"].items() if not passed
        )
        raise ValueError(
            "planned V6 calibration differs from frozen protocol: %s"
            % ", ".join(failed)
        )
    if args.mode == V6_POOL_MODE:
        schedule = build_v6_pool_schedule(bank, seed=seed)
        audit = audit_v6_pool_schedule(schedule, bank)
    else:
        schedule = build_v6_validation_schedule(bank, seed=seed)
        audit = audit_v6_validation_schedule(schedule, bank)
    print("LatentTarget V6 target-free calibration")
    print("  mode: %s" % args.mode)
    print("  model: %s @ %s" % (model, revision))
    print("  bank SHA-256: %s" % bank.sha256())
    print("  prompts: %d; target/history: absent" % len(schedule))
    print("  schedule audit: %s" % ("PASS" if audit["pass"] else "FAIL"))
    print("  frozen calibration protocol: PASS")
    if not audit["pass"]:
        raise ValueError("V6 calibration schedule audit failed")
    if args.dry_run:
        print("DRY RUN PASSED: no model loaded and no outcomes generated")
        return 0
    result = run_v6_target_free_calibration(
        bank=bank,
        provider=provider,
        run_id=args.run_id,
        out_dir=args.out_dir,
        seed=seed,
        mode=args.mode,
        n_episode_blocks=episode_blocks,
        provenance={
            "protocol_path": os.path.abspath(args.protocol_spec),
            "protocol_file_sha256": file_sha256(args.protocol_spec),
            "plan_audit": plan_audit,
            **(
                {"prevalidation_checkpoint": prevalidation_reference}
                if prevalidation_reference is not None
                else {}
            ),
        },
    )
    print("wrote %d records to %s" % (len(result["records"]), result["log_path"]))
    print("manifest: %s" % result["manifest_path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
