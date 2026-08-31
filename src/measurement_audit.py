"""Auditable comparison of two blind persuasion-strategy instruments.

The first real run was initially measured with a keyword classifier that
shared vocabulary with the target simulator. This module aligns that immutable
source log with an independently judged copy, fails closed if any experimental
record changed, and reports every agreement and disagreement without selecting
examples by outcome.
"""

from __future__ import annotations

import csv
import json
import math
import os
from collections import Counter
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from config import ALL_LABELS


Record = Mapping[str, Any]
RecordPair = Tuple[Record, Record]

IMMUTABLE_FIELDS = (
    "run_id",
    "episode_id",
    "round",
    "condition",
    "hidden_target_type",
    "scenario_id",
    "focal_message",
    "target_choice",
    "target_p_a",
    "round_seed",
)

CLASSIFIER_FIELDS = frozenset(
    {
        "strategy_scores",
        "primary_strategy",
        "strategy_confidence",
        "classifier_name",
        "classifier_ok",
        "classifier_error",
        "classifier_raw",
    }
)


def record_key(record: Record) -> Tuple[str, str, int]:
    return (
        str(record.get("run_id", "")),
        str(record["episode_id"]),
        int(record["round"]),
    )


def align_classifier_records(
    source: Iterable[Record], independent: Iterable[Record]
) -> List[RecordPair]:
    """Align two logs and prove that only classifier fields may differ."""

    def indexed(records: Iterable[Record], label: str) -> Dict[Tuple[str, str, int], Record]:
        out: Dict[Tuple[str, str, int], Record] = {}
        for record in records:
            key = record_key(record)
            if key in out:
                raise ValueError("duplicate %s record key: %r" % (label, key))
            out[key] = record
        return out

    left = indexed(source, "source")
    right = indexed(independent, "independent")
    if set(left) != set(right):
        missing = sorted(set(left) - set(right))
        extra = sorted(set(right) - set(left))
        raise ValueError(
            "classifier logs have different record keys; missing=%r extra=%r"
            % (missing[:5], extra[:5])
        )
    pairs = []
    for key in sorted(left):
        a, b = left[key], right[key]
        for field in IMMUTABLE_FIELDS:
            if a.get(field) != b.get(field):
                raise ValueError("non-classifier field %s changed at %r" % (field, key))
        # The independent-judge pass is a pure measurement transform. Compare
        # every non-classifier field, not just the minimum alignment key, so a
        # changed history, probability, score, prompt, or seed cannot hide in a
        # seemingly aligned copy.
        for field in sorted((set(a) | set(b)) - CLASSIFIER_FIELDS):
            if a.get(field) != b.get(field):
                raise ValueError("non-classifier field %s changed at %r" % (field, key))
        pairs.append((a, b))
    if not pairs:
        raise ValueError("classifier logs are empty")
    return pairs


def cohens_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    """Unweighted Cohen's kappa over the fixed four-label vocabulary."""
    if len(a) != len(b):
        raise ValueError("label sequences have different lengths")
    if not a:
        return float("nan")
    unknown = (set(a) | set(b)) - set(ALL_LABELS)
    if unknown:
        raise ValueError("unknown strategy labels: %s" % sorted(unknown))
    n = float(len(a))
    observed = sum(x == y for x, y in zip(a, b)) / n
    expected = 0.0
    for label in ALL_LABELS:
        expected += (a.count(label) / n) * (b.count(label) / n)
    if math.isclose(expected, 1.0):
        return float("nan")
    return (observed - expected) / (1.0 - expected)


def _classifier_name(records: Sequence[Record], fallback: str) -> List[str]:
    names = sorted({str(record.get("classifier_name", fallback)) for record in records})
    return names


