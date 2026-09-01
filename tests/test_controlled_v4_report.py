from __future__ import annotations

import json

from config import ControlledExperimentConfig, ModelConfig
from scripts.make_controlled_v4_report import render_report
from src.controlled_analysis import evaluate_controlled_checkpoint
from src.controlled_experiment import run_controlled_experiment


def test_v4_report_uses_three_fixed_complete_target_balanced_transcripts(tmp_path):
    cfg = ControlledExperimentConfig(
        experiment_id="report-test",
        n_rounds=8,
        swap_round=4,
        heldout_start_round=7,
        n_episode_seeds=1,
        conditions=["full_history", "no_history", "shuffled_history", "random_target", "swap"],
        model=ModelConfig(provider="mock:v4_bayesian", model="mock"),
        out_dir=str(tmp_path),
    )
    result = run_controlled_experiment(cfg, run_id="report")
    manifest = json.load(open(result.manifest_path, encoding="utf-8"))
    summary = evaluate_controlled_checkpoint(
        result.records, manifest, n_boot=50, n_perm=100, seed=1
    )
    report = render_report(result.records, manifest, summary)
    assert report.count("### `full_history-000-") == 3
    assert report.count("#### Round ") == 24
    assert "MOCK/SYNTHETIC ONLY" in report
    assert "Hidden target (not model-visible): **fairness**" in report
    assert "Hidden target (not model-visible): **risk**" in report
    assert "Hidden target (not model-visible): **expertise**" in report
    assert "### Exact round-1 user prompt" in report
    assert "### Exact history-bearing user prompt" in report
    assert "--- Previous interactions ---" in report

    real_manifest = json.loads(json.dumps(manifest))
    real_manifest["provider"]["provider"] = "huggingface"
    real_manifest["provider"]["model"] = "Qwen/example"
    real_summary = json.loads(json.dumps(summary))
    real_summary["decision"] = "STOP_BEFORE_FREEFORM_OR_MECHANISTIC_SCALING"
    real_summary["effect_gates"]["silent_swap_new_over_old"] = True
    real_summary["swap_metrics"]["late_new_over_old"]["mean"] = 0.0
    real_report = render_report(result.records, real_manifest, real_summary)
    assert real_report.startswith("# LatentTarget V4 real-model behavioral checkpoint")
    assert "REAL-MODEL CONTROLLED-CHOICE CHECKPOINT" in real_report
    assert "MOCK/SYNTHETIC ONLY" not in real_report
    assert "Treat it substantively as zero" in real_report
