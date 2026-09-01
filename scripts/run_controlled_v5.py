#!/usr/bin/env python3
"""Run local/mock V5 controlled-choice implementation checks."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import sys

from config import ControlledExperimentConfig, ControlledTargetParams, ModelConfig
from src.controlled_experiment import run_controlled_experiment
from src.controlled_v5_messages import make_v5_protocol


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", default="data/v5/v5_candidate_pool_v1.json")
    parser.add_argument("--provider", default="mock:v5_bayesian")
    parser.add_argument("--episode-seeds", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20261001)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", default="data/raw")
    args = parser.parse_args(argv)
    cfg = ControlledExperimentConfig(
        experiment_id="controlled_v5_local_validation",
        n_rounds=24,
        swap_round=12,
        heldout_start_round=19,
        n_episode_seeds=args.episode_seeds,
        seed=args.seed,
        conditions=[
            "full_history",
            "no_history",
            "shuffled_history",
            "random_target",
            "swap",
        ],
        target_params=ControlledTargetParams(),
        model=ModelConfig(provider=args.provider, model="mock", max_tokens=2),
        out_dir=args.out_dir,
    )
    result = run_controlled_experiment(
        cfg,
        run_id=args.run_id,
        protocol=make_v5_protocol(args.bank),
    )
    print("wrote %d rows to %s" % (result.n_records, result.log_path))
    print("manifest: %s" % result.manifest_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
