#!/usr/bin/env python3
"""Evaluate no-history validation and finalize a V5 selected bank only on pass."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

from src.controlled_v5_messages import V5MessageBank
from src.logging_utils import read_jsonl
from src.v5_calibration import (
    audit_v5_calibration_run,
    evaluate_v5_bank_validation,
    finalize_validated_v5_bank,
)
from src.v5_protocol_gate import file_sha256


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pending-bank", required=True)
    parser.add_argument("--validation-log", required=True)
    parser.add_argument("--validation-manifest", default=None)
    parser.add_argument("--validation-out", required=True)
    parser.add_argument("--final-bank-out", required=True)
    args = parser.parse_args(argv)
    for path in (args.validation_out, args.final_bank_out):
        if os.path.exists(path):
            raise FileExistsError("refusing to overwrite %s" % path)
    pending = V5MessageBank.load(args.pending_bank)
    records = list(read_jsonl(args.validation_log))
    manifest_path = args.validation_manifest or args.validation_log.replace(
        ".jsonl", ".manifest.json"
    )
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    run_audit = audit_v5_calibration_run(
        records, manifest, pending, "selected_bank_validation"
    )
    if not run_audit["pass"]:
        failed = sorted(
            name for name, passed in run_audit["checks"].items() if not passed
        )
        raise ValueError(
            "selected-bank validation artifact audit failed: %s" % ", ".join(failed)
        )
    if file_sha256(args.validation_log) != manifest.get("log_file_sha256"):
        raise ValueError("selected-bank validation log hash differs from its manifest")
    validation = evaluate_v5_bank_validation(records, pending)
    validation["calibration_run_audit"] = run_audit
    validation["validation_manifest_file_sha256"] = file_sha256(manifest_path)
    validation["validation_log_file_sha256"] = file_sha256(args.validation_log)
    parent = os.path.dirname(args.validation_out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.validation_out, "w", encoding="utf-8") as handle:
        json.dump(validation, handle, indent=2)
    if not validation["pass"]:
        print("SELECTED BANK VALIDATION FAILED; confirmatory run remains blocked")
        return 2
    final_payload = finalize_validated_v5_bank(pending.payload, validation)
    parent = os.path.dirname(args.final_bank_out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.final_bank_out, "w", encoding="utf-8") as handle:
        json.dump(final_payload, handle, indent=2)
    print("selected bank validation: PASS")
    print("wrote finalized bank to %s" % args.final_bank_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
