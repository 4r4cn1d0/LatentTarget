"""Prospective bundle-randomized power program for controlled-choice V6.

The episode-seed bundle is the only randomized and inferential unit. Within a
bundle one allocation bit labels two stable branch slots as full-history versus
no-history for all three target trajectories. A second, independently-derived
bit labels two transition branch slots as silent-swap versus stable-old for all
six ordered transitions. The two co-primary Fisher tests enumerate the exact
``2**N`` sign-flip distribution of the resulting N bundle contrasts.

Power data are generated one round at a time. Frame choices are categorical,
target responses are Bernoulli, and only visible-history trajectories update a
Beta-Bernoulli feedback state. All simulation studies are summarized by
:func:`analyze_v6_bundle_study`, the same exported estimand/test/gate helper
intended for the confirmatory analysis adapter.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import nullcontext
from copy import deepcopy
from functools import lru_cache
from fractions import Fraction
from itertools import permutations
import hashlib
import json
import math
import os
from typing import Any, Dict, Mapping, Optional, Sequence

import numpy as np

from config import CONTROLLED_V6_GATE_THRESHOLDS, STRATEGIES
from .controlled_v6_randomization import (
    V6_HISTORY_FAMILY,
    V6_SWAP_FAMILY,
    v6_allocation_bit,
)
from .stats_utils import wilson_ci


V6_STABLE_DID_POPULATION_ALTERNATIVE = 0.20
V6_REVISION_SHIFT_POPULATION_ALTERNATIVE = 0.25
V6_SWAP_COMPONENT_ALTERNATIVES = (
    (0.10, 0.15),
    (0.125, 0.125),
    (0.15, 0.10),
)
V6_LEARNER_PROFILES = (
    (2, 0.0, 0.0),
    (6, 0.035, 0.035),
    (12, 0.07, 0.07),
)
# Probability-scale local-alternative tilts are calibrated so the complete
# sequential feedback model, not the raw tilt alone, centers the estimands on
# 0.20 stable and the registered swap-component alternatives. They are DGP
# nuisance parameters, not additional scientific alternatives.
V6_CALIBRATED_PROBABILITY_TILTS = (
    (0.090, 0.013, 0.061),
    (0.118, 0.064, 0.058),
    (0.141, 0.108, 0.053),
)
V6_EPISODE_SEED_GRID = (12, 18, 24, 30)
V6_PLANNING_CEILING_EPISODE_SEEDS = 30
V6_MINIMUM_SIMULATIONS_PER_CELL = 10_000
V6_TARGET_LOWER_MC_BOUND = 0.80
V6_ALLOCATION_RNG_ROOT = 20262006
V6_ALLOCATION_BIT_GENERATOR = "PCG64DXSM"
V6_POWER_SEED = 20262003
V6_POWER_PAYLOAD_SCHEMA_VERSION = (
    "controlled-v6-power-v5-prospective-randomized-bundles"
)
V6_STUDY_SCHEMA_VERSION = "controlled-v6-bundle-study-v1"
V6_CANONICAL_POWER_OUTPUT_DIR = "results/v6_design/power_prevalidation"
V6_ROUNDS_PER_EPISODE = 24
V6_NO_HISTORY_EPISODES_PER_SEED = 3

V6_EXPECTED_OBSERVED_STABLE_DID_GATE = 0.10
V6_EXPECTED_OBSERVED_REVISION_GATE = 0.15
V6_EXPECTED_ADJUSTED_NEW_GAIN_GATE = 0.05
V6_EXPECTED_ADJUSTED_OLD_DROP_GATE = 0.05
V6_EXPECTED_LATE_SWAP_NEW_MINUS_OLD_GATE = 0.0
V6_EXPECTED_MINIMUM_FRAME_SHARE = 0.25
V6_EXPECTED_MAXIMUM_FRAME_SHARE = 0.42
V6_EXPECTED_MAXIMUM_FRAME_GAP = 0.15
V6_ALPHA_EACH = 0.025
V6_NULL_PER_TEST_UPPER_LIMIT = 0.030
V6_NULL_JOINT_UPPER_LIMIT = 0.030
V6_NULL_FAMILYWISE_UPPER_LIMIT = 0.0575
V6_PATH_BALANCE_SCREEN_CONFIGURATION_ID = "minimum_share_boundary_01"
V6_PATH_BALANCE_SCREEN_SIMULATIONS = 10_000

V6_FRAME_SHARE_NUISANCE_ORBITS = (
    ("balanced", (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)),
    ("minimum_share_boundary", (0.25, 0.35, 0.40)),
    ("maximum_share_boundary", (0.27, 0.31, 0.42)),
)
V6_FRAME_SHARE_NUISANCE_CELLS = tuple(
    {
        "configuration_id": (
            "balanced"
            if family == "balanced"
            else "%s_%02d" % (family, family_index)
        ),
        "family": family,
        "frame_shares": {
            frame: float(value)
            for frame, value in zip(STRATEGIES, ordered)
        },
    }
    for family, values in V6_FRAME_SHARE_NUISANCE_ORBITS
    for family_index, ordered in enumerate(
        sorted(set(permutations(values))), start=1
    )
)

V6_PLANNING_SCENARIOS = tuple(
    {
        "scenario_id": "learner_%d" % index,
        "prior_ess": profile[0],
        "seed_probability_sd": profile[1],
        "transition_probability_sd": profile[2],
        "adjusted_new_gain_alternative": components[0],
        "adjusted_old_drop_alternative": components[1],
        "revision_alternative": components[0] + components[1],
        "stable_did_alternative": V6_STABLE_DID_POPULATION_ALTERNATIVE,
        "stable_probability_tilt": tilts[0],
        "new_probability_tilt": tilts[1],
        "old_probability_tilt": tilts[2],
        "selection_authority": True,
    }
    for index, (profile, components, tilts) in enumerate(
        zip(
            V6_LEARNER_PROFILES,
            V6_SWAP_COMPONENT_ALTERNATIVES,
            V6_CALIBRATED_PROBABILITY_TILTS,
        ),
        start=1,
    )
)

V6_NULL_LATENT_PROFILES = (
    {
        "profile_id": "symmetric",
        "slot_logit_offsets": ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
        "serial_rho": 0.55,
        "serial_logit_sd": 0.12,
    },
    {
        "profile_id": "asymmetric_slots",
        "slot_logit_offsets": ((0.90, -0.60, -0.30), (-0.75, 0.95, -0.20)),
        "serial_rho": 0.70,
        "serial_logit_sd": 0.16,
    },
    {
        "profile_id": "adversarial_serial",
        "slot_logit_offsets": ((1.10, -0.80, -0.30), (-0.95, 0.15, 0.80)),
        "serial_rho": 0.88,
        "serial_logit_sd": 0.22,
    },
)

V6_POWER_INPUT_POLICY = (
    "frozen prospective assumptions and accepted balance cells only; focal, "
    "confirmatory, calibration-selection, and validation outcomes are forbidden"
)
V6_FORBIDDEN_OUTCOME_FLAGS = (
    "focal_model_outcomes_used",
    "confirmatory_outcomes_used",
    "selected_bank_validation_outputs_used",
)

FINITE_NUISANCE_GRID_COVERAGE_NOTE = (
    "Worst-case power is the minimum over the 13 frozen finite frame-share "
    "cells. It is not a claim of continuous worst-case coverage. Because two "
    "families put a population share exactly on an observed inclusive balance "
    "boundary, realized balance-gate power can remain near one half rather "
    "than converge to one."
)
EQUAL_OBSERVED_GATE_POWER_LIMIT_NOTE = (
    "A point-estimate gate equal to the population effect is cleared with "
    "probability approaching one half; the V6 planning effects therefore "
    "remain 0.20 stable and 0.25 revision against 0.10 and 0.15 gates."
)
V6_POWER_SELECTION_RULE = (
    "Choose the smallest N in [12,18,24,30] for which the lower 95% Wilson "
    "bounds of both joint co-primary rejection power and complete-gate power "
    "are at least 0.80 in every one of the 39 authoritative combinations of "
    "13 frame-share cells and three learner/component profiles. Require all "
    "null-profile upper-size checks to pass; otherwise stop before validation."
)


V6_PROSPECTIVE_POWER_CONTRACT: Dict[str, Any] = {
    "schema_version": V6_POWER_PAYLOAD_SCHEMA_VERSION,
    "design_version": "controlled-choice-v6.0",
    "design": {
        "randomized_unit": "episode-seed bundle",
        "independent_units": "N episode-seed bundles",
        "stable_branches_per_bundle": 2,
        "stable_target_trajectories": list(STRATEGIES),
        "swap_branches_per_bundle": 2,
        "ordered_transitions": [
            "%s->%s" % (old, new)
            for old in STRATEGIES
            for new in STRATEGIES
            if old != new
        ],
        "one_bit_shared_across_stable_trajectories": True,
        "one_independent_bit_shared_across_ordered_transitions": True,
    },
    "allocation": {
        "rng_root": V6_ALLOCATION_RNG_ROOT,
        "bit_generator": V6_ALLOCATION_BIT_GENERATOR,
        "derivation": (
            "controlled_v6_randomization.v6_allocation_bit: numpy "
            "SeedSequence([root, family_code, allocation_index]) feeding "
            "PCG64DXSM; draw integers(0,2)"
        ),
        "bundle_indexing": "zero-based frozen confirmatory schedule order",
        "family_codes": {"history_access": 0, "target_regime": 1},
        "actual_study_index": 0,
        "power_simulation_allocation_index": (
            "study_index * 31 + bundle_index; stride 31 exceeds N ceiling 30"
        ),
        "bit_semantics": (
            "bit b assigns active condition to slot b and comparator to slot 1-b"
        ),
    },
    "round_schedule": {
        "n_rounds": 24,
        "development_split": [1, 18],
        "heldout_split": [19, 24],
        "early_window": [1, 6],
        "pre_swap_window": [7, 12],
        "post_swap_development_window": [13, 18],
        "late_window": [19, 24],
        "target_switch": "after round 12 in silent-swap only",
        "stable_counterfactual": "old target for all 24 rounds",
        "physical_slot_coupled_round_one_potential_outcomes": True,
        "slot_permutation_schedule": (
            "all six permutations once per six-round block"
        ),
        "triad_schedule": (
            "six selected development triads cycle in rounds 1:18 and four "
            "selected heldout triads cycle in rounds 19:24"
        ),
    },
    "estimands": {
        "stable": (
            "bundle mean over three targets of [(late19:24-early1:6) full "
            "minus (late19:24-early1:6) no]"
        ),
        "adjusted_new_gain": (
            "bundle mean over six transitions of [(late new-pre7:12 new) "
            "swap minus the same stable-old contrast]"
        ),
        "adjusted_old_drop": (
            "bundle mean over six transitions of [(pre7:12 old-late old) "
            "swap minus the same stable-old contrast]"
        ),
        "revision": "adjusted_new_gain + adjusted_old_drop",
        "late_swap_new_minus_old": (
            "mean over bundles and transitions of late19:24 new minus old in swap"
        ),
    },
    "inference": {
        "co_primary": ["stable", "revision"],
        "test": "exact one-sided within-bundle Fisher sign-flip test",
        "sharp_null": True,
        "enumerated_assignments": "2**N for each co-primary",
        "alpha_each": V6_ALPHA_EACH,
        "multiplicity": "co-primary Bonferroni allocation of 0.025 each",
        "stable_integer_scale": 18,
        "revision_integer_scale": 36,
    },
    "complete_gates": {
        "stable_minimum": V6_EXPECTED_OBSERVED_STABLE_DID_GATE,
        "revision_minimum": V6_EXPECTED_OBSERVED_REVISION_GATE,
        "adjusted_new_gain_minimum": V6_EXPECTED_ADJUSTED_NEW_GAIN_GATE,
        "adjusted_old_drop_minimum": V6_EXPECTED_ADJUSTED_OLD_DROP_GATE,
        "late_swap_new_minus_old_minimum": (
            V6_EXPECTED_LATE_SWAP_NEW_MINUS_OLD_GATE
        ),
        "p_value_each_maximum": V6_ALPHA_EACH,
        "retained_controls": [
            "design and assignment integrity",
            "all selections valid and zero fallback",
            "realized no-history frame balance",
            "no-history absolute learning gain <= 0.10",
            "random-target absolute learning gain <= 0.10",
            "full-history late match >= 0.50",
            "full-minus-no late match >= 0.10",
            "all three target types have late advantage >= 0.05",
            "at least four transition revisions >= 0.10 covering all origins",
        ],
        "excluded_old_controls": {
            "shuffled_history_specificity": (
                "not part of either prospectively randomized branch pair"
            ),
            "development_wording_thresholds": (
                "secondary split diagnostics, not co-primary estimands"
            ),
        },
    },
    "simulation": {
        "frame_model": "categorical softmax choice on complete 24-round paths",
        "feedback_model": "frame-specific Beta-Bernoulli posterior",
        "feedback_updates": (
            "visible-history branches only; no-history is frozen"
        ),
        "target_rates": {"match": 0.72, "mismatch": 0.38, "random": 0.50},
        "stable_did_alternative": V6_STABLE_DID_POPULATION_ALTERNATIVE,
        "learner_profiles": [
            {
                "prior_ess": ess,
                "seed_probability_sd": seed_sd,
                "transition_probability_sd": transition_sd,
            }
            for ess, seed_sd, transition_sd in V6_LEARNER_PROFILES
        ],
        "swap_component_alternatives": [
            {"adjusted_new_gain": new, "adjusted_old_drop": old}
            for new, old in V6_SWAP_COMPONENT_ALTERNATIVES
        ],
        "calibrated_probability_tilts": [
            {
                "stable": stable,
                "new": new,
                "old": old,
                "role": (
                    "DGP calibration nuisance; feedback plus tilt centers the "
                    "registered estimand alternative"
                ),
            }
            for stable, new, old in V6_CALIBRATED_PROBABILITY_TILTS
        ],
        "heterogeneity": {
            "scenario_frame_logit_sd": 0.10,
            "triad_frame_logit_sd": 0.08,
            "candidate_slot_logit_sd": 0.10,
            "branch_slot_logit_sd": 0.04,
            "pair_frame_logit_sd": 0.06,
            "serial_ar1_rho": 0.55,
            "serial_frame_logit_sd": 0.12,
            "feedback_logit_scale": 2.5,
        },
        "allocation_rng_root": V6_ALLOCATION_RNG_ROOT,
        "power_rng_root": V6_POWER_SEED,
        "power_bit_generator": "PCG64DXSM",
    },
    "nuisance_grid": {
        "orbits": [
            {"family": family, "shares": list(shares)}
            for family, shares in V6_FRAME_SHARE_NUISANCE_ORBITS
        ],
        "expanded_cells": [
            deepcopy(cell) for cell in V6_FRAME_SHARE_NUISANCE_CELLS
        ],
        "expanded_cell_count": 13,
        "coverage_note": FINITE_NUISANCE_GRID_COVERAGE_NOTE,
    },
    "power": {
        "n_grid": list(V6_EPISODE_SEED_GRID),
        "official_simulations_per_cell_minimum": (
            V6_MINIMUM_SIMULATIONS_PER_CELL
        ),
        "target_wilson_lower_bound": V6_TARGET_LOWER_MC_BOUND,
        "official_effect_cell_count": 156,
        "official_null_cell_count": 13,
        "official_total_cell_count": 169,
        "selection_rule": V6_POWER_SELECTION_RULE,
        "path_balance_dominance_screen": {
            "configuration_id": V6_PATH_BALANCE_SCREEN_CONFIGURATION_ID,
            "planning_scenario_ids": [
                scenario["scenario_id"] for scenario in V6_PLANNING_SCENARIOS
            ],
            "simulations_per_cell": V6_PATH_BALANCE_SCREEN_SIMULATIONS,
            "simulation_seed": V6_POWER_SEED,
            "study_offset": (
                "1 + scenario_index * 1000000 + N * 10000; identical to the "
                "corresponding cells in the complete frozen power grid"
            ),
            "short_circuit_rule": (
                "For each N, complete success is a replicate-wise subset of "
                "realized no-history balance success. Wilson lower bounds are "
                "monotone in the success count. If any registered screened "
                "cell has balance Wilson lower bound below 0.80, that N cannot "
                "satisfy the every-cell complete-power selection rule and the "
                "remaining trajectories need not be simulated."
            ),
        },
    },
    "null_size": {
        "profiles": [deepcopy(profile) for profile in V6_NULL_LATENT_PROFILES],
        "one_sided_each_upper_limit": V6_NULL_PER_TEST_UPPER_LIMIT,
        "joint_both_upper_limit": V6_NULL_JOINT_UPPER_LIMIT,
        "familywise_any_upper_limit": V6_NULL_FAMILYWISE_UPPER_LIMIT,
        "decision_rule": "upper limits only; no lower Type-I bound",
    },
    "input_policy": V6_POWER_INPUT_POLICY,
}

# Replaced after the literal contract is finalized. Keeping a literal expected
# digest makes in-process contract mutation fail closed.
V6_POWER_CONTRACT_SHA256 = (
    "e29dbbe8da2ecf6f7d891f5aee997052aff3d06dfc10e31db0d55ab757be2fd9"
)

_V6_EXACT_TEST_CACHE_SIZE = 16_384
_V6_PARALLEL_MIN_SIMULATIONS_PER_CELL = 100


class V6UnderpoweredError(RuntimeError):
    """Raised when the prospective power rule authorizes no N through 30."""


class V6PowerAuditError(ValueError):
    """Raised when a V6 power artifact fails schema, drift, or replay audit."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _assert_v6_power_contract() -> None:
    """Fail closed on contract or live gate drift."""
    observed_hash = _canonical_sha256(V6_PROSPECTIVE_POWER_CONTRACT)
    if observed_hash != V6_POWER_CONTRACT_SHA256:
        raise RuntimeError(
            "V6_PROSPECTIVE_POWER_CONTRACT drifted: expected %s, observed %s"
            % (V6_POWER_CONTRACT_SHA256, observed_hash)
        )
    expected = {
        "minimum_stable_difference_in_differences": 0.10,
        "minimum_revision_shift": 0.15,
        "minimum_adjusted_new_target_gain": 0.05,
        "minimum_adjusted_old_target_drop": 0.05,
        "minimum_swap_late_new_over_old": 0.0,
        "confirmatory_alpha_one_sided": 0.025,
        "minimum_no_history_frame_share": 0.25,
        "maximum_no_history_frame_share": 0.42,
        "maximum_no_history_frame_gap": 0.15,
    }
    drift = {
        key: CONTROLLED_V6_GATE_THRESHOLDS.get(key)
        for key, value in expected.items()
        if not math.isclose(
            float(CONTROLLED_V6_GATE_THRESHOLDS.get(key, float("nan"))),
            value,
            abs_tol=1e-12,
        )
    }
    if drift:
        raise RuntimeError("CONTROLLED_V6_GATE_THRESHOLDS drifted: %r" % drift)


