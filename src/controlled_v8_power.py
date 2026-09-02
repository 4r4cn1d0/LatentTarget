"""V8: declared milestone. Prior-cancelling revision test with a REQUIRED
destination-stratified acquisition gate.

Why V8 exists (see docs/V8_MILESTONE_DECLARATION.md for the full ledger):

* V7 removed V6's no-history balance gate and was rejected by adversarial
  review (docs/V7_REVIEW.md): its pooled revision rule is satisfied by pure
  default-attraction -- a model that acquires the new frame only when that frame
  is its default, and merely abandons the old one otherwise -- which is the very
  pattern V4 identified as NOT revision. The gates that separate "lands on the
  new frame" from "drifts to the default" had been demoted.
* V8 keeps everything prior-cancelling from V6/V7 (matched stable-old twin,
  swap-minus-twin estimands, exact bundle randomization tests) and ADDS the
  gate the review prescribed: bundle-mean adjusted new-frame gain over the
  transitions whose DESTINATION is a non-default frame, with its own exact
  within-bundle sign-flip test. Regression to the default predicts zero here.
* The "default frame" is registered from the target-free prior measurement on
  the instrument (largest no-history share); it is not chosen after outcomes.

Rule (all required):
  integrity   design_integrity, all_selections_valid, zero_fallback,
              no_history_learning_control, random_target_learning_control
  learning    full_over_no_late >= 0.10 (relative), stable DID >= 0.10,
              stable exact test <= alpha
  revision    revision >= 0.15, adjusted_old_drop >= 0.05, revision exact
              test <= alpha
  acquisition stratified_new_gain >= 0.05 over non-default-destination
              transitions, stratified exact test <= alpha
  alpha_each = 0.05 / 3 (three required exact tests; family-wise <= 0.05)

Dropped from V6, with reasons (reported, never required):
  full_history_late_level        absolute level; binds under a strong default
                                 regardless of learning (V7 screen)
  all_target_types_supported     absolute per-type level; ceiling-doomed
  late_swap_new_minus_old        raw crossover; prior-confounded (V4)
  directional_transition_support, all_origin_types_support_revision
                                 ORIGIN-based; replaced by the DESTINATION-
                                 stratified gate above (review finding 2)
  no_history_frame_balance       instrument property the model sets (V5)

Secondary (reported, not required): toward-default minus away-from-default
acquisition contrast. It is entailed by the no-gating null (review finding 3),
so in the confirmatory analysis it is compared against this DGP's own
prediction at the measured shares, never against zero.

Study offsets are pinned and disjoint: screen 100000+, null 200000+,
official 300000+. V7's screen used 1-24000 and its diagnostics 5000+/20000+.
"""

from __future__ import annotations

import json
import math
import os
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np

from src.controlled_v6_power import (
    STRATEGIES,
    V6_EPISODE_SEED_GRID,
    V6_NULL_LATENT_PROFILES,
    V6_PLANNING_SCENARIOS,
    V6_POWER_SEED,
    _canonical_sha256,
    _condition_slot,
    _planning_scenario,
    _window_match,
    analyze_v6_bundle_study,
    exact_one_sided_bundle_randomization_test,
)
from src.controlled_v7_power import _clean_simplex_frame_shares, simulate_v7_bundle_study

V8_DESIGN_ID = "v8_declared_prior_cancelling_with_destination_gate"
V8_ALPHA_EACH = 0.05 / 3.0
V8_STRATIFIED_NEW_GAIN_GATE = 0.05
V8_SCREEN_STUDY_OFFSET = 100_000
V8_NULL_STUDY_OFFSET = 200_000
V8_OFFICIAL_STUDY_OFFSET = 300_000
V8_SCREEN_STATUS = "V8_EXPLORATORY_SCREEN_NOT_THE_REGISTERED_POWER_RUN"

