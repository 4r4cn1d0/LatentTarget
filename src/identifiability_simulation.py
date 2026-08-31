"""Post-hoc positive control for target identifiability.

The behavioral checkpoint can fail because the response channel is intrinsically
uninformative, or because the focal model does not send messages that separate
the target hypotheses.  This module distinguishes those cases by simulating an
oracle experimental-design policy over three highly specific messages selected
from the saved message pool using target scores only.  It never changes or
rescues the frozen behavioral decision.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

import numpy as np

from config import STRATEGIES, TargetParams
from .bayesian_observer import BayesianEvidenceObserver, BayesianObserverConfig
from .target_simulator import PersuasionScorer, PersuasionScores


def _wilson_interval(successes: float, n: int, z: float = 1.959963984540054) -> list[float]:
    """Wilson 95% interval for Monte Carlo classification accuracy."""
    if n <= 0:
        raise ValueError("Wilson interval requires n > 0")
    p = float(successes) / n
    denominator = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denominator
    half = z * np.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denominator
    return [float(centre - half), float(centre + half)]


class FixedScoreScorer:
    """Message scorer backed by an audited fixed mapping."""

    name = "fixed_score_scorer"

    def __init__(self, mapping: Mapping[str, PersuasionScores]) -> None:
        self.mapping = dict(mapping)

    def score(self, message: str) -> PersuasionScores:
        try:
            return self.mapping[str(message)]
        except KeyError as exc:
            raise KeyError("message is absent from fixed-score mapping") from exc


def select_diagnostic_messages(
    records: Sequence[Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Select one outcome-blind, high-specificity saved message per dimension.

    Specificity is the rewarded score for a dimension minus the largest other
    rewarded score.  Target choices, judge labels, conditions, rounds, and
    hidden types are never consulted.
    """
    if not records:
        raise ValueError("cannot select diagnostic messages from an empty log")
    unique: Dict[str, Dict[str, float]] = {}
    for index, record in enumerate(records):
        message = str(record.get("focal_message", ""))
        if not message:
            raise ValueError("empty focal message at row %d" % index)
        raw = record.get("target_scores")
        if not isinstance(raw, Mapping) or any(name not in raw for name in STRATEGIES):
            raise ValueError("missing rewarded target scores at row %d" % index)
        scores = {name: float(raw[name]) for name in STRATEGIES}
        if message in unique and any(
            not np.isclose(unique[message][name], scores[name], atol=1e-12, rtol=0.0)
            for name in STRATEGIES
        ):
            raise ValueError("same message has inconsistent target scores")
        unique[message] = scores

    selected: Dict[str, Dict[str, Any]] = {}
    for strategy in STRATEGIES:
        candidates = []
        for message, scores in unique.items():
            other_max = max(scores[name] for name in STRATEGIES if name != strategy)
            specificity = scores[strategy] - other_max
            candidates.append((specificity, scores[strategy], message, scores))
        specificity, own_score, message, scores = max(
            candidates, key=lambda item: (item[0], item[1], item[2])
        )
        selected[strategy] = {
            "message": message,
            "scores": scores,
            "specificity_margin": float(specificity),
            "own_score": float(own_score),
        }
    return selected


def scorer_from_selection(
    selected: Mapping[str, Mapping[str, Any]],
) -> FixedScoreScorer:
    mapping: Dict[str, PersuasionScores] = {}
    for strategy in STRATEGIES:
        item = selected[strategy]
        scores = item["scores"]
        mapping[str(item["message"])] = PersuasionScores(
            fairness=float(scores["fairness"]),
            risk=float(scores["risk"]),
            expertise=float(scores["expertise"]),
            intensity=sum(float(scores[name]) for name in STRATEGIES),
        )
    return FixedScoreScorer(mapping)


def expected_posterior_entropy(
    observer: BayesianEvidenceObserver,
    prior: Sequence[float],
    message: str,
) -> float:
    """Expected entropy after the next binary outcome for one message."""
    p = np.asarray(prior, dtype=float)
    p = p / p.sum()
    p_a_by_type = np.asarray(
        [observer.p_a(message, target) for target in STRATEGIES], dtype=float
    )
    p_a = float(np.dot(p, p_a_by_type))
    post_a = p * p_a_by_type
    post_a /= post_a.sum()
    post_b = p * (1.0 - p_a_by_type)
    post_b /= post_b.sum()
    return p_a * observer.entropy(post_a) + (1.0 - p_a) * observer.entropy(post_b)


def choose_information_message(
    observer: BayesianEvidenceObserver,
    prior: Sequence[float],
    selected: Mapping[str, Mapping[str, Any]],
) -> str:
    """Choose the candidate with minimum expected posterior entropy."""
    choices = []
    for order, strategy in enumerate(STRATEGIES):
        message = str(selected[strategy]["message"])
        choices.append(
            (expected_posterior_entropy(observer, prior, message), order, message)
        )
    return min(choices)[2]


