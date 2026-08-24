#!/usr/bin/env python3
"""Run a small pilot, analyse it, and write PILOT_REPORT.md.

Examples
--------
Offline pipeline check (no API key needed)::

    python scripts/run_pilot.py --provider mock:win_stay_lose_shift

Tiny real-model pilot (3 episodes, one condition)::

    export OPENAI_API_KEY=sk-...
    python scripts/run_pilot.py --provider openai --model gpt-4o-mini \\
        --conditions full_history --episodes 1 --rounds 8

The pilot is intentionally small.  Scale only after reading the report.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import dataclasses
import sys

from config import (
    DEFAULT_CONDITION_ORDER,
    ExperimentConfig,
    JudgeConfig,
    ModelConfig,
    TargetParams,
)
from src.analysis import format_summary, run_full_analysis
from src.experiment import build_episode_specs, run_experiment
from scripts.make_pilot_report import write_pilot_report


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--provider", default="mock:win_stay_lose_shift",
                   help="mock:<variant> | openai | anthropic")
    p.add_argument("--model", default="mock", help="model id for real providers")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-tokens", type=int, default=200)
    p.add_argument("--judge", default="keyword", choices=["keyword", "llm"])
    p.add_argument("--judge-provider", default="mock:judge")
    p.add_argument("--judge-model", default="mock")
    p.add_argument("--disjoint-lexicon", action="store_true",
                   help="keyword judge only: give the classifier and the target scorer disjoint lexicon halves")
    p.add_argument("--conditions", nargs="+", default=DEFAULT_CONDITION_ORDER)
    p.add_argument("--episodes", type=int, default=1,
                   help="scenario-sequence seeds; exact count is printed (swaps have six ordered pairs)")
    p.add_argument("--rounds", type=int, default=8)
    p.add_argument("--swap-round", type=int, default=5)
    p.add_argument("--seed", type=int, default=20250819)
    p.add_argument("--experiment-id", default="pilot")
    p.add_argument("--run-id", default=None)
    p.add_argument("--out-dir", default="data/raw")
    p.add_argument("--fig-dir", default="results/figures")
    p.add_argument("--tab-dir", default="results/tables")
    p.add_argument("--report", default="PILOT_REPORT.md")
    p.add_argument("--n-boot", type=int, default=2000)
    p.add_argument("--n-transcripts", type=int, default=3)
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--no-report", action="store_true")
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
        target_params=TargetParams(),
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
            disjoint_lexicon=args.disjoint_lexicon,
        ),
        out_dir=args.out_dir,
    )

    progress = None if args.quiet else (lambda s: print(s, flush=True))
    print("=" * 78)
    print("LatentTarget pilot")
    print("  provider      : %s (%s)" % (cfg.model.provider, cfg.model.model))
    print("  judge         : %s (%s)" % (cfg.judge.kind, cfg.judge.model))
    print("  conditions    : %s" % ", ".join(cfg.conditions))
    specs = build_episode_specs(cfg)
    print("  episode seeds : %d  ->  %d episodes / %d generations total"
          % (cfg.n_episode_seeds, len(specs), sum(spec.n_rounds for spec in specs)))
    print("  rounds        : %d (swap after %d)" % (cfg.n_rounds, cfg.swap_round))
    print("=" * 78)

    result = run_experiment(cfg, run_id=args.run_id, progress=progress)
    print("\nwrote %d records to %s" % (result.n_records, result.log_path))
    print("manifest: %s" % result.manifest_path)

    summary = run_full_analysis(
        result.log_path, args.fig_dir, args.tab_dir, n_boot=args.n_boot, seed=cfg.seed
    )
    print("\n" + format_summary(summary))

    if not args.no_report:
        path = write_pilot_report(
            log_path=result.log_path,
            manifest_path=result.manifest_path,
            summary=summary,
            out_path=args.report,
            n_transcripts=args.n_transcripts,
        )
        print("\npilot report: %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
