"""Blind, two-judge semantic gate for flattened V6 triad candidates."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from config import (
    ALL_LABELS,
    CONTROLLED_V6_SEMANTIC_THRESHOLDS,
    STRATEGIES,
)
from .measurement_audit import cohens_kappa


def _pool_payload(pool: Any) -> Mapping[str, Any]:
    payload = pool if isinstance(pool, Mapping) else getattr(pool, "payload", None)
    if not isinstance(payload, Mapping):
        raise ValueError("V6 semantic pool must be a mapping or bank-like object")
    return payload


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_v6_semantic_pool(path: str) -> Dict[str, Any]:
    """Load a pool after validating the candidate structure used by this gate."""
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    semantic_candidate_rows(payload)
    return payload


def semantic_candidate_rows(pool: Any) -> List[Dict[str, str]]:
    """Flatten immutable triads into one target-free rendered message each.

    The returned intended frame and triad metadata are for the post-judging
    join only.  Callers must pass only ``message`` values to a blind judge.
    """
    rows: List[Dict[str, str]] = []
    triad_ids: List[str] = []
    payload = _pool_payload(pool)
    splits = payload.get("splits", {})
    if not isinstance(splits, Mapping):
        raise ValueError("V6 semantic pool has no splits mapping")
    if set(splits) != {"development", "heldout"}:
        raise ValueError("V6 semantic pool must contain exactly two registered splits")
    for split in ("development", "heldout"):
        triads = splits.get(split)
        if not isinstance(triads, list) or not triads:
            raise ValueError("V6 semantic pool has no %s triads" % split)
        for triad in triads:
            if not isinstance(triad, Mapping):
                raise ValueError("V6 semantic pool contains a malformed triad")
            triad_id = str(triad.get("triad_id", ""))
            if not triad_id:
                raise ValueError("V6 semantic pool contains an empty triad ID")
            candidates = triad.get("candidates")
            if not isinstance(candidates, Mapping) or set(candidates) != set(
                STRATEGIES
            ):
                raise ValueError(
                    "V6 semantic triad %s does not contain exactly one candidate "
                    "per intended frame" % triad_id
                )
            triad_ids.append(triad_id)
            for intended_frame in STRATEGIES:
                entry = candidates[intended_frame]
                if not isinstance(entry, Mapping):
                    raise ValueError(
                        "V6 semantic triad %s contains a malformed candidate"
                        % triad_id
                    )
                candidate_id = str(entry.get("candidate_id", ""))
                template = str(entry.get("template", ""))
                if not candidate_id or not template:
                    raise ValueError(
                        "V6 semantic triad %s contains an empty candidate ID or text"
                        % triad_id
                    )
                try:
                    rendered = template.format(a="Option A")
                except (IndexError, KeyError, ValueError) as exc:
                    raise ValueError(
                        "V6 semantic candidate %s could not be rendered"
                        % candidate_id
                    ) from exc
                rows.append(
                    {
                        "candidate_id": candidate_id,
                        "split": split,
                        "triad_id": triad_id,
                        "intended_frame": intended_frame,
                        "message": " ".join(rendered.split()),
                    }
                )
    if len(set(triad_ids)) != len(triad_ids):
        raise ValueError("V6 semantic triads contain duplicate IDs")
    if len({row["candidate_id"] for row in rows}) != len(rows):
        raise ValueError("V6 semantic candidates contain duplicate IDs")
    if len({row["message"] for row in rows}) != len(rows):
        raise ValueError("V6 semantic candidates contain duplicate rendered messages")
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
    rows: Sequence[Mapping[str, str]],
    results: Mapping[str, Mapping[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    expected_messages = {row["message"] for row in rows}
    if set(results) != expected_messages:
        raise ValueError("semantic judge results do not exactly cover the V6 pool")
    clean = {
        message: _validated_result(result) for message, result in results.items()
    }
    labels = [clean[row["message"]]["primary_strategy"] for row in rows]
    intended = [row["intended_frame"] for row in rows]
    recalls: Dict[str, float] = {}
    for frame in STRATEGIES:
        indices = [index for index, value in enumerate(intended) if value == frame]
        if not indices:
            raise ValueError("V6 semantic pool has no %s candidates" % frame)
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
    result: Mapping[str, Any],
    intended: str,
    thresholds: Mapping[str, float],
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


def evaluate_v6_semantic_validation(
    pool: Any,
    primary_results: Mapping[str, Mapping[str, Any]],
    sensitivity_results: Mapping[str, Mapping[str, Any]],
    primary_description: Mapping[str, Any],
    sensitivity_description: Mapping[str, Any],
    primary_artifact_audit: Mapping[str, Any],
    sensitivity_artifact_audit: Mapping[str, Any],
    thresholds: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    """Join intended frames and triad IDs after both blind calls have finished."""
    thresholds = dict(thresholds or CONTROLLED_V6_SEMANTIC_THRESHOLDS)
    payload = _pool_payload(pool)
    rows = semantic_candidate_rows(payload)
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
    raw_kappa = cohens_kappa(primary_labels, sensitivity_labels)
    kappa = raw_kappa if math.isfinite(raw_kappa) else None

    candidate_rows: List[Dict[str, Any]] = []
    by_triad: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        primary = primary_clean[row["message"]]
        sensitivity = sensitivity_clean[row["message"]]
        primary_pass, primary_checks, primary_margin = _candidate_pass(
            primary, row["intended_frame"], thresholds
        )
        sensitivity_pass, sensitivity_checks, sensitivity_margin = _candidate_pass(
            sensitivity, row["intended_frame"], thresholds
        )
        result_row: Dict[str, Any] = {
            **row,
            "primary_judge": primary,
            "sensitivity_judge": sensitivity,
            "primary_checks": primary_checks,
            "sensitivity_checks": sensitivity_checks,
            "primary_margin": primary_margin,
            "sensitivity_margin": sensitivity_margin,
            "passes_both_judges": primary_pass and sensitivity_pass,
            "eligible": primary_pass and sensitivity_pass,
        }
        candidate_rows.append(result_row)
        by_triad[(row["split"], row["triad_id"])].append(result_row)

    eligible_candidate_ids = [
        row["candidate_id"] for row in candidate_rows if row["eligible"]
    ]
    eligible_triad_ids: List[str] = []
    eligible_triad_candidate_ids: List[str] = []
    eligible_counts: Counter = Counter()
    triad_rows: List[Dict[str, Any]] = []
    for (split, triad_id), members in by_triad.items():
        intended_frames = {row["intended_frame"] for row in members}
        complete = len(members) == len(STRATEGIES) and intended_frames == set(
            STRATEGIES
        )
        candidates_pass = complete and all(
            row["passes_both_judges"] for row in members
        )
        eligible = candidates_pass
        if eligible:
            eligible_triad_ids.append(triad_id)
            eligible_triad_candidate_ids.extend(
                row["candidate_id"] for row in members
            )
            eligible_counts[split] += 1
        for row in members:
            row["triad_eligible"] = eligible
        triad_rows.append(
            {
                "triad_id": triad_id,
                "split": split,
                "candidate_ids": [row["candidate_id"] for row in members],
                "complete_three_frame_triad": complete,
                "all_candidates_pass_both_judges": candidates_pass,
                "eligible": eligible,
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
        "interjudge_kappa": kappa is not None
        and kappa >= thresholds["minimum_interjudge_kappa"],
        "enough_development_triads": eligible_counts["development"]
        >= int(thresholds["minimum_eligible_development_triads"]),
        "enough_heldout_triads": eligible_counts["heldout"]
        >= int(thresholds["minimum_eligible_heldout_triads"]),
    }
    return {
        "pass": all(gates.values()),
        "scientific_status": (
            "machine-only blind semantic manipulation gate; not human validation"
        ),
        "pool_id": str(payload.get("pool_id", "")),
        "pool_sha256": _canonical_hash(payload),
        "n_triads": len(by_triad),
        "n_candidates": len(rows),
        "judge_visible_fields": ["sample_id", "message"],
        "intended_metadata_fields": ["intended_frame", "triad_id", "split"],
        "intended_metadata_supplied_to_judges": False,
        "metadata_joined_after_both_judge_calls": True,
        "intended_labels_supplied_to_judges": False,
        "intended_frames_supplied_to_judges": False,
        "triad_ids_supplied_to_judges": False,
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
        "interjudge_kappa_defined": kappa is not None,
        "eligible_counts": {
            split: eligible_counts[split]
            for split in ("development", "heldout")
        },
        "eligible_candidate_ids": eligible_candidate_ids,
        "eligible_triad_candidate_ids": eligible_triad_candidate_ids,
        "eligible_triad_ids": eligible_triad_ids,
        "triad_results": triad_rows,
        "candidate_results": candidate_rows,
        "primary_artifact_audit": dict(primary_artifact_audit),
        "sensitivity_artifact_audit": dict(sensitivity_artifact_audit),
        "gates": gates,
    }
