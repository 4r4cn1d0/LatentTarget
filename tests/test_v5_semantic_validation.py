from __future__ import annotations

from pathlib import Path

from config import STRATEGIES
from src.controlled_v5_messages import V5MessageBank
from src.v5_semantic_validation import (
    evaluate_v5_semantic_validation,
    semantic_candidate_rows,
)


POOL = Path(__file__).parents[1] / "data" / "v5" / "v5_candidate_pool_v1.json"


def _result(label, confidence=0.95):
    values = {frame: 0.05 for frame in (*STRATEGIES, "other")}
    values[label] = 0.90
    return {**values, "primary_strategy": label, "confidence": confidence}


def _perfect_results(rows):
    return {row["message"]: _result(row["intended_frame"]) for row in rows}


def _description(model):
    return {"provider": "test", "model": model, "judge_prompt_version": "test"}


def test_v5_two_judge_semantic_gate_passes_clean_distinct_judges():
    bank = V5MessageBank.load(str(POOL))
    rows = semantic_candidate_rows(bank)
    results = _perfect_results(rows)
    summary = evaluate_v5_semantic_validation(
        bank,
        results,
        results,
        _description("judge-a"),
        _description("judge-b"),
        {"ok": True},
        {"ok": True},
    )
    assert summary["pass"] is True
    assert summary["pool_sha256"] == bank.sha256()
    assert len(summary["eligible_candidate_ids"]) == 42
    assert summary["intended_labels_supplied_to_judges"] is False
    assert summary["judge_visible_fields"] == ["sample_id", "message"]


def test_ambiguous_candidates_are_excluded_before_bank_selection():
    bank = V5MessageBank.load(str(POOL))
    rows = semantic_candidate_rows(bank)
    primary = _perfect_results(rows)
    sensitivity = _perfect_results(rows)
    removed = []
    for frame in STRATEGIES:
        row = next(item for item in rows if item["intended_frame"] == frame)
        sensitivity[row["message"]] = _result("other")
        removed.append(row["candidate_id"])
    summary = evaluate_v5_semantic_validation(
        bank,
        primary,
        sensitivity,
        _description("judge-a"),
        _description("judge-b"),
        {"ok": True},
        {"ok": True},
    )
    assert summary["pass"] is True
    assert not set(removed) & set(summary["eligible_candidate_ids"])


def test_semantic_gate_fails_same_model_or_failed_artifact_audit():
    bank = V5MessageBank.load(str(POOL))
    rows = semantic_candidate_rows(bank)
    results = _perfect_results(rows)
    summary = evaluate_v5_semantic_validation(
        bank,
        results,
        results,
        _description("same"),
        _description("same"),
        {"ok": True},
        {"ok": False},
    )
    assert summary["pass"] is False
    assert summary["gates"]["judge_models_distinct"] is False
    assert summary["gates"]["both_artifact_audits_pass"] is False
