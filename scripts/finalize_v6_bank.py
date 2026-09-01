#!/usr/bin/env python3
"""Apply the one independent V6 validation gate and finalize only on pass."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

from src.controlled_v6_messages import V6TriadBank
from src.logging_utils import read_jsonl
from src.v6_calibration import (
    V6_VALIDATION_MODE,
    audit_v6_calibration_run,
    evaluate_v6_bank_validation,
    file_sha256,
    finalize_validated_v6_bank,
)
from src.v6_protocol_gate import (
    audit_v6_prevalidation_checkpoint,
    build_v6_final_checkpoint,
    v6_artifact_reference,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pending-bank", required=True)
    parser.add_argument("--pre-validation-checkpoint", required=True)
    parser.add_argument("--validation-log", required=True)
    parser.add_argument("--validation-manifest", default=None)
    parser.add_argument("--validation-out", required=True)
    parser.add_argument("--final-bank-out", required=True)
    parser.add_argument("--final-checkpoint-out", required=True)
    args = parser.parse_args(argv)
    for path in (
        args.validation_out,
        args.final_bank_out,
        args.final_checkpoint_out,
    ):
        if os.path.exists(path):
            raise FileExistsError("refusing to overwrite %s" % path)
    pending = V6TriadBank.load(args.pending_bank)
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
            "V6 pre-validation checkpoint audit failed: %s" % ", ".join(failed)
        )
    if prevalidation_audit.get("pending_bank_sha256") != pending.sha256():
        raise ValueError("pending bank differs from the pre-validation checkpoint")
    records = list(read_jsonl(args.validation_log))
    manifest_path = args.validation_manifest or args.validation_log.replace(
        ".jsonl", ".manifest.json"
    )
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    expected_checkpoint_ref = v6_artifact_reference(
        args.pre_validation_checkpoint, _bootstrap.ROOT
    )
    if manifest.get("frozen_protocol", {}).get(
        "prevalidation_checkpoint"
    ) != expected_checkpoint_ref:
        raise ValueError(
            "V6 validation manifest is not bound to the pre-validation checkpoint"
        )
    if manifest.get("run_id") != prevalidation_checkpoint.get(
        "official_run_ids", {}
    ).get("selected_bank_validation"):
        raise ValueError("V6 validation manifest has a non-official run-id")
    run_audit = audit_v6_calibration_run(
        records, manifest, pending, V6_VALIDATION_MODE
    )
    if not run_audit["pass"]:
        failed = sorted(
            name for name, passed in run_audit["checks"].items() if not passed
        )
        raise ValueError(
            "V6 validation artifact audit failed: %s" % ", ".join(failed)
        )
    if file_sha256(args.validation_log) != manifest.get("log_file_sha256"):
        raise ValueError("V6 validation log hash differs from its manifest")
    validation = evaluate_v6_bank_validation(records, pending)
    validation["calibration_run_audit"] = run_audit
    validation["validation_manifest_file_sha256"] = file_sha256(manifest_path)
    validation["validation_log_file_sha256"] = file_sha256(args.validation_log)
    parent = os.path.dirname(args.validation_out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.validation_out, "w", encoding="utf-8") as handle:
        json.dump(validation, handle, indent=2, allow_nan=False)
    if not validation["pass"]:
        print("V6 SELECTED BANK VALIDATION FAILED; terminal instrument stop")
        return 2
    final_payload = finalize_validated_v6_bank(pending.payload, validation)
    parent = os.path.dirname(args.final_bank_out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.final_bank_out, "w", encoding="utf-8") as handle:
        json.dump(final_payload, handle, indent=2, allow_nan=False)
    final_checkpoint = build_v6_final_checkpoint(
        prevalidation_checkpoint_path=args.pre_validation_checkpoint,
        validation_summary_path=args.validation_out,
        validation_log_path=args.validation_log,
        validation_manifest_path=manifest_path,
        validated_bank_path=args.final_bank_out,
        repository_root=_bootstrap.ROOT,
    )
    parent = os.path.dirname(args.final_checkpoint_out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.final_checkpoint_out, "w", encoding="utf-8") as handle:
        json.dump(final_checkpoint, handle, indent=2, allow_nan=False)
    print("V6 selected bank validation: PASS")
    print("wrote finalized bank to %s" % args.final_bank_out)
    print("wrote final checkpoint to %s" % args.final_checkpoint_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
