from __future__ import annotations

import pytest

from src.controlled_power import simulate_controlled_v4_power


def test_controlled_power_counts_episode_units_and_returns_mc_intervals():
    result = simulate_controlled_v4_power(
        n_episode_seeds=5,
        full_late_match=0.55,
        swap_late_new_match=0.55,
        n_sim=200,
        seed=3,
    )
    assert result["stable_episodes_per_condition"] == 15
    assert result["swap_episodes"] == 30
    for metric in ("stable_test", "swap_test", "joint_co_primary"):
        assert 0.0 <= result[metric]["mc_ci_lo"] <= result[metric]["power"]
        assert result[metric]["power"] <= result[metric]["mc_ci_hi"] <= 1.0


def test_more_episode_seeds_increase_power_for_a_clear_effect():
    small = simulate_controlled_v4_power(3, 0.60, 0.60, n_sim=800, seed=10)
    large = simulate_controlled_v4_power(20, 0.60, 0.60, n_sim=800, seed=11)
    assert large["joint_co_primary"]["power"] > small["joint_co_primary"]["power"]


def test_power_rejects_non_positive_effect():
    with pytest.raises(ValueError, match="exceed"):
        simulate_controlled_v4_power(5, 1 / 3, 0.5, n_sim=10)
