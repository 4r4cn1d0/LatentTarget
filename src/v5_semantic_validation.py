"""Blind, two-judge semantic manipulation gate for the V5 candidate pool."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from config import (
    ALL_LABELS,
    CONTROLLED_V5_SEMANTIC_THRESHOLDS,
    STRATEGIES,
)
from .controlled_v5_messages import V5MessageBank
from .measurement_audit import cohens_kappa


def semantic_candidate_rows(bank: V5MessageBank) -> List[Dict[str, str]]:
    """Render one target-free example per immutable candidate template."""
    rows: List[Dict[str, str]] = []
    for split in ("development", "heldout"):
        for intended_frame in STRATEGIES:
            for entry in bank.payload["splits"][split][intended_frame]:
                rows.append(
                    {
                        "candidate_id": str(entry["candidate_id"]),
                        "split": split,
                        "intended_frame": intended_frame,
                        "message": " ".join(
                            str(entry["template"]).format(a="Option A").split()
                        ),
                    }
                )
    if len({row["candidate_id"] for row in rows}) != len(rows):
        raise ValueError("V5 semantic candidates contain duplicate IDs")
    if len({row["message"] for row in rows}) != len(rows):
        raise ValueError("V5 semantic candidates contain duplicate rendered messages")
    return rows


def _validated_result(result: Mapping[str, Any]) -> Dict[str, Any]:
    primary = str(result.get("primary_strategy", ""))
    if primary not in ALL_LABELS:
        raise ValueError("semantic judge returned an invalid primary strategy")
    clean: Dict[str, Any] = {"primary_strategy": primary}
    for field in (*ALL_LABELS, "confidence"):
        value = result.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("semantic judge field %s is not numeric" % field)
        value = float(value)
        if not 0.0 <= value <= 1.0:
            raise ValueError("semantic judge field %s is outside [0,1]" % field)
        clean[field] = value
    return clean


def _judge_metrics(
    rows: Sequence[Mapping[str, str]], results: Mapping[str, Mapping[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    expected_messages = {row["message"] for row in rows}
    if set(results) != expected_messages:
        raise ValueError("semantic judge results do not exactly cover the V5 pool")
    clean = {message: _validated_result(result) for message, result in results.items()}
    labels = [clean[row["message"]]["primary_strategy"] for row in rows]
    intended = [row["intended_frame"] for row in rows]
    recalls = {}
    for frame in STRATEGIES:
        indices = [index for index, value in enumerate(intended) if value == frame]
        recalls[frame] = sum(labels[index] == frame for index in indices) / float(
            len(indices)
        )
    return (
        {
            "accuracy": sum(a == b for a, b in zip(intended, labels))
            / float(len(rows)),
            "recall_by_intended_frame": recalls,
            "predicted_distribution": dict(Counter(labels)),
        },
        clean,
    )


def _candidate_pass(
    result: Mapping[str, Any], intended: str, thresholds: Mapping[str, float]
) -> Tuple[bool, Dict[str, bool], float]:
    other_scores = [float(result[label]) for label in ALL_LABELS if label != intended]
    margin = float(result[intended]) - max(other_scores)
    checks = {
        "primary_label": result["primary_strategy"] == intended,
        "confidence": float(result["confidence"])
        >= thresholds["minimum_candidate_confidence"],
        "intended_score": float(result[intended])
        >= thresholds["minimum_candidate_intended_score"],
        "score_margin": margin >= thresholds["minimum_candidate_margin"],
    }
    return all(checks.values()), checks, margin


def evaluate_v5_semantic_validation(
    bank: V5MessageBank,
    primary_results: Mapping[str, Mapping[str, Any]],
    sensitivity_results: Mapping[str, Mapping[str, Any]],
    primary_description: Mapping[str, Any],
    sensitivity_description: Mapping[str, Any],
    primary_artifact_audit: Mapping[str, Any],
    sensitivity_artifact_audit: Mapping[str, Any],
    thresholds: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    """Join hidden intended labels only after both blind judge calls finish."""
    thresholds = dict(thresholds or CONTROLLED_V5_SEMANTIC_THRESHOLDS)
    rows = semantic_candidate_rows(bank)
    primary_metrics, primary_clean = _judge_metrics(rows, primary_results)
    sensitivity_metrics, sensitivity_clean = _judge_metrics(
        rows, sensitivity_results
    )
    primary_labels = [
        primary_clean[row["message"]]["primary_strategy"] for row in rows
    ]
    sensitivity_labels = [
        sensitivity_clean[row["message"]]["primary_strategy"] for row in rows
    ]
    kappa = cohens_kappa(primary_labels, sensitivity_labels)

    eligible: List[str] = []
    candidate_rows: List[Dict[str, Any]] = []
    eligible_counts: Counter = Counter()
    for row in rows:
        primary = primary_clean[row["message"]]
        sensitivity = sensitivity_clean[row["message"]]
        primary_pass, primary_checks, primary_margin = _candidate_pass(
            primary, row["intended_frame"], thresholds
        )
        sensitivity_pass, sensitivity_checks, sensitivity_margin = _candidate_pass(
            sensitivity, row["intended_frame"], thresholds
        )
        is_eligible = primary_pass and sensitivity_pass
        if is_eligible:
            eligible.append(row["candidate_id"])
            eligible_counts[(row["split"], row["intended_frame"])] += 1
        candidate_rows.append(
            {
                **row,
                "primary_judge": primary,
                "sensitivity_judge": sensitivity,
                "primary_checks": primary_checks,
                "sensitivity_checks": sensitivity_checks,
                "primary_margin": primary_margin,
                "sensitivity_margin": sensitivity_margin,
                "eligible": is_eligible,
            }
        )

    primary_model = str(primary_description.get("model", ""))
    sensitivity_model = str(sensitivity_description.get("model", ""))
    gates = {
        "pool_structurally_valid": True,
        "judge_models_distinct": bool(primary_model)
        and bool(sensitivity_model)
        and primary_model != sensitivity_model,
        "both_artifact_audits_pass": bool(primary_artifact_audit.get("ok"))
        and bool(sensitivity_artifact_audit.get("ok")),
        "primary_accuracy": primary_metrics["accuracy"]
        >= thresholds["minimum_judge_accuracy"],
        "primary_all_class_recall": min(
            primary_metrics["recall_by_intended_frame"].values()
        )
        >= thresholds["minimum_judge_class_recall"],
        "sensitivity_accuracy": sensitivity_metrics["accuracy"]
        >= thresholds["minimum_judge_accuracy"],
        "sensitivity_all_class_recall": min(
            sensitivity_metrics["recall_by_intended_frame"].values()
        )
        >= thresholds["minimum_judge_class_recall"],
        "interjudge_kappa": kappa >= thresholds["minimum_interjudge_kappa"],
        "enough_development_candidates_per_frame": all(
            eligible_counts[("development", frame)]
            >= int(thresholds["minimum_eligible_development_per_frame"])
            for frame in STRATEGIES
        ),
        "enough_heldout_candidates_per_frame": all(
            eligible_counts[("heldout", frame)]
            >= int(thresholds["minimum_eligible_heldout_per_frame"])
            for frame in STRATEGIES
        ),
    }
    return {
        "pass": all(gates.values()),
        "scientific_status": (
            "machine-only blind semantic manipulation gate; not human validation"
        ),
        "pool_sha256": bank.sha256(),
        "n_candidates": len(rows),
        "judge_visible_fields": ["sample_id", "message"],
        "intended_labels_supplied_to_judges": False,
        "thresholds_frozen_before_judging": thresholds,
        "primary_judge": dict(primary_description),
        "sensitivity_judge": dict(sensitivity_description),
        "primary_metrics": primary_metrics,
        "sensitivity_metrics": sensitivity_metrics,
        "interjudge_agreement": sum(
            a == b for a, b in zip(primary_labels, sensitivity_labels)
        )
        / float(len(rows)),
        "interjudge_kappa": kappa,
        "eligible_counts": {
            split: {
                frame: eligible_counts[(split, frame)] for frame in STRATEGIES
            }
            for split in ("development", "heldout")
        },
        "eligible_candidate_ids": eligible,
        "candidate_results": candidate_rows,
        "primary_artifact_audit": dict(primary_artifact_audit),
        "sensitivity_artifact_audit": dict(sensitivity_artifact_audit),
        "gates": gates,
    }
