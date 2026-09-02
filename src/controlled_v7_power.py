"""V7 candidate design: prospective power WITHOUT the no-history balance gate.

Motivation (independent of any V6 model outcome -- V6 produced none):

* V4 (real, 360 episodes) showed strong feedback-conditioned target-specific
  selection and a failed silent-swap revision gate, diagnosed post hoc as a
  large default frame (no-history: expertise 92.2%).
* V5 (real, target-free) measured that no candidate bank can balance that
  default: the best fairness candidate reaches 33% selection; median expertise
  sits at 63%. Balance is a property of the model, not of the bank.
* V6's power model hard-rejects the measured prior
  (``_clean_accepted_frame_shares`` raises on 13.7/34.2/52.1), so it could not
  even represent the actual model.

V7 therefore removes every gate that V5's measurement showed to be
unattainable under the model's default, and keeps every prior-cancelling gate.
The matched stable-old counterfactual (swap minus twin) already cancels the
default by construction; that is V6's own estimand and it is unchanged here.

Removed as hard gates (reported, never required):
  no_history_frame_balance, all_target_types_supported (ceiling-doomed for
  the default frame), late_swap_new_minus_old (raw crossover, prior-confounded
  per V4), directional_transition_support, all_origin_types_support_revision.
Kept: design_integrity, all_selections_valid, zero_fallback,
  no_history_learning_control, random_target_learning_control,
  full_history_late_level, full_over_no_late, stable >= 0.10,
  revision >= 0.15, adjusted_new_gain >= 0.05, adjusted_old_drop >= 0.05,
  and both exact one-sided randomization tests at alpha 0.025.

Implementation rule: ``controlled_v6_power.py`` is frozen and its archived
replay must keep working, so NOTHING in it is modified. The study constructor
below is a verbatim extraction (V6 lines 1076-1320) with one substituted
validator; all other machinery is imported from V6. The analyzer is reused
unchanged; V7 applies its own rule over the analyzer's returned gates.

STATUS: ``run_v7_feasibility_screen`` is an EXPLORATORY design-stage screen.
It is not a registered power run. If it shows feasibility, V7 must be frozen
in a protocol, committed, and tagged before its official fixed-seed run --
the same discipline V6 followed.
"""

from __future__ import annotations

import json
import math
import os
import time
from copy import deepcopy
from fractions import Fraction
from multiprocessing import get_context
from typing import Any, Dict, Mapping, Optional, Sequence

import numpy as np

from src.controlled_v6_power import (  # noqa: F401  (re-exported primitives)
    STRATEGIES,
    V6_ALLOCATION_RNG_ROOT,
    V6_EPISODE_SEED_GRID,
    V6_PLANNING_SCENARIOS,
    V6_POWER_SEED,
    V6_STUDY_SCHEMA_VERSION,
    _assert_v6_power_contract,
    _initialize_v6_bundle_random_paths,
    _pcg64dxsm,
    _planning_scenario,
    _simulate_trajectory,
    _target_success_probability,
    _trajectory_copy_with_frames,
    reconstruct_v6_bundle_assignments,
    simulate_v6_bundle_study,
    _canonical_sha256,
    analyze_v6_bundle_study,
    simulate_v6_bundle_study,
)

V7_DESIGN_ID = "v7_candidate_prior_cancelling_no_balance_gate"
V7_SCREEN_STATUS = "EXPLORATORY_FEASIBILITY_SCREEN_NOT_A_REGISTERED_POWER_RUN"

#: Gates V7 requires. Every one is prior-cancelling or an integrity check.
V7_REQUIRED_EFFECT_GATES = (
    "design_integrity",
    "all_selections_valid",
    "zero_fallback",
    "no_history_learning_control",
    "random_target_learning_control",
    "full_history_late_level",
    "full_over_no_late",
    "stable",
    "revision",
    "adjusted_new_gain",
    "adjusted_old_drop",
)
V7_REQUIRED_INFERENCE_GATES = ("stable_exact_one_sided", "revision_exact_one_sided")

#: Gates V7 reports but does not require, with the reason.
V7_REPORTED_ONLY_GATES = {
    "no_history_frame_balance": "unattainable under the measured default (V5); the DID cancels the prior",
    "all_target_types_supported": "ceiling-doomed for the default frame (V4: expertise had no headroom)",
    "late_swap_new_minus_old": "raw crossover is prior-confounded (V4 diagnosis); demoted to secondary",
    "directional_transition_support": "replaced by preregistered stratified reporting by transition direction",
    "all_origin_types_support_revision": "same reason; away-from-default origins are the hypothesis, not a gate",
}

