#!/usr/bin/env python3
"""Select a V5 bank from blind-semantic and target-free focal calibration data."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

from src.controlled_v5_messages import V5MessageBank
from src.logging_utils import read_jsonl
from src.v5_calibration import audit_v5_calibration_run, select_v5_bank
from src.v5_protocol_gate import file_sha256


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", required=True)
    parser.add_argument("--calibration-log", required=True)
    parser.add_argument("--calibration-manifest", default=None)
    parser.add_argument("--semantic-validation", required=True)
    parser.add_argument("--bank-out", required=True)
    parser.add_argument("--report-out", required=True)
    args = parser.parse_args(argv)
    for path in (args.bank_out, args.report_out):
        if os.path.exists(path):
            raise FileExistsError("refusing to overwrite %s" % path)
    pool = V5MessageBank.load(args.pool)
    records = list(read_jsonl(args.calibration_log))
    manifest_path = args.calibration_manifest or args.calibration_log.replace(
        ".jsonl", ".manifest.json"
    )
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    run_audit = audit_v5_calibration_run(
        records, manifest, pool, "pool_calibration"
    )
    if not run_audit["pass"]:
        failed = sorted(
            name for name, passed in run_audit["checks"].items() if not passed
        )
        raise ValueError("pool calibration artifact audit failed: %s" % ", ".join(failed))
    if file_sha256(args.calibration_log) != manifest.get("log_file_sha256"):
        raise ValueError("pool calibration log hash differs from its manifest")
    with open(args.semantic_validation, "r", encoding="utf-8") as handle:
        semantic = json.load(handle)
    selected, report = select_v5_bank(pool, records, semantic)
    report["calibration_run_audit"] = run_audit
    report["calibration_manifest_file_sha256"] = file_sha256(manifest_path)
    report["calibration_log_file_sha256"] = file_sha256(args.calibration_log)
    for path, payload in ((args.bank_out, selected), (args.report_out, report)):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
    print("wrote pending selected bank to %s" % args.bank_out)
    print("wrote selection report to %s" % args.report_out)
    print("PAID CONFIRMATORY RUN REMAINS BLOCKED pending selected-bank validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
