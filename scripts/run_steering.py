#!/usr/bin/env python3
"""Run paired causal interventions using a fitted target-type probe.

GPU pod only. This is a post-hoc generation experiment over untouched probe-
test prompts. For each prompt and proposed target class, target, opposite,
random-norm-matched, and zero-vector interventions share the same sampling
seed. Messages are classified from text alone after generation.

The default coefficients (1, 3, 6 residual-norm units) are a predeclared
dose-response grid, not values selected after seeing outcomes.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import hashlib
import json
import os
import sys

from config import STRATEGIES
from src.focal_agent import clean_message
from src.hf_provider import HuggingFaceProvider
from src.logging_utils import JsonlWriter, read_jsonl, write_manifest
from src.probing import Probe
from src.seeding import derive_seed
from src.steering import intervention_directions
from src.strategy_classifier import KeywordStrategyClassifier


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _select_prompts(records, allowed_episodes, maximum):
    candidates = [
        row for row in records
        if row["episode_id"] in allowed_episodes
        and row["condition"] == "full_history"
        and not row["swap_condition"]
    ]
    candidates.sort(key=lambda row: (int(row["round"]), str(row["episode_id"])))
    # Deterministic round-robin over hidden types is used only for sampling the
    # prompt set. Every selected prompt is steered toward all three classes.
    chosen = []
    by_type = {
        target: [row for row in candidates if row["hidden_target_type"] == target]
        for target in STRATEGIES
    }
    while len(chosen) < maximum and any(by_type.values()):
        for target in STRATEGIES:
            if by_type[target] and len(chosen) < maximum:
                chosen.append(by_type[target].pop(0))
    return chosen


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--log", required=True)
    parser.add_argument("--probe", required=True)
    parser.add_argument("--probe-summary", required=True,
                        help="probe_summary.json containing untouched test episode IDs")
    parser.add_argument("--model", default=None)
    parser.add_argument("--out", default="data/raw/steering.jsonl")
    parser.add_argument("--max-prompts", type=int, default=12)
    parser.add_argument("--coefficients", nargs="+", type=float, default=[1.0, 3.0, 6.0])
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=200)
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--seed", type=int, default=20250819)
    args = parser.parse_args(argv)
    if args.max_prompts < 1:
        parser.error("--max-prompts must be positive")
    if any(value <= 0 for value in args.coefficients):
        parser.error("--coefficients must all be positive")
    if os.path.exists(args.out):
        parser.error("output already exists; choose a new --out path to avoid duplicate trials")

    records = list(read_jsonl(args.log))
    with open(args.probe_summary, "r", encoding="utf-8") as fh:
        summary = json.load(fh)
    test_episodes = set(summary["split_episode_ids"]["test"])
    prompts = _select_prompts(records, test_episodes, args.max_prompts)
    if not prompts:
        parser.error("no untouched full_history test prompts found")
    model_names = sorted(set(str(row["model_name"]) for row in prompts))
    model = args.model or (model_names[0] if len(model_names) == 1 else None)
    if model is None:
        parser.error("log has multiple model names; pass --model")
    if len(model_names) == 1 and model != model_names[0]:
        parser.error("--model differs from the focal model in the selected prompts")

    probe = Probe.load(args.probe)
    layer = int(summary["best_layer"])
    provider = HuggingFaceProvider(
        model=model, temperature=args.temperature, max_tokens=args.max_tokens,
        dtype=args.dtype, capture=False, seed=args.seed,
    )
    classifier = KeywordStrategyClassifier()
    n = 0
    with JsonlWriter(args.out, validate=False) as writer:
        for prompt_index, source in enumerate(prompts):
            for steer_target in STRATEGIES:
                directions = intervention_directions(
                    probe, steer_target,
                    seed=derive_seed(args.seed, source["episode_id"], source["round"], steer_target),
                )
                jobs = list(
                    (condition, coefficient)
                    for coefficient in args.coefficients
                    for condition in ("zero", "target", "opposite", "random")
                )
                for condition, coefficient in jobs:
                    paired_seed = derive_seed(
                        args.seed, "steering", prompt_index, steer_target, coefficient
                    )
                    raw = provider.generate_with_steering(
                        source["focal_system_prompt"], source["focal_user_prompt"],
                        layer, directions[condition], coefficient, paired_seed,
                    )
                    message = clean_message(raw)
                    classification = classifier.classify(message)
                    writer.write({
                        "source_episode_id": source["episode_id"],
                        "source_round": source["round"],
                        "source_active_target": source["hidden_target_type"],
                        "steer_target": steer_target,
                        "intervention": condition,
                        "coefficient": coefficient,
                        "hidden_state_index": layer,
                        "paired_seed": paired_seed,
                        "focal_system_prompt": source["focal_system_prompt"],
                        "focal_user_prompt": source["focal_user_prompt"],
                        "message_raw": raw,
                        "message": message,
                        "strategy_classification": classification.as_dict(),
                        "model_name": model,
                    })
                    n += 1
                    print("[%d] %s r%s -> %s/%s@%g: %s" % (
                        n, source["episode_id"], source["round"], steer_target,
                        condition, coefficient, classification.primary_strategy,
                    ), flush=True)

    manifest_path = args.out[:-6] + ".manifest.json" if args.out.endswith(".jsonl") else args.out + ".manifest.json"
    write_manifest(manifest_path, {
        "kind": "probe_direction_steering",
        "source_log": args.log,
        "probe": args.probe,
        "probe_sha256": _sha256(args.probe),
        "probe_summary": args.probe_summary,
        "probe_summary_sha256": _sha256(args.probe_summary),
        "model": model,
        "hidden_state_index": layer,
        "coefficients": args.coefficients,
        "n_source_prompts": len(prompts),
        "n_generations": n,
        "controls": ["zero", "target", "opposite", "random_norm_matched"],
        "sampling": "paired seed within source prompt, steer target, and coefficient",
        "classifier_blinding": "classifier receives generated message text only",
        "warning": (
            "A change in rhetorical output establishes causal control of output, "
            "not that the direction is a natural or uniquely identifiable belief."
        ),
        "provider": provider.describe(),
    })
    print("wrote %d steering generations to %s" % (n, args.out))
    print("manifest: %s" % manifest_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
