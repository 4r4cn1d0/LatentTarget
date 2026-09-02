"""V8: the destination-stratified gate and the declared rule."""

from __future__ import annotations

import numpy as np
import pytest

from src.controlled_v6_power import V6_PLANNING_SCENARIOS, analyze_v6_bundle_study
from src.controlled_v7_power import V7_MEASURED_NUISANCE_CELLS, simulate_v7_bundle_study
from src.controlled_v8_power import (
    V8_ALPHA_EACH, V8_DROPPED_GATES, V8_NULL_STUDY_OFFSET, V8_OFFICIAL_STUDY_OFFSET,
    V8_REQUIRED_ANALYZER_EFFECT_GATES, V8_SCREEN_STUDY_OFFSET,
    default_frame_from_shares, per_transition_adjusted_new_gain, simulate_controlled_v8_power,
    strata_for_default, v8_gate_evaluation, v8_payload_canonical_sha256, v8_stratified_contrasts,
)

MEASURED = V7_MEASURED_NUISANCE_CELLS[0]["frame_shares"]


@pytest.mark.parametrize("study_index", [1, 5, 9])
def test_v8_extraction_matches_analyzer_pooled_mean(study_index):
    """The analyzer returns only the six-transition mean of adjusted new gain per
    bundle; V8's per-transition re-extraction must average back to it exactly."""
    study = simulate_v7_bundle_study(6, baseline_frame_shares=MEASURED, study_index=study_index)
    analysis = analyze_v6_bundle_study(study)
    for b, pooled in zip(study["bundles"], analysis["adjusted_new_gain_bundle_contrasts"]):
        mine = np.mean(list(per_transition_adjusted_new_gain(b).values()))
        assert mine == pytest.approx(pooled, abs=1e-12)


def test_contrasts_lie_on_the_declared_lattice():
    study = simulate_v7_bundle_study(6, baseline_frame_shares=MEASURED, study_index=2)
    strat = v8_stratified_contrasts(study, "expertise")
    for s in ("non_default_destination", "orthogonal_pair", "toward_default", "away_from_default"):
        scale = strat[s]["integer_scale"]
        for v in strat[s]["bundle_contrasts"]:
            assert abs(v * scale - round(v * scale)) < 1e-9, (s, v, scale)
    assert strat["non_default_destination"]["integer_scale"] == 24
    assert strat["orthogonal_pair"]["integer_scale"] == 12


def test_strata_definitions():
    s = strata_for_default("expertise")
    assert set(s["non_default_destination"]) == {"expertise->fairness", "expertise->risk", "fairness->risk", "risk->fairness"}
    assert set(s["orthogonal_pair"]) == {"fairness->risk", "risk->fairness"}
    assert set(s["toward_default"]) == {"fairness->expertise", "risk->expertise"}
    assert set(s["away_from_default"]) == {"expertise->fairness", "expertise->risk"}
    with pytest.raises(ValueError):
        strata_for_default("charisma")


def test_default_frame_is_the_largest_measured_share():
    assert default_frame_from_shares(MEASURED) == "expertise"
    assert default_frame_from_shares({"fairness": 0.5, "risk": 0.3, "expertise": 0.2}) == "fairness"


def test_rule_requires_the_destination_gate_and_three_tests():
    study = simulate_v7_bundle_study(6, baseline_frame_shares=MEASURED, study_index=3)
    ev = v8_gate_evaluation(analyze_v6_bundle_study(study), study, "expertise")
    req = set(ev["required"])
    assert {"stratified_new_gain", "stable_exact_test", "revision_exact_test", "stratified_exact_test"} <= req
    assert set(V8_REQUIRED_ANALYZER_EFFECT_GATES) <= req
    assert "adjusted_new_gain" not in req and "full_history_late_level" not in req
    assert set(ev["reported_only"]) <= set(V8_DROPPED_GATES)
    assert ev["v8_complete"] == all(ev["required"].values())


def test_alpha_and_offsets_are_pinned_and_disjoint():
    assert V8_ALPHA_EACH == pytest.approx(0.05 / 3)
    assert V8_SCREEN_STUDY_OFFSET < V8_NULL_STUDY_OFFSET < V8_OFFICIAL_STUDY_OFFSET
    assert V8_SCREEN_STUDY_OFFSET > 24_000      # V7's screen used 1-24000
    assert V8_SCREEN_STUDY_OFFSET > 20_199 and V8_NULL_STUDY_OFFSET > 44_000  # V7 diagnostics/null runs


def test_power_cell_and_null_cell_run_and_report():
    from src.controlled_v6_power import V6_NULL_LATENT_PROFILES
    out = simulate_controlled_v8_power(12, 3, MEASURED, planning_scenario=V6_PLANNING_SCENARIOS[0])
    assert out["default_frame"] == "expertise" and out["simulation_study_offset"] == V8_SCREEN_STUDY_OFFSET
    assert set(out["required_test_wilson_hi"]) == {"stable_exact_test", "revision_exact_test", "stratified_exact_test"}
    assert "strat:non_default_destination" in out["mean_estimates"]
    null = simulate_controlled_v8_power(12, 3, MEASURED, planning_scenario=V6_PLANNING_SCENARIOS[0],
                                        null_profile=V6_NULL_LATENT_PROFILES[0], simulation_study_offset=V8_NULL_STUDY_OFFSET)
    assert null["status"] == "V8_NULL_SIZE" and null["null_profile_id"] == "symmetric"


def test_payload_hash_ignores_timing():
    base = {"design_id": "x", "wall_seconds": 1.0, "cells": [{"cell_id": "a", "v8_complete": {"rate": 0.5}, "wall_seconds": 2.0}]}
    alt = {**base, "wall_seconds": 9.0, "cells": [{**base["cells"][0], "wall_seconds": 7.0}]}
    assert v8_payload_canonical_sha256(base) == v8_payload_canonical_sha256(alt)
