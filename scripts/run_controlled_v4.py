#!/usr/bin/env python3
"""Run the V4 controlled-choice task with mocks or a network provider.

This script does not load open-weight checkpoints locally. Use
``run_controlled_open_weight.py`` on a GPU host for that provider.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import sys

from config import (
    DEFAULT_CONTROLLED_CONDITION_ORDER,
    ControlledExperimentConfig,
    ControlledTargetParams,
    ModelConfig,
)
from src.controlled_experiment import (
    build_controlled_episode_specs,
    run_controlled_experiment,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default="mock:v4_bayesian")
    parser.add_argument("--model", default="mock-v4-bayesian")
    parser.add_argument("--revision", default=None,
                        help="optional immutable provider/model revision")
    parser.add_argument("--conditions", nargs="+", default=DEFAULT_CONTROLLED_CONDITION_ORDER)
    parser.add_argument("--episodes", type=int, default=4,
                        help="scenario-sequence seeds; each stable condition has 3x this many episodes")
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument("--swap-round", type=int, default=10)
    parser.add_argument("--heldout-start-round", type=int, default=16)
    parser.add_argument("--p-match", type=float, default=0.72)
    parser.add_argument("--p-mismatch", type=float, default=0.38)
    parser.add_argument("--p-random", type=float, default=0.50)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=96)
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--experiment-id", default="controlled_v4_development")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--out-dir", default="data/raw")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--resume", action="store_true",
                        help="resume a matching run at the next incomplete episode")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    cfg = ControlledExperimentConfig(
        experiment_id=args.experiment_id,
        n_rounds=args.rounds,
        swap_round=args.swap_round,
        heldout_start_round=args.heldout_start_round,
        n_episode_seeds=args.episodes,
        seed=args.seed,
        conditions=list(args.conditions),
        target_params=ControlledTargetParams(
            p_match=args.p_match,
            p_mismatch=args.p_mismatch,
            p_random=args.p_random,
        ),
        model=ModelConfig(
            provider=args.provider,
            model=args.model,
            revision=args.revision,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        ),
        out_dir=args.out_dir,
    )
    specs = build_controlled_episode_specs(cfg)
    print("LatentTarget V4 controlled-choice run")
    print("  provider: %s (%s)" % (cfg.model.provider, cfg.model.model))
    print("  conditions: %s" % ", ".join(cfg.conditions))
    print("  episodes: %d; generations: %d" % (
        len(specs), sum(spec.n_rounds for spec in specs)
    ))
    progress = None if args.quiet else (lambda message: print(message, flush=True))
    result = run_controlled_experiment(
        cfg=cfg, run_id=args.run_id, progress=progress, resume=args.resume
    )
    print("wrote %d rows to %s" % (result.n_records, result.log_path))
    print("manifest: %s" % result.manifest_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
