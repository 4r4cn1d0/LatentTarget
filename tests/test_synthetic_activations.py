import importlib.util
from pathlib import Path
import sys

import numpy as np

from config import ExperimentConfig, JudgeConfig, ModelConfig
from src.experiment import run_experiment
from src.probing import ActivationStore


def _module():
    path = Path(__file__).parents[1] / "scripts" / "generate_synthetic_activations.py"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("generate_synthetic_activations", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_synthetic_activation_generator_aligns_to_mock_log(tmp_path):
    cfg = ExperimentConfig(
        experiment_id="synthetic_fixture", n_episode_seeds=1,
        conditions=["full_history"],
        model=ModelConfig(provider="mock:round_robin", model="mock"),
        judge=JudgeConfig(kind="keyword"), out_dir=str(tmp_path),
    )
    mock_run_small = run_experiment(cfg, run_id="synthetic_fixture")
    out = str(tmp_path / "acts.npz")
    first = _module().generate(mock_run_small.log_path, out, d_model=12, n_layers=4, seed=3)
    loaded = ActivationStore.load(out)
    assert loaded.acts.shape == first.acts.shape
    assert loaded.d_model == 12 and loaded.n_layers == 4
    assert loaded.meta[0]["synthetic_oracle_activation"] is True
    assert np.isfinite(loaded.acts).all()
