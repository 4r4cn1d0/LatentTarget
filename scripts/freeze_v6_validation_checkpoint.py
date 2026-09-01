#!/usr/bin/env python3
"""Freeze the exact V6 artifact graph before independent validation."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

from src.v6_protocol_gate import build_v6_prevalidation_checkpoint


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--calibration-protocol",
        default=os.path.join(_bootstrap.ROOT, "docs", "v6_calibration_protocol.json"),
    )
    parser.add_argument("--source-pool", required=True)
    parser.add_argument("--semantic-validation", required=True)
    parser.add_argument("--quality-validation", required=True)
    parser.add_argument("--prevalidation-power", required=True)
    parser.add_argument("--pool-calibration-log", required=True)
    parser.add_argument("--pool-calibration-manifest", required=True)
    parser.add_argument("--selection-report", required=True)
    parser.add_argument("--pending-bank", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if os.path.exists(args.out):
        raise FileExistsError("refusing to overwrite frozen checkpoint %s" % args.out)

    checkpoint = build_v6_prevalidation_checkpoint(
        calibration_protocol_path=args.calibration_protocol,
        source_pool_path=args.source_pool,
        semantic_validation_path=args.semantic_validation,
        quality_validation_path=args.quality_validation,
        prevalidation_power_path=args.prevalidation_power,
        pool_calibration_log_path=args.pool_calibration_log,
        pool_calibration_manifest_path=args.pool_calibration_manifest,
        selection_report_path=args.selection_report,
        pending_bank_path=args.pending_bank,
        repository_root=_bootstrap.ROOT,
    )
    parent = os.path.dirname(args.out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(checkpoint, handle, indent=2, ensure_ascii=False, allow_nan=False)
    print("FROZEN %s" % args.out)
    print("pending bank: %s" % checkpoint["pending_bank"]["bank_sha256"])
    print(
        "official validation run-id: %s"
        % checkpoint["official_run_ids"]["selected_bank_validation"]
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
