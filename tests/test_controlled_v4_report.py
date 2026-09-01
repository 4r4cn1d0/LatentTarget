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
