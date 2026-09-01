from __future__ import annotations

import json
from pathlib import Path

import pytest

from config import ControlledExperimentConfig, ModelConfig
from src.controlled_experiment import run_controlled_experiment
from src.controlled_v5_analysis import evaluate_controlled_v5_checkpoint
from src.controlled_v5_messages import make_v5_protocol
from src.focal_agent import ProviderError


POOL = Path(__file__).parents[1] / "data" / "v5" / "v5_candidate_pool_v1.json"
CONDITIONS = [
    "full_history",
    "no_history",
    "shuffled_history",
    "random_target",
    "swap",
]


def _config(tmp_path, provider: str, n_seeds: int = 8):
    return ControlledExperimentConfig(
        experiment_id="v5-test",
        n_rounds=24,
        swap_round=12,
        heldout_start_round=19,
        n_episode_seeds=n_seeds,
        seed=20261001,
        conditions=list(CONDITIONS),
        model=ModelConfig(provider=provider, model="mock", max_tokens=2),
        out_dir=str(tmp_path),
    )


def _run_and_evaluate(tmp_path, provider: str, run_id: str):
    result = run_controlled_experiment(
        _config(tmp_path, provider),
        run_id=run_id,
        protocol=make_v5_protocol(str(POOL)),
    )
    manifest = json.load(open(result.manifest_path, encoding="utf-8"))
    summary = evaluate_controlled_v5_checkpoint(
        result.records, manifest, n_boot=150, n_perm=800, seed=17
    )
    return result, manifest, summary


def test_v5_bayesian_positive_control_passes_all_local_gates(tmp_path):
    result, manifest, summary = _run_and_evaluate(
        tmp_path, "mock:v5_bayesian", "positive"
    )
    assert result.n_episodes == 18 * 8
    assert result.n_records == 18 * 8 * 24
    assert manifest["task_version"] == "controlled-choice-v5.0"
    assert manifest["selection_policy"] == {
        "strict_selection": True,
        "constrained_choices": ["1", "2", "3"],
        "invalid_output_policy": "abort episode; no fallback",
    }
    assert summary["pattern_pass"] is True
    assert summary["scientific_pass"] is False
    assert summary["decision"] == "MOCK_V5_PIPELINE_PASS_NOT_SCIENTIFIC_EVIDENCE"
    assert all(summary["effect_gates"].values())
    assert all(summary["inference_gates"].values())
    assert summary["primary_contrasts"][
        "stable_full_vs_no_difference_in_differences"
    ]["n_blocks"] == 8
    assert summary["swap_metrics"]["revision_shift"]["n_episode_values"] == 48


def test_v5_random_policy_fails_learning_and_revision(tmp_path):
    _, _, summary = _run_and_evaluate(tmp_path, "mock:v4_random", "random")
    assert summary["pattern_pass"] is False
    assert not summary["effect_gates"]["stable_difference_in_differences"]
    assert not summary["effect_gates"]["baseline_adjusted_revision"]


def test_v5_asymmetric_prior_cannot_hide_behind_aggregate_revision(tmp_path):
    _, _, summary = _run_and_evaluate(
        tmp_path, "mock:v5_biased_bayesian", "biased"
    )
    assert summary["pattern_pass"] is False
    assert summary["effect_gates"]["no_history_bank_balance"] is False
    assert summary["effect_gates"]["all_target_types_supported"] is False
    assert summary["no_history_frame_balance"]["overall"]["shares"]["expertise"] == 1.0


def test_v5_invalid_output_aborts_without_fallback_record(tmp_path):
    with pytest.raises(ProviderError, match="strict controlled protocol"):
        run_controlled_experiment(
            _config(tmp_path, "mock:v4_invalid", n_seeds=1),
            run_id="invalid",
            protocol=make_v5_protocol(str(POOL)),
        )
    manifest = json.load(open(tmp_path / "invalid.manifest.json", encoding="utf-8"))
    assert manifest["run_status"] == "running"
    log = tmp_path / "invalid.jsonl"
    assert not log.exists() or not log.read_text(encoding="utf-8")


def test_v5_analysis_detects_fallback_tampering(tmp_path):
    result, manifest, _ = _run_and_evaluate(
        tmp_path, "mock:v5_bayesian", "tamper"
    )
    changed = [dict(row) for row in result.records]
    changed[0]["fallback_used"] = True
    changed[0]["selection_valid"] = False
    summary = evaluate_controlled_v5_checkpoint(
        changed, manifest, n_boot=50, n_perm=100, seed=2
    )
    assert summary["effect_gates"]["design_integrity"] is False
    assert summary["effect_gates"]["all_selections_valid"] is False
    assert summary["effect_gates"]["no_fallback"] is False
