from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "run_controlled_open_weight.py"


def _run(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--run-id", "unit-dry-run", "--dry-run", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_open_weight_runner_accepts_the_exact_frozen_plan_without_loading_model():
    result = _run()
    assert result.returncode == 0, result.stderr
    assert "DRY RUN PASSED" in result.stdout


def test_open_weight_runner_rejects_checkpoint_drift_before_loading_model():
    result = _run("--episodes", "19")
    assert result.returncode != 0
    assert "planned run differs" in result.stderr
    assert "episode_count" in result.stderr
    assert "record_count" in result.stderr