V8_REQUIRED_ANALYZER_EFFECT_GATES = (
    "design_integrity", "all_selections_valid", "zero_fallback",
    "no_history_learning_control", "random_target_learning_control",
    "full_over_no_late", "stable", "revision", "adjusted_old_drop",
)
V8_DROPPED_GATES = {
    "full_history_late_level": "absolute level; binds under a strong default regardless of learning",
    "all_target_types_supported": "absolute per-type level; ceiling-doomed for the default frame",
    "late_swap_new_minus_old": "raw crossover; prior-confounded (V4 diagnosis)",
    "directional_transition_support": "origin-based; replaced by the destination-stratified gate",
    "all_origin_types_support_revision": "origin-based; replaced by the destination-stratified gate",
    "no_history_frame_balance": "instrument property set by the model, not the design (V5)",
    "adjusted_new_gain": "pooled over all transitions; passes on default-attraction (review finding 1); replaced by the stratified gate",
}

WINDOW_EARLY = (6, 12)
WINDOW_LATE = (18, 24)


def transition_names() -> List[str]:
    return ["%s->%s" % (a, b) for a in STRATEGIES for b in STRATEGIES if a != b]


def default_frame_from_shares(shares: Mapping[str, float]) -> str:
    """The registered default: the largest measured no-history share."""
    clean = _clean_simplex_frame_shares(shares)
    return max(STRATEGIES, key=lambda f: clean[f])


def strata_for_default(default_frame: str) -> Dict[str, List[str]]:
    if default_frame not in STRATEGIES:
        raise ValueError("unknown default frame %r" % (default_frame,))
    names = transition_names()
    return {
        "non_default_destination": [t for t in names if t.split("->")[1] != default_frame],
        "orthogonal_pair": [t for t in names if default_frame not in t.split("->")],
        "toward_default": [t for t in names if t.split("->")[1] == default_frame],
        "away_from_default": [t for t in names if t.split("->")[0] == default_frame],
    }


def per_transition_adjusted_new_gain(bundle: Mapping[str, Any]) -> Dict[str, float]:
    """Swap-minus-twin new-frame gain for each of the six transitions.

    Mirrors the analyzer's internal computation exactly (window means over
    rounds 18-24 minus 6-12, swap branch minus stable-old branch); the analyzer
    only returns the six-transition mean, so V8 re-extracts the parts.
    ``test_v8_extraction_matches_analyzer_pooled_mean`` pins the equivalence.
    """
    swap = _condition_slot(bundle["transition_slots"], "silent_swap")
    stable = _condition_slot(bundle["transition_slots"], "stable_old")
    out: Dict[str, float] = {}
    for name in transition_names():
        old, new = name.split("->")
        sf = list(swap["transitions"][name]["frames"])
        tf = list(stable["transitions"][name]["frames"])
        swap_gain = _window_match(sf, new, *WINDOW_LATE) - _window_match(sf, new, *WINDOW_EARLY)
        stable_gain = _window_match(tf, new, *WINDOW_LATE) - _window_match(tf, new, *WINDOW_EARLY)
        out[name] = float(swap_gain - stable_gain)
    return out


