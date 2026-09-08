"""Exact, offline design checks. Not an implemented LLM experiment.

Tests whether an immediate response vector is sufficient for a specified
future prediction. Inspired by Shai et al. (2405.15943), not their task/code.
"""

from fractions import Fraction as F
from itertools import combinations


def _distribution(values):
    values = tuple(F(str(x)) for x in values)
    if not values or any(x < 0 for x in values) or sum(values) != 1:
        raise ValueError("Expected a nonnegative distribution with mass one")
    return values


def response_vector(belief, emissions):
    """Return P(A) for every action. Emission rows need not sum to one."""
    belief = _distribution(belief)
    rows = tuple(tuple(F(str(x)) for x in row) for row in emissions)
    if len(rows) != len(belief) or not rows or not rows[0]:
        raise ValueError("Emission dimensions do not match belief")
    if any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("Emission rows have different lengths")
    if any(not 0 <= x <= 1 for row in rows for x in row):
        raise ValueError("Response probabilities must be between zero and one")
    return tuple(sum(b * row[j] for b, row in zip(belief, rows))
                 for j in range(len(rows[0])))


def transition_belief(belief, transitions):
    belief = _distribution(belief)
    rows = tuple(_distribution(row) for row in transitions)
    if len(rows) != len(belief) or any(len(row) != len(belief) for row in rows):
        raise ValueError("Transition matrix must be square and match belief")
    return tuple(sum(b * row[j] for b, row in zip(belief, rows))
                 for j in range(len(belief)))


def bernoulli_update(belief, likelihoods, observed_a):
    belief = _distribution(belief)
    likelihoods = tuple(F(str(x)) for x in likelihoods)
    if len(likelihoods) != len(belief) or any(not 0 <= p <= 1 for p in likelihoods):
        raise ValueError("Invalid observation likelihoods")
    if type(observed_a) is not bool:
        raise ValueError("Observation must be a boolean")
    weights = tuple(b * (p if observed_a else 1 - p)
                    for b, p in zip(belief, likelihoods))
    total = sum(weights)
    if not total:
        raise ValueError("Observation has zero probability")
    return tuple(w / total for w in weights)


def simplex_grid(denominator=4):
    if type(denominator) is not int or denominator < 1:
        raise ValueError("Denominator must be a positive integer")
    return tuple((F(a, denominator), F(b, denominator),
                  F(denominator-a-b, denominator))
                 for a in range(denominator+1)
                 for b in range(denominator+1-a))


def alias_pairs(beliefs, emissions, transitions):
    """Enumerate every pair: equal immediate vector, unequal future vector."""
    cases = []
    for left, right in combinations(beliefs, 2):
        current_left = response_vector(left, emissions)
        current_right = response_vector(right, emissions)
        future_left = response_vector(transition_belief(left, transitions), emissions)
        future_right = response_vector(transition_belief(right, transitions), emissions)
        if current_left == current_right and future_left != future_right:
            cases.append({"left": left, "right": right, "current": current_left,
                          "future_left": future_left, "future_right": future_right})
    return cases


def design_certificate():
    # Original pure framing response matrix is invertible in belief space.
    original = tuple(tuple(F(72 if i == j else 38, 100) for j in range(3))
                     for i in range(3))
    # Proposed mathematical witness: S0 and S1 have equal immediate responses.
    emissions = ((F(3, 5), F(2, 5), F(1, 2)),
                 (F(3, 5), F(2, 5), F(1, 2)),
                 (F(2, 5), F(3, 5), F(1, 2)))
    transitions = ((1, 0, 0), (0, 0, 1), (0, 0, 1))
    identity = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    prior = (F(1, 2), F(1, 2), F(0))
    # A different earlier context supplies information about S0 versus S1.
    likelihoods = (F(3, 4), F(1, 4), F(1, 2))
    left = bernoulli_update(prior, likelihoods, True)
    right = bernoulli_update(prior, likelihoods, False)
    witnesses = alias_pairs((left, right), emissions, transitions)
    if len(witnesses) != 1:
        raise AssertionError("Expected one recoverable predictive alias witness")
    grid = simplex_grid()
    old_aliases = alias_pairs(grid, original, transitions)
    identity_aliases = alias_pairs(grid, emissions, identity)
    if old_aliases or identity_aliases:
        raise AssertionError("Negative controls failed")
    return {
        "status": "OFFLINE_DESIGN_CERTIFICATE_NOT_MODEL_EVIDENCE",
        "model_calls": 0,
        "method_reference": "https://arxiv.org/html/2405.15943v3#S3.SS2",
        "grid_beliefs": len(grid), "grid_pairs": len(grid)*(len(grid)-1)//2,
        "original_predictive_aliases": len(old_aliases),
        "identity_transition_predictive_aliases": len(identity_aliases),
        "proposed_emissions": emissions, "proposed_transitions": transitions,
        "earlier_prior": prior, "earlier_a_likelihoods": likelihoods,
        "recoverable_witness": witnesses[0],
        "all_grid_witnesses": alias_pairs(grid, emissions, transitions),
        "boundary": (
            "Refutes sufficiency of only the immediate response vector for this "
            "specified transition. Does not distinguish belief from a richer reward "
            "predictor, history lookup, or any invertible representation of state. "
            "Earlier context likelihoods and transition knowledge are assumptions, "
            "not demonstrated LLM abilities. This is not a deployable experiment."
        ),
    }
