#!/usr/bin/env python3
"""Ask the focal model directly which framing the participant responds to.

GPU pod only; this script performs model generations. Run it after the main
experiment, never during an episode. It checkpoints after every answer and can
be resumed safely.

Example:
    python scripts/run_black_box_baseline.py --log data/raw/run.jsonl \
        --model Qwen/Qwen3.8-27B --out data/processed/black_box.json
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys
import tempfile

from src.black_box_baseline import collect_black_box_guesses, score_black_box_guesses
from src.hf_provider import HuggingFaceProvider
from src.logging_utils import read_jsonl, write_manifest


def _atomic_json(path, value):
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".black-box-", suffix=".json", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(value, fh, indent=2, sort_keys=True)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--log", required=True)
    parser.add_argument("--model", default=None,
                        help="defaults to the unique model_name recorded in the log")
    parser.add_argument("--out", default="data/processed/black_box_guesses.json")
    parser.add_argument(
        "--raw-out", default=None,
        help="exact generated answers (defaults to <out>.raw.json)",
    )
    parser.add_argument("--conditions", nargs="+",
                        default=["full_history", "swap", "shuffled_history"])
    parser.add_argument("--dtype", default="bfloat16")
    args = parser.parse_args(argv)

    records = list(read_jsonl(args.log))
    records = [row for row in records if row["condition"] in set(args.conditions)]
    if not records:
        parser.error("no records remain after --conditions filtering")
    recorded_models = sorted(set(str(row["model_name"]) for row in records))
    if args.model is None:
        if len(recorded_models) != 1:
            parser.error("log contains multiple model names; pass --model explicitly")
        args.model = recorded_models[0]
    if len(recorded_models) == 1 and args.model != recorded_models[0]:
        parser.error(
            "--model %r differs from focal model recorded in log (%r)" %
            (args.model, recorded_models[0])
        )

    args.raw_out = args.raw_out or args.out + ".raw.json"
    existing = {}
    if os.path.exists(args.out):
        with open(args.out, "r", encoding="utf-8") as fh:
            existing = json.load(fh)
    raw_answers = {}
    if os.path.exists(args.raw_out):
        with open(args.raw_out, "r", encoding="utf-8") as fh:
            raw_answers = json.load(fh)
    provider = HuggingFaceProvider(
        model=args.model, temperature=0.0, max_tokens=16,
        dtype=args.dtype, capture=False,
    )
    guesses = collect_black_box_guesses(
        records, provider, existing=existing,
        checkpoint=lambda current: _atomic_json(args.out, current),
        raw_answers=raw_answers,
        raw_checkpoint=lambda current: _atomic_json(args.raw_out, current),
    )
    metrics = score_black_box_guesses(records, guesses)
    n_raw = sum(len(rounds) for rounds in raw_answers.values())
    manifest = write_manifest(args.out + ".manifest.json", {
        "kind": "black_box_target_guess",
        "source_log": args.log,
        "model": args.model,
        "conditions": args.conditions,
        "provider": provider.describe(),
        "metrics": metrics,
        "raw_answers_path": args.raw_out,
        "n_raw_answers": n_raw,
        "information_boundary": (
            "Each guess sees only the focal user prompt at that round. The query "
            "runs separately and is never shown inside an episode."
        ),
    })
    print("wrote %d guesses to %s" % (metrics["n_scored"], args.out))
    print("wrote %d raw answers to %s" % (n_raw, args.raw_out))
    print("accuracy: %s" % (
        "%.3f" % metrics["accuracy"] if metrics["accuracy"] is not None else "n/a"
    ))
    print("manifest: %s" % (args.out + ".manifest.json"))
    assert manifest["kind"] == "black_box_target_guess"
    return 0


if __name__ == "__main__":
    sys.exit(main())