def simulate_identifiability(
    selected: Mapping[str, Mapping[str, Any]],
    params: TargetParams,
    n_per_target: int = 3000,
    n_per_swap_pair: int = 1000,
    stable_rounds: int = 8,
    swap_round: int = 5,
    total_swap_rounds: int = 10,
    swap_hazard: float = 0.10,
    seed: int = 20260901,
) -> Dict[str, Any]:
    """Run stable and silent-swap simulator-capacity positive controls."""
    if n_per_target <= 0 or n_per_swap_pair <= 0:
        raise ValueError("simulation counts must be positive")
    if not 0 < swap_round < total_swap_rounds:
        raise ValueError("swap_round must be inside the swap episode")
    scorer: PersuasionScorer = scorer_from_selection(selected)
    stable_observer = BayesianEvidenceObserver(
        params=params,
        config=BayesianObserverConfig(change_hazard=0.0),
        scorer=scorer,
    )
    swap_observer = BayesianEvidenceObserver(
        params=params,
        config=BayesianObserverConfig(change_hazard=swap_hazard),
        scorer=scorer,
    )
    rng = np.random.default_rng(seed)

    stable_correct = np.zeros(stable_rounds, dtype=float)
    stable_entropy = np.zeros(stable_rounds, dtype=float)
    stable_n = n_per_target * len(STRATEGIES)
    for target in STRATEGIES:
        target_idx = STRATEGIES.index(target)
        for _ in range(n_per_target):
            posterior = stable_observer.initial.copy()
            for round_idx in range(stable_rounds):
                message = choose_information_message(stable_observer, posterior, selected)
                choice = "A" if rng.random() < stable_observer.p_a(message, target) else "B"
                posterior = stable_observer.update(posterior, message, choice)
                stable_correct[round_idx] += int(int(np.argmax(posterior)) == target_idx)
                stable_entropy[round_idx] += stable_observer.entropy(posterior)

    ordered_pairs = [
        (old, new) for old in STRATEGIES for new in STRATEGIES if old != new
    ]
    swap_correct_active = np.zeros(total_swap_rounds, dtype=float)
    swap_p_final = np.zeros(total_swap_rounds, dtype=float)
    swap_n = n_per_swap_pair * len(ordered_pairs)
    for old, new in ordered_pairs:
        new_idx = STRATEGIES.index(new)
        for _ in range(n_per_swap_pair):
            posterior = swap_observer.initial.copy()
            for round_idx in range(total_swap_rounds):
                target = old if round_idx < swap_round else new
                target_idx = STRATEGIES.index(target)
                message = choose_information_message(swap_observer, posterior, selected)
                choice = "A" if rng.random() < swap_observer.p_a(message, target) else "B"
                posterior = swap_observer.update(posterior, message, choice)
                swap_correct_active[round_idx] += int(
                    int(np.argmax(posterior)) == target_idx
                )
                swap_p_final[round_idx] += float(posterior[new_idx])
                if round_idx < total_swap_rounds - 1:
                    posterior = swap_observer.transition(posterior)

    p_a_matrix = {
        strategy: {
            target: stable_observer.p_a(str(selected[strategy]["message"]), target)
            for target in STRATEGIES
        }
        for strategy in STRATEGIES
    }
    return {
        "status": "post-hoc simulator-capacity positive control; not a behavioral result",
        "selection_rule": (
            "one saved message per rewarded dimension maximizing own target score "
            "minus the largest other rewarded score; outcomes and judge labels ignored"
        ),
        "policy": "choose the candidate minimizing expected posterior entropy",
        "seed": seed,
        "params": {
            "base_bias": params.base_bias,
            "w_match": params.w_match,
            "w_off": params.w_off,
            "logit_noise_sd": params.logit_noise_sd,
        },
        "selected_messages": dict(selected),
        "marginal_p_a_by_message_and_target": p_a_matrix,
        "stable": {
            "n_simulated_episodes": stable_n,
            "n_rounds": stable_rounds,
            "accuracy_after_each_outcome": (stable_correct / stable_n).tolist(),
            "mean_entropy_after_each_outcome": (stable_entropy / stable_n).tolist(),
            "final_accuracy": float(stable_correct[-1] / stable_n),
            "final_accuracy_mc_ci95": _wilson_interval(stable_correct[-1], stable_n),
        },
        "swap": {
            "n_simulated_episodes": swap_n,
            "n_ordered_pairs": len(ordered_pairs),
            "swap_after_round": swap_round,
            "n_rounds": total_swap_rounds,
            "change_hazard": swap_hazard,
            "active_target_accuracy_after_each_outcome": (
                swap_correct_active / swap_n
            ).tolist(),
            "mean_probability_final_target_after_each_outcome": (
                swap_p_final / swap_n
            ).tolist(),
            "final_target_accuracy": float(swap_correct_active[-1] / swap_n),
            "final_target_accuracy_mc_ci95": _wilson_interval(
                swap_correct_active[-1], swap_n
            ),
        },
        "interpretation_boundary": (
            "High accuracy shows that the frozen response function is learnable "
            "under an oracle information-seeking message policy. It does not show "
            "that the focal model used that policy or formed a latent target model."
        ),
    }
