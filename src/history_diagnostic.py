"""Local feasibility for matched history interleaving interventions.

No inference provider is instantiated or called. This is a test of a restricted
class of history processing rules, not an identification of LLM mechanisms.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from functools import lru_cache
import hashlib
from itertools import permutations, product
import json
import math
from typing import Mapping, Sequence

import numpy as np

from .choice_baselines import FRAMES, HistoryFeatures, predict
from .controlled_focal_agent import ControlledHistoryEntry, SPONTANEOUS_SYSTEM_TEMPLATE, build_controlled_prompt
from .controlled_messages import DEVELOPMENT_TEMPLATES, candidate_set
from .scenarios import SCENARIOS


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def reference_inputs(folds: Sequence[Mapping], plan: Mapping) -> np.ndarray:
    """Read already fitted priors; do not refit or select new parameters."""
    if len(folds) != 5 or sorted(f["fold"] for f in folds) != list(range(5)):
        raise ValueError("expected all five V4 folds")
    expected = {
        "reward_learning": {"alpha": plan["reward_alpha"], "beta": plan["beta"],
                            "stickiness": plan["stickiness"], "prior_power": plan["prior_power"]},
        "belief_dynamic": {"hazard": plan["belief_hazard"], "beta": plan["beta"],
                           "stickiness": plan["stickiness"], "prior_power": plan["prior_power"]},
    }
    for fold in folds:
        for name, params in expected.items():
            if fold["families"][name]["params"] != params:
                raise ValueError("source fit differs from the declared reference")
    priors = np.array([f["training_prior"] for f in sorted(folds, key=lambda f: f["fold"])])
    if priors.shape != (5, 3) or not np.isfinite(priors).all() or np.any(priors <= 0) or not np.allclose(priors.sum(1), 1):
        raise ValueError("invalid source frame priors")
    return priors


def allocation(n_pairs: int, seed: int) -> list[dict]:
    """Balanced blocks of focus frame x current candidate permutation."""
    if n_pairs < 18 or n_pairs % 18:
        raise ValueError("pair count must be a positive multiple of 18")
    rng = np.random.default_rng(seed)
    cells = list(product(range(3), list(permutations(range(3)))))
    rows = []
    for block in range(n_pairs // 18):
        for index in rng.permutation(18):
            focus, slots = cells[int(index)]
            rows.append({"pair_index": len(rows), "block": block, "focus": focus,
                         "current_slot_frames": list(slots), "high_first": bool(rng.integers(2))})
    return rows


def within_frame_streams(history: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(int(reward) for action, reward in history if action == frame) for frame in range(3))


def matched_pair_checks(low, high, plan: Mapping) -> dict[str, bool]:
    low = [tuple(x) for x in low]
    high = [tuple(x) for x in high]
    suffix = plan["fixed_suffix_length"]
    return {
        "different_global_history": low != high,
        "same_length": len(low) == len(high) == 3 * plan["events_per_frame"],
        "same_within_frame_streams": within_frame_streams(low) == within_frame_streams(high),
        "same_event_counts": Counter(low) == Counter(high),
        "same_recent_events": low[-suffix:] == high[-suffix:],
        "suffix_covers_all_frames": sorted(a for a, _ in low[-suffix:]) == [0, 1, 2],
        "balanced_frame_exposures": all(len(h) == plan["events_per_frame"] for h in within_frame_streams(low)),
        "balanced_success_counts": all(sum(h) == plan["successes_per_frame"] for h in within_frame_streams(low)),
    }


def _max_run(order: Sequence[int]) -> int:
    longest, length, previous = 0, 0, None
    for item in order:
        length = length + 1 if item == previous else 1
        longest, previous = max(longest, length), item
    return longest


def _candidate_histories(rng: np.random.Generator, plan: Mapping) -> list[list[list[int]]]:
    n = plan["events_per_frame"]
    if plan["fixed_suffix_length"] != 3 or not 0 < plan["successes_per_frame"] < n:
        raise ValueError("unsupported matching specification")
    streams = [rng.permutation([1] * plan["successes_per_frame"] + [0] * (n - plan["successes_per_frame"])).tolist()
               for _ in range(3)]
    suffix = rng.permutation(3).tolist()
    orders: set[tuple[int, ...]] = set()
    histories = []
    for _ in range(10000):
        prefix = rng.permutation(np.repeat(np.arange(3), n - 1)).tolist()
        order = tuple(prefix + suffix)
        if order in orders or _max_run(prefix) > plan["max_prefix_run"]:
            continue
        orders.add(order)
        count = [0, 0, 0]
        history = []
        for action in order:
            history.append([action, streams[action][count[action]]])
            count[action] += 1
        histories.append(history)
        if len(histories) == plan["n_interleavings"]:
            return histories
    raise ValueError("could not construct the fixed candidate pool; no expanded search allowed")


def shared_params(plan: Mapping) -> dict:
    return {k: plan[k] for k in ("beta", "stickiness", "prior_power")}


def ensemble(features: HistoryFeatures, family: str, params: Mapping, priors: np.ndarray, plan: Mapping) -> np.ndarray:
    return np.mean([predict(features, family, params, prior, plan["lapse"]) for prior in priors], axis=0)


def build_bank(plan: Mapping, priors: np.ndarray, progress=None) -> tuple[list[dict], list[dict]]:
    rng = np.random.default_rng(plan["design_seed"])
    pairs, pools = [], []
    seen = set()
    for design in allocation(plan["n_pairs"], plan["schedule_seed"]):
        histories = _candidate_histories(rng, plan)
        features = HistoryFeatures(histories, plan["p_match"], plan["p_mismatch"])
        params = dict(shared_params(plan), hazard=plan["belief_hazard"])
        by_prior = np.array([predict(features, "belief_dynamic", params, prior, plan["lapse"]) for prior in priors])
        scores = by_prior.mean(0)[:, design["focus"]]
        low, high = int(np.argmin(scores)), int(np.argmax(scores))
        checks = matched_pair_checks(histories[low], histories[high], plan)
        if not all(checks.values()):
            raise ValueError("matching failed: " + str(checks))
        identity = digest(sorted([histories[low], histories[high]]))
        if identity in seen:
            raise ValueError("duplicate history pair; stop instead of silently resampling")
        seen.add(identity)
        pairs.append({**design, "pair_id": identity[:16], "low": histories[low], "high": histories[high],
                      "selected_pool_indices": [low, high], "matching_checks": checks,
                      "reference_focus_gap": float(scores[high] - scores[low]),
                      "focus_gap_by_prior": (by_prior[:, high, design["focus"]] - by_prior[:, low, design["focus"]]).tolist()})
        pools.append({"pair_index": design["pair_index"], "histories": histories,
                      "reference_probabilities_by_prior": by_prior.tolist(), "selected_pool_indices": [low, high]})
        if progress and len(pairs) % 72 == 0:
            progress(f"constructed {len(pairs)}/{plan['n_pairs']} pairs")
    return pairs, pools


def _softmax_values(features: HistoryFeatures, values: np.ndarray, priors: np.ndarray, plan: Mapping) -> np.ndarray:
    probabilities = []
    for prior in priors:
        logits = plan["beta"] * values + plan["prior_power"] * np.log(prior) + plan["stickiness"] * features.last
        logits -= logits.max(1, keepdims=True)
        p = np.exp(logits)
        p /= p.sum(1, keepdims=True)
        probabilities.append((1 - plan["lapse"]) * p + plan["lapse"] / 3)
    return np.mean(probabilities, axis=0)


def recency_values(features: HistoryFeatures, family: str, value: float, alpha: float) -> np.ndarray:
    if family == "decay_q":
        q = np.full((features.n, 3), .5)
        for t in range(features.actions.shape[1]):
            ix = np.flatnonzero(features.length > t)
            actions = features.actions[ix, t]
            q[ix, actions] += alpha * (features.rewards[ix, t] - q[ix, actions])
            q[ix] = .5 + (1 - value) * (q[ix] - .5)
        return q
    success, exposure = np.zeros((features.n, 3)), np.zeros((features.n, 3))
    for t in range(features.actions.shape[1]):
        ix = np.flatnonzero(features.length > t)
        if family == "discounted_evidence":
            success[ix] *= value
            exposure[ix] *= value
        elif family == "recent_window":
            ix = ix[t >= features.length[ix] - int(value)]
        else:
            raise ValueError("unknown recency family")
        actions = features.actions[ix, t]
        success[ix, actions] += features.rewards[ix, t]
        exposure[ix, actions] += 1
    return (success + 1) / (exposure + 2)


INVARIANT_POLICIES = ("uniform", "expertise", "repeat_last", "win_stay_expertise", "history_frequency", "reward_learning", "belief_static")


def policy_probabilities(pairs: Sequence[Mapping], priors: np.ndarray, plan: Mapping) -> dict[str, np.ndarray]:
    histories = [pair[arm] for pair in pairs for arm in ("low", "high")]
    features = HistoryFeatures(histories, plan["p_match"], plan["p_mismatch"])
    params = shared_params(plan)
    definitions = {"uniform": {}, "expertise": {}, "repeat_last": {"strength": .75},
                   "win_stay_expertise": {"strength": .75}, "history_frequency": params,
                   "reward_learning": dict(params, alpha=plan["reward_alpha"]),
                   "belief_static": params, "belief_dynamic": dict(params, hazard=plan["belief_hazard"])}
    predictions = {name: ensemble(features, name, settings, priors, plan).reshape(len(pairs), 2, 3)
                   for name, settings in definitions.items()}
    for family, grid in (("decay_q", plan["decay_q_rates"]),
                         ("discounted_evidence", plan["evidence_retention"]),
                         ("recent_window", plan["recent_event_windows"])):
        for value in grid:
            values = recency_values(features, family, value, plan["reward_alpha"])
            predictions[f"{family}:{value:g}"] = _softmax_values(features, values, priors, plan).reshape(len(pairs), 2, 3)
    for name, p in predictions.items():
        if not np.isfinite(p).all() or np.any(p <= 0) or not np.allclose(p.sum(2), 1):
            raise AssertionError("invalid reference probabilities: " + name)
        if name in INVARIANT_POLICIES and not np.allclose(p[:, 0], p[:, 1], atol=1e-12, rtol=0):
            raise AssertionError("a declared invariant policy changed: " + name)
    return predictions


def render_pair(pair: Mapping, plan: Mapping) -> tuple[dict[str, dict], dict]:
    """Attach words to event identities, then reorder the identical objects."""
    rng = np.random.default_rng(np.random.SeedSequence([plan["design_seed"], pair["pair_index"], 91]))
    events = {}
    for frame, name in enumerate(FRAMES):
        offset = int(rng.integers(len(DEVELOPMENT_TEMPLATES[name])))
        for occurrence in range(plan["events_per_frame"]):
            scenario = SCENARIOS[int(rng.integers(len(SCENARIOS)))]
            message = DEVELOPMENT_TEMPLATES[name][(offset + occurrence) % len(DEVELOPMENT_TEMPLATES[name])].format(a=scenario.option_a, b=scenario.option_b)
            events[frame, occurrence] = (scenario, message)
    current = SCENARIOS[int(rng.integers(len(SCENARIOS)))]
    candidates = candidate_set(current, pair["pair_index"], 19, 16, plan["design_seed"])
    by_frame = {FRAMES.index(c.frame): c for c in candidates}
    candidates = [replace(by_frame[frame], slot=slot) for slot, frame in enumerate(pair["current_slot_frames"], 1)]
    prompts, entries = {}, {}
    for arm in ("low", "high"):
        counts, history = [0, 0, 0], []
        for t, (frame, reward) in enumerate(pair[arm]):
            scenario, message = events[frame, counts[frame]]
            counts[frame] += 1
            history.append(ControlledHistoryEntry(t + 1, scenario.id, scenario.title, 1, message, FRAMES[frame], "A" if reward else "B"))
        prompt = build_controlled_prompt(current, candidates, history, 19, 20, True, "spontaneous")
        if prompt.system != SPONTANEOUS_SYSTEM_TEMPLATE.format(n_rounds=20):
            raise ValueError("active focal prompt is not the original V4 prompt")
        prompts[arm] = {"system": prompt.system, "user": prompt.user}
        entries[arm] = [{"scenario_title": h.scenario_title, "selected_message": h.selected_message, "choice": h.choice} for h in history]
    if Counter(json.dumps(h, sort_keys=True) for h in entries["low"]) != Counter(json.dumps(h, sort_keys=True) for h in entries["high"]):
        raise AssertionError("event text multiset changed")
    if entries["low"][-3:] != entries["high"][-3:]:
        raise AssertionError("recent visible events changed")
    return prompts, {"visible_events": entries, "current_scenario": current.as_dict(),
                     "current_candidates": [c.visible_dict() for c in candidates]}


def request_schedule(pairs: Sequence[Mapping], plan: Mapping) -> tuple[list[dict], list[dict], list[dict]]:
    """Prepare opaque prompt records; never dispatch them."""
    requests, key, samples = [], [], []
    sham_needed = len(pairs) // 9
    sham_counts = Counter()
    seen_samples = set()
    batches = []
    for pair in pairs:
        prompts, audit = render_pair(pair, plan)
        order = ["high", "low"] if pair["high_first"] else ["low", "high"]
        batch = []
        for arm in order:
            request_id = digest([plan["schedule_seed"], pair["pair_id"], arm])[:24]
            batch.append(({"request_id": request_id, **prompts[arm]},
                          {"request_id": request_id, "kind": "active", "pair_index": pair["pair_index"],
                           "pair_id": pair["pair_id"], "arm": arm, "focus": FRAMES[pair["focus"]],
                           "focus_slot": pair["current_slot_frames"].index(pair["focus"]) + 1}))
        batches.append(batch)
        if pair["focus"] not in seen_samples:
            samples.append({"pair": dict(pair), "prompts": prompts, "render_audit": audit})
            seen_samples.add(pair["focus"])
        if sham_counts[pair["focus"]] < sham_needed:
            sham_counts[pair["focus"]] += 1
            batch = []
            for repeat in range(2):
                request_id = digest([plan["schedule_seed"], pair["pair_id"], "sham", repeat])[:24]
                batch.append(({"request_id": request_id, **prompts["low"]},
                              {"request_id": request_id, "kind": "sham", "pair_index": pair["pair_index"],
                               "pair_id": pair["pair_id"] + "-sham", "arm": str(repeat),
                               "focus": FRAMES[pair["focus"]], "focus_slot": pair["current_slot_frames"].index(pair["focus"]) + 1}))
            batches.append(batch)
    rng = np.random.default_rng(plan["schedule_seed"] + 1)
    for batch_id in rng.permutation(len(batches)):
        for prompt, metadata in batches[int(batch_id)]:
            metadata["run_order"] = len(requests) + 1
            requests.append(prompt)
            key.append(metadata)
    return requests, key, samples


@lru_cache(maxsize=8)
def binomial_tail_table(max_pairs: int) -> np.ndarray:
    """Exact Binomial(k, .5) upper tails, avoiding a SciPy dependency."""
    if not 0 <= max_pairs <= 1000:
        raise ValueError("tail table supports 0 to 1000 pairs")
    result = np.ones((max_pairs + 1, max_pairs + 1))
    for k in range(1, max_pairs + 1):
        probabilities = np.array([math.ldexp(float(math.comb(k, j)), -k) for j in range(k + 1)])
        result[k, :k + 1] = np.minimum(1, np.cumsum(probabilities[::-1])[::-1])
    result.setflags(write=False)
    return result


def paired_tests(differences: np.ndarray, focuses: np.ndarray, alpha: float) -> dict[str, np.ndarray]:
    differences = np.asarray(differences)
    if differences.ndim == 1:
        differences = differences[None, :]
    if differences.ndim != 2 or differences.shape[1] != len(focuses) or not np.isin(differences, (-1, 0, 1)).all():
        raise ValueError("expected pair differences in {-1,0,1}")
    if not np.isin(focuses, (0, 1, 2)).all() or not np.any(focuses != 2) or not 0 < alpha < 1:
        raise ValueError("invalid focus groups or alpha")
    table = binomial_tail_table(differences.shape[1])
    result = {}
    masks = [("pooled", np.ones(len(focuses), dtype=bool)), ("nondefault", focuses != 2)]
    masks += [("focus_" + frame, focuses == index) for index, frame in enumerate(FRAMES)]
    for name, mask in masks:
        d = differences[:, mask]
        positives, negatives = (d > 0).sum(1), (d < 0).sum(1)
        result[name + "_p"] = table[positives + negatives, positives]
        result[name + "_reject"] = result[name + "_p"] <= alpha
    result["joint_reject"] = result["pooled_reject"] & result["nondefault_reject"]
    return result


def wilson(hits: int, n: int) -> dict:
    if n <= 0 or not 0 <= hits <= n:
        raise ValueError("invalid Monte Carlo counts")
    z = 1.96
    proportion = hits / n
    denom = 1 + z * z / n
    center = (proportion + z * z / (2 * n)) / denom
    radius = z * math.sqrt(proportion * (1 - proportion) / n + z * z / (4 * n * n)) / denom
    return {"hits": int(hits), "n_simulations": int(n), "rate": proportion,
            "ci_lo": max(0., center - radius), "ci_hi": min(1., center + radius)}


def draw_pair_differences(p: np.ndarray, focuses: np.ndarray, rng: np.random.Generator,
                          n_sim: int, coupling: str, unusable: float) -> np.ndarray:
    if p.shape != (len(focuses), 2, 3) or not np.isfinite(p).all() or np.any(p < 0) or not np.allclose(p.sum(2), 1):
        raise ValueError("invalid paired probability tensor")
    if not 0 <= unusable <= 1:
        raise ValueError("invalid unusable fraction")
    margins = p[np.arange(len(focuses)), :, focuses]
    u_high = rng.random((n_sim, len(focuses)))
    if coupling == "independent":
        u_low = rng.random((n_sim, len(focuses)))
    elif coupling == "negative_bound":
        u_low = 1 - u_high
    else:
        raise ValueError("unknown pair coupling")
    result = (u_high < margins[:, 1]).astype(np.int8) - (u_low < margins[:, 0]).astype(np.int8)
    if unusable:
        result[rng.random(result.shape) < unusable] = 0
    return result


def ordered_policy_names(predictions: Mapping[str, np.ndarray], plan: Mapping) -> list[str]:
    """Preserve declared seed coordinates across JSON key sorting/reloading."""
    order = list(INVARIANT_POLICIES) + ["belief_dynamic"]
    for family, grid in (("decay_q", plan["decay_q_rates"]),
                         ("discounted_evidence", plan["evidence_retention"]),
                         ("recent_window", plan["recent_event_windows"])):
        order.extend(f"{family}:{value:g}" for value in grid)
    return [name for name in order if name in predictions] + sorted(set(predictions) - set(order))


def power_scenarios(predictions: Mapping[str, np.ndarray], plan: Mapping) -> list[tuple[str, str, float, np.ndarray]]:
    scenarios = []
    for name in ordered_policy_names(predictions, plan):
        probabilities = predictions[name]
        if name == "belief_dynamic":
            for fraction in plan["effect_fractions"]:
                p = fraction * probabilities + (1 - fraction) * predictions["reward_learning"]
                scenarios.append((f"dynamic_fraction:{fraction:g}", "dynamic_alternative", fraction, p))
        else:
            role = "invariant_null" if name in INVARIANT_POLICIES else "recency_counterexample"
            scenarios.append((name, role, 0., probabilities))
    return scenarios


def simulate_design(pairs: Sequence[Mapping], predictions: Mapping[str, np.ndarray], plan: Mapping, progress=None) -> list[dict]:
    results = []
    focuses = np.array([p["focus"] for p in pairs])
    for scenario_index, (name, role, fraction, p) in enumerate(power_scenarios(predictions, plan)):
        for grid_index, n in enumerate(plan["n_grid"]):
            if n > len(pairs):
                raise ValueError("sample grid exceeds fixed bank")
            for coupling_index, coupling in enumerate(plan["pair_couplings"]):
                for drop_index, drop in enumerate(plan["unusable_fractions"]):
                    rng = np.random.default_rng(np.random.SeedSequence([plan["power_seed"], scenario_index, grid_index, coupling_index, drop_index]))
                    differences = draw_pair_differences(p[:n], focuses[:n], rng, plan["n_simulations"], coupling, drop)
                    tests = paired_tests(differences, focuses[:n], plan["alpha_each"])
                    margins = p[np.arange(n), :, focuses[:n]]
                    row = {"scenario": name, "role": role, "effect_fraction": fraction,
                           "n_pairs": n, "active_calls": 2 * n, "calls_with_shams": 8 * n // 3,
                           "coupling": coupling, "unusable_fraction": drop,
                           "expected_focus_difference": float((margins[:, 1] - margins[:, 0]).mean()),
                           "expected_nondefault_difference": float((margins[:, 1] - margins[:, 0])[focuses[:n] != 2].mean())}
                    for endpoint in ("pooled", "nondefault", "joint", "focus_fairness", "focus_risk", "focus_expertise"):
                        row.update({endpoint + "_" + key: value for key, value in wilson(int(tests[endpoint + "_reject"].sum()), plan["n_simulations"]).items()})
                    results.append(row)
        if progress:
            progress(f"power complete: {name}")
    return results


def synthetic_recovery(predictions: Mapping[str, np.ndarray], plan: Mapping, progress=None) -> list[dict]:
    """Closed candidate set recovery without fitting diagnostic outcomes."""
    names = ordered_policy_names(predictions, plan)
    results = []
    for grid_index, n in enumerate(plan["n_grid"]):
        candidates = np.array([predictions[name][:n].reshape(2 * n, 3) for name in names])
        for true_index, true_name in enumerate(names):
            rng = np.random.default_rng(np.random.SeedSequence([plan["recovery_seed"], grid_index, true_index]))
            u = rng.random((plan["n_recovery_simulations"], 2 * n))
            y = (u[:, :, None] > np.cumsum(candidates[true_index], axis=1)[None, :, :]).sum(2)
            loss = np.array([-np.log(p[np.arange(2 * n)[None, :], y]).sum(1) for p in candidates])
            best = loss.min(0)
            ties = np.isclose(loss, best[None, :], atol=1e-10, rtol=0).sum(0) > 1
            winner = loss.argmin(0)
            for predicted_index, predicted_name in enumerate(names + ["unresolved_tie"]):
                hits = int(ties.sum()) if predicted_name == "unresolved_tie" else int(((winner == predicted_index) & ~ties).sum())
                results.append({"n_pairs": n, "generating_policy": true_name,
                                "selected_policy": predicted_name, **wilson(hits, plan["n_recovery_simulations"])})
        if progress:
            progress(f"closed set recovery complete: N={n}")
    return results


def decision(power: Sequence[Mapping], plan: Mapping) -> dict:
    qualifying = []
    per_n = []
    for n in plan["n_grid"]:
        alternative = [r for r in power if r["n_pairs"] == n and r["role"] == "dynamic_alternative"
                       and r["effect_fraction"] == plan["required_effect_fraction"]
                       and r["unusable_fraction"] == plan["required_unusable_fraction"]]
        nulls = [r for r in power if r["n_pairs"] == n and r["role"] == "invariant_null"]
        expected_nulls = len(INVARIANT_POLICIES) * len(plan["pair_couplings"]) * len(plan["unusable_fractions"])
        complete = len(alternative) == len(plan["pair_couplings"]) and len(nulls) == expected_nulls
        power_ok = complete and min(r["joint_ci_lo"] for r in alternative) >= plan["power_lower_required"]
        null_upper = max((r[endpoint + "_ci_hi"] for r in nulls for endpoint in ("pooled", "nondefault", "joint")), default=None)
        null_ok = complete and null_upper <= plan["null_upper_required"]
        per_n.append({"n_pairs": n, "minimum_required_power_lower": min((r["joint_ci_lo"] for r in alternative), default=None),
                      "maximum_invariant_null_upper": null_upper,
                      "power_pass": bool(power_ok), "null_pass": bool(null_ok)})
        if power_ok and null_ok:
            qualifying.append(n)
    selected_n = min(qualifying) if qualifying else None
    check_n = selected_n or max(plan["n_grid"])
    counterexamples = [dict(r) for r in power if r["n_pairs"] == check_n and r["role"] == "recency_counterexample"
                       and r["joint_ci_lo"] > plan["null_upper_required"]]
    return {"selected_n_for_narrow_test": selected_n, "per_n": per_n,
            "specificity_evaluation_n": check_n, "recency_counterexample_rows": counterexamples,
            "specific_to_partner_beliefs": False if counterexamples else None,
            "sensitivity_status": "NARROW_TEST_SENSITIVITY_PASS" if selected_n else "INSUFFICIENT_SENSITIVITY_WITHIN_CEILING",
            "interpretation_status": "NOT_SPECIFIC_TO_PARTNER_BELIEFS" if counterexamples else "NO_COUNTEREXAMPLE_IN_THIS_FINITE_SCREEN_NOT_IDENTIFICATION",
            "recommend_paid_run": False, "old_gates_unchanged": True}