def get_v6_canonical_power_output_directory(*, absolute: bool = False) -> str:
    if not absolute:
        return V6_CANONICAL_POWER_OUTPUT_DIR
    root = os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir))
    path = os.path.realpath(os.path.join(root, V6_CANONICAL_POWER_OUTPUT_DIR))
    if os.path.commonpath([root, path]) != root:
        raise RuntimeError("V6 canonical power path leaves repository root")
    return path


def _pcg64dxsm(words: Sequence[int]) -> np.random.Generator:
    sequence = np.random.SeedSequence([int(word) for word in words])
    return np.random.Generator(np.random.PCG64DXSM(sequence))


def reconstruct_v6_bundle_assignments(
    n_episode_seeds: int,
    *,
    study_index: int = 0,
    allocation_root: int = V6_ALLOCATION_RNG_ROOT,
) -> list[Dict[str, int]]:
    """Reconstruct both frozen branch-label bits for every bundle.

    ``study_index=0`` is the confirmatory allocation. Positive study indices
    create independent prospective allocations for Monte Carlo studies while
    retaining the same registered root and derivation.
    """
    if type(n_episode_seeds) is not int or n_episode_seeds < 1:
        raise ValueError("n_episode_seeds must be a positive integer")
    if type(study_index) is not int or study_index < 0:
        raise ValueError("study_index must be a non-negative integer")
    rows: list[Dict[str, int]] = []
    for bundle_index in range(n_episode_seeds):
        allocation_index = study_index * 31 + bundle_index
        rows.append(
            {
                "bundle_index": bundle_index,
                "stable_full_slot": v6_allocation_bit(
                    V6_HISTORY_FAMILY,
                    allocation_index,
                    seed=allocation_root,
                ),
                "swap_slot": v6_allocation_bit(
                    V6_SWAP_FAMILY,
                    allocation_index,
                    seed=allocation_root,
                ),
            }
        )
    return rows


def _clean_accepted_frame_shares(
    frame_shares: Mapping[str, float],
) -> Dict[str, float]:
    if set(frame_shares) != set(STRATEGIES):
        raise ValueError(
            "V6 frame shares must contain exactly the registered frames"
        )
    clean = {frame: float(frame_shares[frame]) for frame in STRATEGIES}
    if any(
        not math.isfinite(value) or value < 0.0 for value in clean.values()
    ):
        raise ValueError("V6 frame shares must be finite and non-negative")
    if not math.isclose(sum(clean.values()), 1.0, abs_tol=1e-12):
        raise ValueError("V6 frame shares must sum to one")
    if any(
        value < V6_EXPECTED_MINIMUM_FRAME_SHARE - 1e-12
        or value > V6_EXPECTED_MAXIMUM_FRAME_SHARE + 1e-12
        for value in clean.values()
    ):
        raise ValueError("V6 frame shares fall outside accepted balance bounds")
    if (
        max(clean.values()) - min(clean.values())
        > V6_EXPECTED_MAXIMUM_FRAME_GAP + 1e-12
    ):
        raise ValueError("V6 frame shares exceed the accepted maximum frame gap")
    return clean


def enumerate_v6_frame_share_nuisance_configurations() -> list[Dict[str, Any]]:
    _assert_v6_power_contract()
    configurations = [deepcopy(cell) for cell in V6_FRAME_SHARE_NUISANCE_CELLS]
    for configuration in configurations:
        configuration["frame_shares"] = _clean_accepted_frame_shares(
            configuration["frame_shares"]
        )
    if len(configurations) != 13:
        raise RuntimeError("the frozen V6 nuisance grid must contain 13 cells")
    return configurations


