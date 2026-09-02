#!/usr/bin/env python3
"""V8 target-free prior measurement on the frozen V5 bank.

A MEASUREMENT, not a gate: it registers a model's no-history frame shares and
its default frame, which become a nuisance cell and the stratification key for
the V8 rule. No history, no target, no capture.

    python scripts/run_v8_prior_measurement.py --model-key gemma4_31b \\
        --run-id v8-gemma4-prior --dry-run          # audit + schedule only
    python scripts/run_v8_prior_measurement.py --model-key gemma4_31b \\
        --run-id v8-gemma4-prior                     # on the pod

Flow is the V5 runner's, verbatim, with the V8 audit in place of V5's.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

from src.controlled_v5_messages import V5MessageBank
from src.hf_provider import HuggingFaceProvider
from src.v5_calibration import (
    audit_v5_calibration_schedule,
    build_v5_calibration_schedule,
    run_v5_no_history_calibration,
)
from src.v5_protocol_gate import file_sha256
from src.v8_protocol_gate import audit_v8_measurement_plan


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--protocol-spec", default=os.path.join(_bootstrap.ROOT, "docs", "v8_protocol.json"))
    parser.add_argument("--model-key", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", default="data/calibration")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    with open(args.protocol_spec, "r", encoding="utf-8") as handle:
        spec = json.load(handle)
    model = spec["models"][args.model_key]
    generation = spec["generation"]
    schedule_spec = spec["prior_measurement_schedule"]
    bank_path = os.path.join(_bootstrap.ROOT, spec["selected_bank"]["path"])
    bank = V5MessageBank.load(bank_path)

    provider = HuggingFaceProvider(
        model=model["id"], revision=model["revision"],
        temperature=generation["temperature"], max_tokens=generation["max_tokens"],
        device=args.device, dtype=generation["dtype"], capture=False,
        seed=schedule_spec["seed"], enable_thinking=generation["enable_thinking"],
        top_p=generation["top_p"], top_k=generation["top_k"],
        constrained_choices=tuple(generation["constrained_choices"]),
    )
    plan_audit = audit_v8_measurement_plan(
        spec=spec, bank=bank, provider=provider.describe(), model_key=args.model_key,
        n_episode_blocks=schedule_spec["n_episode_blocks"], n_rounds=schedule_spec["n_rounds"],
        heldout_start_round=schedule_spec["heldout_start_round"], seed=schedule_spec["seed"],
        repository_root=_bootstrap.ROOT,
    )
    if not plan_audit["pass"]:
        failed = sorted(name for name, ok in plan_audit["checks"].items() if not ok)
        raise ValueError("planned measurement differs from the V8 protocol: %s" % ", ".join(failed))
    schedule = build_v5_calibration_schedule(
        bank, n_episode_blocks=schedule_spec["n_episode_blocks"], n_rounds=schedule_spec["n_rounds"],
        heldout_start_round=schedule_spec["heldout_start_round"], seed=schedule_spec["seed"],
    )
    audit = audit_v5_calibration_schedule(schedule, bank)
    print("LatentTarget V8 target-free prior measurement")
    print("  model key: %s -> %s @ %s" % (args.model_key, model["id"], model["revision"]))
    print("  bank SHA-256: %s" % bank.sha256())
    print("  prompts: %d; target/history/capture: absent" % len(schedule))
    print("  schedule audit: %s" % ("PASS" if audit["pass"] else "FAIL"))
    print("  V8 protocol audit: PASS (%d checks)" % len(plan_audit["checks"]))
    if not audit["pass"]:
        raise ValueError("calibration schedule audit failed")
    if args.dry_run:
        print("DRY RUN PASSED: no model loaded and no outcomes generated")
        return 0
    result = run_v5_no_history_calibration(
        bank=bank, provider=provider, run_id=args.run_id, out_dir=args.out_dir,
        n_episode_blocks=schedule_spec["n_episode_blocks"], n_rounds=schedule_spec["n_rounds"],
        heldout_start_round=schedule_spec["heldout_start_round"], seed=schedule_spec["seed"],
        mode="selected_bank_validation",
        provenance={"protocol": "v8", "protocol_path": os.path.abspath(args.protocol_spec),
                    "protocol_file_sha256": file_sha256(args.protocol_spec),
                    "model_key": args.model_key, "plan_audit": plan_audit, "is_gate": False},
    )
    print("wrote %d records to %s" % (len(result["records"]), result["log_path"]))
    print("manifest: %s" % result["manifest_path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
