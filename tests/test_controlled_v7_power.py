"""V7 candidate power module: faithful to V6 where it should be, freer where it must be."""

from __future__ import annotations

import pytest

from src.controlled_v6_power import (
    V6_PLANNING_SCENARIOS,
    _canonical_sha256,
    analyze_v6_bundle_study,
    simulate_v6_bundle_study,
)
from src.controlled_v7_power import (
    V7_MEASURED_NUISANCE_CELLS,
    V7_REPORTED_ONLY_GATES,
    V7_REQUIRED_EFFECT_GATES,
    _clean_simplex_frame_shares,
    simulate_controlled_v7_power,
    simulate_v7_bundle_study,
    v7_gate_evaluation,
)

BALANCED = {"fairness": 1 / 3, "risk": 1 / 3, "expertise": 1 / 3}
MEASURED = V7_MEASURED_NUISANCE_CELLS[0]["frame_shares"]


@pytest.mark.parametrize("study_index", [1, 7])
@pytest.mark.parametrize("scenario", list(V6_PLANNING_SCENARIOS)[:2])
def test_v7_constructor_is_byte_identical_to_v6_under_balanced_shares(study_index, scenario):
    """The one substitution must be invisible whenever V6's validator would have passed."""
    v6 = simulate_v6_bundle_study(12, baseline_frame_shares=BALANCED, planning_scenario=scenario, study_index=study_index)
    v7 = simulate_v7_bundle_study(12, baseline_frame_shares=BALANCED, planning_scenario=scenario, study_index=study_index)
    assert _canonical_sha256(v7) == _canonical_sha256(v6)


def test_v7_accepts_the_measured_prior_that_v6_rejects():
    with pytest.raises(ValueError, match="balance bounds"):
        simulate_v6_bundle_study(12, baseline_frame_shares=MEASURED, study_index=1)
    study = simulate_v7_bundle_study(12, baseline_frame_shares=MEASURED, study_index=1)
    counts = analyze_v6_bundle_study(study)["no_history_frame_counts"]
    assert counts["expertise"] > counts["fairness"]      # the default actually shows up in the DGP


@pytest.mark.parametrize("bad", [
    {"fairness": 0.5, "risk": 0.5},                                   # missing frame
    {"fairness": -0.1, "risk": 0.6, "expertise": 0.5},                # negative
    {"fairness": 0.0, "risk": 0.5, "expertise": 0.5},                 # zero (log would be -inf)
    {"fairness": 0.4, "risk": 0.4, "expertise": 0.4},                 # not a simplex
])
def test_simplex_validator_rejects_non_simplex(bad):
    with pytest.raises(ValueError):
        _clean_simplex_frame_shares(bad)


def test_simplex_validator_accepts_any_interior_point():
    for shares in (BALANCED, MEASURED, {"fairness": 0.012, "risk": 0.065, "expertise": 0.923}):
        clean = _clean_simplex_frame_shares(shares)
        assert abs(sum(clean.values()) - 1.0) < 1e-12


def test_v7_rule_is_a_strict_subset_of_v6_rule():
    """V6-complete implies V7-complete; the dropped gates are exactly the reported-only ones."""
    for study_index in range(1, 9):
        a = analyze_v6_bundle_study(simulate_v7_bundle_study(12, baseline_frame_shares=BALANCED, study_index=study_index))
        ev = v7_gate_evaluation(a)
        if ev["v6_complete"]:
            assert ev["v7_complete"]
        assert set(ev["required"]) == set(V7_REQUIRED_EFFECT_GATES) | {"stable_exact_one_sided", "revision_exact_one_sided"}
        assert set(ev["reported_only"]) == set(V7_REPORTED_ONLY_GATES)
        assert set(a["effect_gates"]) == set(V7_REQUIRED_EFFECT_GATES) | set(V7_REPORTED_ONLY_GATES)


def test_v7_power_cell_reports_rates_and_labels_itself_exploratory():
    out = simulate_controlled_v7_power(12, 3, MEASURED, planning_scenario=V6_PLANNING_SCENARIOS[0])
    assert "EXPLORATORY" in out["status"]
    for k in ("v7_complete", "joint_co_primary", "v6_complete_for_reference"):
        assert 0.0 <= out[k]["rate"] <= 1.0 and out[k]["wilson_lo"] <= out[k]["rate"] <= out[k]["wilson_hi"]
    assert set(out["required_gate_rates"]) >= set(V7_REQUIRED_EFFECT_GATES)
    assert set(out["reported_only_gate_rates"]) == set(V7_REPORTED_ONLY_GATES)
    assert out["scenario_id"] == "learner_1"


def test_measured_cells_carry_provenance_and_are_simplex():
    for cell in V7_MEASURED_NUISANCE_CELLS:
        assert cell["provenance"]
        _clean_simplex_frame_shares(cell["frame_shares"])
