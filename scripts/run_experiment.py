#!/usr/bin/env python3
"""Run the full experiment (all conditions, many episodes) and log it.

Only run this after the pilot checkpoint has been reviewed.  Cost scales as
``episodes x 3 target types x conditions x rounds`` focal-model calls, plus the
same number of judge calls if ``--judge llm`` is used.

    python scripts/run_experiment.py --provider openai --model gpt-4o-mini \\
        --episodes 20 --judge llm --judge-provider openai --judge-model gpt-4o-mini
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import sys

from config import DEFAULT_CONDITION_ORDER, ExperimentConfig, JudgeConfig, ModelConfig, TargetParams
from src.experiment import build_episode_specs, run_experiment


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--provider", default="mock:win_stay_lose_shift")
    p.add_argument("--model", default="mock")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-tokens", type=int, default=200)
    p.add_argument("--judge", default="keyword", choices=["keyword", "llm"])
    p.add_argument("--judge-provider", default="mock:judge")
    p.add_argument("--judge-model", default="mock")
    p.add_argument("--judge-cache", default="data/processed/judge_cache.jsonl")
    p.add_argument("--disjoint-lexicon", action="store_true")
    p.add_argument("--conditions", nargs="+", default=DEFAULT_CONDITION_ORDER)
    p.add_argument("--episodes", type=int, default=20)
    p.add_argument("--rounds", type=int, default=8)
    p.add_argument("--swap-round", type=int, default=5)
    p.add_argument("--seed", type=int, default=20250819)
    p.add_argument("--experiment-id", default="main")
    p.add_argument("--run-id", default=None)
    p.add_argument("--out-dir", default="data/raw")
    # Target-simulator sweep knobs (for the robustness check).
    p.add_argument("--base-bias", type=float, default=TargetParams().base_bias)
    p.add_argument("--w-match", type=float, default=TargetParams().w_match)
    p.add_argument("--w-off", type=float, default=TargetParams().w_off)
    p.add_argument("--logit-noise-sd", type=float, default=TargetParams().logit_noise_sd)
    p.add_argument("--saturation-k", type=int, default=TargetParams().saturation_k)
    p.add_argument("--random-p-a", type=float, default=TargetParams().random_p_a)
    p.add_argument("--quiet", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    cfg = ExperimentConfig(
        experiment_id=args.experiment_id,
        n_rounds=args.rounds,
        swap_round=args.swap_round,
        n_episode_seeds=args.episodes,
        seed=args.seed,
        conditions=list(args.conditions),
        target_params=TargetParams(
            base_bias=args.base_bias,
            w_match=args.w_match,
            w_off=args.w_off,
            logit_noise_sd=args.logit_noise_sd,
            saturation_k=args.saturation_k,
            random_p_a=args.random_p_a,
        ),
        model=ModelConfig(
            provider=args.provider,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        ),
        judge=JudgeConfig(
            kind=args.judge,
            provider=args.judge_provider,
            model=args.judge_model,
            cache_path=args.judge_cache,
            disjoint_lexicon=args.disjoint_lexicon,
        ),
        out_dir=args.out_dir,
    )
    specs = build_episode_specs(cfg)
    n_episodes = len(specs)
    n_calls = sum(spec.n_rounds for spec in specs)
    print("about to run %d episodes (%d focal-model calls)"
          % (n_episodes, n_calls))
    progress = None if args.quiet else (lambda s: print(s, flush=True))
    res = run_experiment(cfg, run_id=args.run_id, progress=progress, keep_records=False)
    print("\nwrote %d records to %s" % (res.n_records, res.log_path))
    print("manifest: %s" % res.manifest_path)
    print("\nnext: python scripts/analyze_results.py --log %s" % res.log_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