def summarize_classifier_comparison(pairs: Sequence[RecordPair]) -> Dict[str, Any]:
    """Return aggregate and cell-level diagnostics for aligned records."""
    if not pairs:
        raise ValueError("no aligned records")
    source_records = [a for a, _ in pairs]
    independent_records = [b for _, b in pairs]
    source_labels = [str(row["primary_strategy"]) for row in source_records]
    independent_labels = [str(row["primary_strategy"]) for row in independent_records]
    unknown = (set(source_labels) | set(independent_labels)) - set(ALL_LABELS)
    if unknown:
        raise ValueError("unknown strategy labels: %s" % sorted(unknown))

    confusion = {
        source: {independent: 0 for independent in ALL_LABELS}
        for source in ALL_LABELS
    }
    comparison_rows: List[Dict[str, Any]] = []
    for source, independent in pairs:
        source_label = str(source["primary_strategy"])
        independent_label = str(independent["primary_strategy"])
        confusion[source_label][independent_label] += 1
        condition = str(source["condition"])
        target = str(source["hidden_target_type"])
        comparison_rows.append(
            {
                "run_id": source.get("run_id"),
                "episode_id": source["episode_id"],
                "round": int(source["round"]),
                "condition": condition,
                "hidden_target_type": target,
                "source_label": source_label,
                "independent_label": independent_label,
                "changed": source_label != independent_label,
                "source_match": source_label == target,
                "independent_match": independent_label == target,
                "independent_confidence": float(
                    independent.get("strategy_confidence", float("nan"))
                ),
                "source_classifier": str(source.get("classifier_name", "source")),
                "independent_classifier": str(
                    independent.get("classifier_name", "independent")
                ),
                "focal_message": str(source["focal_message"]),
            }
        )

    conditions = sorted({str(a["condition"]) for a, _ in pairs})
    targets = sorted({str(a["hidden_target_type"]) for a, _ in pairs})
    match_rates = []
    distribution = []
    target_cells: Dict[str, Dict[str, Any]] = {}
    for condition in conditions:
        condition_pairs = [pair for pair in pairs if pair[0]["condition"] == condition]
        match_rates.append(
            {
                "condition": condition,
                "n": len(condition_pairs),
                "source_match_rate": sum(
                    a["primary_strategy"] == a["hidden_target_type"]
                    for a, _ in condition_pairs
                )
                / float(len(condition_pairs)),
                "independent_match_rate": sum(
                    b["primary_strategy"] == a["hidden_target_type"]
                    for a, b in condition_pairs
                )
                / float(len(condition_pairs)),
            }
        )
        for target in targets:
            target_pairs = [
                pair
                for pair in condition_pairs
                if pair[0]["hidden_target_type"] == target
            ]
            if not target_pairs:
                continue
            key = condition + "/" + target
            source_match_n = sum(
                a["primary_strategy"] == target for a, _ in target_pairs
            )
            independent_match_n = sum(
                b["primary_strategy"] == target for _, b in target_pairs
            )
            target_cells[key] = {
                "n": len(target_pairs),
                "source_matching_n": source_match_n,
                "source_matching_rate": source_match_n / float(len(target_pairs)),
                "independent_matching_n": independent_match_n,
                "independent_matching_rate": independent_match_n
                / float(len(target_pairs)),
            }
            for label in ALL_LABELS:
                count = sum(b["primary_strategy"] == label for _, b in target_pairs)
                distribution.append(
                    {
                        "condition": condition,
                        "hidden_target_type": target,
                        "independent_label": label,
                        "n": count,
                        "fraction": count / float(len(target_pairs)),
                        "cell_n": len(target_pairs),
                    }
                )

    fairness_rescued_rows = [
        (a, b)
        for a, b in pairs
        if a["primary_strategy"] != "fairness" and b["primary_strategy"] == "fairness"
    ]
    expertise_overcalled_rows = [
        (a, b)
        for a, b in pairs
        if a["primary_strategy"] == "expertise" and b["primary_strategy"] != "expertise"
    ]
    expertise_terms = Counter()
    for source, _ in expertise_overcalled_rows:
        matched = source.get("classifier_raw", {}).get("matched_terms", {})
        expertise_terms.update(str(term) for term in matched.get("expertise", []))
    fairness_zero_reward = 0
    fairness_reward_available = 0
    for source, _ in fairness_rescued_rows:
        scores = source.get("target_scores", {})
        if "fairness" in scores:
            fairness_reward_available += 1
            if float(scores["fairness"]) == 0.0:
                fairness_zero_reward += 1
    n_agree = sum(a == b for a, b in zip(source_labels, independent_labels))
    return {
        "n_records": len(pairs),
        "source_classifiers": _classifier_name(source_records, "source"),
        "independent_classifiers": _classifier_name(
            independent_records, "independent"
        ),
        "raw_agreement": n_agree / float(len(pairs)),
        "cohens_kappa": cohens_kappa(source_labels, independent_labels),
        "n_labels_changed": len(pairs) - n_agree,
        "confusion_source_rows_independent_columns": confusion,
        "match_rates": match_rates,
        "target_cells": target_cells,
        "diagnoses": {
            "fairness_rescued_from_source_false_negative_n": len(fairness_rescued_rows),
            "fairness_rescued_with_zero_target_fairness_reward_n": fairness_zero_reward,
            "fairness_rescued_with_target_scores_available_n": fairness_reward_available,
            "source_expertise_relabelled_by_independent_n": len(
                expertise_overcalled_rows
            ),
            "expertise_terms_in_relabelled_source_rows": dict(
                sorted(expertise_terms.items(), key=lambda item: (-item[1], item[0]))
            ),
            "full_history_fairness": target_cells.get("full_history/fairness"),
            "no_history_fairness": target_cells.get("no_history/fairness"),
            "full_history_expertise": target_cells.get("full_history/expertise"),
            "no_history_expertise": target_cells.get("no_history/expertise"),
        },
        "comparison_rows": comparison_rows,
        "independent_distribution": distribution,
    }


def write_measurement_audit(
    summary: Mapping[str, Any], output_dir: str, prefix: str = ""
) -> Dict[str, str]:
    """Write complete, deterministic audit tables and a compact JSON summary."""
    os.makedirs(output_dir, exist_ok=True)
    paths = {
        "summary": os.path.join(output_dir, prefix + "measurement_audit.json"),
        "comparison": os.path.join(
            output_dir, prefix + "classifier_comparison_all_rows.csv"
        ),
        "confusion": os.path.join(output_dir, prefix + "classifier_confusion.csv"),
        "distribution": os.path.join(
            output_dir, prefix + "independent_strategy_distribution.csv"
        ),
    }

    compact = {
        k: v
        for k, v in summary.items()
        if k not in {"comparison_rows", "independent_distribution"}
    }
    with open(paths["summary"], "w", encoding="utf-8") as fh:
        json.dump(compact, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")

    comparison_rows = list(summary["comparison_rows"])
    with open(paths["comparison"], "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=list(comparison_rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(comparison_rows)

    with open(paths["confusion"], "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["source_label"] + list(ALL_LABELS))
        confusion = summary["confusion_source_rows_independent_columns"]
        for label in ALL_LABELS:
            writer.writerow([label] + [confusion[label][col] for col in ALL_LABELS])

    distribution = list(summary["independent_distribution"])
    with open(paths["distribution"], "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=list(distribution[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(distribution)
    return paths
