#!/usr/bin/env python3
"""Load the planned model and validate one generation before any full GPU run.

This is intentionally the first paid-compute command. It checks processor and
AutoModel compatibility, text-layer discovery, prompt-token activation shape,
generation, and a zero-vector steering intervention. It exits non-zero on any
contract failure and writes a machine-readable report.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

import numpy as np

from src.focal_agent import FocalPrompt
from src.hf_provider import HuggingFaceProvider
from src.logging_utils import write_manifest
from src.preflight import validate_capture
from src.steering import find_text_layers


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--model", default="Qwen/Qwen3.8-27B")
    parser.add_argument("--revision", default=None,
                        help="immutable Hugging Face model commit")
    parser.add_argument("--controlled-v4-spec", default=None,
                        help="use the exact first-round V4 candidate prompt from this checkpoint JSON")
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--out", default="results/tables/open_weight_preflight.json")
    parser.add_argument("--seed", type=int, default=20250819)
    args = parser.parse_args(argv)

    max_tokens = 16
    checkpoint = None
    if args.controlled_v4_spec:
        with open(args.controlled_v4_spec, "r", encoding="utf-8") as handle:
            checkpoint = json.load(handle)
        if checkpoint["primary_model"]["id"] != args.model:
            raise ValueError("--model differs from the controlled V4 checkpoint")
        if checkpoint["primary_model"]["revision"] != args.revision:
            raise ValueError("--revision differs from the controlled V4 checkpoint")
        max_tokens = int(checkpoint["generation"]["max_tokens"])

    provider = HuggingFaceProvider(
        model=args.model, revision=args.revision,
        temperature=0.0, max_tokens=max_tokens,
        dtype=args.dtype, layer_stride=1, capture=True, seed=args.seed,
    )
    controlled_result = None
    if checkpoint is not None:
        from src.controlled_focal_agent import build_controlled_prompt, parse_controlled_choice
        from src.controlled_messages import candidate_set, message_bank_sha256
        from src.scenarios import scenario_sequence
        from src.seeding import derive_seed

        experiment = checkpoint["experiment"]
        scenario = scenario_sequence(0, experiment["n_rounds"], experiment["master_seed"])[0]
        candidates = candidate_set(
            scenario, 0, 1, experiment["heldout_start_round"], experiment["master_seed"]
        )
        prompt = build_controlled_prompt(
            scenario, candidates, [], 1, experiment["n_rounds"], True, "spontaneous"
        )
        round_seed = derive_seed(experiment["master_seed"], "v4_preflight", 1)
        provider.set_next_seed(round_seed)
    else:
        prompt = FocalPrompt(
            system="You are a concise assistant.",
            user="Reply with exactly: Option A is worth considering.",
        )
    generated = provider.generate(prompt)
    if checkpoint is not None:
        parsed = parse_controlled_choice(generated, "spontaneous", round_seed)
        controlled_result = {
            "selection_valid": parsed.selection_valid,
            "selected_slot": parsed.selected_slot,
            "fallback_used": parsed.fallback_used,
            "message_bank_sha256": message_bank_sha256(),
            "message_bank_matches_checkpoint": (
                message_bank_sha256() == checkpoint["message_bank"]["sha256"]
            ),
            "prompt_context_keys": sorted(prompt.context),
        }
    provider.tag_last({"episode_id": "preflight", "round": 1, "run_id": "preflight"})
    store = provider.to_store()
    layers = find_text_layers(provider._model)
    report = validate_capture(store, n_text_blocks=len(layers))
    report.update({
        "model": args.model,
        "generated_text": generated,
        "generated_text_nonempty": bool(generated.strip()),
        "provider": provider.describe(),
        "controlled_v4": controlled_result,
    })
    if not generated.strip():
        report["ok"] = False
        report["issues"].append("generation returned empty text")
    if controlled_result is not None:
        if not controlled_result["selection_valid"]:
            report["ok"] = False
            report["issues"].append("model did not return a valid V4 candidate number")
        if not controlled_result["message_bank_matches_checkpoint"]:
            report["ok"] = False
            report["issues"].append("V4 message bank hash differs from frozen checkpoint")
        if controlled_result["prompt_context_keys"]:
            report["ok"] = False
            report["issues"].append("real V4 preflight prompt carried structured context")

    # A zero vector must be a true instrumentation control. With greedy
    # decoding it should reproduce the unsteered output byte for byte.
    middle = store.layers[len(store.layers) // 2]
    zero_text = provider.generate_with_steering(
        prompt.system, prompt.user, middle, np.zeros(store.d_model), 6.0, args.seed
    )
    report["zero_steering_hidden_state_index"] = middle
    report["zero_steering_text"] = zero_text
    report["zero_steering_matches_unsteered"] = zero_text == generated
    if zero_text != generated:
        report["ok"] = False
        report["issues"].append("zero-vector intervention changed greedy output")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    write_manifest(args.out, {"kind": "open_weight_preflight", **report})
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        print("PRECHECK FAILED: do not start the full run", file=sys.stderr)
        return 1
    print("PRECHECK PASSED: architecture contracts are compatible")
    return 0


if __name__ == "__main__":
    sys.exit(main())