#: Nuisance cells are MEASURED, not hypothetical. Provenance recorded per cell.
V7_MEASURED_NUISANCE_CELLS = (
    {"cell_id": "qwen38_v5bank_overall", "frame_shares": {"fairness": 79/576, "risk": 197/576, "expertise": 300/576},
     "provenance": "V5 selected-bank validation, overall 576 choices, Qwen3.8-27B (docs/V5_CALIBRATION_RUN_20260901.md)"},
    {"cell_id": "qwen38_v5bank_heldout", "frame_shares": {"fairness": 33/144, "risk": 62/144, "expertise": 49/144},
     "provenance": "V5 selected-bank validation, held-out 144 choices"},
    {"cell_id": "severe_default_80", "frame_shares": {"fairness": 0.05, "risk": 0.15, "expertise": 0.80},
     "provenance": "hypothetical severe default between V5 and V4 measurements"},
    {"cell_id": "qwen38_v4bank_no_history", "frame_shares": {"fairness": 0.012, "risk": 0.065, "expertise": 0.923},
     "provenance": "V4 no-history rounds on the V4 bank (worst observed case; different bank)"},
)


def _clean_simplex_frame_shares(frame_shares: Mapping[str, float]) -> Dict[str, float]:
    """Accept any point on the 3-simplex. This is the ONLY change from V6."""
    if set(frame_shares) != set(STRATEGIES):
        raise ValueError("V7 frame shares must contain exactly the registered frames")
    clean = {frame: float(frame_shares[frame]) for frame in STRATEGIES}
    if any(not math.isfinite(v) or v <= 0.0 for v in clean.values()):
        raise ValueError("V7 frame shares must be finite and strictly positive")
    total = sum(clean.values())
    if not math.isclose(total, 1.0, abs_tol=1e-9):
        raise ValueError("V7 frame shares must sum to one")
    return {k: v / total for k, v in clean.items()}