def v8_stratified_contrasts(study: Mapping[str, Any], default_frame: str) -> Dict[str, Any]:
    """Per-bundle stratum means of adjusted new gain, and the exact tests.

    Each per-transition contrast is a difference of window means over six
    rounds, so it lies on a 1/6 lattice; a mean over k transitions lies on a
    1/(6k) lattice, hence ``integer_scale = 6k`` for the exact test.
    """
    strata = strata_for_default(default_frame)
    per_bundle = {s: [] for s in strata}
    secondary: List[float] = []
    for bundle in study["bundles"]:
        g = per_transition_adjusted_new_gain(bundle)
        for s, names in strata.items():
            per_bundle[s].append(float(np.mean([g[n] for n in names])))
        secondary.append(
            float(np.mean([g[n] for n in strata["toward_default"]])
                  - np.mean([g[n] for n in strata["away_from_default"]]))
        )
    out: Dict[str, Any] = {"default_frame": default_frame, "strata": strata}
    for s, values in per_bundle.items():
        k = len(strata[s])
        test = exact_one_sided_bundle_randomization_test(values, integer_scale=6 * k)
        out[s] = {"bundle_contrasts": values, "mean": float(np.mean(values)),
                  "integer_scale": 6 * k, "p_value_one_sided": test["p_value_one_sided"]}
    sec_test = exact_one_sided_bundle_randomization_test(secondary, integer_scale=12)
    out["secondary_toward_minus_away"] = {
        "bundle_contrasts": secondary, "mean": float(np.mean(secondary)),
        "integer_scale": 12, "p_value_one_sided": sec_test["p_value_one_sided"],
        "note": "reported only; compare against this DGP's no-gating prediction, not zero",
    }
    return out


def v8_gate_evaluation(analysis: Mapping[str, Any], study: Mapping[str, Any],
                       default_frame: str) -> Dict[str, Any]:
    """Apply the V8 rule over the unchanged V6 analyzer output plus V8's strata."""
    effect = analysis["effect_gates"]
    inference = analysis["inference_gates"]
    strat = v8_stratified_contrasts(study, default_frame)
    nd = strat["non_default_destination"]
    required = {k: bool(effect[k]) for k in V8_REQUIRED_ANALYZER_EFFECT_GATES}
    required["stratified_new_gain"] = nd["mean"] >= V8_STRATIFIED_NEW_GAIN_GATE
    # V6 tests are evaluated at 0.025 inside the analyzer; V8 re-evaluates all
    # three at its own alpha from the raw p-values.
    required["stable_exact_test"] = analysis["stable_test"]["p_value_one_sided"] <= V8_ALPHA_EACH
    required["revision_exact_test"] = analysis["revision_test"]["p_value_one_sided"] <= V8_ALPHA_EACH
    required["stratified_exact_test"] = nd["p_value_one_sided"] <= V8_ALPHA_EACH
    reported = {k: bool(effect[k]) for k in V8_DROPPED_GATES if k in effect}
    return {
        "required": required,
        "reported_only": reported,
        "joint_three_tests": bool(required["stable_exact_test"] and required["revision_exact_test"]
                                  and required["stratified_exact_test"]),
        "v8_complete": all(required.values()),
        "v6_complete": bool(analysis["complete_gate"]),
        "stratified": {k: {"mean": v["mean"], "p": v["p_value_one_sided"]}
                       for k, v in strat.items() if isinstance(v, dict) and "mean" in v},
    }


def _wilson(s: int, n: int, z: float = 1.96) -> Dict[str, float]:
    p = s / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return {"successes": s, "rate": p, "wilson_lo": max(0.0, c - h), "wilson_hi": min(1.0, c + h)}


