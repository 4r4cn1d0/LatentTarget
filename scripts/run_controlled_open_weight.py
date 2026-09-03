#!/usr/bin/env python3
"""Run V4 with a local Hugging Face open-weight model on a GPU host."""

from __future__ import annotations

import _bootstrap
import argparse
import json
import os
import sys

from config import (
    ControlledExperimentConfig,
    ControlledTargetParams,
    ModelConfig,
)
from src.controlled_experiment import build_controlled_episode_specs, run_controlled_experiment
from src.controlled_analysis import audit_frozen_checkpoint_plan
from src.hf_provider import HuggingFaceProvider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkpoint-spec",
        default=os.path.join(_bootstrap.ROOT, "docs", "behavioral_checkpoint_v4.json"),
        help="frozen pre-outcome checkpoint; unspecified run settings are read from it",
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--revision", default=None,
                        help="full immutable Hugging Face commit SHA")
    parser.add_argument("--conditions", nargs="+", default=None)
    parser.add_argument("--episodes", type=int, default=None)
    parser.add_argument("--rounds", type=int, default=None)
    parser.add_argument("--swap-round", type=int, default=None)
    parser.add_argument("--heldout-start-round", type=int, default=None)
    parser.add_argument("--p-match", type=float, default=None)
    parser.add_argument("--p-mismatch", type=float, default=None)
    parser.add_argument("--p-random", type=float, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--dtype", default=None)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--layer-stride", type=int, default=1)
    parser.add_argument("--capture", action="store_true",
                        help="for post-gate mechanistic pilots only; behavioral runs omit this")
    parser.add_argument("--enable-thinking", action="store_true")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--experiment-id", default="controlled_v4_checkpoint")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", default="data/raw")
    parser.add_argument("--activation-out", default=None)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--resume", action="store_true",
                        help="resume a matching run at the next incomplete episode")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate the frozen plan and manipulation gate without loading the model")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    with open(args.checkpoint_spec, "r", encoding="utf-8") as handle:
        checkpoint = json.load(handle)
    experiment = checkpoint["experiment"]
    target = checkpoint["target"]
    generation = checkpoint["generation"]
    primary_model = checkpoint["primary_model"]
    from src.controlled_focal_agent import set_spontaneous_prompt_variant
    prompt_variant = generation.get("prompt_variant", "v4")
    set_spontaneous_prompt_variant(prompt_variant)

    # The frozen file is the source of truth. Explicit CLI overrides remain
    # available for reproducibility checks, but any drift fails before model
    # loading through ``audit_frozen_checkpoint_plan`` below.
    args.model = args.model or primary_model["id"]
    args.revision = args.revision or primary_model["revision"]
    args.conditions = args.conditions or list(experiment["conditions"])
    args.episodes = args.episodes if args.episodes is not None else experiment["n_episode_seeds"]
    args.rounds = args.rounds if args.rounds is not None else experiment["n_rounds"]
    args.swap_round = args.swap_round if args.swap_round is not None else experiment["swap_round"]
    args.heldout_start_round = (
        args.heldout_start_round
        if args.heldout_start_round is not None
        else experiment["heldout_start_round"]
    )
    args.p_match = args.p_match if args.p_match is not None else target["p_match"]
    args.p_mismatch = (
        args.p_mismatch if args.p_mismatch is not None else target["p_mismatch"]
    )
    args.p_random = args.p_random if args.p_random is not None else target["p_random"]
    args.temperature = (
        args.temperature if args.temperature is not None else generation["temperature"]
    )
    args.top_p = args.top_p if args.top_p is not None else generation["top_p"]
    args.top_k = args.top_k if args.top_k is not None else generation["top_k"]
    args.max_tokens = (
        args.max_tokens if args.max_tokens is not None else generation["max_tokens"]
    )
    args.dtype = args.dtype or generation["dtype"]
    args.seed = args.seed if args.seed is not None else experiment["master_seed"]

    if args.capture and not args.activation_out:
        raise ValueError("--capture requires --activation-out")
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
            provider="huggingface",
            model=args.model,
            revision=args.revision,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        ),
        out_dir=args.out_dir,
    )
    specs = build_controlled_episode_specs(cfg)
    print("LatentTarget V4 open-weight run")
    print("  model: %s" % args.model)
    print("  spontaneous prompt variant: %s" % prompt_variant)
    print("  capture: %s" % args.capture)
    print("  episodes: %d; generations: %d" % (
        len(specs), sum(spec.n_rounds for spec in specs)
    ))
    provider = HuggingFaceProvider(
        model=args.model,
        revision=args.revision,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        device=args.device,
        dtype=args.dtype,
        layer_stride=args.layer_stride,
        capture=args.capture,
        seed=args.seed,
        enable_thinking=args.enable_thinking,
        top_p=args.top_p,
        top_k=args.top_k,
    )
    plan_audit = audit_frozen_checkpoint_plan(
        cfg,
        provider.describe(),
        expected_n_records=sum(spec.n_rounds for spec in specs),
        expected_n_episodes=len(specs),
        frozen_spec=checkpoint,
    )
    if not plan_audit["pass"]:
        failed = sorted(name for name, passed in plan_audit["checks"].items() if not passed)
        raise ValueError(
            "planned run differs from the frozen V4 checkpoint: %s" % ", ".join(failed)
        )

    validation_ref = checkpoint["message_bank"]["blind_validation"]
    validation_path = (
        validation_ref if os.path.isabs(validation_ref)
        else os.path.join(_bootstrap.ROOT, validation_ref)
    )
    with open(validation_path, "r", encoding="utf-8") as handle:
        bank_validation = json.load(handle)
    if not bank_validation.get("pass"):
        raise ValueError("the frozen message-bank manipulation check did not pass")
    if bank_validation.get("message_bank_sha256") != checkpoint["message_bank"]["sha256"]:
        raise ValueError("message-bank validation hash differs from the frozen checkpoint")

    print("  frozen checkpoint: %s" % args.checkpoint_spec)
    print("  blind message-bank gate: PASS")
    if args.dry_run:
        print("DRY RUN PASSED: no model loaded and no outcomes generated")
        return 0
    progress = None if args.quiet else (lambda message: print(message, flush=True))
    result = run_controlled_experiment(
        cfg=cfg, run_id=args.run_id, provider=provider, progress=progress,
        resume=args.resume,
    )
    print("wrote %d rows to %s" % (result.n_records, result.log_path))
    print("manifest: %s" % result.manifest_path)
    if args.capture:
        parent = os.path.dirname(args.activation_out)
        if parent:
            os.makedirs(parent, exist_ok=True)
        provider.to_store().save(args.activation_out)
        print("activations: %s" % args.activation_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
