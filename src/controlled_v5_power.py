"""Exact-test Monte Carlo power sensitivity for the blocked V5 design.

The simulated observations have the same six-round windows and integer-valued
episode summaries as the real analysis.  Sign-flip p-values are computed by
dynamic programming over the complete null distribution, not by a normal or
Monte Carlo approximation.  Monte Carlo uncertainty therefore comes only from
estimating repeated-study power.
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
import math
from typing import Dict, Mapping, Optional, Sequence

import numpy as np

from config import CONTROLLED_V5_GATE_THRESHOLDS, STRATEGIES
from .stats_utils import wilson_ci


TRANSITIONS = tuple(
    (old, new) for old in STRATEGIES for new in STRATEGIES if old != new
)


def exact_one_sided_sign_flip_p(integer_block_values: Sequence[int]) -> float:
    """Return the complete-enumeration sign-flip p-value for a positive mean.

    V5 block summaries lie on a small rational grid. Multiplying by their
    common denominator gives the integer values accepted here, allowing an
    exact dynamic-programming distribution even for 30 blocks (where explicit
    enumeration of ``2**30`` signs would be wasteful).
    """
    values = [int(value) for value in integer_block_values]
    if not values:
        return 1.0
    observed = sum(values)
    distribution = Counter({0: 1})
    for value in values:
        updated: Counter = Counter()
        for subtotal, count in distribution.items():
            updated[subtotal + value] += count
            updated[subtotal - value] += count
        distribution = updated
    exceed = sum(count for subtotal, count in distribution.items() if subtotal >= observed)
    return exceed / float(2 ** len(values))


def exact_rational_sign_flip_test(values: Sequence[float]) -> Dict[str, float]:
    """Exact sign-flip test for rational-valued analysis summaries."""
    if not values:
        return {
            "mean": float("nan"),
            "p_value_one_sided": 1.0,
            "n": 0,
            "n_sign_assignments": 0,
            "test_method": "exact sign flip",
        }
    fractions = [Fraction(float(value)).limit_denominator(100000) for value in values]
    denominator = 1
    for value in fractions:
        denominator = math.lcm(denominator, value.denominator)
    integer_values = [
        int(value.numerator * (denominator // value.denominator))
        for value in fractions
    ]
    return {
        "mean": float(np.mean(values)),
        "p_value_one_sided": exact_one_sided_sign_flip_p(integer_values),
        "n": len(values),
        "n_sign_assignments": 2 ** len(values),
        "test_method": "complete exact sign-flip distribution",
    }


def _power_result(successes: int, n_sim: int) -> Dict[str, float]:
    low, high = wilson_ci(successes, n_sim)
    return {
        "power": successes / float(n_sim),
        "mc_ci_lo": low,
        "mc_ci_hi": high,
    }


def _validate_shares(frame_shares: Mapping[str, float]) -> Dict[str, float]:
    if set(frame_shares) != set(STRATEGIES):
        raise ValueError("baseline frame shares must contain all three V5 frames")
    clean = {frame: float(frame_shares[frame]) for frame in STRATEGIES}
    if any(not 0.0 < value < 1.0 for value in clean.values()):
        raise ValueError("baseline frame shares must lie in (0,1)")
    if not np.isclose(sum(clean.values()), 1.0, atol=1e-9):
        raise ValueError("baseline frame shares must sum to one")
    return clean


def _bounded(probability: float) -> float:
    return float(np.clip(probability, 0.01, 0.98))


def _multinomial_new_old(
    generator: np.random.Generator, new_probability: float, old_probability: float
) -> tuple[int, int]:
    other = 1.0 - new_probability - old_probability
    if min(new_probability, old_probability, other) < 0.0:
        raise ValueError("invalid simulated swap category probabilities")
    new_count, old_count, _ = generator.multinomial(
        6, [new_probability, old_probability, other]
    )
    return int(new_count), int(old_count)


def simulate_controlled_v5_power(
    n_episode_seeds: int,
    stable_did: float,
    revision_shift: float,
    n_sim: int = 5000,
    baseline_frame_shares: Optional[Mapping[str, float]] = None,
    pre_swap_old_match: float = 0.50,
    development_effect_fraction: float = 0.80,
    shuffled_effect_fraction: float = 0.0,
    seed_probability_sd: float = 0.035,
    transition_effect_sd: float = 0.035,
    alpha_each: float = 0.025,
    seed: int = 0,
) -> Dict[str, object]:
    """Simulate both co-primary tests and the complete substantive pattern.

    ``stable_did`` and ``revision_shift`` are population-scale smallest effects
    of interest on probability-difference scales. The baseline shares should be
    replaced by the selected-bank no-history validation shares before final
    sample-size selection.
    """
    if n_episode_seeds < 1 or n_sim < 1:
        raise ValueError("episode seeds and simulations must be positive")
    if not 0.0 <= stable_did < 0.50 or not 0.0 <= revision_shift < 0.75:
        raise ValueError("V5 effect sizes are outside the supported range")
    if not 0.0 <= development_effect_fraction <= 1.0:
        raise ValueError("development_effect_fraction must lie in [0,1]")
    if not 0.0 <= shuffled_effect_fraction <= 1.0:
        raise ValueError("shuffled_effect_fraction must lie in [0,1]")
    if not 1.0 / 3.0 < pre_swap_old_match < 0.90:
        raise ValueError("pre_swap_old_match must exceed chance and remain below .90")
    if seed_probability_sd < 0.0 or transition_effect_sd < 0.0:
        raise ValueError("simulation standard deviations cannot be negative")
    if not 0.0 < alpha_each < 0.5:
        raise ValueError("alpha_each must lie in (0,.5)")
    shares = _validate_shares(
        baseline_frame_shares or {frame: 1.0 / 3.0 for frame in STRATEGIES}
    )

    thresholds = CONTROLLED_V5_GATE_THRESHOLDS
    generator = np.random.default_rng(seed)
    stable_hits = revision_hits = joint_hits = complete_hits = 0
    stable_estimates = []
    revision_estimates = []
    transition_support_counts = []

    for _ in range(n_sim):
        # Stable conditions: three target episodes are collapsed within each
        # scenario-sequence seed before the exact sign flip.
        stable_block_numerators = []
        full_late_counts = Counter()
        no_late_counts = Counter()
        shuffled_late_total = 0
        no_gain_numerator = 0
        random_gain_numerator = 0
        development_stable_numerator = 0
        for _seed_index in range(n_episode_seeds):
            block_offset = generator.normal(0.0, seed_probability_sd)
            block_numerator = 0
            for target in STRATEGIES:
                target_offset = generator.normal(0.0, seed_probability_sd / 2.0)
                baseline = _bounded(shares[target] + block_offset + target_offset)
                full_early = int(generator.binomial(6, baseline))
                no_early = int(generator.binomial(6, baseline))
                no_late = int(generator.binomial(6, baseline))
                full_late_probability = _bounded(baseline + stable_did)
                full_late = int(generator.binomial(6, full_late_probability))
                development_full = int(
                    generator.binomial(
                        6,
                        _bounded(
                            baseline + stable_did * development_effect_fraction
                        ),
                    )
                )
                development_no = int(generator.binomial(6, baseline))
                shuffled_late = int(
                    generator.binomial(
                        6,
                        _bounded(baseline + stable_did * shuffled_effect_fraction),
                    )
                )
                random_early = int(generator.binomial(6, baseline))
                random_late = int(generator.binomial(6, baseline))
                block_numerator += full_late - full_early - no_late + no_early
                development_stable_numerator += (
                    development_full - full_early - development_no + no_early
                )
                no_gain_numerator += no_late - no_early
                random_gain_numerator += random_late - random_early
                full_late_counts[target] += full_late
                no_late_counts[target] += no_late
                shuffled_late_total += shuffled_late
            stable_block_numerators.append(block_numerator)
        stable_mean = sum(stable_block_numerators) / float(
            18 * n_episode_seeds
        )
        stable_p = exact_one_sided_sign_flip_p(stable_block_numerators)
        stable_hit = (
            stable_mean >= thresholds["minimum_stable_difference_in_differences"]
            and stable_p <= alpha_each
        )

        # Swap conditions: every seed has all six ordered transitions. Equal
        # averaging within seed gives each transition identical weight.
        swap_block_numerators = []
        transition_numerators = Counter()
        development_swap_numerator = 0
        for _seed_index in range(n_episode_seeds):
            seed_effect = generator.normal(0.0, seed_probability_sd)
            block_numerator = 0
            for transition in TRANSITIONS:
                transition_effect = generator.normal(0.0, transition_effect_sd)
                effective_shift = float(
                    np.clip(revision_shift + seed_effect + transition_effect, 0.0, 0.70)
                )
                pre_old = _bounded(
                    pre_swap_old_match
                    + generator.normal(0.0, seed_probability_sd / 2.0)
                )
                pre_new = (1.0 - pre_old) / 2.0
                late_new = pre_new + effective_shift / 2.0
                late_old = pre_old - effective_shift / 2.0
                development_shift = effective_shift * development_effect_fraction
                development_new = pre_new + development_shift / 2.0
                development_old = pre_old - development_shift / 2.0
                pre_new_count, pre_old_count = _multinomial_new_old(
                    generator, pre_new, pre_old
                )
                late_new_count, late_old_count = _multinomial_new_old(
                    generator, late_new, late_old
                )
                dev_new_count, dev_old_count = _multinomial_new_old(
                    generator, development_new, development_old
                )
                numerator = (
                    late_new_count
                    - late_old_count
                    - pre_new_count
                    + pre_old_count
                )
                development_numerator = (
                    dev_new_count
                    - dev_old_count
                    - pre_new_count
                    + pre_old_count
                )
                transition_numerators[transition] += numerator
                development_swap_numerator += development_numerator
                block_numerator += numerator
            swap_block_numerators.append(block_numerator)
        revision_mean = sum(swap_block_numerators) / float(
            36 * n_episode_seeds
        )
        revision_p = exact_one_sided_sign_flip_p(swap_block_numerators)
        revision_hit = (
            revision_mean >= thresholds["minimum_revision_shift"]
            and revision_p <= alpha_each
        )

        stable_hits += int(stable_hit)
        revision_hits += int(revision_hit)
        joint_hits += int(stable_hit and revision_hit)
        stable_estimates.append(stable_mean)
        revision_estimates.append(revision_mean)

        transition_means = {
            transition: transition_numerators[transition]
            / float(6 * n_episode_seeds)
            for transition in TRANSITIONS
        }
        supporting = {
            transition
            for transition, value in transition_means.items()
            if value >= thresholds["minimum_transition_revision_shift"]
        }
        origins = {old for old, _new in supporting}
        transition_support_counts.append(len(supporting))
        denominator = float(18 * n_episode_seeds)
        full_late_mean = sum(full_late_counts.values()) / denominator
        full_no_late = (
            sum(full_late_counts.values()) - sum(no_late_counts.values())
        ) / denominator
        full_shuffled_late = (
            sum(full_late_counts.values()) - shuffled_late_total
        ) / denominator
        per_type_supported = all(
            (full_late_counts[target] - no_late_counts[target])
            / float(6 * n_episode_seeds)
            >= thresholds["minimum_per_type_late_advantage"]
            for target in STRATEGIES
        )
        development_stable = development_stable_numerator / denominator
        development_revision = development_swap_numerator / float(
            36 * n_episode_seeds
        )
        no_gain = no_gain_numerator / denominator
        random_gain = random_gain_numerator / denominator
        complete = (
            stable_hit
            and revision_hit
            and full_late_mean >= thresholds["minimum_full_history_late_match"]
            and full_no_late >= thresholds["minimum_full_over_no_late_match"]
            and full_shuffled_late
            >= thresholds["minimum_full_over_shuffled_late_match"]
            and abs(no_gain)
            <= thresholds["maximum_absolute_no_history_learning_gain"]
            and abs(random_gain)
            <= thresholds["maximum_absolute_random_learning_gain"]
            and per_type_supported
            and development_stable
            >= thresholds["minimum_development_stable_difference_in_differences"]
            and development_revision
            >= thresholds["minimum_development_revision_shift"]
            and len(supporting) >= thresholds["minimum_supporting_transitions"]
            and len(origins) >= thresholds["minimum_supporting_origin_types"]
        )
        complete_hits += int(complete)

    return {
        "n_episode_seeds": n_episode_seeds,
        "stable_episodes_per_condition": 3 * n_episode_seeds,
        "swap_episodes": 6 * n_episode_seeds,
        "total_confirmatory_episodes": 18 * n_episode_seeds,
        "total_confirmatory_generations": 18 * n_episode_seeds * 24,
        "stable_did_seoi": stable_did,
        "revision_shift_seoi": revision_shift,
        "stable_co_primary": {
            **_power_result(stable_hits, n_sim),
            "mean_estimated_effect": float(np.mean(stable_estimates)),
        },
        "revision_co_primary": {
            **_power_result(revision_hits, n_sim),
            "mean_estimated_effect": float(np.mean(revision_estimates)),
        },
        "joint_co_primary": _power_result(joint_hits, n_sim),
        "complete_behavioral_pattern": _power_result(complete_hits, n_sim),
        "mean_supporting_transitions": float(np.mean(transition_support_counts)),
        "n_sim": n_sim,
        "assumptions": {
            "baseline_frame_shares": shares,
            "pre_swap_old_match": pre_swap_old_match,
            "development_effect_fraction": development_effect_fraction,
            "shuffled_effect_fraction": shuffled_effect_fraction,
            "seed_probability_sd": seed_probability_sd,
            "transition_effect_sd": transition_effect_sd,
            "analysis_window_rounds": 6,
            "alpha_each": alpha_each,
            "independent_unit": "scenario-sequence seed block",
            "randomization_block": "scenario-sequence seed",
            "transition_weighting": "all six ordered transitions weighted equally within seed",
            "test": "exact one-sided sign flip by integer-grid dynamic programming",
        },
    }
