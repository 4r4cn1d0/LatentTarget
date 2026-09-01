#!/usr/bin/env python3
"""Run V4 mock positive/negative controls and preserve an auditable summary."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import hashlib
import json
import os
import platform
import sys
import tempfile
import time

from config import ControlledExperimentConfig, ModelConfig
from src.controlled_analysis import evaluate_controlled_checkpoint
from src.controlled_experiment import run_controlled_experiment


PRIMARY_CONDITIONS = [
    "full_history", "no_history", "shuffled_history", "random_target", "swap"
]


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run_case(root: str, name: str, provider: str, n_seeds: int, n_boot: int, n_perm: int):
    out_dir = os.path.join(root, name)
    cfg = ControlledExperimentConfig(
        experiment_id="controlled_v4_local_validation",
        n_episode_seeds=n_seeds,
        conditions=list(PRIMARY_CONDITIONS),
        model=ModelConfig(provider=provider, model="mock", max_tokens=16),
        out_dir=out_dir,
    )
    result = run_controlled_experiment(cfg, run_id=name)
    with open(result.manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    gate = evaluate_controlled_checkpoint(
        result.records, manifest, n_boot=n_boot, n_perm=n_perm, seed=cfg.seed
    )
    return {
        "provider": provider,
        "n_episode_seeds": n_seeds,
        "n_episodes": result.n_episodes,
        "n_records": result.n_records,
        "source_log_sha256": _sha256(result.log_path),
        "manifest_sha256": _sha256(result.manifest_path),
        "decision": gate["decision"],
        "pattern_pass": gate["pattern_pass"],
        "scientific_pass": gate["scientific_pass"],
        "effect_gates": gate["effect_gates"],
        "inference_gates": gate["inference_gates"],
        "valid_selection_rate": gate["valid_selection_rate"],
        "stable_condition_metrics": gate["stable_condition_metrics"],
        "primary_contrasts": gate["primary_contrasts"],
        "swap_metrics": gate["swap_metrics"],
        "supporting_target_types": gate["supporting_target_types"],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="results/v4_design/local_validation.json")
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--n-perm", type=int, default=5000)
    args = parser.parse_args(argv)

    started = time.time()
    with tempfile.TemporaryDirectory(prefix="latenttarget-v4-validation-") as root:
        positive = _run_case(
            root, "bayesian_positive", "mock:v4_bayesian", 20,
            args.n_boot, args.n_perm,
        )
        random_negative = _run_case(
            root, "random_negative", "mock:v4_random", 12,
            args.n_boot, args.n_perm,
        )
        invalid_negative = _run_case(
            root, "invalid_negative", "mock:v4_invalid", 4,
            args.n_boot, args.n_perm,
        )

    checks = {
        "bayesian_pattern_detected": positive["pattern_pass"] is True,
        "bayesian_never_scientific": positive["scientific_pass"] is False,
        "random_policy_rejected": random_negative["pattern_pass"] is False,
        "invalid_output_policy_rejected": invalid_negative["pattern_pass"] is False,
        "invalid_output_rate_gate_failed": invalid_negative["effect_gates"][
            "valid_selection_rate"
        ] is False,
    }
    payload = {
        "status": "MOCK/SYNTHETIC ONLY; implementation evidence, not LLM evidence",
        "run_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "python": sys.version,
        "platform": platform.platform(),
        "elapsed_seconds": time.time() - started,
        "checks": checks,
        "pass": all(checks.values()),
        "positive_control": positive,
        "random_policy_negative_control": random_negative,
        "invalid_output_negative_control": invalid_negative,
    }
    parent = os.path.dirname(args.out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
    print("PASS" if payload["pass"] else "FAIL")
    for name, passed in checks.items():
        print("  %-42s %s" % (name, "PASS" if passed else "FAIL"))
    print("wrote %s" % args.out)
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
