from __future__ import annotations

import pytest

from src.controlled_v5_power import (
    exact_one_sided_sign_flip_p,
    exact_rational_sign_flip_test,
    simulate_controlled_v5_power,
)


def test_exact_sign_flip_uses_complete_null_distribution():
    assert exact_one_sided_sign_flip_p([1] * 6) == pytest.approx(1.0 / 64.0)
    assert exact_one_sided_sign_flip_p([0, 0, 0]) == 1.0
    assert exact_one_sided_sign_flip_p([]) == 1.0
    rational = exact_rational_sign_flip_test([1.0 / 6.0] * 6)
    assert rational["p_value_one_sided"] == pytest.approx(1.0 / 64.0)
    assert rational["n_sign_assignments"] == 64


def test_v5_power_is_reproducible_and_counts_episode_units():
    first = simulate_controlled_v5_power(
        8, 0.20, 0.30, n_sim=300, seed=11
    )
    second = simulate_controlled_v5_power(
        8, 0.20, 0.30, n_sim=300, seed=11
    )
    assert first == second
    assert first["stable_episodes_per_condition"] == 24
    assert first["swap_episodes"] == 48
    assert first["total_confirmatory_episodes"] == 144
    assert first["total_confirmatory_generations"] == 3456
    for name in (
        "stable_co_primary",
        "revision_co_primary",
        "joint_co_primary",
        "complete_behavioral_pattern",
    ):
        assert 0.0 <= first[name]["mc_ci_lo"] <= first[name]["power"]
        assert first[name]["power"] <= first[name]["mc_ci_hi"] <= 1.0


def test_v5_power_increases_with_effect_and_sample_size():
    null = simulate_controlled_v5_power(8, 0.0, 0.0, n_sim=400, seed=7)
    strong_small = simulate_controlled_v5_power(
        8, 0.20, 0.30, n_sim=400, seed=7
    )
    strong_large = simulate_controlled_v5_power(
        20, 0.20, 0.30, n_sim=400, seed=7
    )
    assert null["joint_co_primary"]["power"] < 0.03
    assert strong_small["joint_co_primary"]["power"] > null["joint_co_primary"]["power"]
    assert strong_large["joint_co_primary"]["power"] > strong_small["joint_co_primary"]["power"]


def test_v5_power_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        simulate_controlled_v5_power(0, 0.1, 0.2)
    with pytest.raises(ValueError):
        simulate_controlled_v5_power(8, -0.1, 0.2)
    with pytest.raises(ValueError):
        simulate_controlled_v5_power(
            8,
            0.1,
            0.2,
            baseline_frame_shares={"fairness": 0.5, "risk": 0.5},
        )
