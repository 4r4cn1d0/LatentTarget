"""Simulation-based pre-data power sensitivity for V4.

The independent unit is an episode. Five rounds in an analysis window are
repeated measurements used to construct one episode summary; they never count
as five independent replicates.
"""

from __future__ import annotations

import math
from typing import Dict

import numpy as np

from .stats_utils import wilson_ci


def _logit(probability: float) -> float:
    return math.log(probability / (1.0 - probability))


def _sigmoid(value):
    return 1.0 / (1.0 + np.exp(-value))


def _one_sided_normal_p(values: np.ndarray) -> float:
    """Planning approximation to the preregistered sign-flip test."""
    values = np.asarray(values, dtype=float)
    if len(values) < 2:
        return 1.0
    standard_error = float(values.std(ddof=1) / math.sqrt(len(values)))
    if standard_error <= 0.0:
        return 0.0 if float(values.mean()) > 0.0 else 1.0
    z_value = float(values.mean()) / standard_error
    return 0.5 * math.erfc(z_value / math.sqrt(2.0))


def _power_result(successes: int, n_sim: int) -> Dict[str, float]:
    low, high = wilson_ci(successes, n_sim)
    return {
        "power": successes / float(n_sim),
        "mc_ci_lo": low,
        "mc_ci_hi": high,
    }


def simulate_controlled_v4_power(
    n_episode_seeds: int,
    full_late_match: float,
    swap_late_new_match: float,
    n_sim: int = 2000,
    baseline_match: float = 1.0 / 3.0,
    pre_swap_old_match: float = 0.55,
    late_old_fraction_of_errors: float = 0.50,
    episode_logit_sd: float = 0.45,
    alpha_each: float = 0.025,
    seed: int = 0,
) -> Dict[str, object]:
    """Estimate power for the two co-primary V4 episode-level contrasts.

    Stable contrast: paired difference-in-differences between full and no
    history using five early and five held-out rounds per episode.

    Swap contrast: late new-target minus old-target match over five held-out
    rounds. Six ordered swap episodes are present per scenario-sequence seed.

    The sign-flip test is approximated by its one-sided normal statistic during
    planning; the final analysis uses Monte Carlo sign flips. This approximation
    is declared in every output rather than presented as exact power.
    """
    if n_episode_seeds < 1 or n_sim < 1:
        raise ValueError("episode seeds and simulations must be positive")
    for name, value in (
        ("baseline_match", baseline_match),
        ("full_late_match", full_late_match),
        ("pre_swap_old_match", pre_swap_old_match),
        ("swap_late_new_match", swap_late_new_match),
        ("late_old_fraction_of_errors", late_old_fraction_of_errors),
        ("alpha_each", alpha_each),
    ):
        if not 0.0 < value < 1.0:
            raise ValueError("%s must be in (0,1)" % name)
    if full_late_match <= baseline_match:
        raise ValueError("full_late_match must exceed baseline_match")
    if swap_late_new_match <= baseline_match:
        raise ValueError("swap_late_new_match must exceed baseline_match")

    generator = np.random.default_rng(seed)
    n_stable = 3 * n_episode_seeds
    n_swap = 6 * n_episode_seeds
    stable_significant = 0
    swap_significant = 0
    joint_significant = 0
    stable_estimates = []
    swap_estimates = []
    swap_new_gain_estimates = []
    swap_old_drop_estimates = []

    for _ in range(n_sim):
        stable_offset = generator.normal(0.0, episode_logit_sd, size=n_stable)
        p_base = _sigmoid(_logit(baseline_match) + stable_offset)
        p_full_late = _sigmoid(_logit(full_late_match) + stable_offset)
        full_early = generator.binomial(1, p_base[:, None], size=(n_stable, 5)).mean(axis=1)
        full_late = generator.binomial(1, p_full_late[:, None], size=(n_stable, 5)).mean(axis=1)
        no_early = generator.binomial(1, p_base[:, None], size=(n_stable, 5)).mean(axis=1)
        no_late = generator.binomial(1, p_base[:, None], size=(n_stable, 5)).mean(axis=1)
        stable_values = (full_late - full_early) - (no_late - no_early)
        stable_p = _one_sided_normal_p(stable_values)
        stable_hit = stable_p <= alpha_each
        stable_significant += int(stable_hit)
        stable_estimates.append(float(stable_values.mean()))

        swap_offset = generator.normal(0.0, episode_logit_sd, size=n_swap)
        p_new = _sigmoid(_logit(swap_late_new_match) + swap_offset)
        # Preserve a valid three-category distribution while allowing stale-old
        # choices to occupy a declared fraction of non-new choices.
        p_old = (1.0 - p_new) * late_old_fraction_of_errors
        draws = generator.random((n_swap, 5))
        new_rate = (draws < p_new[:, None]).mean(axis=1)
        old_rate = (
            (draws >= p_new[:, None])
            & (draws < (p_new + p_old)[:, None])
        ).mean(axis=1)
        p_pre_old = _sigmoid(_logit(pre_swap_old_match) + swap_offset)
        p_pre_new = (1.0 - p_pre_old) / 2.0
        pre_draws = generator.random((n_swap, 5))
        pre_old_rate = (pre_draws < p_pre_old[:, None]).mean(axis=1)
        pre_new_rate = (
            (pre_draws >= p_pre_old[:, None])
            & (pre_draws < (p_pre_old + p_pre_new)[:, None])
        ).mean(axis=1)
        swap_values = new_rate - old_rate
        swap_p = _one_sided_normal_p(swap_values)
        swap_hit = swap_p <= alpha_each
        swap_significant += int(swap_hit)
        swap_estimates.append(float(swap_values.mean()))
        swap_new_gain_estimates.append(float((new_rate - pre_new_rate).mean()))
        swap_old_drop_estimates.append(float((pre_old_rate - old_rate).mean()))
        joint_significant += int(stable_hit and swap_hit)

    return {
        "n_episode_seeds": n_episode_seeds,
        "stable_episodes_per_condition": n_stable,
        "swap_episodes": n_swap,
        "full_late_match": full_late_match,
        "stable_nominal_advantage": full_late_match - baseline_match,
        "swap_late_new_match": swap_late_new_match,
        "stable_test": {
            **_power_result(stable_significant, n_sim),
            "mean_estimated_difference_in_differences": float(np.mean(stable_estimates)),
        },
        "swap_test": {
            **_power_result(swap_significant, n_sim),
            "mean_estimated_late_new_over_old": float(np.mean(swap_estimates)),
            "mean_estimated_new_target_gain": float(np.mean(swap_new_gain_estimates)),
            "mean_estimated_old_target_drop": float(np.mean(swap_old_drop_estimates)),
        },
        "joint_co_primary": _power_result(joint_significant, n_sim),
        "n_sim": n_sim,
        "assumptions": {
            "baseline_match": baseline_match,
            "pre_swap_old_match": pre_swap_old_match,
            "late_old_fraction_of_errors": late_old_fraction_of_errors,
            "episode_logit_sd": episode_logit_sd,
            "analysis_window_rounds": 5,
            "alpha_each": alpha_each,
            "independent_unit": "episode",
            "planning_test_approximation": "one-sided normal approximation to sign-flip test",
        },
    }
