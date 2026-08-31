#!/usr/bin/env python3
"""Apply the frozen v3 stop/go gate to the blind independently judged log."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

from src.blind_judge import audit_codex_artifacts
from src.checkpoint_gate import evaluate_behavioral_checkpoint
from src.logging_utils import read_jsonl
from src.measurement_audit import align_classifier_records


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-log", required=True)
    parser.add_argument("--independent-log", required=True)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    source = list(read_jsonl(args.source_log))
    independent = list(read_jsonl(args.independent_log))
    pairs = align_classifier_records(source, independent)
    records = [judged for _, judged in pairs]
    manifest_path = args.manifest or args.source_log.replace(".jsonl", ".manifest.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError("source manifest not found: %s" % manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    audit = audit_codex_artifacts(args.artifact_dir)
    result = evaluate_behavioral_checkpoint(records, manifest, audit)
    result["source_log"] = args.source_log
    result["independent_log"] = args.independent_log
    result["source_manifest"] = manifest_path
    result["judge_artifact_dir"] = args.artifact_dir

    parent = os.path.dirname(args.out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, default=str)
    print(result["decision"])
    for name, passed in result["gates"].items():
        print("  %-38s %s" % (name, "PASS" if passed else "FAIL"))
    print("wrote %s" % args.out)
    # A scientifically negative result is a valid completed execution. Return
    # success so automation preserves artifacts rather than treating STOP as a
    # software crash.
    return 0


if __name__ == "__main__":
    sys.exit(main())