def simulate_controlled_v8_power(
    n_episode_seeds: int, n_sim: int, baseline_frame_shares: Mapping[str, float], *,
    planning_scenario: Optional[Any] = None, seed: int = V6_POWER_SEED,
    simulation_study_offset: int = V8_SCREEN_STUDY_OFFSET,
    default_frame: Optional[str] = None, null_profile: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """One cell. Under ``null_profile`` this is a size (Type I) run."""
    if type(n_sim) is not int or n_sim < 1:
        raise ValueError("n_sim must be a positive integer")
    shares = _clean_simplex_frame_shares(baseline_frame_shares)
    default_frame = default_frame or default_frame_from_shares(shares)
    scenario = _planning_scenario(planning_scenario)
    counts: Dict[str, int] = {}
    sums: Dict[str, float] = {}
    t0 = time.time()
    for i in range(n_sim):
        study = simulate_v7_bundle_study(
            n_episode_seeds, baseline_frame_shares=shares, planning_scenario=scenario,
            seed=seed, study_index=simulation_study_offset + i, null_profile=null_profile,
        )
        analysis = analyze_v6_bundle_study(study)
        ev = v8_gate_evaluation(analysis, study, default_frame)
        for k, v in ev["required"].items(): counts[k] = counts.get(k, 0) + int(v)
        for k, v in ev["reported_only"].items(): counts["reported:" + k] = counts.get("reported:" + k, 0) + int(v)
        for k in ("joint_three_tests", "v8_complete", "v6_complete"): counts[k] = counts.get(k, 0) + int(ev[k])
        for k in ("stable", "revision", "adjusted_new_gain", "adjusted_old_drop", "full_history_late_match"):
            sums[k] = sums.get(k, 0.0) + float(analysis[k])
        for k, v in ev["stratified"].items(): sums["strat:" + k] = sums.get("strat:" + k, 0.0) + v["mean"]
    return {
        "design_id": V8_DESIGN_ID, "status": V8_SCREEN_STATUS if null_profile is None else "V8_NULL_SIZE",
        "n_episode_seeds": n_episode_seeds, "n_sim": n_sim, "seed": seed,
        "simulation_study_offset": simulation_study_offset, "scenario_id": scenario.get("scenario_id"),
        "null_profile_id": (null_profile or {}).get("profile_id"),
        "baseline_frame_shares": shares, "default_frame": default_frame, "alpha_each": V8_ALPHA_EACH,
        "v8_complete": _wilson(counts.get("v8_complete", 0), n_sim),
        "joint_three_tests": _wilson(counts.get("joint_three_tests", 0), n_sim),
        "v6_complete_for_reference": _wilson(counts.get("v6_complete", 0), n_sim),
        "required_gate_rates": {k: counts.get(k, 0) / n_sim for k in list(V8_REQUIRED_ANALYZER_EFFECT_GATES)
                                + ["stratified_new_gain", "stable_exact_test", "revision_exact_test", "stratified_exact_test"]},
        "required_test_wilson_hi": {k: _wilson(counts.get(k, 0), n_sim)["wilson_hi"]
                                    for k in ("stable_exact_test", "revision_exact_test", "stratified_exact_test")},
        "reported_only_gate_rates": {k: counts.get("reported:" + k, 0) / n_sim for k in V8_DROPPED_GATES},
        "mean_estimates": {k: v / n_sim for k, v in sums.items()},
        "wall_seconds": time.time() - t0,
    }


def v8_payload_canonical_sha256(payload: Mapping[str, Any]) -> str:
    stripped = {k: v for k, v in payload.items() if k not in ("wall_seconds", "canonical_sha256")}
    stripped["cells"] = [{k: v for k, v in c.items() if k != "wall_seconds"} for c in payload.get("cells", [])]
    return _canonical_sha256(stripped)


def _cell_worker(task: tuple) -> Dict[str, Any]:
    cell, scenario, n, n_sim, seed, offset, null_profile = task
    out = simulate_controlled_v8_power(n, n_sim, cell["frame_shares"], planning_scenario=scenario, seed=seed,
                                       simulation_study_offset=offset, null_profile=null_profile)
    out["cell_id"] = cell["cell_id"]; out["kind"] = cell.get("kind"); out["provenance"] = cell.get("provenance")
    return out


def run_v8_grid(cells: Sequence[Mapping[str, Any]], *, n_sim: int, n_workers: int, seed: int = V6_POWER_SEED,
                seed_grid: Sequence[int] = V6_EPISODE_SEED_GRID, scenarios: Optional[Sequence[Mapping[str, Any]]] = None,
                null_profiles: Optional[Sequence[Mapping[str, Any]]] = None, offset_base: int = V8_SCREEN_STUDY_OFFSET,
                out_path: str = "results/v8_design/screen/v8_screen.json", status: str = V8_SCREEN_STATUS) -> Dict[str, Any]:
    """Power grid (null_profiles=None) or size grid (null_profiles given). Offsets pinned and non-overlapping."""
    from multiprocessing import get_context
    scenarios = list(scenarios if scenarios is not None else V6_PLANNING_SCENARIOS)
    nulls: List[Optional[Mapping[str, Any]]] = list(null_profiles) if null_profiles else [None]
    tasks = []; offset = offset_base
    for cell in cells:
        for scenario in scenarios:
            for n in seed_grid:
                for prof in nulls:
                    tasks.append((dict(cell), dict(scenario), int(n), int(n_sim), int(seed), offset, prof)); offset += n_sim
    t0 = time.time()
    with get_context("spawn").Pool(processes=n_workers) as pool:
        results = pool.map(_cell_worker, tasks)
    payload = {"design_id": V8_DESIGN_ID, "status": status, "alpha_each": V8_ALPHA_EACH,
               "required_gates": list(V8_REQUIRED_ANALYZER_EFFECT_GATES) + ["stratified_new_gain", "stable_exact_test", "revision_exact_test", "stratified_exact_test"],
               "dropped_gates": dict(V8_DROPPED_GATES), "n_sim_per_cell": n_sim, "seed": seed,
               "study_offset_range": [offset_base, offset - 1], "n_cells": len(results), "wall_seconds": time.time() - t0, "cells": results}
    payload["canonical_sha256"] = v8_payload_canonical_sha256(payload)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=float)
    return payload


