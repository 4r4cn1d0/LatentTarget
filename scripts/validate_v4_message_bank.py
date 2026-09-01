#!/usr/bin/env python3
"""Blind two-judge manipulation check for the registered V4 message bank."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import csv
import json
import os
import sys
from collections import Counter

from config import CONTROLLED_MESSAGE_BANK_GATE_THRESHOLDS, STRATEGIES
from src.blind_judge import CodexBlindJudge, audit_codex_artifacts
from src.controlled_messages import (
    DEVELOPMENT_TEMPLATES,
    HELDOUT_TEMPLATES,
    message_bank_sha256,
)
from src.measurement_audit import cohens_kappa
from src.scenarios import SCENARIOS


THRESHOLDS = CONTROLLED_MESSAGE_BANK_GATE_THRESHOLDS


def build_samples():
    """Render every template against two scenarios without exposing labels."""
    samples = []
    for split, bank in (("development", DEVELOPMENT_TEMPLATES),
                        ("heldout", HELDOUT_TEMPLATES)):
        for frame in STRATEGIES:
            for template_index, template in enumerate(bank[frame]):
                for scenario in (SCENARIOS[0], SCENARIOS[7]):
                    message = " ".join(template.format(
                        a=scenario.option_a, b=scenario.option_b
                    ).split())
                    samples.append({
                        "sample_id": "v4-%s-%s-%02d-%s" %
                        (split, frame, template_index, scenario.id),
                        "split": split,
                        "intended_frame": frame,
                        "template_index": template_index,
                        "scenario_id": scenario.id,
                        "message": message,
                    })
    if len(samples) != 90 or len({row["message"] for row in samples}) != 90:
        raise ValueError("expected 90 unique rendered manipulation-check messages")
    return samples


def _judge(samples, model, cache, artifact_dir, batch_size, seed, executable, timeout):
    judge = CodexBlindJudge(
        model=model,
        cache_path=cache,
        artifact_dir=artifact_dir,
        batch_size=batch_size,
        seed=seed,
        executable=executable,
        timeout_s=timeout,
    )
    results = judge.classify_messages(row["message"] for row in samples)
    audit = audit_codex_artifacts(artifact_dir)
    labels = [results[row["message"]]["primary_strategy"] for row in samples]
    return judge, results, labels, audit


def _metrics(samples, labels):
    intended = [row["intended_frame"] for row in samples]
    by_class = {}
    for frame in STRATEGIES:
        indices = [index for index, label in enumerate(intended) if label == frame]
        by_class[frame] = sum(labels[index] == frame for index in indices) / float(len(indices))
    return {
        "accuracy": sum(left == right for left, right in zip(intended, labels)) / float(len(labels)),
        "recall_by_intended_frame": by_class,
        "predicted_distribution": dict(Counter(labels)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-model", default="gpt-5.6-sol")
    parser.add_argument("--sensitivity-model", default="gpt-5.6-luna")
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--codex-executable", default="codex")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--out-dir", default="results/v4_design/message_bank_validation")
    parser.add_argument("--cache-dir", default="data/processed/v4_message_bank_validation")
    args = parser.parse_args(argv)

    samples = build_samples()
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.cache_dir, exist_ok=True)
    primary_dir = os.path.join(args.out_dir, "primary_batches")
    sensitivity_dir = os.path.join(args.out_dir, "sensitivity_batches")
    primary = _judge(
        samples, args.primary_model,
        os.path.join(args.cache_dir, "primary_cache.jsonl"),
        primary_dir, args.batch_size, args.seed,
        args.codex_executable, args.timeout,
    )
    sensitivity = _judge(
        samples, args.sensitivity_model,
        os.path.join(args.cache_dir, "sensitivity_cache.jsonl"),
        sensitivity_dir, args.batch_size, args.seed + 1,
        args.codex_executable, args.timeout,
    )
    primary_judge, primary_results, primary_labels, primary_audit = primary
    sensitivity_judge, sensitivity_results, sensitivity_labels, sensitivity_audit = sensitivity
    primary_metrics = _metrics(samples, primary_labels)
    sensitivity_metrics = _metrics(samples, sensitivity_labels)
    agreement = sum(a == b for a, b in zip(primary_labels, sensitivity_labels)) / len(samples)
    kappa = cohens_kappa(primary_labels, sensitivity_labels)

    gates = {
        "both_judge_artifact_audits": bool(primary_audit["ok"] and sensitivity_audit["ok"]),
        "primary_accuracy": primary_metrics["accuracy"] >= THRESHOLDS["minimum_primary_accuracy"],
        "primary_all_class_recall": min(primary_metrics["recall_by_intended_frame"].values())
        >= THRESHOLDS["minimum_primary_class_recall"],
        "sensitivity_accuracy": sensitivity_metrics["accuracy"]
        >= THRESHOLDS["minimum_sensitivity_accuracy"],
        "sensitivity_all_class_recall": min(
            sensitivity_metrics["recall_by_intended_frame"].values()
        ) >= THRESHOLDS["minimum_sensitivity_class_recall"],
        "interjudge_kappa": kappa >= THRESHOLDS["minimum_interjudge_kappa"],
    }

    rows = []
    for sample, primary_label, sensitivity_label in zip(
        samples, primary_labels, sensitivity_labels
    ):
        rows.append({
            **sample,
            "primary_label": primary_label,
            "primary_confidence": primary_results[sample["message"]]["confidence"],
            "sensitivity_label": sensitivity_label,
            "sensitivity_confidence": sensitivity_results[sample["message"]]["confidence"],
        })
    with open(os.path.join(args.out_dir, "classifications.csv"), "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    with open(os.path.join(args.out_dir, "samples_with_intended_labels.json"), "w", encoding="utf-8") as handle:
        json.dump(samples, handle, indent=2)

    summary = {
        "status": "machine-only blind manipulation check; not human validation",
        "n_messages": len(samples),
        "message_bank_sha256": message_bank_sha256(),
        "judge_visible_fields": ["sample_id", "message"],
        "intended_labels_supplied_to_judges": False,
        "thresholds_frozen_in_code_before_judging": THRESHOLDS,
        "primary_judge": primary_judge.describe(),
        "sensitivity_judge": sensitivity_judge.describe(),
        "primary_metrics": primary_metrics,
        "sensitivity_metrics": sensitivity_metrics,
        "interjudge_agreement": agreement,
        "interjudge_kappa": kappa,
        "primary_artifact_audit": primary_audit,
        "sensitivity_artifact_audit": sensitivity_audit,
        "gates": gates,
        "pass": all(gates.values()),
    }
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False)
    print("PASS" if summary["pass"] else "FAIL")
    print("primary accuracy %.3f; sensitivity %.3f; kappa %.3f" % (
        primary_metrics["accuracy"], sensitivity_metrics["accuracy"], kappa
    ))
    for name, passed in gates.items():
        print("  %-36s %s" % (name, "PASS" if passed else "FAIL"))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
