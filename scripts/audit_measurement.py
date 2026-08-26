#!/usr/bin/env python3
"""Audit blind judge artifacts and compare them with the source classifier."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import sys

from src.blind_judge import audit_codex_artifacts
from src.logging_utils import read_jsonl
from src.measurement_audit import (
    align_classifier_records,
    summarize_classifier_comparison,
    write_measurement_audit,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-log", required=True)
    parser.add_argument("--independent-log", required=True)
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    artifact_audit = audit_codex_artifacts(args.artifact_dir)
    pairs = align_classifier_records(
        list(read_jsonl(args.source_log)), list(read_jsonl(args.independent_log))
    )
    summary = summarize_classifier_comparison(pairs)
    summary["blind_artifact_audit"] = artifact_audit
    summary["source_log"] = args.source_log
    summary["independent_log"] = args.independent_log
    paths = write_measurement_audit(summary, args.out_dir)

    print("blind artifact audit: PASS")
    print(
        "  %d batches, %d unique messages; visible sample keys=%s"
        % (
            artifact_audit["n_batches"],
            artifact_audit["n_unique_messages"],
            artifact_audit["sample_keys_visible_to_judge"],
        )
    )
    print(
        "classifier agreement=%.3f  kappa=%.3f  changed=%d/%d"
        % (
            summary["raw_agreement"],
            summary["cohens_kappa"],
            summary["n_labels_changed"],
            summary["n_records"],
        )
    )
    for row in summary["match_rates"]:
        print(
            "%-16s source match=%.3f  independent match=%.3f  n=%d"
            % (
                row["condition"],
                row["source_match_rate"],
                row["independent_match_rate"],
                row["n"],
            )
        )
    print("wrote:")
    for path in paths.values():
        print("  " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
