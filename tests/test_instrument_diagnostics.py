"""Tests for deterministic behavioral-instrument diagnostics."""

from __future__ import annotations

import pytest

from src.instrument_diagnostics import summarize_instrument


def _row(label, target, raw, condition="full_history"):
    return {
        "primary_strategy": label,
        "classifier_name": "blind-judge",
        "hidden_target_type": target,
        "condition": condition,
        "target_p_a": 0.4,
        "target_scores": {
            "fairness": raw["fairness"],
            "risk": raw["risk"],
            "expertise": raw["expertise"],
            "raw_scores": raw,
        },
    }


def test_instrument_summary_distinguishes_four_way_and_rewarded_argmax():
    records = [
        _row(
            "other",
            "fairness",
            {"fairness": 0.10, "risk": 0.05, "expertise": 0.05, "other": 0.80},
        ),
        _row(
            "risk",
            "risk",
            {"fairness": 0.10, "risk": 0.60, "expertise": 0.20, "other": 0.10},
            "no_history",
        ),
    ]
    summary = summarize_instrument(records)
    assert summary["n_records"] == 2
    assert summary["target_semantic_argmax_distribution_four_way"]["other"] == 1
    assert summary["target_rewarded_argmax_distribution_three_way"]["fairness"] == 1
    assert summary["agreement"]["judge_primary_vs_target_semantic_four_way"] == 1.0
    assert summary["agreement"]["judge_primary_vs_target_rewarded_three_way"] == 0.5
    assert summary["score_statistics"]["rewarded_mass_sum_fairness_risk_expertise"][
        "mean"
    ] == pytest.approx(0.55)
    assert summary["match_rate_by_condition"] == {
        "full_history": 0.0,
        "no_history": 1.0,
    }


def test_instrument_summary_rejects_unknown_label():
    record = _row(
        "other",
        "risk",
        {"fairness": 0.2, "risk": 0.3, "expertise": 0.1, "other": 0.4},
    )
    record["primary_strategy"] = "mystery"
    with pytest.raises(ValueError, match="unknown primary strategy"):
        summarize_instrument([record])
