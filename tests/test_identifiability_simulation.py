"""Tests for the simulator-capacity positive control."""

from __future__ import annotations

import pytest

from config import TargetParams
from src.bayesian_observer import BayesianEvidenceObserver, BayesianObserverConfig
from src.identifiability_simulation import (
    choose_information_message,
    scorer_from_selection,
    select_diagnostic_messages,
    simulate_identifiability,
)


def _record(message, fairness, risk, expertise):
    return {
        "focal_message": message,
        "target_scores": {
            "fairness": fairness,
            "risk": risk,
            "expertise": expertise,
        },
    }


def _selection():
    return select_diagnostic_messages(
        [
            _record("fair message", 1.0, 0.0, 0.0),
            _record("risk message", 0.0, 1.0, 0.0),
            _record("expert message", 0.0, 0.0, 1.0),
            _record("mixed", 0.4, 0.3, 0.3),
        ]
    )


def test_selection_maximizes_specificity_without_outcomes():
    selected = _selection()
    assert selected["fairness"]["message"] == "fair message"
    assert selected["risk"]["message"] == "risk message"
    assert selected["expertise"]["message"] == "expert message"
    assert selected["fairness"]["specificity_margin"] == pytest.approx(1.0)


def test_information_message_is_one_of_the_frozen_candidates():
    selected = _selection()
    params = TargetParams(base_bias=-2.5, w_match=5.0, w_off=0.0, logit_noise_sd=0.0)
    observer = BayesianEvidenceObserver(
        params=params,
        config=BayesianObserverConfig(change_hazard=0.0),
        scorer=scorer_from_selection(selected),
    )
    message = choose_information_message(observer, observer.initial, selected)
    assert message in {item["message"] for item in selected.values()}


def test_oracle_policy_identifies_a_separable_simulator():
    selected = _selection()
    params = TargetParams(base_bias=-2.5, w_match=5.0, w_off=0.0, logit_noise_sd=0.0)
    result = simulate_identifiability(
        selected,
        params,
        n_per_target=300,
        n_per_swap_pair=100,
        stable_rounds=8,
        swap_round=5,
        total_swap_rounds=10,
        seed=7,
    )
    assert result["stable"]["final_accuracy"] > 0.9
    assert result["swap"]["final_target_accuracy"] > 0.7
    assert result["stable"]["final_accuracy_mc_ci95"][0] <= result["stable"][
        "final_accuracy"
    ] <= result["stable"]["final_accuracy_mc_ci95"][1]
