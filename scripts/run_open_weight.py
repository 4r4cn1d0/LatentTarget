#!/usr/bin/env python3
"""Run the experiment with a local open-weight focal model, capturing activations.

GPU pod only. Two modes, and you should run them in this order:

    # 1. CHEAP CHECK (no capture): does this model adapt at all in this
    #    environment? If it doesn't, there is no belief to decode and the
    #    probing extension is pointless. ~20 min on an A100 for the defaults.
    python scripts/run_open_weight.py --model Qwen/Qwen3.8-27B \
        --conditions full_history no_history --episodes 4 --no-capture

    # 2. FULL RUN with activation capture, once step 1 passes.
    python scripts/run_open_weight.py --model Qwen/Qwen3.8-27B \
        --conditions full_history no_history shuffled_history random_target swap \
        --episodes 8 --acts data/processed/acts_qwen38_27b.npz

Judging is a SEPARATE later pass over the saved messages
(`analyze_results.py --reclassify`), so the judge model never has to be in
memory at the same time as the focal model.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import sys

from config import (
    DEFAULT_CONDITION_ORDER,
    ExperimentConfig,
    JudgeConfig,
    ModelConfig,
    TargetScorerConfig,
)
from src.experiment import build_episode_specs, run_experiment
from src.hf_provider import HuggingFaceProvider


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", required=True, help="HF model id, e.g. Qwen/Qwen3.8-27B")
    p.add_argument("--conditions", nargs="+", default=DEFAULT_CONDITION_ORDER)
    p.add_argument("--episodes", type=int, default=8)
    p.add_argument("--rounds", type=int, default=8)
    p.add_argument("--swap-round", type=int, default=5)
    p.add_argument("--seed", type=int, default=20250819)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--top-p", type=float, default=0.8)
    p.add_argument("--top-k", type=int, default=20)
    p.add_argument("--enable-thinking", action="store_true",
                   help="NOT preregistered; default disables Qwen reasoning output")
    p.add_argument("--max-tokens", type=int, default=200)
    p.add_argument("--dtype", default="bfloat16")
    p.add_argument(
        "--target-scorer",
        choices=["keyword_v1", "semantic_nli_v2", "semantic_nli_v3"],
        default="semantic_nli_v3",
        help="controlled target reward instrument (real runs default to semantic v3)",
    )
    p.add_argument(
        "--target-scorer-device", default="auto",
        help="Transformers device for semantic_nli_v2 (default: auto)",
    )
    p.add_argument(
        "--target-scorer-dtype", default="float16",
        help="dtype for semantic_nli_v2 (default: float16)",
    )
    p.add_argument("--layer-stride", type=int, default=1)
    p.add_argument("--no-capture", action="store_true",
                   help="skip activation capture (behavioural check only)")
    p.add_argument("--acts", default="data/processed/activations.npz")
    p.add_argument("--out-dir", default="data/raw")
    p.add_argument("--run-id", default=None)
    p.add_argument("--experiment-id", default="openweight")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    cfg = ExperimentConfig(
        experiment_id=args.experiment_id,
        n_rounds=args.rounds,
        swap_round=args.swap_round,
        n_episode_seeds=args.episodes,
        seed=args.seed,
        conditions=list(args.conditions),
        target_scorer=TargetScorerConfig(
            kind=args.target_scorer,
            device=args.target_scorer_device,
            dtype=args.target_scorer_dtype,
        ),
        # The keyword classifier runs inline and is free; the real classification
        # pass happens afterwards with an LLM judge over the saved messages.
        judge=JudgeConfig(kind="keyword"),
        model=ModelConfig(provider="huggingface", model=args.model,
                          temperature=args.temperature, max_tokens=args.max_tokens),
        out_dir=args.out_dir,
    )

    provider = HuggingFaceProvider(
        model=args.model, temperature=args.temperature, max_tokens=args.max_tokens,
        dtype=args.dtype, layer_stride=args.layer_stride,
        capture=not args.no_capture, seed=args.seed,
        enable_thinking=args.enable_thinking, top_p=args.top_p, top_k=args.top_k,
    )

    specs = build_episode_specs(cfg)
    n_ep = len(specs)
    n_calls = sum(spec.n_rounds for spec in specs)
    print("=" * 78)
    print("open-weight run: %s" % args.model)
    print("  conditions : %s" % ", ".join(cfg.conditions))
    print("  episodes   : %d  (%d generations)" % (n_ep, n_calls))
    print("  capture    : %s" % (not args.no_capture))
    print("  scorer     : %s" % args.target_scorer)
    print("=" * 78)

    progress = None if args.quiet else (lambda s: print(s, flush=True))
    res = run_experiment(cfg, provider=provider, run_id=args.run_id,
                         progress=progress, keep_records=False)
    print("\nwrote %d records to %s" % (res.n_records, res.log_path))

    if not args.no_capture:
        store = provider.to_store()
        store.save(args.acts)
        print("activations: %s  shape=%s (rows, layers, d_model)"
              % (args.acts, tuple(store.acts.shape)))
        if store.n_rows != res.n_records:
            print("WARNING: %d activation rows vs %d log records -- investigate "
                  "before training any probe." % (store.n_rows, res.n_records))
        print("\nnext: python scripts/train_probe.py --log %s --acts %s"
              % (res.log_path, args.acts))
    else:
        print("\nnext: python scripts/analyze_results.py --log %s" % res.log_path)
        print("      ^ check full_history rises across rounds and no_history does not.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