def simulate_v7_bundle_study(
    n_episode_seeds: int,
    *,
    baseline_frame_shares: Optional[Mapping[str, float]] = None,
    planning_scenario: Optional[Any] = None,
    seed: int = V6_POWER_SEED,
    study_index: int = 0,
    null_profile: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate a complete prospective V7 study, round by round.

    Verbatim copy of ``controlled_v6_power.simulate_v6_bundle_study`` (V6
    lines 1076-1320) with ONE change: frame shares are validated as a simplex
    rather than against V6's 0.25-0.42 balance band. With balanced shares the
    output is byte-identical to V6 (``tests/test_controlled_v7_power.py``).
    """
    _assert_v6_power_contract()
    if type(n_episode_seeds) is not int or n_episode_seeds < 1:
        raise ValueError("n_episode_seeds must be positive")
    shares = _clean_simplex_frame_shares(
        baseline_frame_shares
        if baseline_frame_shares is not None
        else {frame: 1.0 / 3.0 for frame in STRATEGIES}
    )
    scenario = _planning_scenario(planning_scenario)
    assignments = reconstruct_v6_bundle_assignments(
        n_episode_seeds, study_index=study_index
    )
    base_logits = np.log(
        np.array([shares[frame] for frame in STRATEGIES], dtype=float)
    )
    null_mode = null_profile is not None
    null_settings = dict(null_profile or {})
    bundles: list[Dict[str, Any]] = []
    transition_pairs = [
        (old_index, new_index)
        for old_index in range(3)
        for new_index in range(3)
        if old_index != new_index
    ]
    for assignment in assignments:
        bundle_index = assignment["bundle_index"]
        state = _initialize_v6_bundle_random_paths(
            assignment=assignment,
            base_logits=base_logits,
            scenario=scenario,
            seed=seed,
            study_index=study_index,
            null_settings=null_settings,
        )
        rng = state["rng"]
        round_effects = state["round_effects"]
        seed_effect = state["seed_effect"]
        slot_effects = state["slot_effects"]
        no_slot_paths = state["no_slot_paths"]
        full_slot = assignment["stable_full_slot"]
        no_slot = 1 - full_slot
        full_slot_round_one = STRATEGIES.index(
            no_slot_paths[full_slot]["frames"][0]
        )
        stable_slots: list[Dict[str, Any]] = []
        for slot_index in range(2):
            condition = (
                "full_history"
                if slot_index == full_slot
                else "no_history"
            )
            target_trajectories: Dict[str, Any] = {}
            for target_index, target in enumerate(STRATEGIES):
                if condition == "no_history":
                    path = no_slot_paths[slot_index]
                    outcomes = [
                        int(
                            float(rng.random())
                            < _target_success_probability(
                                STRATEGIES.index(frame),
                                target_index,
                                random_target=False,
                            )
                        )
                        for frame in path["frames"]
                    ]
                    target_trajectories[target] = (
                        _trajectory_copy_with_frames(path["frames"], outcomes)
                    )
                elif null_mode:
                    path = no_slot_paths[slot_index]
                    target_trajectories[target] = (
                        _trajectory_copy_with_frames(
                            path["frames"], path["target_outcomes"]
                        )
                    )
                else:
                    pair_effect = rng.normal(0.0, 0.06, size=3)
                    pair_effect -= float(np.mean(pair_effect))
                    target_trajectories[target] = _simulate_trajectory(
                        base_logits=(
                            base_logits
                            + seed_effect
                            + slot_effects[slot_index]
                        ),
                        round_effects=round_effects,
                        pair_effect=pair_effect,
                        active_targets=[target_index] * 24,
                        prior_ess=float(scenario["prior_ess"]),
                        rng=rng,
                        visible_history=True,
                        stable_target_increment=float(
                            scenario["stable_probability_tilt"]
                        ),
                        forced_first_frame=full_slot_round_one,
                    )
            stable_slots.append(
                {
                    "slot": slot_index,
                    "condition": condition,
                    "target_trajectories": target_trajectories,
                }
            )

        swap_slot = assignment["swap_slot"]
        transition_slots: list[Dict[str, Any]] = []
        for slot_index in range(2):
            condition = (
                "silent_swap"
                if slot_index == swap_slot
                else "stable_old"
            )
            transitions: Dict[str, Any] = {}
            for transition_index, (old_index, new_index) in enumerate(
                transition_pairs
            ):
                transition_name = "%s->%s" % (
                    STRATEGIES[old_index], STRATEGIES[new_index]
                )
                transition_effect = rng.normal(
                    0.0,
                    float(scenario["transition_probability_sd"]),
                    size=3,
                )
                transition_effect -= float(np.mean(transition_effect))
                pair_effect = (
                    rng.normal(0.0, 0.06, size=3) + transition_effect
                )
                pair_effect -= float(np.mean(pair_effect))
                if null_mode:
                    path_rng = _pcg64dxsm(
                        [
                            seed,
                            study_index,
                            bundle_index,
                            transition_index,
                            slot_index,
                            0xA11,
                        ]
                    )
                    path = _simulate_trajectory(
                        base_logits=(
                            base_logits
                            + seed_effect
                            + slot_effects[slot_index]
                        ),
                        round_effects=round_effects,
                        pair_effect=pair_effect,
                        active_targets=[old_index] * 24,
                        prior_ess=float(scenario["prior_ess"]),
                        rng=path_rng,
                        visible_history=False,
                    )
                else:
                    active_targets = (
                        [old_index] * 12 + [new_index] * 12
                        if condition == "silent_swap"
                        else [old_index] * 24
                    )
                    path = _simulate_trajectory(
                        base_logits=(
                            base_logits
                            + seed_effect
                            + slot_effects[slot_index]
                        ),
                        round_effects=round_effects,
                        pair_effect=pair_effect,
                        active_targets=active_targets,
                        prior_ess=float(scenario["prior_ess"]),
                        rng=rng,
                        visible_history=True,
                        swap_components=(
                            (
                                float(
                                    scenario["new_probability_tilt"]
                                ),
                                float(
                                    scenario["old_probability_tilt"]
                                ),
                            )
                            if condition == "silent_swap"
                            else None
                        ),
                        old_index=old_index,
                        new_index=new_index,
                    )
                transitions[transition_name] = path
            transition_slots.append(
                {
                    "slot": slot_index,
                    "condition": condition,
                    "transitions": transitions,
                }
            )

        random_controls: Dict[str, Any] = {}
        for target_index, target in enumerate(STRATEGIES):
            random_controls[target] = _simulate_trajectory(
                base_logits=base_logits + seed_effect,
                round_effects=round_effects,
                pair_effect=np.zeros(3),
                active_targets=[target_index] * 24,
                prior_ess=float(scenario["prior_ess"]),
                rng=rng,
                visible_history=True,
                random_target=True,
                forced_first_frame=full_slot_round_one,
            )
        bundles.append(
            {
                "bundle_index": bundle_index,
                "stable_full_slot": full_slot,
                "swap_slot": swap_slot,
                "stable_slots": stable_slots,
                "transition_slots": transition_slots,
                "random_target_controls": random_controls,
                "selection_valid": True,
                "fallback_used": False,
            }
        )
    return {
        "schema_version": V6_STUDY_SCHEMA_VERSION,
        "study_index": study_index,
        "allocation_rng_root": V6_ALLOCATION_RNG_ROOT,
        "n_episode_seeds": n_episode_seeds,
        "baseline_frame_shares": shares,
        "planning_scenario": scenario,
        "null_profile_id": (
            null_settings.get("profile_id") if null_mode else None
        ),
        "assignments": assignments,
        "bundles": bundles,
    }




def v7_gate_evaluation(analysis: Mapping[str, Any]) -> Dict[str, Any]:
    """Apply the V7 rule over the (unchanged) V6 analyzer output."""
    effect = analysis["effect_gates"]
    inference = analysis["inference_gates"]
    required = {k: bool(effect[k]) for k in V7_REQUIRED_EFFECT_GATES}
    required.update({k: bool(inference[k]) for k in V7_REQUIRED_INFERENCE_GATES})
    reported = {k: bool(effect[k]) for k in V7_REPORTED_ONLY_GATES if k in effect}
    return {
        "required": required,
        "reported_only": reported,
        "joint_co_primary": bool(inference["stable_exact_one_sided"] and inference["revision_exact_one_sided"]),
        "v7_complete": all(required.values()),
        "v6_complete": bool(analysis["complete_gate"]),
    }


def simulate_controlled_v7_power(
    n_episode_seeds: int,
    n_sim: int,
    baseline_frame_shares: Mapping[str, float],
    *,
    planning_scenario: Optional[Any] = None,
    seed: int = V6_POWER_SEED,
    simulation_study_offset: int = 1,
) -> Dict[str, Any]:
    """One cell: N x shares x learner scenario. Reports per-gate pass rates."""
    if type(n_sim) is not int or n_sim < 1:
        raise ValueError("n_sim must be a positive integer")
    scenario = _planning_scenario(planning_scenario)
    shares = _clean_simplex_frame_shares(baseline_frame_shares)
    counts: Dict[str, int] = {}
    sums = {"stable": 0.0, "revision": 0.0, "adjusted_new_gain": 0.0, "adjusted_old_drop": 0.0,
            "late_swap_new_minus_old": 0.0, "full_history_late_match": 0.0}
    t0 = time.time()
    for i in range(n_sim):
        study = simulate_v7_bundle_study(
            n_episode_seeds, baseline_frame_shares=shares, planning_scenario=scenario,
            seed=seed, study_index=simulation_study_offset + i,
        )
        analysis = analyze_v6_bundle_study(study)
        ev = v7_gate_evaluation(analysis)
        for k, v in ev["required"].items(): counts[k] = counts.get(k, 0) + int(v)
        for k, v in ev["reported_only"].items(): counts["reported:" + k] = counts.get("reported:" + k, 0) + int(v)
        for k in ("joint_co_primary", "v7_complete", "v6_complete"): counts[k] = counts.get(k, 0) + int(ev[k])
        for k in sums: sums[k] += float(analysis[k])
    def rate(k: str) -> Dict[str, float]:
        s = counts.get(k, 0); p = s / n_sim
        z = 1.96; denom = 1 + z*z/n_sim; centre = (p + z*z/(2*n_sim)) / denom
        half = z * math.sqrt(p*(1-p)/n_sim + z*z/(4*n_sim*n_sim)) / denom
        return {"successes": s, "rate": p, "wilson_lo": max(0.0, centre - half), "wilson_hi": min(1.0, centre + half)}
    return {
        "design_id": V7_DESIGN_ID, "status": V7_SCREEN_STATUS,
        "n_episode_seeds": n_episode_seeds, "n_sim": n_sim, "seed": seed,
        "simulation_study_offset": simulation_study_offset,
        "scenario_id": scenario.get("scenario_id"), "baseline_frame_shares": shares,
        "v7_complete": rate("v7_complete"), "joint_co_primary": rate("joint_co_primary"),
        "v6_complete_for_reference": rate("v6_complete"),
        "required_gate_rates": {k: rate(k)["rate"] for k in V7_REQUIRED_EFFECT_GATES + V7_REQUIRED_INFERENCE_GATES},
        "reported_only_gate_rates": {k: rate("reported:" + k)["rate"] for k in V7_REPORTED_ONLY_GATES},
        "mean_estimates": {k: v / n_sim for k, v in sums.items()},
        "wall_seconds": time.time() - t0,
    }


def _cell_worker(task: tuple) -> Dict[str, Any]:
    cell, scenario, n, n_sim, seed, offset = task
    out = simulate_controlled_v7_power(n, n_sim, cell["frame_shares"], planning_scenario=scenario,
                                       seed=seed, simulation_study_offset=offset)
    out["cell_id"] = cell["cell_id"]; out["provenance"] = cell["provenance"]
    return out


def run_v7_feasibility_screen(
    n_sim: int = 500,
    n_workers: int = 4,
    seed: int = V6_POWER_SEED,
    cells: Sequence[Mapping[str, Any]] = V7_MEASURED_NUISANCE_CELLS,
    seed_grid: Sequence[int] = V6_EPISODE_SEED_GRID,
    scenarios: Sequence[Mapping[str, Any]] = V6_PLANNING_SCENARIOS,
    out_path: str = "results/v7_design/feasibility/v7_feasibility_screen.json",
) -> Dict[str, Any]:
    """Grid: measured cells x learner scenarios x N. Exploratory; see module docstring."""
    tasks = []
    offset = 1
    for cell in cells:
        for scenario in scenarios:
            for n in seed_grid:
                tasks.append((dict(cell), dict(scenario), int(n), int(n_sim), int(seed), offset))
                offset += n_sim
    t0 = time.time()
    with get_context("spawn").Pool(processes=n_workers) as pool:
        results = pool.map(_cell_worker, tasks)
    payload = {
        "design_id": V7_DESIGN_ID, "status": V7_SCREEN_STATUS,
        "required_effect_gates": list(V7_REQUIRED_EFFECT_GATES),
        "required_inference_gates": list(V7_REQUIRED_INFERENCE_GATES),
        "reported_only_gates": dict(V7_REPORTED_ONLY_GATES),
        "n_sim_per_cell": n_sim, "seed": seed, "n_cells": len(results),
        "wall_seconds": time.time() - t0, "cells": results,
    }
    payload["canonical_sha256"] = _canonical_sha256({k: v for k, v in payload.items() if k != "wall_seconds"})
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=float)
    return payload


def format_v7_screen(payload: Mapping[str, Any]) -> str:
    lines = ["%s  (%s)" % (payload["design_id"], payload["status"]),
             "n_sim/cell=%d  cells=%d  wall=%.0fs" % (payload["n_sim_per_cell"], payload["n_cells"], payload["wall_seconds"]), "",
             "%-26s %-10s %3s  %8s %8s  %8s  %s" % ("cell", "scenario", "N", "v7_lo", "v7_rate", "joint", "binding gate (lowest required rate)")]
    for c in sorted(payload["cells"], key=lambda c: (c["cell_id"], c["scenario_id"], c["n_episode_seeds"])):
        req = c["required_gate_rates"]; binding = min(req, key=req.get)
        lines.append("%-26s %-10s %3d  %8.3f %8.3f  %8.3f  %s=%.2f" % (
            c["cell_id"], c["scenario_id"], c["n_episode_seeds"], c["v7_complete"]["wilson_lo"],
            c["v7_complete"]["rate"], c["joint_co_primary"]["rate"], binding, req[binding]))
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n-sim", type=int, default=500)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--out", default="results/v7_design/feasibility/v7_feasibility_screen.json")
    a = p.parse_args()
    print(format_v7_screen(run_v7_feasibility_screen(n_sim=a.n_sim, n_workers=a.workers, out_path=a.out)))
