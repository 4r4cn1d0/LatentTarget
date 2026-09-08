"""Transparent numerical reference policies; never an LLM implementation claim."""
from __future__ import annotations

import numpy as np

from src.partner_state import TYPE_PAIRS, ORDERS

POLICIES = ("expertise", "fixed_slot", "name_bias", "uniform", "global_reward", "global_recency",
            "participant_reward", "participant_recency", "participant_feature_reward", "static_belief", "dynamic_belief")


def state_values(frames, recipients, outcomes, policy, params):
    """Inputs (studies,bundles,24). Output participant x frame expected values."""
    if policy not in POLICIES:
        raise ValueError("unknown policy")
    frames, recipients, outcomes = map(np.asarray, (frames, recipients, outcomes))
    if frames.shape != recipients.shape or frames.shape != outcomes.shape or frames.shape[-1] != 24:
        raise ValueError("history tensor mismatch")
    shape = (*frames.shape[:-1], 2, 3)
    q = np.full(shape, params["initial_reward"], dtype=float)
    if policy in ("expertise", "fixed_slot", "uniform", "name_bias"):
        return np.broadcast_to(np.array([.38, .38, .72]), shape).copy()
    global_policy = policy.startswith("global_")
    if "belief" in policy:
        posterior = np.full(shape, 1/3.)
        hazard = params["belief_hazard"] if policy == "dynamic_belief" else 0.
        for event in range(24):
            f, r, y = frames[..., event], recipients[..., event], outcomes[..., event]
            p = .38 + .34 * (f[..., None] == np.arange(3))
            likelihood = np.where(y[..., None], p, 1-p)
            for who in range(2):
                proposed = ((1-hazard)*posterior[..., who, :] + hazard/3) * likelihood
                proposed /= proposed.sum(axis=-1, keepdims=True)
                posterior[..., who, :] = np.where((r == who)[..., None], proposed, posterior[..., who, :])
        return .38 + .34 * posterior
    if "recency" in policy:
        successes = np.zeros(shape); counts = np.zeros(shape)
        seen = np.zeros(shape[:-1], dtype=int)
        for event in reversed(range(24)):
            f, r, y = frames[..., event], recipients[..., event], outcomes[..., event]
            for who in range(2):
                active = (seen[..., who] < params["recent_window"]) & (True if global_policy else r == who)
                mask = active[..., None] & (f[..., None] == np.arange(3))
                counts[..., who, :] += mask
                successes[..., who, :] += mask * y[..., None]
                seen[..., who] += active
        return (successes + 1) / (counts + 2)
    for event in range(24):
        f, r, y = frames[..., event], recipients[..., event], outcomes[..., event]
        for who in range(2):
            mask = (f[..., None] == np.arange(3)) & (True if global_policy else (r == who)[..., None])
            q[..., who, :] += params["reward_alpha"] * mask * (y[..., None] - q[..., who, :])
    return q


def simulation_geometry(n):
    if n <= 0 or n % 36:
        raise ValueError("balanced N required")
    types = np.array([t for _ in range(n//36) for t in TYPE_PAIRS for _ in ORDERS])
    orders = np.array([o for _ in range(n//36) for _ in TYPE_PAIRS for o in ORDERS])
    pure = np.eye(3)[orders]
    mixed = (np.array([[2,1,0], [0,2,1], [1,0,2]]) / 3)[orders]
    vectors = np.stack([pure, mixed, pure, pure, mixed, pure], axis=1)
    strata = np.repeat(np.arange(6), 6).tolist() * (n//36)
    return types, orders, vectors, np.array(strata)


def simulate_choices(batch, n, rng, scenario, params):
    """Fresh target records per simulated study; all branches share their history.

    Balanced abstract allocation is in canonical order, an innocuous relabeling
    for these frame based policies. No text model is being approximated here.
    """
    types, orders, vectors, strata = simulation_geometry(n)
    frames = np.repeat(rng.random((batch, n, 4, 3)).argsort(axis=-1).reshape(batch, n, 12), 2, axis=-1)
    first = rng.integers(0, 2, (batch, n, 12))
    recipients = np.stack([first, 1-first], axis=-1).reshape(batch, n, 24)
    actual_types = np.take_along_axis(np.broadcast_to(types, (batch, n, 2)), recipients, axis=-1)
    outcomes = rng.random((batch, n, 24)) < (.38 + .34 * (frames == actual_types))
    random_outcomes = rng.random((batch, n, 24)) < .5
    policy = scenario["policy"]
    values = state_values(frames, recipients, outcomes, policy, params)
    random_values = state_values(frames, recipients, random_outcomes, policy, params)
    # Name preferences are arbitrary fixed slots, independent of assigned types.
    name_slots = rng.integers(0, 3, (batch, n, 2))
    selected = np.full((batch, n, 6, 4), -1, dtype=np.int8)
    shared_route = rng.random((batch, n)) < scenario["strength"]
    for metric in range(6):
        count = 2 if metric in (3, 4) else 4
        candidate_vectors = vectors[:, metric]
        default = np.argmax(candidate_vectors[..., 2], axis=-1)
        for cell in range(count):
            who = cell % 2
            rebound = cell >= 2
            source = 1-who if rebound else who
            q = random_values[..., source, :] if metric == 5 else values[..., source, :]
            if metric in (3, 4):
                q = np.full_like(q, .5)
            if policy == "participant_reward":
                # Dominant frame generalization, not the additive feature rule.
                scores = np.take_along_axis(q, np.broadcast_to(candidate_vectors.argmax(-1), q.shape), axis=-1)
            else:
                scores = np.einsum("bnf,njf->bnj", q, candidate_vectors)
            # Ties resolved by smallest displayed slot, with numerical tolerance.
            choices = (scores >= scores.max(-1, keepdims=True) - 1e-12).argmax(-1)
            if policy == "fixed_slot":
                choices = np.zeros((batch, n), dtype=int)
            elif policy == "name_bias":
                choices = name_slots[..., who]
            elif policy == "uniform":
                choices = rng.integers(0, 3, (batch, n))
            route = shared_route if scenario["coupling"] == "shared" else rng.random((batch, n)) < scenario["strength"]
            selected[:, :, metric, cell] = np.where(route, choices, default)
    missing = scenario["missing"]
    if missing not in ("none", "mcar", "fairness_selective"):
        raise ValueError("unknown missingness mechanism")
    if missing != "none":
        rate = scenario["rate"]
        p = np.full(selected.shape, rate)
        if missing == "fairness_selective":
            frame = np.take_along_axis(np.broadcast_to(vectors.argmax(-1), (batch, n, 6, 3)), np.maximum(selected, 0), axis=-1)
            p = np.where(frame == 0, min(3*rate, 1.), 0.)
        selected[rng.random(selected.shape) < p] = -1
    return selected, types, vectors, strata
