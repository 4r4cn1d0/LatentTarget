"""Deterministic diagnostics for the behavioral checkpoint instrument.

These summaries describe what the target scorer and an independent strategy
judge actually saw.  They do not decide whether the behavioral checkpoint
passes; that decision remains frozen in :mod:`src.checkpoint_gate`.
"""

from __future__ import annotations

import math
from collections import Counter
from statistics import mean, median
from typing import Any, Dict, Mapping, Sequence

from config import ALL_LABELS, STRATEGIES


def _quantile(values: Sequence[float], q: float) -> float:
    """Return a linearly interpolated quantile without a numpy dependency."""
    if not values:
        return float("nan")
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _summary(values: Sequence[float]) -> Dict[str, float]:
    if not values:
        return {
            "mean": float("nan"),
            "median": float("nan"),
            "p10": float("nan"),
            "p90": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
        }
    vals = [float(value) for value in values]
    return {
        "mean": mean(vals),
        "median": median(vals),
        "p10": _quantile(vals, 0.10),
        "p90": _quantile(vals, 0.90),
        "min": min(vals),
        "max": max(vals),
    }


def summarize_instrument(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Profile semantic target scores and independent strategy labels.

    The target scorer's three rewarded dimensions are taken from the top-level
    ``target_scores`` fields.  Its four-way semantic distribution is read from
    ``target_scores.raw_scores``.  The function fails closed on missing fields
    or labels so malformed logs cannot silently become a reassuring summary.
    """
    if not records:
        raise ValueError("instrument log is empty")

    judge_distribution: Counter[str] = Counter()
    semantic_distribution: Counter[str] = Counter()
    rewarded_distribution: Counter[str] = Counter()
    rewarded_mass = []
    rewarded_top_margin = []
    hidden_type_score = []
    target_probabilities = []
    judge_matches_semantic = 0
    judge_matches_rewarded = 0
    judge_strategy_rows = 0
    judge_strategy_matches_rewarded = 0

    condition_match: Dict[str, list[int]] = {}
    full_history_cells: Dict[str, Counter[str]] = {
        strategy: Counter() for strategy in STRATEGIES
    }

    for index, record in enumerate(records):
        label = str(record.get("primary_strategy", ""))
        if label not in ALL_LABELS:
            raise ValueError("unknown primary strategy at row %d: %r" % (index, label))
        target_type = str(record.get("hidden_target_type", ""))
        if target_type not in STRATEGIES:
            raise ValueError("unknown target type at row %d: %r" % (index, target_type))

        scores = record.get("target_scores")
        if not isinstance(scores, Mapping):
            raise ValueError("missing target_scores at row %d" % index)
        raw = scores.get("raw_scores")
        if not isinstance(raw, Mapping) or any(name not in raw for name in ALL_LABELS):
            raise ValueError("missing four-way raw target scores at row %d" % index)
        if any(name not in scores for name in STRATEGIES):
            raise ValueError("missing rewarded target scores at row %d" % index)

        rewarded = {name: float(scores[name]) for name in STRATEGIES}
        raw_scores = {name: float(raw[name]) for name in ALL_LABELS}
        semantic_primary = max(ALL_LABELS, key=lambda name: raw_scores[name])
        rewarded_primary = max(STRATEGIES, key=lambda name: rewarded[name])
        sorted_rewarded = sorted(rewarded.values(), reverse=True)

        judge_distribution[label] += 1
        semantic_distribution[semantic_primary] += 1
        rewarded_distribution[rewarded_primary] += 1
        rewarded_mass.append(sum(rewarded.values()))
        rewarded_top_margin.append(sorted_rewarded[0] - sorted_rewarded[1])
        hidden_type_score.append(rewarded[target_type])
        target_probabilities.append(float(record["target_p_a"]))
        judge_matches_semantic += int(label == semantic_primary)
        judge_matches_rewarded += int(label == rewarded_primary)
        if label in STRATEGIES:
            judge_strategy_rows += 1
            judge_strategy_matches_rewarded += int(label == rewarded_primary)

        condition = str(record.get("condition", ""))
        condition_match.setdefault(condition, []).append(int(label == target_type))
        if condition == "full_history":
            full_history_cells[target_type][label] += 1

    n = len(records)
    return {
        "n_records": n,
        "classifier_names": sorted(
            {str(record.get("classifier_name", "")) for record in records}
        ),
        "judge_primary_distribution": {
            label: judge_distribution[label] for label in ALL_LABELS
        },
        "target_semantic_argmax_distribution_four_way": {
            label: semantic_distribution[label] for label in ALL_LABELS
        },
        "target_rewarded_argmax_distribution_three_way": {
            label: rewarded_distribution[label] for label in STRATEGIES
        },
        "agreement": {
            "judge_primary_vs_target_semantic_four_way": judge_matches_semantic / n,
            "judge_primary_vs_target_rewarded_three_way": judge_matches_rewarded / n,
            "judge_strategy_only_vs_target_rewarded_three_way": (
                judge_strategy_matches_rewarded / judge_strategy_rows
                if judge_strategy_rows
                else None
            ),
            "n_judge_strategy_rows": judge_strategy_rows,
        },
        "score_statistics": {
            "rewarded_mass_sum_fairness_risk_expertise": _summary(rewarded_mass),
            "rewarded_top_minus_second_margin": _summary(rewarded_top_margin),
            "active_hidden_type_score": _summary(hidden_type_score),
            "realized_target_probability_a": _summary(target_probabilities),
        },
        "match_rate_by_condition": {
            condition: sum(values) / float(len(values))
            for condition, values in sorted(condition_match.items())
        },
        "full_history_judge_labels_by_target": {
            target: {label: full_history_cells[target][label] for label in ALL_LABELS}
            for target in STRATEGIES
        },
        "interpretation": (
            "This is a descriptive instrument profile, not a hypothesis test. "
            "Four-way target argmax includes unspent 'other' mass; three-way "
            "argmax asks which rewarded dimension is largest even when all are weak."
        ),
    }
