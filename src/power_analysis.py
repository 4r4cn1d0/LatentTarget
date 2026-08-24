"""Simulation-based design sensitivity for clustered LatentTarget outcomes.

The episode, not the round, is the independent unit. These simulations are a
planning aid before real-model variance is known; they are not retrospective
power calculations and do not manufacture evidence from observed results.
"""

from __future__ import annotations

import math
from typing import Dict

import numpy as np


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _two_sided_normal_p(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    if len(values) < 2:
        return 1.0
    se = float(values.std(ddof=1) / math.sqrt(len(values)))
    if se <= 0:
        return 0.0 if abs(float(values.mean())) > 0 else 1.0
    z = abs(float(values.mean())) / se
    return math.erfc(z / math.sqrt(2.0))


def simulate_behavior_power(
    n_episode_seeds: int,
    late_match_increase: float,
    n_sim: int = 2000,
    n_rounds: int = 8,
    base_match_rate: float = 1.0 / 3.0,
    episode_logit_sd: float = 0.55,
    alpha: float = 0.05,
    seed: int = 0,
) -> Dict[str, float]:
    """Power for the preregistered full-history vs no-history change contrast.

    There are three matched scenario/target episodes per episode seed. The
    estimand is ``(late - early)_full - (late - early)_no_history``. A shared
    episode intercept induces realistic within-episode clustering and pairing.
    ``late_match_increase`` is the nominal final-round increase at intercept 0.
    """
    if n_episode_seeds < 1 or n_sim < 1 or n_rounds < 4:
        raise ValueError("positive seeds/simulations and at least 4 rounds required")
    if not 0 <= late_match_increase <= 1 - base_match_rate:
        raise ValueError("late_match_increase is outside the probability range")
    rng = np.random.default_rng(seed)
    n_pairs = 3 * n_episode_seeds
    base_logit = math.log(base_match_rate / (1 - base_match_rate))
    final = base_match_rate + late_match_increase
    effect_logit = math.log(final / (1 - final)) - base_logit if late_match_increase else 0.0
    progress = np.linspace(0.0, 1.0, n_rounds)
    significant = 0
    estimates = []
    for _ in range(n_sim):
        intercept = rng.normal(0.0, episode_logit_sd, size=n_pairs)
        p_no = _sigmoid(base_logit + intercept[:, None]) * np.ones((1, n_rounds))
        p_full = _sigmoid(
            base_logit + intercept[:, None] + effect_logit * progress[None, :]
        )
        no = rng.binomial(1, p_no)
        full = rng.binomial(1, p_full)
        no_change = no[:, -3:].mean(axis=1) - no[:, :2].mean(axis=1)
        full_change = full[:, -3:].mean(axis=1) - full[:, :2].mean(axis=1)
        paired = full_change - no_change
        estimates.append(float(paired.mean()))
        significant += int(_two_sided_normal_p(paired) < alpha)
    return {
        "power": significant / n_sim,
        "mean_estimated_contrast": float(np.mean(estimates)),
        "n_episode_seeds": n_episode_seeds,
        "episodes_per_condition": n_pairs,
        "late_match_increase": late_match_increase,
        "n_sim": n_sim,
        "alpha": alpha,
        "episode_logit_sd": episode_logit_sd,
    }


def simulate_swap_gap_power(
    n_episode_seeds: int,
    standardized_gap: float,
    n_sim: int = 5000,
    alpha: float = 0.05,
    seed: int = 0,
) -> Dict[str, float]:
    """Sensitivity for the episode-level probe-minus-behaviour trajectory gap.

    Fully counterbalanced swaps create six ordered-transition episodes per
    episode seed. ``standardized_gap`` is the episode-level mean divided by its
    standard deviation; values are simulated as Normal(d, 1).
    """
    if n_episode_seeds < 1 or n_sim < 1 or standardized_gap < 0:
        raise ValueError("seeds/simulations must be positive and gap non-negative")
    rng = np.random.default_rng(seed)
    n_episodes = 6 * n_episode_seeds
    significant = 0
    for _ in range(n_sim):
        values = rng.normal(standardized_gap, 1.0, size=n_episodes)
        significant += int(_two_sided_normal_p(values) < alpha)
    return {
        "power": significant / n_sim,
        "n_episode_seeds": n_episode_seeds,
        "swap_episodes": n_episodes,
        "standardized_gap": standardized_gap,
        "n_sim": n_sim,
        "alpha": alpha,
    }
