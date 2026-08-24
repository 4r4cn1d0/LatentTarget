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
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--out", default="results/tables/open_weight_preflight.json")
    parser.add_argument("--seed", type=int, default=20250819)
    args = parser.parse_args(argv)

    provider = HuggingFaceProvider(
        model=args.model, temperature=0.0, max_tokens=16,
        dtype=args.dtype, layer_stride=1, capture=True, seed=args.seed,
    )
    prompt = FocalPrompt(
        system="You are a concise assistant.",
        user="Reply with exactly: Option A is worth considering.",
    )
    generated = provider.generate(prompt)
    provider.tag_last({"episode_id": "preflight", "round": 1, "run_id": "preflight"})
    store = provider.to_store()
    layers = find_text_layers(provider._model)
    report = validate_capture(store, n_text_blocks=len(layers))
    report.update({
        "model": args.model,
        "generated_text": generated,
        "generated_text_nonempty": bool(generated.strip()),
        "provider": provider.describe(),
    })
    if not generated.strip():
        report["ok"] = False
        report["issues"].append("generation returned empty text")

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
