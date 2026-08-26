from __future__ import annotations

import json
import os
import subprocess
import sys

from config import ExperimentConfig, JudgeConfig, ModelConfig
from src.experiment import run_experiment


def test_bayesian_script_writes_outputs(tmp_path):
    raw = tmp_path / "raw"
    tables = tmp_path / "tables"
    figures = tmp_path / "figures"
    cfg = ExperimentConfig(
        experiment_id="bayes-script",
        n_rounds=4,
        swap_round=2,
        n_episode_seeds=2,
        conditions=["full_history", "no_history", "swap"],
        model=ModelConfig(provider="mock:win_stay_lose_shift", model="mock"),
        judge=JudgeConfig(kind="keyword"),
        out_dir=str(raw),
    )
    result = run_experiment(cfg, run_id="bayes-script", keep_records=False)
    cmd = [
        sys.executable, "scripts/analyze_bayesian_observer.py",
        "--log", result.log_path,
        "--hazards", "0.1", "0.0",
        "--n-boot", "100",
        "--out-dir", str(tables),
        "--fig-dir", str(figures),
    ]
    completed = subprocess.run(cmd, cwd=os.getcwd(), text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    assert (tables / "bayesian_observer_trajectory.csv").exists()
    assert (figures / "fig8_bayesian_observer.png").exists()
    payload = json.loads((tables / "bayesian_observer_summary.json").read_text())
    assert payload["primary_hazard"] == 0.1
    assert payload["sensitivity_hazards"] == [0.0]


def test_bayesian_script_handles_stable_only_run_without_legend_warning(tmp_path):
    raw = tmp_path / "raw"
    tables = tmp_path / "tables"
    figures = tmp_path / "figures"
    cfg = ExperimentConfig(
        experiment_id="bayes-stable",
        n_rounds=3,
        n_episode_seeds=1,
        conditions=["full_history", "no_history"],
        model=ModelConfig(provider="mock:win_stay_lose_shift", model="mock"),
        judge=JudgeConfig(kind="keyword"),
        out_dir=str(raw),
    )
    result = run_experiment(cfg, run_id="bayes-stable", keep_records=False)
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_bayesian_observer.py",
            "--log",
            result.log_path,
            "--hazards",
            "0.1",
            "--n-boot",
            "50",
            "--out-dir",
            str(tables),
            "--fig-dir",
            str(figures),
        ],
        cwd=os.getcwd(),
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "No artists with labels" not in completed.stderr
    assert (figures / "fig8_bayesian_observer.png").exists()


def test_bayesian_script_refuses_missing_manifest(tmp_path):
    log = tmp_path / "orphan.jsonl"
    log.write_text("{}\n")
    completed = subprocess.run(
        [sys.executable, "scripts/analyze_bayesian_observer.py", "--log", str(log)],
        cwd=os.getcwd(), text=True, capture_output=True,
    )
    assert completed.returncode != 0
    assert "manifest not found" in completed.stderr