def format_v8_grid(payload: Mapping[str, Any]) -> str:
    lines = ["%s (%s)  n_sim/cell=%d  cells=%d  offsets %s  wall=%.0fs" % (
        payload["design_id"], payload["status"], payload["n_sim_per_cell"], payload["n_cells"], payload["study_offset_range"], payload["wall_seconds"]),
        "%-26s %-9s %-18s %3s %7s %7s %7s  %-24s %s" % ("cell", "scenario", "null", "N", "v8_lo", "v8", "3tests", "binding gate", "stable/rev/stratNew(nd)")]
    for c in sorted(payload["cells"], key=lambda c: (c["cell_id"], c["scenario_id"], str(c["null_profile_id"]), c["n_episode_seeds"])):
        req = c["required_gate_rates"]; b = min(req, key=req.get); m = c["mean_estimates"]
        lines.append("%-26s %-9s %-18s %3d %7.3f %7.3f %7.3f  %-24s %.2f/%.2f/%.2f" % (
            c["cell_id"], c["scenario_id"], str(c["null_profile_id"]), c["n_episode_seeds"], c["v8_complete"]["wilson_lo"],
            c["v8_complete"]["rate"], c["joint_three_tests"]["rate"], "%s=%.2f" % (b, req[b]),
            m["stable"], m["revision"], m.get("strat:non_default_destination", float("nan"))))
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    import argparse
    from src.controlled_v7_power import V7_MEASURED_NUISANCE_CELLS
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=["screen", "null"], default="screen")
    p.add_argument("--n-sim", type=int, default=500)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--cells", default="measured", choices=["measured", "all"])
    p.add_argument("--out", default=None)
    a = p.parse_args()
    cells = [c for c in V7_MEASURED_NUISANCE_CELLS if a.cells == "all" or c["kind"] == "measured"]
    if a.mode == "screen":
        out = a.out or "results/v8_design/screen/v8_screen.json"
        print(format_v8_grid(run_v8_grid(cells, n_sim=a.n_sim, n_workers=a.workers, out_path=out)))
    else:
        out = a.out or "results/v8_design/screen/v8_null_size.json"
        print(format_v8_grid(run_v8_grid(cells, n_sim=a.n_sim, n_workers=a.workers, seed_grid=(18,), scenarios=[V6_PLANNING_SCENARIOS[1]],
                                         null_profiles=list(V6_NULL_LATENT_PROFILES), offset_base=V8_NULL_STUDY_OFFSET, out_path=out, status="V8_NULL_SIZE")))