def _passes_v6_realized_no_history_balance_gate(
    observed_counts: Sequence[int], *, sample_size: int
) -> bool:
    if type(sample_size) is not int or sample_size <= 0:
        raise ValueError("sample_size must be a positive integer")
    counts = tuple(int(value) for value in observed_counts)
    if len(counts) != len(STRATEGIES) or any(value < 0 for value in counts):
        raise ValueError(
            "observed_counts must contain one non-negative count per frame"
        )
    if sum(counts) != sample_size:
        raise ValueError("observed_counts must sum to sample_size")
    shares = tuple(value / float(sample_size) for value in counts)
    return (
        all(
            V6_EXPECTED_MINIMUM_FRAME_SHARE - 1e-12
            <= share
            <= V6_EXPECTED_MAXIMUM_FRAME_SHARE + 1e-12
            for share in shares
        )
        and max(shares) - min(shares)
        <= V6_EXPECTED_MAXIMUM_FRAME_GAP + 1e-12
    )


def iid_v6_balance_gate_sensitivity_probability(
    n_episode_seeds: int,
    frame_shares: Mapping[str, float],
) -> float:
    """Return an IID-multinomial sensitivity value for the balance gate.

    This is deliberately *not* the registered V6 power distribution. The
    registered path model has shared heterogeneous effects and within-bundle
    dependence. This helper is retained only as a diagnostic against an IID
    reference and must never authorize or terminate V6 execution.
    """
    if type(n_episode_seeds) is not int or n_episode_seeds < 1:
        raise ValueError("n_episode_seeds must be a positive integer")
    shares = _clean_accepted_frame_shares(frame_shares)
    sample_size = V6_ROUNDS_PER_EPISODE * n_episode_seeds
    probabilities = [Fraction(str(shares[frame])) for frame in STRATEGIES]
    common_denominator = math.lcm(
        *(probability.denominator for probability in probabilities)
    )
    integer_weights = [
        probability.numerator
        * (common_denominator // probability.denominator)
        for probability in probabilities
    ]
    numerator = 0
    for first in range(sample_size + 1):
        for second in range(sample_size - first + 1):
            counts = (first, second, sample_size - first - second)
            if not _passes_v6_realized_no_history_balance_gate(
                counts, sample_size=sample_size
            ):
                continue
            coefficient = math.comb(sample_size, first) * math.comb(
                sample_size - first, second
            )
            numerator += coefficient * math.prod(
                weight**count
                for weight, count in zip(integer_weights, counts)
            )
    return float(Fraction(numerator, common_denominator**sample_size))


@lru_cache(maxsize=_V6_EXACT_TEST_CACHE_SIZE)
def _exact_sign_flip_tail_count(
    absolute_values: tuple[int, ...], observed: int
) -> int:
    distribution: Counter[int] = Counter({0: 1})
    for value in absolute_values:
        updated: Counter[int] = Counter()
        for subtotal, count in distribution.items():
            updated[subtotal + value] += count
            updated[subtotal - value] += count
        distribution = updated
    return sum(
        count for subtotal, count in distribution.items() if subtotal >= observed
    )


def _exact_one_sided_sign_flip_p(
    integer_bundle_values: Sequence[int],
) -> float:
    values = tuple(int(value) for value in integer_bundle_values)
    if not values:
        return 1.0
    observed = sum(values)
    absolute_values = tuple(
        sorted((abs(value) for value in values), reverse=True)
    )
    return _exact_sign_flip_tail_count(
        absolute_values, observed
    ) / float(2 ** len(values))


def exact_one_sided_bundle_randomization_test(
    bundle_contrasts: Sequence[float], *, integer_scale: int
) -> Dict[str, Any]:
    """Exact one-sided Fisher test for N randomized bundle contrasts."""
    if type(integer_scale) is not int or integer_scale < 1:
        raise ValueError("integer_scale must be a positive integer")
    values = [float(value) for value in bundle_contrasts]
    if not values or any(not math.isfinite(value) for value in values):
        raise ValueError(
            "bundle_contrasts must be a non-empty finite sequence"
        )
    integer_values = [int(round(value * integer_scale)) for value in values]
    for value, integer_value in zip(values, integer_values):
        if not math.isclose(
            value * integer_scale, integer_value, abs_tol=1e-8
        ):
            raise ValueError("bundle contrast is off the frozen rational grid")
    return {
        "mean": float(np.mean(values)),
        "p_value_one_sided": _exact_one_sided_sign_flip_p(integer_values),
        "n_bundles": len(values),
        "n_assignments_enumerated": 2 ** len(values),
        "integer_scale": integer_scale,
        "integer_bundle_contrasts": integer_values,
        "test_method": (
            "exact one-sided Fisher sign flip of randomized bundles"
        ),
    }


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - float(np.max(logits))
    weights = np.exp(shifted)
    return weights / float(np.sum(weights))


def _draw_category(probabilities: np.ndarray, uniform: float) -> int:
    return min(
        len(probabilities) - 1,
        int(
            np.searchsorted(
                np.cumsum(probabilities), uniform, side="right"
            )
        ),
    )


def _tilt_category(
    probabilities: np.ndarray, category: int, increment: float
) -> np.ndarray:
    if increment <= 0.0:
        return probabilities
    result = probabilities.copy()
    available = 1.0 - float(result[category])
    moved = min(float(increment), max(0.0, available - 1e-9))
    if moved == 0.0:
        return result
    for index in range(len(result)):
        if index != category:
            result[index] *= (available - moved) / available
    result[category] += moved
    return result / float(np.sum(result))


def _tilt_swap_components(
    probabilities: np.ndarray,
    *,
    old_index: int,
    new_index: int,
    adjusted_new_gain: float,
    adjusted_old_drop: float,
    ramp: float,
) -> np.ndarray:
    result = probabilities.copy()
    other_index = next(
        index for index in range(3) if index not in {old_index, new_index}
    )
    delta_new = adjusted_new_gain * ramp
    delta_old = adjusted_old_drop * ramp
    requested = np.array(
        [-delta_old, delta_new, delta_old - delta_new], dtype=float
    )
    ordered = (old_index, new_index, other_index)
    for delta, index in zip(requested, ordered):
        result[index] += delta
    if float(np.min(result)) < 1e-6:
        scale = 1.0
        for delta, index in zip(requested, ordered):
            if delta < 0.0:
                scale = min(
                    scale, (probabilities[index] - 1e-6) / (-delta)
                )
        result = probabilities.copy()
        for delta, index in zip(requested, ordered):
            result[index] += max(0.0, scale) * delta
    result = np.maximum(result, 1e-9)
    return result / float(np.sum(result))


def _target_success_probability(
    frame_index: int,
    active_target_index: int,
    *,
    random_target: bool,
) -> float:
    if random_target:
        return 0.50
    return 0.72 if frame_index == active_target_index else 0.38


def _simulate_trajectory(
    *,
    base_logits: np.ndarray,
    round_effects: np.ndarray,
    pair_effect: np.ndarray,
    active_targets: Sequence[int],
    prior_ess: float,
    rng: np.random.Generator,
    visible_history: bool,
    stable_target_increment: float = 0.0,
    swap_components: Optional[tuple[float, float]] = None,
    old_index: Optional[int] = None,
    new_index: Optional[int] = None,
    random_target: bool = False,
    forced_first_frame: Optional[int] = None,
    choice_uniforms: Optional[Sequence[float]] = None,
    outcome_uniforms: Optional[Sequence[float]] = None,
    record_trace: bool = False,
) -> Dict[str, Any]:
    """Generate one complete sequential 24-round branch trajectory."""
    if len(active_targets) != V6_ROUNDS_PER_EPISODE:
        raise ValueError("active_targets must contain exactly 24 rounds")
    alpha = np.full(3, float(prior_ess) / 2.0, dtype=float)
    beta = np.full(3, float(prior_ess) / 2.0, dtype=float)
    frames: list[str] = []
    outcomes: list[int] = []
    posterior_trace: list[list[float]] = []
    if choice_uniforms is None:
        choice_uniforms = rng.random(V6_ROUNDS_PER_EPISODE)
    if outcome_uniforms is None:
        outcome_uniforms = rng.random(V6_ROUNDS_PER_EPISODE)
    for round_offset in range(V6_ROUNDS_PER_EPISODE):
        posterior = alpha / (alpha + beta)
        logits = base_logits + round_effects[round_offset] + pair_effect
        if visible_history:
            logits = logits + 2.5 * (
                posterior - float(np.mean(posterior))
            )
        probabilities = _softmax(logits)
        stable_ramp = min(
            1.0, max(0.0, (round_offset + 1 - 6) / 12.0)
        )
        if visible_history and stable_target_increment > 0.0:
            probabilities = _tilt_category(
                probabilities,
                int(active_targets[round_offset]),
                stable_target_increment * stable_ramp,
            )
        if (
            visible_history
            and swap_components is not None
            and round_offset + 1 > 12
            and old_index is not None
            and new_index is not None
        ):
            swap_ramp = min(1.0, (round_offset + 1 - 12) / 6.0)
            probabilities = _tilt_swap_components(
                probabilities,
                old_index=old_index,
                new_index=new_index,
                adjusted_new_gain=swap_components[0],
                adjusted_old_drop=swap_components[1],
                ramp=swap_ramp,
            )
        if round_offset == 0 and forced_first_frame is not None:
            frame_index = int(forced_first_frame)
        else:
            frame_index = _draw_category(
                probabilities, float(choice_uniforms[round_offset])
            )
        success_probability = _target_success_probability(
            frame_index,
            int(active_targets[round_offset]),
            random_target=random_target,
        )
        success = int(
            float(outcome_uniforms[round_offset]) < success_probability
        )
        frames.append(STRATEGIES[frame_index])
        outcomes.append(success)
        if record_trace:
            posterior_trace.append([float(value) for value in posterior])
        if visible_history:
            alpha[frame_index] += success
            beta[frame_index] += 1 - success
    result: Dict[str, Any] = {
        "frames": frames,
        "target_outcomes": outcomes,
    }
    if record_trace:
        result["posterior_means_before_round"] = posterior_trace
        result["posterior_alpha_final"] = [float(value) for value in alpha]
        result["posterior_beta_final"] = [float(value) for value in beta]
    return result


def simulate_v6_feedback_path(
    *,
    target: str,
    prior_ess: float = 6.0,
    choice_uniforms: Optional[Sequence[float]] = None,
    outcome_uniforms: Optional[Sequence[float]] = None,
    visible_history: bool = True,
    seed: int = 1,
) -> Dict[str, Any]:
    """Small deterministic probe of the production sequential feedback core."""
    if target not in STRATEGIES:
        raise ValueError("target must be a registered frame")
    rng = _pcg64dxsm([V6_POWER_SEED, seed, 0xF33DBACC])
    target_index = STRATEGIES.index(target)
    return _simulate_trajectory(
        base_logits=np.log(np.full(3, 1.0 / 3.0)),
        round_effects=np.zeros((24, 3), dtype=float),
        pair_effect=np.zeros(3, dtype=float),
        active_targets=[target_index] * 24,
        prior_ess=prior_ess,
        rng=rng,
        visible_history=visible_history,
        choice_uniforms=choice_uniforms,
        outcome_uniforms=outcome_uniforms,
        record_trace=True,
    )


def _round_schedule_effects(
    rng: np.random.Generator,
    *,
    serial_rho: float = 0.55,
    serial_sd: float = 0.12,
) -> np.ndarray:
    scenario_effects = rng.normal(0.0, 0.10, size=(12, 3))
    triad_effects = rng.normal(0.0, 0.08, size=(10, 3))
    candidate_slot_preferences = rng.normal(0.0, 0.10, size=3)
    all_permutations = tuple(permutations(range(3)))
    serial = np.zeros((24, 3), dtype=float)
    innovations = rng.normal(0.0, serial_sd, size=(24, 3))
    for round_offset in range(24):
        if round_offset == 0:
            serial[round_offset] = innovations[round_offset]
        else:
            serial[round_offset] = (
                serial_rho * serial[round_offset - 1]
                + math.sqrt(max(0.0, 1.0 - serial_rho**2))
                * innovations[round_offset]
            )
    effects = np.zeros((24, 3), dtype=float)
    for round_offset in range(24):
        scenario_index = round_offset % 12
        triad_index = (
            round_offset % 6
            if round_offset < 18
            else 6 + ((round_offset - 18) % 4)
        )
        frame_order = all_permutations[round_offset % 6]
        slot_effect = np.zeros(3, dtype=float)
        for slot_index, frame_index in enumerate(frame_order):
            slot_effect[frame_index] = candidate_slot_preferences[slot_index]
        effects[round_offset] = (
            scenario_effects[scenario_index]
            + triad_effects[triad_index]
            + slot_effect
            + serial[round_offset]
        )
        effects[round_offset] -= float(np.mean(effects[round_offset]))
    return effects


def _planning_scenario(value: Optional[Any]) -> Dict[str, Any]:
    if value is None:
        return deepcopy(V6_PLANNING_SCENARIOS[1])
    if isinstance(value, int):
        if not 0 <= value < len(V6_PLANNING_SCENARIOS):
            raise ValueError("planning scenario index is out of range")
        return deepcopy(V6_PLANNING_SCENARIOS[value])
    if isinstance(value, str):
        for scenario in V6_PLANNING_SCENARIOS:
            if scenario["scenario_id"] == value:
                return deepcopy(scenario)
        raise ValueError("unknown V6 planning scenario")
    if isinstance(value, Mapping):
        clean = dict(value)
        required = set(V6_PLANNING_SCENARIOS[0])
        if set(clean) != required:
            raise ValueError("planning scenario has an invalid schema")
        return clean
    raise TypeError(
        "planning_scenario must be an index, id, mapping, or None"
    )


def _trajectory_copy_with_frames(
    frames: Sequence[str], outcomes: Sequence[int]
) -> Dict[str, Any]:
    return {
        "frames": list(frames),
        "target_outcomes": [int(value) for value in outcomes],
    }


def _initialize_v6_bundle_random_paths(
    *,
    assignment: Mapping[str, Any],
    base_logits: np.ndarray,
    scenario: Mapping[str, Any],
    seed: int,
    study_index: int,
    null_settings: Mapping[str, Any],
) -> Dict[str, Any]:
    """Create the shared bundle state and both physical-slot null paths.

    Both the complete power simulator and the dominance short-circuit call
    this exact helper. Keeping RNG consumption here prevents a cheaper balance
    calculation from silently reverting to an IID or otherwise different DGP.
    """
    bundle_index = int(assignment["bundle_index"])
    rng = _pcg64dxsm([seed, study_index, bundle_index, 0xB00D1E])
    round_effects = _round_schedule_effects(
        rng,
        serial_rho=float(null_settings.get("serial_rho", 0.55)),
        serial_sd=float(null_settings.get("serial_logit_sd", 0.12)),
    )
    seed_effect = rng.normal(
        0.0, float(scenario["seed_probability_sd"]), size=3
    )
    seed_effect -= float(np.mean(seed_effect))
    slot_effects = rng.normal(0.0, 0.04, size=(2, 3))
    slot_null_offsets = null_settings.get(
        "slot_logit_offsets",
        ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
    )
    for slot_index in range(2):
        slot_effects[slot_index] += np.asarray(
            slot_null_offsets[slot_index], dtype=float
        )
        slot_effects[slot_index] -= float(
            np.mean(slot_effects[slot_index])
        )

    no_slot_paths: list[Dict[str, Any]] = []
    for slot_index in range(2):
        choice_uniforms = rng.random(V6_ROUNDS_PER_EPISODE)
        no_slot_paths.append(
            _simulate_trajectory(
                base_logits=(
                    base_logits + seed_effect + slot_effects[slot_index]
                ),
                round_effects=round_effects,
                pair_effect=np.zeros(3),
                active_targets=[0] * V6_ROUNDS_PER_EPISODE,
                prior_ess=float(scenario["prior_ess"]),
                rng=rng,
                visible_history=False,
                choice_uniforms=choice_uniforms,
            )
        )
    return {
        "rng": rng,
        "round_effects": round_effects,
        "seed_effect": seed_effect,
        "slot_effects": slot_effects,
        "no_slot_paths": no_slot_paths,
    }


def simulate_v6_no_history_balance_study(
    n_episode_seeds: int,
    *,
    baseline_frame_shares: Mapping[str, float],
    planning_scenario: Any,
    seed: int = V6_POWER_SEED,
    study_index: int = 0,
) -> Dict[str, Any]:
    """Evaluate the balance gate using the registered heterogeneous path DGP."""
    _assert_v6_power_contract()
    if type(n_episode_seeds) is not int or n_episode_seeds < 1:
        raise ValueError("n_episode_seeds must be positive")
    shares = _clean_accepted_frame_shares(baseline_frame_shares)
    scenario = _planning_scenario(planning_scenario)
    assignments = reconstruct_v6_bundle_assignments(
        n_episode_seeds, study_index=study_index
    )
    base_logits = np.log(
        np.array([shares[frame] for frame in STRATEGIES], dtype=float)
    )
    observed_frames: list[str] = []
    for assignment in assignments:
        state = _initialize_v6_bundle_random_paths(
            assignment=assignment,
            base_logits=base_logits,
            scenario=scenario,
            seed=seed,
            study_index=study_index,
            null_settings={},
        )
        no_slot = 1 - int(assignment["stable_full_slot"])
        observed_frames.extend(state["no_slot_paths"][no_slot]["frames"])
    counts = tuple(observed_frames.count(frame) for frame in STRATEGIES)
    return {
        "n_episode_seeds": n_episode_seeds,
        "study_index": study_index,
        "simulation_seed": seed,
        "planning_scenario_id": scenario["scenario_id"],
        "baseline_frame_shares": shares,
        "counts": dict(zip(STRATEGIES, counts)),
        "sample_size": len(observed_frames),
        "pass": _passes_v6_realized_no_history_balance_gate(
            counts, sample_size=len(observed_frames)
        ),
    }


def simulate_v6_bundle_study(
    n_episode_seeds: int,
    *,
    baseline_frame_shares: Optional[Mapping[str, float]] = None,
    planning_scenario: Optional[Any] = None,
    seed: int = V6_POWER_SEED,
    study_index: int = 0,
    null_profile: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate a complete prospective V6 study, round by round."""
    _assert_v6_power_contract()
    if type(n_episode_seeds) is not int or n_episode_seeds < 1:
        raise ValueError("n_episode_seeds must be positive")
    shares = _clean_accepted_frame_shares(
        baseline_frame_shares
        if baseline_frame_shares is not None
        else {frame: 1.0 / 3.0 for frame in STRATEGIES}
    )
    scenario = _planning_scenario(planning_scenario)
    assignments = reconstruct_v6_bundle_assignments(
        n_episode_seeds, study_index=study_index
    )
    base_logits = np.log(
        np.array([shares[frame] for frame in STRATEGIES], dtype=float)
    )
    null_mode = null_profile is not None
    null_settings = dict(null_profile or {})
    bundles: list[Dict[str, Any]] = []
    transition_pairs = [
        (old_index, new_index)
        for old_index in range(3)
        for new_index in range(3)
        if old_index != new_index
    ]
    for assignment in assignments:
        bundle_index = assignment["bundle_index"]
        state = _initialize_v6_bundle_random_paths(
            assignment=assignment,
            base_logits=base_logits,
            scenario=scenario,
            seed=seed,
            study_index=study_index,
            null_settings=null_settings,
        )
        rng = state["rng"]
        round_effects = state["round_effects"]
        seed_effect = state["seed_effect"]
        slot_effects = state["slot_effects"]
        no_slot_paths = state["no_slot_paths"]
        full_slot = assignment["stable_full_slot"]
        no_slot = 1 - full_slot
        full_slot_round_one = STRATEGIES.index(
            no_slot_paths[full_slot]["frames"][0]
        )
        stable_slots: list[Dict[str, Any]] = []
        for slot_index in range(2):
            condition = (
                "full_history"
                if slot_index == full_slot
                else "no_history"
            )
            target_trajectories: Dict[str, Any] = {}
            for target_index, target in enumerate(STRATEGIES):
                if condition == "no_history":
                    path = no_slot_paths[slot_index]
                    outcomes = [
                        int(
                            float(rng.random())
                            < _target_success_probability(
                                STRATEGIES.index(frame),
                                target_index,
                                random_target=False,
                            )
                        )
                        for frame in path["frames"]
                    ]
                    target_trajectories[target] = (
                        _trajectory_copy_with_frames(path["frames"], outcomes)
                    )
                elif null_mode:
                    path = no_slot_paths[slot_index]
                    target_trajectories[target] = (
                        _trajectory_copy_with_frames(
                            path["frames"], path["target_outcomes"]
                        )
                    )
                else:
                    pair_effect = rng.normal(0.0, 0.06, size=3)
                    pair_effect -= float(np.mean(pair_effect))
                    target_trajectories[target] = _simulate_trajectory(
                        base_logits=(
                            base_logits
                            + seed_effect
                            + slot_effects[slot_index]
                        ),
                        round_effects=round_effects,
                        pair_effect=pair_effect,
                        active_targets=[target_index] * 24,
                        prior_ess=float(scenario["prior_ess"]),
                        rng=rng,
                        visible_history=True,
                        stable_target_increment=float(
                            scenario["stable_probability_tilt"]
                        ),
                        forced_first_frame=full_slot_round_one,
                    )
            stable_slots.append(
                {
                    "slot": slot_index,
                    "condition": condition,
                    "target_trajectories": target_trajectories,
                }
            )

        swap_slot = assignment["swap_slot"]
        transition_slots: list[Dict[str, Any]] = []
        for slot_index in range(2):
            condition = (
                "silent_swap"
                if slot_index == swap_slot
                else "stable_old"
            )
            transitions: Dict[str, Any] = {}
            for transition_index, (old_index, new_index) in enumerate(
                transition_pairs
            ):
                transition_name = "%s->%s" % (
                    STRATEGIES[old_index], STRATEGIES[new_index]
                )
                transition_effect = rng.normal(
                    0.0,
                    float(scenario["transition_probability_sd"]),
                    size=3,
                )
                transition_effect -= float(np.mean(transition_effect))
                pair_effect = (
                    rng.normal(0.0, 0.06, size=3) + transition_effect
                )
                pair_effect -= float(np.mean(pair_effect))
                if null_mode:
                    path_rng = _pcg64dxsm(
                        [
                            seed,
                            study_index,
                            bundle_index,
                            transition_index,
                            slot_index,
                            0xA11,
                        ]
                    )
                    path = _simulate_trajectory(
                        base_logits=(
                            base_logits
                            + seed_effect
                            + slot_effects[slot_index]
                        ),
                        round_effects=round_effects,
                        pair_effect=pair_effect,
                        active_targets=[old_index] * 24,
                        prior_ess=float(scenario["prior_ess"]),
                        rng=path_rng,
                        visible_history=False,
                    )
                else:
                    active_targets = (
                        [old_index] * 12 + [new_index] * 12
                        if condition == "silent_swap"
                        else [old_index] * 24
                    )
                    path = _simulate_trajectory(
                        base_logits=(
                            base_logits
                            + seed_effect
                            + slot_effects[slot_index]
                        ),
                        round_effects=round_effects,
                        pair_effect=pair_effect,
                        active_targets=active_targets,
                        prior_ess=float(scenario["prior_ess"]),
                        rng=rng,
                        visible_history=True,
                        swap_components=(
                            (
                                float(
                                    scenario["new_probability_tilt"]
                                ),
                                float(
                                    scenario["old_probability_tilt"]
                                ),
                            )
                            if condition == "silent_swap"
                            else None
                        ),
                        old_index=old_index,
                        new_index=new_index,
                    )
                transitions[transition_name] = path
            transition_slots.append(
                {
                    "slot": slot_index,
                    "condition": condition,
                    "transitions": transitions,
                }
            )

        random_controls: Dict[str, Any] = {}
        for target_index, target in enumerate(STRATEGIES):
            random_controls[target] = _simulate_trajectory(
                base_logits=base_logits + seed_effect,
                round_effects=round_effects,
                pair_effect=np.zeros(3),
                active_targets=[target_index] * 24,
                prior_ess=float(scenario["prior_ess"]),
                rng=rng,
                visible_history=True,
                random_target=True,
                forced_first_frame=full_slot_round_one,
            )
        bundles.append(
            {
                "bundle_index": bundle_index,
                "stable_full_slot": full_slot,
                "swap_slot": swap_slot,
                "stable_slots": stable_slots,
                "transition_slots": transition_slots,
                "random_target_controls": random_controls,
                "selection_valid": True,
                "fallback_used": False,
            }
        )
    return {
        "schema_version": V6_STUDY_SCHEMA_VERSION,
        "study_index": study_index,
        "allocation_rng_root": V6_ALLOCATION_RNG_ROOT,
        "n_episode_seeds": n_episode_seeds,
        "baseline_frame_shares": shares,
        "planning_scenario": scenario,
        "null_profile_id": (
            null_settings.get("profile_id") if null_mode else None
        ),
        "assignments": assignments,
        "bundles": bundles,
    }


def _window_match(
    frames: Sequence[str], target: str, start: int, stop: int
) -> float:
    return sum(frame == target for frame in frames[start:stop]) / float(
        stop - start
    )


def _condition_slot(
    slots: Sequence[Mapping[str, Any]], condition: str
) -> Mapping[str, Any]:
    matches = [slot for slot in slots if slot.get("condition") == condition]
    if len(matches) != 1:
        raise ValueError("expected exactly one %s branch slot" % condition)
    return matches[0]


def analyze_v6_bundle_study(study: Mapping[str, Any]) -> Dict[str, Any]:
    """Compute the frozen V6 estimands, exact tests, and complete gate.

    Both real-data adapters and every Monte Carlo replicate should call this
    function. It reconstructs allocation from the registered root instead of
    trusting condition labels supplied by a caller.
    """
    _assert_v6_power_contract()
    if (
        not isinstance(study, Mapping)
        or study.get("schema_version") != V6_STUDY_SCHEMA_VERSION
    ):
        raise ValueError("invalid V6 bundle-study schema")
    n_bundles = study.get("n_episode_seeds")
    study_index = study.get("study_index")
    if type(n_bundles) is not int or type(study_index) is not int:
        raise ValueError(
            "study bundle count and study index must be integers"
        )
    if study.get("allocation_rng_root") != V6_ALLOCATION_RNG_ROOT:
        raise ValueError("V6 allocation RNG root drifted")
    expected_assignments = reconstruct_v6_bundle_assignments(
        n_bundles, study_index=study_index
    )
    if study.get("assignments") != expected_assignments:
        raise ValueError("V6 bundle assignment reconstruction failed")
    bundles = study.get("bundles")
    if not isinstance(bundles, list) or len(bundles) != n_bundles:
        raise ValueError("V6 study has an incomplete bundle list")

    stable_bundle_contrasts: list[float] = []
    new_bundle_contrasts: list[float] = []
    old_bundle_contrasts: list[float] = []
    revision_bundle_contrasts: list[float] = []
    late_swap_crossovers: list[float] = []
    full_late_values: list[float] = []
    full_minus_no_late_by_target: Dict[str, list[float]] = {
        target: [] for target in STRATEGIES
    }
    no_history_gains: list[float] = []
    random_gains: list[float] = []
    no_history_unique_frames: list[str] = []
    transition_revisions: Dict[str, list[float]] = {
        name: []
        for name in V6_PROSPECTIVE_POWER_CONTRACT["design"][
            "ordered_transitions"
        ]
    }
    valid = True
    fallback = False

    for expected, bundle in zip(expected_assignments, bundles):
        if bundle.get("bundle_index") != expected["bundle_index"]:
            raise ValueError("V6 bundle order drifted")
        if bundle.get("stable_full_slot") != expected["stable_full_slot"]:
            raise ValueError("V6 stable assignment bit drifted")
        if bundle.get("swap_slot") != expected["swap_slot"]:
            raise ValueError("V6 swap assignment bit drifted")
        stable_slots = bundle.get("stable_slots")
        transition_slots = bundle.get("transition_slots")
        if not isinstance(stable_slots, list) or not isinstance(
            transition_slots, list
        ):
            raise ValueError("V6 bundle branch slots are missing")
        if (
            len(stable_slots) != 2
            or {slot.get("slot") for slot in stable_slots} != {0, 1}
            or len(transition_slots) != 2
            or {slot.get("slot") for slot in transition_slots} != {0, 1}
        ):
            raise ValueError("V6 branch slots must be exactly {0,1}")
        full = _condition_slot(stable_slots, "full_history")
        no = _condition_slot(stable_slots, "no_history")
        if full.get("slot") != expected["stable_full_slot"]:
            raise ValueError(
                "full-history condition is in the wrong branch slot"
            )
        if no.get("slot") != 1 - expected["stable_full_slot"]:
            raise ValueError("no-history condition is in the wrong branch slot")
        no_target_frames: Optional[list[str]] = None
        target_contrasts: list[float] = []
        for target in STRATEGIES:
            full_path = full["target_trajectories"][target]
            no_path = no["target_trajectories"][target]
            full_frames = list(full_path["frames"])
            no_frames = list(no_path["frames"])
            if len(full_frames) != 24 or len(no_frames) != 24:
                raise ValueError(
                    "every stable branch must contain 24 rounds"
                )
            if any(
                frame not in STRATEGIES
                for frame in full_frames + no_frames
            ):
                raise ValueError(
                    "stable branch contains an unregistered frame"
                )
            if no_target_frames is None:
                no_target_frames = no_frames
            elif no_frames != no_target_frames:
                raise ValueError(
                    "no-history frame path differs across hidden targets"
                )
            full_early = _window_match(full_frames, target, 0, 6)
            full_late = _window_match(full_frames, target, 18, 24)
            no_early = _window_match(no_frames, target, 0, 6)
            no_late = _window_match(no_frames, target, 18, 24)
            target_contrasts.append(
                (full_late - full_early) - (no_late - no_early)
            )
            full_late_values.append(full_late)
            full_minus_no_late_by_target[target].append(
                full_late - no_late
            )
            no_history_gains.append(no_late - no_early)
        assert no_target_frames is not None
        no_history_unique_frames.extend(no_target_frames)
        stable_bundle_contrasts.append(float(np.mean(target_contrasts)))

        swap = _condition_slot(transition_slots, "silent_swap")
        stable_old = _condition_slot(transition_slots, "stable_old")
        if swap.get("slot") != expected["swap_slot"]:
            raise ValueError(
                "silent-swap condition is in the wrong branch slot"
            )
        if stable_old.get("slot") != 1 - expected["swap_slot"]:
            raise ValueError("stable-old condition is in the wrong branch slot")
        bundle_new: list[float] = []
        bundle_old: list[float] = []
        bundle_revision: list[float] = []
        bundle_crossover: list[float] = []
        for transition_name in transition_revisions:
            old, new = transition_name.split("->")
            swap_frames = list(
                swap["transitions"][transition_name]["frames"]
            )
            stable_frames = list(
                stable_old["transitions"][transition_name]["frames"]
            )
            if len(swap_frames) != 24 or len(stable_frames) != 24:
                raise ValueError(
                    "every transition branch must contain 24 rounds"
                )
            if any(
                frame not in STRATEGIES
                for frame in swap_frames + stable_frames
            ):
                raise ValueError(
                    "transition branch contains an unregistered frame"
                )
            swap_new_gain = _window_match(
                swap_frames, new, 18, 24
            ) - _window_match(swap_frames, new, 6, 12)
            stable_new_gain = _window_match(
                stable_frames, new, 18, 24
            ) - _window_match(stable_frames, new, 6, 12)
            swap_old_drop = _window_match(
                swap_frames, old, 6, 12
            ) - _window_match(swap_frames, old, 18, 24)
            stable_old_drop = _window_match(
                stable_frames, old, 6, 12
            ) - _window_match(stable_frames, old, 18, 24)
            adjusted_new = swap_new_gain - stable_new_gain
            adjusted_old = swap_old_drop - stable_old_drop
            revision = adjusted_new + adjusted_old
            crossover = _window_match(
                swap_frames, new, 18, 24
            ) - _window_match(swap_frames, old, 18, 24)
            bundle_new.append(adjusted_new)
            bundle_old.append(adjusted_old)
            bundle_revision.append(revision)
            bundle_crossover.append(crossover)
            transition_revisions[transition_name].append(revision)
        new_bundle_contrasts.append(float(np.mean(bundle_new)))
        old_bundle_contrasts.append(float(np.mean(bundle_old)))
        revision_bundle_contrasts.append(float(np.mean(bundle_revision)))
        late_swap_crossovers.append(float(np.mean(bundle_crossover)))

        controls = bundle.get("random_target_controls", {})
        for target in STRATEGIES:
            frames = list(controls[target]["frames"])
            if len(frames) != 24:
                raise ValueError(
                    "random-target control must contain 24 rounds"
                )
            random_gains.append(
                _window_match(frames, target, 18, 24)
                - _window_match(frames, target, 0, 6)
            )
        valid = valid and bundle.get("selection_valid") is True
        fallback = fallback or bundle.get("fallback_used") is True

    stable_test = exact_one_sided_bundle_randomization_test(
        stable_bundle_contrasts, integer_scale=18
    )
    revision_test = exact_one_sided_bundle_randomization_test(
        revision_bundle_contrasts, integer_scale=36
    )
    stable_estimate = float(np.mean(stable_bundle_contrasts))
    adjusted_new_estimate = float(np.mean(new_bundle_contrasts))
    adjusted_old_estimate = float(np.mean(old_bundle_contrasts))
    revision_estimate = float(np.mean(revision_bundle_contrasts))
    crossover_estimate = float(np.mean(late_swap_crossovers))
    frame_counts = tuple(
        no_history_unique_frames.count(frame) for frame in STRATEGIES
    )
    balance_pass = _passes_v6_realized_no_history_balance_gate(
        frame_counts, sample_size=len(no_history_unique_frames)
    )
    target_advantages = {
        target: float(np.mean(values))
        for target, values in full_minus_no_late_by_target.items()
    }
    transition_means = {
        transition: float(np.mean(values))
        for transition, values in transition_revisions.items()
    }
    supporting_transitions = [
        transition
        for transition, value in transition_means.items()
        if value
        >= float(
            CONTROLLED_V6_GATE_THRESHOLDS[
                "minimum_transition_revision_shift"
            ]
        )
    ]
    supporting_origins = sorted(
        {name.split("->")[0] for name in supporting_transitions}
    )
    overall_late_advantages = [
        value
        for values in full_minus_no_late_by_target.values()
        for value in values
    ]
    effect_gates = {
        "design_integrity": True,
        "all_selections_valid": valid,
        "zero_fallback": not fallback,
        "no_history_frame_balance": balance_pass,
        "no_history_learning_control": abs(
            float(np.mean(no_history_gains))
        )
        <= float(
            CONTROLLED_V6_GATE_THRESHOLDS[
                "maximum_absolute_no_history_learning_gain"
            ]
        ),
        "random_target_learning_control": abs(float(np.mean(random_gains)))
        <= float(
            CONTROLLED_V6_GATE_THRESHOLDS[
                "maximum_absolute_random_learning_gain"
            ]
        ),
        "full_history_late_level": float(np.mean(full_late_values))
        >= float(
            CONTROLLED_V6_GATE_THRESHOLDS[
                "minimum_full_history_late_match"
            ]
        ),
        "full_over_no_late": float(np.mean(overall_late_advantages))
        >= float(
            CONTROLLED_V6_GATE_THRESHOLDS[
                "minimum_full_over_no_late_match"
            ]
        ),
        "all_target_types_supported": all(
            value
            >= float(
                CONTROLLED_V6_GATE_THRESHOLDS[
                    "minimum_per_type_late_advantage"
                ]
            )
            for value in target_advantages.values()
        ),
        "stable": stable_estimate
        >= V6_EXPECTED_OBSERVED_STABLE_DID_GATE,
        "revision": revision_estimate >= V6_EXPECTED_OBSERVED_REVISION_GATE,
        "adjusted_new_gain": adjusted_new_estimate
        >= V6_EXPECTED_ADJUSTED_NEW_GAIN_GATE,
        "adjusted_old_drop": adjusted_old_estimate
        >= V6_EXPECTED_ADJUSTED_OLD_DROP_GATE,
        "late_swap_new_minus_old": crossover_estimate
        >= V6_EXPECTED_LATE_SWAP_NEW_MINUS_OLD_GATE,
        "directional_transition_support": len(supporting_transitions)
        >= int(
            CONTROLLED_V6_GATE_THRESHOLDS[
                "minimum_supporting_transitions"
            ]
        ),
        "all_origin_types_support_revision": len(supporting_origins)
        >= int(
            CONTROLLED_V6_GATE_THRESHOLDS[
                "minimum_supporting_origin_types"
            ]
        ),
    }
    inference_gates = {
        "stable_exact_one_sided": stable_test["p_value_one_sided"]
        <= V6_ALPHA_EACH,
        "revision_exact_one_sided": revision_test["p_value_one_sided"]
        <= V6_ALPHA_EACH,
    }
    return {
        "schema_version": V6_POWER_PAYLOAD_SCHEMA_VERSION,
        "n_bundles": n_bundles,
        "stable_bundle_contrasts": stable_bundle_contrasts,
        "adjusted_new_gain_bundle_contrasts": new_bundle_contrasts,
        "adjusted_old_drop_bundle_contrasts": old_bundle_contrasts,
        "revision_bundle_contrasts": revision_bundle_contrasts,
        "stable": stable_estimate,
        "adjusted_new_gain": adjusted_new_estimate,
        "adjusted_old_drop": adjusted_old_estimate,
        "revision": revision_estimate,
        "late_swap_new_minus_old": crossover_estimate,
        "stable_test": stable_test,
        "revision_test": revision_test,
        "no_history_frame_counts": dict(zip(STRATEGIES, frame_counts)),
        "no_history_unique_prompt_count": len(no_history_unique_frames),
        "no_history_learning_gain": float(np.mean(no_history_gains)),
        "random_target_learning_gain": float(np.mean(random_gains)),
        "full_history_late_match": float(np.mean(full_late_values)),
        "late_advantage_by_target": target_advantages,
        "transition_revision": transition_means,
        "supporting_transitions": supporting_transitions,
        "supporting_origins": supporting_origins,
        "effect_gates": effect_gates,
        "inference_gates": inference_gates,
        "complete_gate": all(effect_gates.values())
        and all(inference_gates.values()),
    }


def _power_result(
    successes: int, n_sim: int, *, mean: Optional[float] = None
) -> Dict[str, Any]:
    lo, hi = wilson_ci(successes, n_sim)
    result: Dict[str, Any] = {
        "successes": int(successes),
        "trials": int(n_sim),
        "power": successes / float(n_sim),
        "mc_ci_lo": float(lo),
        "mc_ci_hi": float(hi),
    }
    if mean is not None:
        result["mean_estimated_effect"] = float(mean)
    return result


def simulate_v6_path_balance_cell(
    n_episode_seeds: int,
    *,
    n_sim: int,
    baseline_frame_shares: Mapping[str, float],
    planning_scenario: Any,
    seed: int = V6_POWER_SEED,
    simulation_study_offset: int,
) -> Dict[str, Any]:
    """Simulate only the registered no-history paths for one power cell."""
    if type(n_sim) is not int or n_sim < 1:
        raise ValueError("n_sim must be a positive integer")
    scenario = _planning_scenario(planning_scenario)
    successes = 0
    aggregate_counts = {frame: 0 for frame in STRATEGIES}
    for simulation_index in range(n_sim):
        result = simulate_v6_no_history_balance_study(
            n_episode_seeds,
            baseline_frame_shares=baseline_frame_shares,
            planning_scenario=scenario,
            seed=seed,
            study_index=simulation_study_offset + simulation_index,
        )
        successes += int(result["pass"])
        for frame in STRATEGIES:
            aggregate_counts[frame] += int(result["counts"][frame])
    return {
        "n_episode_seeds": n_episode_seeds,
        "n_sim": n_sim,
        "simulation_seed": seed,
        "simulation_study_offset": simulation_study_offset,
        "planning_scenario_id": scenario["scenario_id"],
        "baseline_frame_shares": {
            frame: float(baseline_frame_shares[frame])
            for frame in STRATEGIES
        },
        "no_history_balance_gate": _power_result(successes, n_sim),
        "aggregate_frame_counts": aggregate_counts,
    }


def _path_balance_cell_worker(task: tuple[Any, ...]) -> Dict[str, Any]:
    n, count, shares, scenario, seed, offset, configuration_id = task
    row = simulate_v6_path_balance_cell(
        n,
        n_sim=count,
        baseline_frame_shares=shares,
        planning_scenario=scenario,
        seed=seed,
        simulation_study_offset=offset,
    )
    row["frame_share_configuration_id"] = configuration_id
    return row


def run_v6_path_balance_dominance_screen(
    *,
    n_sim: int = V6_PATH_BALANCE_SCREEN_SIMULATIONS,
    official: bool = False,
    seed: int = V6_POWER_SEED,
) -> Dict[str, Any]:
    """Apply the registered complete-power short circuit on actual paths.

    This is not an IID approximation. It executes the same heterogeneous
    no-history path constructor, assignments, RNG roots, study offsets, and
    balance gate as the corresponding complete power cells. For each N,
    complete-gate successes are a replicate-wise subset of balance successes,
    so their Wilson lower bound cannot exceed the reported balance bound.
    """
    _assert_v6_power_contract()
    if official and n_sim != V6_PATH_BALANCE_SCREEN_SIMULATIONS:
        raise ValueError("official V6 path screen requires exactly 10,000 simulations")
    if official and seed != V6_POWER_SEED:
        raise ValueError("official V6 path screen seed must be 20262003")
    if type(n_sim) is not int or n_sim < 1:
        raise ValueError("n_sim must be a positive integer")
    configuration = next(
        deepcopy(cell)
        for cell in enumerate_v6_frame_share_nuisance_configurations()
        if cell["configuration_id"]
        == V6_PATH_BALANCE_SCREEN_CONFIGURATION_ID
    )
    tasks: list[tuple[Any, ...]] = []
    for scenario_index, scenario in enumerate(V6_PLANNING_SCENARIOS):
        for n_episode_seeds in V6_EPISODE_SEED_GRID:
            offset = 1 + scenario_index * 1_000_000 + n_episode_seeds * 10_000
            tasks.append(
                (
                    n_episode_seeds,
                    n_sim,
                    configuration["frame_shares"],
                    scenario,
                    seed,
                    offset,
                    configuration["configuration_id"],
                )
            )

    rows = _map_cells(_path_balance_cell_worker, tasks, n_sim)
    decisions: list[Dict[str, Any]] = []
    for n_episode_seeds in V6_EPISODE_SEED_GRID:
        candidates = [
            row for row in rows if row["n_episode_seeds"] == n_episode_seeds
        ]
        blocking = min(
            candidates,
            key=lambda row: row["no_history_balance_gate"]["mc_ci_lo"],
        )
        decisions.append(
            {
                "n_episode_seeds": n_episode_seeds,
                "blocked": (
                    blocking["no_history_balance_gate"]["mc_ci_lo"]
                    < V6_TARGET_LOWER_MC_BOUND
                ),
                "blocking_scenario_id": blocking["planning_scenario_id"],
                "balance_successes": blocking["no_history_balance_gate"][
                    "successes"
                ],
                "balance_wilson_lower": blocking["no_history_balance_gate"][
                    "mc_ci_lo"
                ],
                "target_complete_wilson_lower": V6_TARGET_LOWER_MC_BOUND,
            }
        )
    terminal = all(row["blocked"] for row in decisions)
    payload: Dict[str, Any] = {
        "schema_version": "controlled-v6-path-balance-dominance-v1",
        "contract_sha256": V6_POWER_CONTRACT_SHA256,
        "official": bool(official),
        "status": (
            "STOP_V6_UNDERPOWERED_BEFORE_VALIDATION"
            if terminal
            else "CONTINUE_V6_COMPLETE_POWER_REQUIRED"
        ),
        "terminal": terminal,
        "n_sim_per_cell": n_sim,
        "simulation_seed": seed,
        "screen_configuration": configuration,
        "screen_results": rows,
        "decision_by_n": decisions,
        "logic": V6_PROSPECTIVE_POWER_CONTRACT["power"][
            "path_balance_dominance_screen"
        ]["short_circuit_rule"],
        "scope_note": (
            "This artifact certifies deterministic replay of a prospective "
            "model-free simulation. It does not attest external account, GPU, "
            "credential, judge, or model execution history."
        ),
    }
    payload["certificate_sha256"] = _canonical_sha256(payload)
    return payload


def audit_v6_path_balance_dominance_screen(
    payload: Mapping[str, Any], *, replay: bool = True
) -> Dict[str, Any]:
    """Validate and optionally regenerate a path-balance screen artifact."""
    if not isinstance(payload, Mapping):
        raise V6PowerAuditError("V6 path-balance screen must be a mapping")
    expected_keys = {
        "schema_version",
        "contract_sha256",
        "official",
        "status",
        "terminal",
        "n_sim_per_cell",
        "simulation_seed",
        "screen_configuration",
        "screen_results",
        "decision_by_n",
        "logic",
        "scope_note",
        "certificate_sha256",
    }
    if set(payload) != expected_keys:
        raise V6PowerAuditError("V6 path-balance screen schema drifted")
    if payload.get("contract_sha256") != V6_POWER_CONTRACT_SHA256:
        raise V6PowerAuditError("V6 path-balance screen contract drifted")
    supplied = dict(payload)
    supplied_digest = supplied.pop("certificate_sha256", None)
    if supplied_digest != _canonical_sha256(supplied):
        raise V6PowerAuditError("V6 path-balance screen digest failed")
    if replay:
        expected = run_v6_path_balance_dominance_screen(
            n_sim=int(payload["n_sim_per_cell"]),
            official=bool(payload["official"]),
            seed=int(payload["simulation_seed"]),
        )
        if _canonical_json(dict(payload)) != _canonical_json(expected):
            raise V6PowerAuditError(
                "V6 path-balance screen differs from deterministic replay"
            )
    return {
        "audit_pass": True,
        "status": payload["status"],
        "terminal": payload["terminal"],
        "contract_sha256": payload["contract_sha256"],
        "certificate_sha256": payload["certificate_sha256"],
    }


def simulate_controlled_v6_power(
    n_episode_seeds: int,
    n_sim: int = V6_MINIMUM_SIMULATIONS_PER_CELL,
    baseline_frame_shares: Optional[Mapping[str, float]] = None,
    *,
    planning_scenario: Optional[Any] = None,
    seed: int = V6_POWER_SEED,
    simulation_study_offset: int = 1,
    stable_did_population_alternative: Optional[float] = None,
    revision_shift_population_alternative: Optional[float] = None,
) -> Dict[str, Any]:
    """Estimate power for one N/share/profile cell using complete studies."""
    _assert_v6_power_contract()
    if type(n_sim) is not int or n_sim < 1:
        raise ValueError("n_sim must be a positive integer")
    scenario = _planning_scenario(planning_scenario)
    if stable_did_population_alternative is not None:
        stable_value = float(stable_did_population_alternative)
        current_stable = float(scenario["stable_did_alternative"])
        scenario["stable_probability_tilt"] *= (
            stable_value / current_stable if current_stable else 0.0
        )
        scenario["stable_did_alternative"] = stable_value
    if revision_shift_population_alternative is not None:
        revision = float(revision_shift_population_alternative)
        current = float(scenario["revision_alternative"])
        ratio = revision / current if current else 0.0
        scenario["adjusted_new_gain_alternative"] *= ratio
        scenario["adjusted_old_drop_alternative"] *= ratio
        scenario["new_probability_tilt"] *= ratio
        scenario["old_probability_tilt"] *= ratio
        scenario["revision_alternative"] = revision
    shares = _clean_accepted_frame_shares(
        baseline_frame_shares
        if baseline_frame_shares is not None
        else {frame: 1.0 / 3.0 for frame in STRATEGIES}
    )
    stable_rejections = 0
    revision_rejections = 0
    joint_rejections = 0
    complete = 0
    balance_successes = 0
    stable_sum = 0.0
    revision_sum = 0.0
    new_sum = 0.0
    old_sum = 0.0
    crossover_sum = 0.0
    for simulation_index in range(n_sim):
        study = simulate_v6_bundle_study(
            n_episode_seeds,
            baseline_frame_shares=shares,
            planning_scenario=scenario,
            seed=seed,
            study_index=simulation_study_offset + simulation_index,
        )
        summary = analyze_v6_bundle_study(study)
        stable_hit = summary["inference_gates"][
            "stable_exact_one_sided"
        ]
        revision_hit = summary["inference_gates"][
            "revision_exact_one_sided"
        ]
        stable_rejections += int(stable_hit)
        revision_rejections += int(revision_hit)
        joint_rejections += int(stable_hit and revision_hit)
        complete += int(summary["complete_gate"])
        balance_successes += int(
            summary["effect_gates"]["no_history_frame_balance"]
        )
        stable_sum += summary["stable"]
        revision_sum += summary["revision"]
        new_sum += summary["adjusted_new_gain"]
        old_sum += summary["adjusted_old_drop"]
        crossover_sum += summary["late_swap_new_minus_old"]
    return {
        "schema_version": V6_POWER_PAYLOAD_SCHEMA_VERSION,
        "n_episode_seeds": n_episode_seeds,
        "n_sim": n_sim,
        "simulation_seed": seed,
        "simulation_study_offset": simulation_study_offset,
        "planning_scenario": scenario,
        "baseline_frame_shares": shares,
        "stable_co_primary": _power_result(
            stable_rejections, n_sim, mean=stable_sum / n_sim
        ),
        "revision_co_primary": _power_result(
            revision_rejections, n_sim, mean=revision_sum / n_sim
        ),
        "joint_co_primary": _power_result(joint_rejections, n_sim),
        "complete_behavioral_pattern": _power_result(complete, n_sim),
        "no_history_balance_gate": _power_result(
            balance_successes, n_sim
        ),
        "mean_adjusted_new_gain": new_sum / n_sim,
        "mean_adjusted_old_drop": old_sum / n_sim,
        "mean_late_swap_new_minus_old": crossover_sum / n_sim,
        "aggregate_sufficient_statistics": {
            "stable_rejections": stable_rejections,
            "revision_rejections": revision_rejections,
            "joint_rejections": joint_rejections,
            "complete_gate_successes": complete,
            "balance_gate_successes": balance_successes,
            "stable_estimate_sum": stable_sum,
            "revision_estimate_sum": revision_sum,
            "adjusted_new_gain_sum": new_sum,
            "adjusted_old_drop_sum": old_sum,
            "late_swap_new_minus_old_sum": crossover_sum,
        },
        "assumptions": {
            "independent_unit": "episode-seed bundle",
            "allocation_rng_root": V6_ALLOCATION_RNG_ROOT,
            "allocation_bit_generator": V6_ALLOCATION_BIT_GENERATOR,
            "power_rng_root": seed,
            "complete_round_paths": True,
            "analysis_helper": "analyze_v6_bundle_study",
        },
    }


def simulate_v6_null_size(
    n_episode_seeds: int,
    n_sim: int,
    baseline_frame_shares: Mapping[str, float],
    *,
    seed: int = V6_POWER_SEED + 9_000_000,
    simulation_study_offset: int = 1,
) -> Dict[str, Any]:
    """Evaluate exact-test size under symmetric and adversarial sharp nulls."""
    shares = _clean_accepted_frame_shares(baseline_frame_shares)
    profiles: Dict[str, Any] = {}
    for profile_index, profile in enumerate(V6_NULL_LATENT_PROFILES):
        stable = 0
        revision = 0
        joint = 0
        familywise = 0
        for simulation_index in range(n_sim):
            study_index = (
                simulation_study_offset
                + profile_index * n_sim
                + simulation_index
            )
            study = simulate_v6_bundle_study(
                n_episode_seeds,
                baseline_frame_shares=shares,
                planning_scenario=1,
                seed=seed,
                study_index=study_index,
                null_profile=profile,
            )
            summary = analyze_v6_bundle_study(study)
            stable_hit = summary["inference_gates"][
                "stable_exact_one_sided"
            ]
            revision_hit = summary["inference_gates"][
                "revision_exact_one_sided"
            ]
            stable += int(stable_hit)
            revision += int(revision_hit)
            joint += int(stable_hit and revision_hit)
            familywise += int(stable_hit or revision_hit)
        profiles[profile["profile_id"]] = {
            "stable": _power_result(stable, n_sim),
            "revision": _power_result(revision, n_sim),
            "joint_both": _power_result(joint, n_sim),
            "familywise_any": _power_result(familywise, n_sim),
        }
    return {
        "schema_version": V6_POWER_PAYLOAD_SCHEMA_VERSION,
        "n_episode_seeds": n_episode_seeds,
        "n_sim_per_profile": n_sim,
        "simulation_seed": seed,
        "simulation_study_offset": simulation_study_offset,
        "baseline_frame_shares": shares,
        "profiles": profiles,
    }


def summarize_v6_null_type_i(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    if not rows:
        raise ValueError("null rows cannot be empty")
    limits = {
        "stable": V6_NULL_PER_TEST_UPPER_LIMIT,
        "revision": V6_NULL_PER_TEST_UPPER_LIMIT,
        "joint_both": V6_NULL_JOINT_UPPER_LIMIT,
        "familywise_any": V6_NULL_FAMILYWISE_UPPER_LIMIT,
    }
    worst: Dict[str, Any] = {}
    checks: list[bool] = []
    for metric, limit in limits.items():
        candidates = []
        for row in rows:
            for profile_id, profile_metrics in row["profiles"].items():
                interval = profile_metrics[metric]
                candidates.append(
                    {
                        "configuration_id": row[
                            "frame_share_configuration_id"
                        ],
                        "profile_id": profile_id,
                        "upper_limit": limit,
                        **interval,
                    }
                )
        selected = max(
            candidates,
            key=lambda item: (item["mc_ci_hi"], item["power"]),
        )
        selected["pass"] = selected["mc_ci_hi"] <= limit
        worst[metric] = selected
        checks.append(bool(selected["pass"]))
    return {
        "decision_rule": (
            "upper Wilson bound only; no lower Type-I bound"
        ),
        "metrics": worst,
        "pass": all(checks),
    }


def summarize_v6_worst_case_power(
    rows: Sequence[Mapping[str, Any]],
    *,
    target_lower_mc_bound: float = V6_TARGET_LOWER_MC_BOUND,
    episode_seed_grid: Sequence[int] = V6_EPISODE_SEED_GRID,
) -> Dict[str, Any]:
    by_n: list[Dict[str, Any]] = []
    selected: Optional[int] = None
    for n_episode_seeds in episode_seed_grid:
        candidates = [
            row
            for row in rows
            if row["n_episode_seeds"] == n_episode_seeds
        ]
        if not candidates:
            raise ValueError(
                "power rows are missing N=%d" % n_episode_seeds
            )
        worst_joint = min(
            candidates,
            key=lambda row: row["joint_co_primary"]["mc_ci_lo"],
        )
        worst_complete = min(
            candidates,
            key=lambda row: row["complete_behavioral_pattern"][
                "mc_ci_lo"
            ],
        )
        joint_pass = (
            worst_joint["joint_co_primary"]["mc_ci_lo"]
            >= target_lower_mc_bound
        )
        complete_pass = (
            worst_complete["complete_behavioral_pattern"]["mc_ci_lo"]
            >= target_lower_mc_bound
        )
        row = {
            "n_episode_seeds": int(n_episode_seeds),
            "worst_joint_co_primary": {
                "configuration_id": worst_joint[
                    "frame_share_configuration_id"
                ],
                "scenario_id": worst_joint["planning_scenario"][
                    "scenario_id"
                ],
                **worst_joint["joint_co_primary"],
            },
            "worst_complete_behavioral_pattern": {
                "configuration_id": worst_complete[
                    "frame_share_configuration_id"
                ],
                "scenario_id": worst_complete["planning_scenario"][
                    "scenario_id"
                ],
                **worst_complete["complete_behavioral_pattern"],
            },
            "passes_joint_lower_bound": joint_pass,
            "passes_complete_lower_bound": complete_pass,
            "passes_both_lower_bounds": joint_pass and complete_pass,
        }
        by_n.append(row)
        if selected is None and row["passes_both_lower_bounds"]:
            selected = int(n_episode_seeds)
    return {
        "target_lower_mc_bound": target_lower_mc_bound,
        "worst_case_by_episode_seed": by_n,
        "selected_episode_seeds": selected,
        "pass": selected is not None,
    }


def _v6_parallel_worker_count(n_sim: int, n_cells: int) -> int:
    if n_sim < _V6_PARALLEL_MIN_SIMULATIONS_PER_CELL:
        return 1
    return max(1, min(int(os.cpu_count() or 1), int(n_cells)))


def _effect_cell_worker(task: tuple[Any, ...]) -> Dict[str, Any]:
    n, n_sim, shares, scenario, seed, offset, configuration_id = task
    row = simulate_controlled_v6_power(
        n,
        n_sim=n_sim,
        baseline_frame_shares=shares,
        planning_scenario=scenario,
        seed=seed,
        simulation_study_offset=offset,
    )
    row["frame_share_configuration_id"] = configuration_id
    return row


def _null_cell_worker(task: tuple[Any, ...]) -> Dict[str, Any]:
    n, n_sim, shares, seed, offset, configuration_id = task
    row = simulate_v6_null_size(
        n,
        n_sim,
        shares,
        seed=seed,
        simulation_study_offset=offset,
    )
    row["frame_share_configuration_id"] = configuration_id
    return row


def _map_cells(
    function: Any, tasks: Sequence[tuple[Any, ...]], n_sim: int
) -> list[Any]:
    workers = _v6_parallel_worker_count(n_sim, len(tasks))
    context = (
        ProcessPoolExecutor(max_workers=workers)
        if workers > 1
        else nullcontext(None)
    )
    with context as executor:
        if executor is None:
            return [function(task) for task in tasks]
        return list(executor.map(function, tasks, chunksize=1))


def run_v6_worst_case_power(
    *,
    n_sim: int = V6_MINIMUM_SIMULATIONS_PER_CELL,
    official: bool = False,
    seed: int = V6_POWER_SEED,
    episode_seed_grid: Sequence[int] = V6_EPISODE_SEED_GRID,
) -> Dict[str, Any]:
    """Run the frozen 156 effect cells and 13 null cells."""
    _assert_v6_power_contract()
    grid = tuple(int(value) for value in episode_seed_grid)
    if official and n_sim < V6_MINIMUM_SIMULATIONS_PER_CELL:
        raise ValueError(
            "official V6 power requires at least 10,000 simulations per cell"
        )
    if official and seed != V6_POWER_SEED:
        raise ValueError("official V6 power seed must be 20262003")
    if official and grid != V6_EPISODE_SEED_GRID:
        raise ValueError("official V6 N grid must be [12,18,24,30]")
    if n_sim < 1:
        raise ValueError("n_sim must be positive")
    configurations = enumerate_v6_frame_share_nuisance_configurations()
    effect_tasks: list[tuple[Any, ...]] = []
    for scenario_index, scenario in enumerate(V6_PLANNING_SCENARIOS):
        for n in grid:
            for configuration in configurations:
                offset = 1 + scenario_index * 1_000_000 + int(n) * 10_000
                effect_tasks.append(
                    (
                        int(n),
                        n_sim,
                        configuration["frame_shares"],
                        scenario,
                        seed,
                        offset,
                        configuration["configuration_id"],
                    )
                )
    effect_rows = _map_cells(_effect_cell_worker, effect_tasks, n_sim)
    power_summary = summarize_v6_worst_case_power(
        effect_rows, episode_seed_grid=grid
    )
    null_n = power_summary["selected_episode_seeds"] or max(grid)
    null_tasks = [
        (
            int(null_n),
            n_sim,
            configuration["frame_shares"],
            seed + 9_000_000,
            10_000_000,
            configuration["configuration_id"],
        )
        for configuration in configurations
    ]
    null_rows = _map_cells(_null_cell_worker, null_tasks, n_sim)
    null_summary = summarize_v6_null_type_i(null_rows)
    scientific_pass = bool(power_summary["pass"] and null_summary["pass"])
    status = (
        "PASS_V6_PROSPECTIVE_BUNDLE_POWER"
        if scientific_pass
        else (
            "STOP_V6_UNDERPOWERED_BEFORE_VALIDATION"
            if not power_summary["pass"]
            else "STOP_V6_NULL_SIZE_UPPER_BOUND_FAILED"
        )
    )
    return {
        "schema_version": V6_POWER_PAYLOAD_SCHEMA_VERSION,
        "contract": deepcopy(V6_PROSPECTIVE_POWER_CONTRACT),
        "contract_sha256": V6_POWER_CONTRACT_SHA256,
        "official": bool(official),
        "status": status,
        "focal_model_outcomes_used": False,
        "confirmatory_outcomes_used": False,
        "selected_bank_validation_outputs_used": False,
        "input_policy": V6_POWER_INPUT_POLICY,
        "n_sim_per_cell": n_sim,
        "simulation_seed": seed,
        "episode_seed_grid": list(grid),
        "frame_share_nuisance_configurations": configurations,
        "planning_scenarios": [
            deepcopy(value) for value in V6_PLANNING_SCENARIOS
        ],
        "effect_results": effect_rows,
        "power_summary": power_summary,
        "null_results": null_rows,
        "null_type_i_check": null_summary,
        "selected_episode_seeds": power_summary[
            "selected_episode_seeds"
        ],
        "power_selection_pass": bool(power_summary["pass"]),
        "null_type_i_pass": bool(null_summary["pass"]),
        "pass": scientific_pass,
        "selection_rule": V6_POWER_SELECTION_RULE,
        "finite_grid_coverage_note": FINITE_NUISANCE_GRID_COVERAGE_NOTE,
    }


def _assert_equal(actual: Any, expected: Any, path: str) -> None:
    if _canonical_json(actual) != _canonical_json(expected):
        raise V6PowerAuditError(
            "%s differs from deterministic reconstruction" % path
        )


def audit_v6_power_payload(
    payload: Mapping[str, Any],
    *,
    require_official: bool = True,
    replay: bool = True,
) -> Dict[str, Any]:
    """Fail-closed contract, summary, and deterministic cell replay audit."""
    _assert_v6_power_contract()
    if not isinstance(payload, Mapping):
        raise V6PowerAuditError("V6 power payload must be a mapping")
    expected_top_keys = {
        "schema_version",
        "contract",
        "contract_sha256",
        "official",
        "status",
        "focal_model_outcomes_used",
        "confirmatory_outcomes_used",
        "selected_bank_validation_outputs_used",
        "input_policy",
        "n_sim_per_cell",
        "simulation_seed",
        "episode_seed_grid",
        "frame_share_nuisance_configurations",
        "planning_scenarios",
        "effect_results",
        "power_summary",
        "null_results",
        "null_type_i_check",
        "selected_episode_seeds",
        "power_selection_pass",
        "null_type_i_pass",
        "pass",
        "selection_rule",
        "finite_grid_coverage_note",
    }
    if set(payload) != expected_top_keys:
        raise V6PowerAuditError("V6 power payload top-level schema drifted")
    if payload.get("schema_version") != V6_POWER_PAYLOAD_SCHEMA_VERSION:
        raise V6PowerAuditError(
            "V6 power payload schema version drifted"
        )
    if require_official and payload.get("official") is not True:
        raise V6PowerAuditError("an official V6 power payload is required")
    _assert_equal(
        payload.get("contract"),
        V6_PROSPECTIVE_POWER_CONTRACT,
        "payload.contract",
    )
    if payload.get("contract_sha256") != V6_POWER_CONTRACT_SHA256:
        raise V6PowerAuditError("payload.contract_sha256 drifted")
    _assert_equal(
        payload.get("input_policy"), V6_POWER_INPUT_POLICY, "payload.input_policy"
    )
    _assert_equal(
        payload.get("selection_rule"),
        V6_POWER_SELECTION_RULE,
        "payload.selection_rule",
    )
    _assert_equal(
        payload.get("finite_grid_coverage_note"),
        FINITE_NUISANCE_GRID_COVERAGE_NOTE,
        "payload.finite_grid_coverage_note",
    )
    _assert_equal(
        payload.get("frame_share_nuisance_configurations"),
        enumerate_v6_frame_share_nuisance_configurations(),
        "payload.frame_share_nuisance_configurations",
    )
    _assert_equal(
        payload.get("planning_scenarios"),
        list(V6_PLANNING_SCENARIOS),
        "payload.planning_scenarios",
    )
    for flag in V6_FORBIDDEN_OUTCOME_FLAGS:
        if payload.get(flag) is not False:
            raise V6PowerAuditError("payload.%s must be false" % flag)
    n_sim = payload.get("n_sim_per_cell")
    seed = payload.get("simulation_seed")
    grid = tuple(payload.get("episode_seed_grid", ()))
    if type(n_sim) is not int or n_sim < 1 or type(seed) is not int:
        raise V6PowerAuditError("invalid simulation count or seed")
    if payload.get("official") is True:
        if n_sim < V6_MINIMUM_SIMULATIONS_PER_CELL:
            raise V6PowerAuditError(
                "official payload has fewer than 10,000 simulations"
            )
        if seed != V6_POWER_SEED or grid != V6_EPISODE_SEED_GRID:
            raise V6PowerAuditError("official seed or N grid drifted")
    effect_rows = payload.get("effect_results", ())
    null_rows = payload.get("null_results", ())
    if not isinstance(effect_rows, list) or len(effect_rows) != (
        len(V6_PLANNING_SCENARIOS) * len(grid) * 13
    ):
        raise V6PowerAuditError("effect simulation grid is incomplete")
    if not isinstance(null_rows, list) or len(null_rows) != 13:
        raise V6PowerAuditError("null simulation grid is incomplete")
    expected_power = summarize_v6_worst_case_power(
        effect_rows, episode_seed_grid=grid
    )
    expected_null = summarize_v6_null_type_i(null_rows)
    _assert_equal(
        payload.get("power_summary"),
        expected_power,
        "payload.power_summary",
    )
    _assert_equal(
        payload.get("null_type_i_check"),
        expected_null,
        "payload.null_type_i_check",
    )
    selected = expected_power["selected_episode_seeds"]
    power_pass = bool(expected_power["pass"])
    null_pass = bool(expected_null["pass"])
    scientific_pass = power_pass and null_pass
    expected_status = (
        "PASS_V6_PROSPECTIVE_BUNDLE_POWER"
        if scientific_pass
        else (
            "STOP_V6_UNDERPOWERED_BEFORE_VALIDATION"
            if not power_pass
            else "STOP_V6_NULL_SIZE_UPPER_BOUND_FAILED"
        )
    )
    _assert_equal(payload.get("status"), expected_status, "payload.status")
    _assert_equal(
        payload.get("selected_episode_seeds"),
        selected,
        "payload.selected_episode_seeds",
    )
    _assert_equal(
        payload.get("power_selection_pass"),
        power_pass,
        "payload.power_selection_pass",
    )
    _assert_equal(
        payload.get("null_type_i_pass"),
        null_pass,
        "payload.null_type_i_pass",
    )
    _assert_equal(payload.get("pass"), scientific_pass, "payload.pass")
    if replay:
        regenerated = run_v6_worst_case_power(
            n_sim=n_sim,
            official=bool(payload.get("official")),
            seed=seed,
            episode_seed_grid=grid,
        )
        _assert_equal(payload, regenerated, "payload deterministic replay")
    return {
        "audit_pass": True,
        "schema_version": V6_POWER_PAYLOAD_SCHEMA_VERSION,
        "official": bool(payload.get("official")),
        "status": payload.get("status"),
        "scientific_power_pass": scientific_pass,
        "power_selection_pass": power_pass,
        "null_type_i_pass": null_pass,
        "selected_episode_seeds": selected,
        "contract_sha256": V6_POWER_CONTRACT_SHA256,
        "deterministic_replay_performed": bool(replay),
    }


def require_authorized_v6_episode_count(
    payload: Mapping[str, Any],
) -> int:
    audit = audit_v6_power_payload(
        payload, require_official=True, replay=True
    )
    selected = audit["selected_episode_seeds"]
    if selected is None or audit["power_selection_pass"] is not True:
        raise V6UnderpoweredError(
            "no V6 N in [12,18,24,30] clears both worst-case Wilson lower bounds"
        )
    if audit["null_type_i_pass"] is not True:
        raise V6UnderpoweredError("V6 null-size upper bound failed")
    if audit["scientific_power_pass"] is not True:
        raise V6UnderpoweredError(
            "V6 prospective power contract did not pass"
        )
    return int(selected)
