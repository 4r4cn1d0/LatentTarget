#!/usr/bin/env python3
"""Run the frozen prospective V6 bundle-randomized power program."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys

try:
    import _bootstrap  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - import-safe test path
    scripts_dir = os.path.dirname(__file__)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from src.controlled_v6_power import (
    V6_MINIMUM_SIMULATIONS_PER_CELL,
    V6UnderpoweredError,
    get_v6_canonical_power_output_directory,
    require_authorized_v6_episode_count,
    run_v6_worst_case_power,
    run_v6_path_balance_dominance_screen,
)
from src.logging_utils import publish_json_idempotent, publish_text_idempotent


def _render_power_summary(payload) -> str:
    handle = io.StringIO(newline="")
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(
        [
            "episode_seed_bundles",
            "worst_joint_share_cell",
            "worst_joint_learner_profile",
            "joint_power",
            "joint_wilson_low",
            "joint_wilson_high",
            "worst_complete_share_cell",
            "worst_complete_learner_profile",
            "complete_power",
            "complete_wilson_low",
            "complete_wilson_high",
            "passes_both_lower_bounds",
        ]
    )
    for row in payload["power_summary"]["worst_case_by_episode_seed"]:
        joint = row["worst_joint_co_primary"]
        complete = row["worst_complete_behavioral_pattern"]
        writer.writerow(
            [
                row["n_episode_seeds"],
                joint["configuration_id"],
                joint["scenario_id"],
                joint["power"],
                joint["mc_ci_lo"],
                joint["mc_ci_hi"],
                complete["configuration_id"],
                complete["scenario_id"],
                complete["power"],
                complete["mc_ci_lo"],
                complete["mc_ci_hi"],
                row["passes_both_lower_bounds"],
            ]
        )
    return handle.getvalue()


def _render_null_size(payload) -> str:
    handle = io.StringIO(newline="")
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(
        [
            "metric",
            "worst_share_cell",
            "worst_latent_profile",
            "rejection_rate",
            "wilson_low",
            "wilson_high",
            "upper_limit",
            "pass",
        ]
    )
    for metric, row in payload["null_type_i_check"]["metrics"].items():
        writer.writerow(
            [
                metric,
                row["configuration_id"],
                row["profile_id"],
                row["power"],
                row["mc_ci_lo"],
                row["mc_ci_hi"],
                row["upper_limit"],
                row["pass"],
            ]
        )
    return handle.getvalue()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--n-sim",
        type=int,
        default=V6_MINIMUM_SIMULATIONS_PER_CELL,
        help="complete Monte Carlo studies per cell (official minimum: 10000)",
    )
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)
    if args.n_sim < V6_MINIMUM_SIMULATIONS_PER_CELL:
        parser.error("official V6 power requires at least 10,000 simulations per cell")

    canonical_out_dir = get_v6_canonical_power_output_directory(absolute=True)
    if args.out_dir is not None:
        supplied = os.path.realpath(
            args.out_dir
            if os.path.isabs(args.out_dir)
            else os.path.join(_bootstrap.ROOT, args.out_dir)
        )
        if supplied != canonical_out_dir:
            raise ValueError(
                "V6 power output must equal the single frozen canonical directory"
            )
    os.makedirs(canonical_out_dir, exist_ok=True)
    dominance_path = os.path.join(
        canonical_out_dir, "v6_path_balance_dominance.json"
    )
    dominance = run_v6_path_balance_dominance_screen(
        n_sim=args.n_sim, official=True
    )
    publish_json_idempotent(dominance_path, dominance)
    print("wrote %s" % dominance_path)
    print("path-balance status: %s" % dominance["status"])
    if dominance.get("terminal") is True:
        print(
            "V6 POWER FAILURE: registered heterogeneous no-history paths "
            "short-circuit the every-cell complete-power rule",
            file=sys.stderr,
        )
        return 2
    json_path = os.path.join(
        canonical_out_dir, "v6_prevalidation_power.json"
    )
    power_csv_path = os.path.join(
        canonical_out_dir, "v6_bundle_power.csv"
    )
    null_csv_path = os.path.join(
        canonical_out_dir, "v6_null_type_i.csv"
    )

    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get("n_sim_per_cell") != args.n_sim:
            raise FileExistsError(
                "existing V6 power payload uses a different simulation count"
            )
    else:
        payload = run_v6_worst_case_power(n_sim=args.n_sim, official=True)

    authorization_error = None
    try:
        selected = require_authorized_v6_episode_count(payload)
    except V6UnderpoweredError as exc:
        selected = None
        authorization_error = exc

    publish_json_idempotent(json_path, payload)
    publish_text_idempotent(power_csv_path, _render_power_summary(payload))
    publish_text_idempotent(null_csv_path, _render_null_size(payload))
    print("wrote %s" % json_path)
    print("wrote %s" % power_csv_path)
    print("wrote %s" % null_csv_path)
    print("status: %s" % payload["status"])
    if authorization_error is not None:
        print("V6 POWER FAILURE: %s" % authorization_error, file=sys.stderr)
        return 2
    assert selected is not None
    print("authorized episode-seed bundles: %d" % selected)
    return 0


if __name__ == "__main__":
    sys.exit(main())
