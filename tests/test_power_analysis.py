import pytest

from src.power_analysis import simulate_behavior_power, simulate_swap_gap_power


def test_behavior_power_is_reproducible_and_effect_sensitive():
    null = simulate_behavior_power(8, 0.0, n_sim=500, seed=3)
    strong = simulate_behavior_power(8, 0.30, n_sim=500, seed=3)
    assert null["power"] < 0.12
    assert strong["power"] > null["power"] + 0.3
    assert simulate_behavior_power(8, 0.30, n_sim=500, seed=3) == strong


def test_swap_power_increases_with_effect():
    weak = simulate_swap_gap_power(4, 0.0, n_sim=500, seed=5)
    strong = simulate_swap_gap_power(4, 0.8, n_sim=500, seed=5)
    assert weak["power"] < 0.12
    assert strong["power"] > 0.9
    assert strong["swap_episodes"] == 24


def test_invalid_power_inputs_fail():
    with pytest.raises(ValueError):
        simulate_behavior_power(0, 0.1)
    with pytest.raises(ValueError):
        simulate_swap_gap_power(1, -0.1)
