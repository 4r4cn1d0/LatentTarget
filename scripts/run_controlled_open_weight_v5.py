#!/usr/bin/env python3
"""Run only an already-frozen V5 confirmatory checkpoint on a GPU host."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

from config import ControlledExperimentConfig, ControlledTargetParams, ModelConfig
from src.controlled_experiment import (
    build_controlled_episode_specs,
    run_controlled_experiment,
)
from src.controlled_v5_analysis import audit_frozen_v5_plan
from src.controlled_v5_messages import make_v5_protocol
from src.hf_provider import HuggingFaceProvider
from src.v5_protocol_gate import audit_v5_checkpoint_artifacts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkpoint-spec",
        default=os.path.join(_bootstrap.ROOT, "docs", "behavioral_checkpoint_v5.json"),
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--revision", default=None)
    parser.add_argument("--episodes", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", default="data/raw")
    parser.add_argument("--experiment-id", default="controlled_v5_checkpoint")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not os.path.isfile(args.checkpoint_spec):
        raise FileNotFoundError(
            "V5 confirmatory checkpoint is not frozen yet: %s" % args.checkpoint_spec
        )
    with open(args.checkpoint_spec, "r", encoding="utf-8") as handle:
        checkpoint = json.load(handle)
    artifact_audit = audit_v5_checkpoint_artifacts(checkpoint, _bootstrap.ROOT)
    if not artifact_audit["pass"]:
        failed = sorted(
            name for name, passed in artifact_audit["checks"].items() if not passed
        )
        raise ValueError("V5 pre-outcome artifact gate failed: %s" % ", ".join(failed))

    experiment = checkpoint["experiment"]
    target = checkpoint["target"]
    generation = checkpoint["generation"]
    model = checkpoint["primary_model"]
    bank_ref = checkpoint["message_bank"]
    bank_path = (
        bank_ref["path"]
        if os.path.isabs(bank_ref["path"])
        else os.path.join(_bootstrap.ROOT, bank_ref["path"])
    )
    selected_model = args.model or model["id"]
    selected_revision = args.revision or model["revision"]
    n_seeds = args.episodes if args.episodes is not None else experiment["n_episode_seeds"]
    master_seed = args.seed if args.seed is not None else experiment["master_seed"]
    cfg = ControlledExperimentConfig(
        experiment_id=args.experiment_id,
        n_rounds=experiment["n_rounds"],
        swap_round=experiment["swap_round"],
        heldout_start_round=experiment["heldout_start_round"],
        n_episode_seeds=n_seeds,
        seed=master_seed,
        conditions=list(experiment["conditions"]),
        target_params=ControlledTargetParams(
            p_match=target["p_match"],
            p_mismatch=target["p_mismatch"],
            p_random=target["p_random"],
        ),
        model=ModelConfig(
            provider="huggingface",
            model=selected_model,
            revision=selected_revision,
            temperature=generation["temperature"],
            max_tokens=generation["max_tokens"],
        ),
        out_dir=args.out_dir,
    )
    provider = HuggingFaceProvider(
        model=selected_model,
        revision=selected_revision,
        temperature=generation["temperature"],
        max_tokens=generation["max_tokens"],
        device=args.device,
        dtype=generation["dtype"],
        capture=False,
        seed=master_seed,
        enable_thinking=generation["enable_thinking"],
        top_p=generation["top_p"],
        top_k=generation["top_k"],
        constrained_choices=tuple(generation["constrained_choices"]),
    )
    provenance = {
        "checkpoint_path": os.path.abspath(args.checkpoint_spec),
        "checkpoint_canonical_sha256": artifact_audit[
            "checkpoint_canonical_sha256"
        ],
        "artifact_audit": artifact_audit,
    }
    protocol = make_v5_protocol(
        bank_path,
        require_validated=True,
        manifest_metadata=provenance,
    )
    specs = build_controlled_episode_specs(cfg)
    plan_audit = audit_frozen_v5_plan(
        cfg,
        provider.describe(),
        expected_n_records=sum(spec.n_rounds for spec in specs),
        expected_n_episodes=len(specs),
        bank_manifest=protocol.message_bank_manifest(),
        bank_sha256=protocol.message_bank_sha256(),
        frozen_spec=checkpoint,
        protocol_provenance=provenance,
    )
    if not plan_audit["pass"]:
        failed = sorted(
            name for name, passed in plan_audit["checks"].items() if not passed
        )
        raise ValueError(
            "planned run differs from frozen V5 checkpoint: %s" % ", ".join(failed)
        )
    print("LatentTarget V5 open-weight confirmatory checkpoint")
    print("  model: %s @ %s" % (selected_model, selected_revision))
    print("  bank: %s" % protocol.message_bank_sha256())
    print(
        "  episodes: %d; generations: %d"
        % (len(specs), sum(spec.n_rounds for spec in specs))
    )
    print("  artifact and frozen-plan gates: PASS")
    print("  activation capture: disabled by design")
    if args.dry_run:
        print("DRY RUN PASSED: no model loaded and no outcomes generated")
        return 0
    progress = None if args.quiet else (lambda message: print(message, flush=True))
    result = run_controlled_experiment(
        cfg,
        run_id=args.run_id,
        provider=provider,
        progress=progress,
        resume=args.resume,
        protocol=protocol,
    )
    print("wrote %d rows to %s" % (result.n_records, result.log_path))
    print("manifest: %s" % result.manifest_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
