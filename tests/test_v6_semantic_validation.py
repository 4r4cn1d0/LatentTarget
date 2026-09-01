from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from config import CONTROLLED_V6_SEMANTIC_THRESHOLDS, STRATEGIES
from src.v6_semantic_validation import (
    evaluate_v6_semantic_validation,
    semantic_candidate_rows,
)


POOL = Path(__file__).parents[1] / "data" / "v6" / "v6_triad_pool_v1.json"


def _pool():
    return json.loads(POOL.read_text(encoding="utf-8"))


def _pool_sha256(pool):
    canonical = json.dumps(
        pool, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _result(label, confidence=0.95):
    values = {frame: 0.05 for frame in (*STRATEGIES, "other")}
    values[label] = 0.90
    return {**values, "primary_strategy": label, "confidence": confidence}


def _perfect_results(rows):
    return {
        row["message"]: _result(row["intended_frame"])
        for row in rows
    }


def _description(model):
    return {"provider": "test", "model": model, "judge_prompt_version": "test"}


def _evaluate(bank, primary, sensitivity, primary_model="judge-a", audit_ok=True):
    return evaluate_v6_semantic_validation(
        bank,
        primary,
        sensitivity,
        _description(primary_model),
        _description("judge-b"),
        {"ok": audit_ok},
        {"ok": True},
    )


def test_v6_two_judge_semantic_gate_passes_clean_distinct_judges():
    bank = _pool()
    rows = semantic_candidate_rows(bank)
    results = _perfect_results(rows)

    summary = _evaluate(bank, results, results)

    assert summary["pass"] is True
    assert summary["pool_sha256"] == _pool_sha256(bank)
    assert summary["n_candidates"] == 60
    assert summary["n_triads"] == 20
    assert summary["eligible_counts"] == {"development": 12, "heldout": 8}
    assert len(summary["eligible_triad_ids"]) == 20
    assert len(summary["eligible_candidate_ids"]) == 60
    assert summary["thresholds_frozen_before_judging"] == (
        CONTROLLED_V6_SEMANTIC_THRESHOLDS
    )
    assert summary["judge_visible_fields"] == ["sample_id", "message"]
    assert summary["intended_metadata_supplied_to_judges"] is False
    assert summary["metadata_joined_after_both_judge_calls"] is True
    assert summary["intended_metadata_fields"] == [
        "intended_frame",
        "triad_id",
        "split",
    ]
    assert all("{a}" not in row["message"] for row in rows)


@pytest.mark.parametrize(
    "failed_check", ["confidence", "intended_score", "score_margin"]
)
def test_one_failed_candidate_excludes_its_complete_triad_only(failed_check):
    bank = _pool()
    rows = semantic_candidate_rows(bank)
    primary = _perfect_results(rows)
    sensitivity = _perfect_results(rows)
    failed = rows[0]
    failed_result = _result(failed["intended_frame"])
    if failed_check == "confidence":
        failed_result["confidence"] = 0.70
    elif failed_check == "intended_score":
        failed_result[failed["intended_frame"]] = 0.59
    else:
        failed_result[failed["intended_frame"]] = 0.60
        failed_result["other"] = 0.41
    sensitivity[failed["message"]] = failed_result

    summary = _evaluate(bank, primary, sensitivity)

    assert summary["pass"] is True
    assert failed["triad_id"] not in summary["eligible_triad_ids"]
    assert len(summary["eligible_candidate_ids"]) == 59
    assert len(summary["eligible_triad_candidate_ids"]) == 57
    members = [
        row
        for row in summary["candidate_results"]
        if row["triad_id"] == failed["triad_id"]
    ]
    assert len(members) == 3
    assert sum(row["passes_both_judges"] for row in members) == 2
    assert all(row["triad_eligible"] is False for row in members)
    failed_summary = next(
        row for row in members if row["candidate_id"] == failed["candidate_id"]
    )
    assert failed_summary["sensitivity_checks"][failed_check] is False


def test_minimum_eligible_triad_count_is_a_gate_even_with_perfect_labels():
    bank = _pool()
    rows = semantic_candidate_rows(bank)
    primary = _perfect_results(rows)
    sensitivity = _perfect_results(rows)
    development_triads = list(
        dict.fromkeys(
            row["triad_id"] for row in rows if row["split"] == "development"
        )
    )
    for triad_id in development_triads[:7]:
        failed = next(row for row in rows if row["triad_id"] == triad_id)
        sensitivity[failed["message"]] = _result(
            failed["intended_frame"], confidence=0.70
        )

    summary = _evaluate(bank, primary, sensitivity)

    assert summary["pass"] is False
    assert summary["eligible_counts"]["development"] == 5
    assert summary["gates"]["enough_development_triads"] is False
    assert summary["gates"]["primary_accuracy"] is True
    assert summary["gates"]["sensitivity_accuracy"] is True
    assert summary["gates"]["interjudge_kappa"] is True


def test_interjudge_kappa_gates_at_accuracy_and_recall_boundaries():
    bank = _pool()
    rows = semantic_candidate_rows(bank)
    primary = _perfect_results(rows)
    sensitivity = _perfect_results(rows)
    triad_ids = list(dict.fromkeys(row["triad_id"] for row in rows))
    chosen = triad_ids[:3] + triad_ids[12:15]
    for index, triad_id in enumerate(chosen):
        fairness = next(
            row
            for row in rows
            if row["triad_id"] == triad_id
            and row["intended_frame"] == "fairness"
        )
        expertise = next(
            row
            for row in rows
            if row["triad_id"] == triad_id
            and row["intended_frame"] == "expertise"
        )
        primary_error = fairness if index < 3 else expertise
        sensitivity_error = expertise if index < 3 else fairness
        primary[primary_error["message"]] = _result("risk")
        sensitivity[sensitivity_error["message"]] = _result("risk")

    summary = _evaluate(bank, primary, sensitivity)

    assert summary["primary_metrics"]["accuracy"] == 0.90
    assert summary["sensitivity_metrics"]["accuracy"] == 0.90
    assert min(
        summary["primary_metrics"]["recall_by_intended_frame"].values()
    ) == 0.85
    assert min(
        summary["sensitivity_metrics"]["recall_by_intended_frame"].values()
    ) == 0.85
    assert summary["gates"]["primary_accuracy"] is True
    assert summary["gates"]["primary_all_class_recall"] is True
    assert summary["gates"]["sensitivity_accuracy"] is True
    assert summary["gates"]["sensitivity_all_class_recall"] is True
    assert summary["interjudge_kappa"] < 0.70
    assert summary["gates"]["interjudge_kappa"] is False
    assert summary["pass"] is False


def test_semantic_gate_fails_same_model_or_failed_artifact_audit():
    bank = _pool()
    rows = semantic_candidate_rows(bank)
    results = _perfect_results(rows)

    summary = _evaluate(
        bank, results, results, primary_model="judge-b", audit_ok=False
    )

    assert summary["pass"] is False
    assert summary["gates"]["judge_models_distinct"] is False
    assert summary["gates"]["both_artifact_audits_pass"] is False


def test_semantic_gate_requires_exact_message_coverage():
    bank = _pool()
    rows = semantic_candidate_rows(bank)
    primary = _perfect_results(rows)
    sensitivity = _perfect_results(rows)
    primary.pop(next(iter(primary)))

    with pytest.raises(ValueError, match="exactly cover"):
        _evaluate(bank, primary, sensitivity)


def test_undefined_kappa_fails_closed_and_remains_json_serializable():
    bank = _pool()
    rows = semantic_candidate_rows(bank)
    identical_single_label = {
        row["message"]: _result("fairness") for row in rows
    }

    summary = _evaluate(
        bank, identical_single_label, identical_single_label
    )

    assert summary["interjudge_kappa"] is None
    assert summary["interjudge_kappa_defined"] is False
    assert summary["gates"]["interjudge_kappa"] is False
    assert summary["pass"] is False
    json.dumps(summary, allow_nan=False)


def _load_cli_module(monkeypatch):
    script = POOL.parents[2] / "scripts" / "validate_v6_semantic_bank.py"
    monkeypatch.syspath_prepend(str(script.parent))
    spec = importlib.util.spec_from_file_location(
        "validate_v6_semantic_bank_test", script
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_defaults_and_flow_pass_only_message_text_to_fake_judges(
    tmp_path, monkeypatch, capsys
):
    cli = _load_cli_module(monkeypatch)
    defaults = cli.build_parser().parse_args([])
    assert defaults.bank == "data/v6/v6_triad_pool_v1.json"
    assert defaults.primary_model == "gpt-5.6-sol"
    assert defaults.sensitivity_model == "gpt-5.6-luna"
    assert defaults.out_dir == "results/v6_design/semantic_validation"
    assert defaults.cache_dir == "data/processed/v6_semantic_validation"

    rows = semantic_candidate_rows(_pool())
    intended_by_message = {
        row["message"]: row["intended_frame"] for row in rows
    }
    calls = []

    class FakeJudge:
        def __init__(self, model):
            self.model = model

        def describe(self):
            return _description(self.model)

    def fake_run_judge(
        messages, model, cache, artifacts, batch_size, seed, executable, timeout
    ):
        messages = list(messages)
        calls.append((model, messages))
        assert len(messages) == 60
        assert all(isinstance(message, str) for message in messages)
        return (
            FakeJudge(model),
            {
                message: _result(intended_by_message[message])
                for message in messages
            },
            {"ok": True, "models": [model]},
        )

    monkeypatch.setattr(cli, "_run_judge", fake_run_judge)
    out_dir = tmp_path / "out"
    cache_dir = tmp_path / "cache"
    exit_code = cli.main(
        [
            "--bank",
            str(POOL),
            "--out-dir",
            str(out_dir),
            "--cache-dir",
            str(cache_dir),
        ]
    )

    assert exit_code == 0
    assert [model for model, _ in calls] == ["gpt-5.6-sol", "gpt-5.6-luna"]
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["pass"] is True
    assert summary["pool_sha256"] == _pool_sha256(_pool())
    assert summary["pool_source_file_sha256"]
    assert "PASS" in capsys.readouterr().out
