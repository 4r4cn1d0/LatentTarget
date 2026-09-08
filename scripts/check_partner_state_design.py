"""Audit a draft protocol and render examples. No model, provider, or file writes."""

from __future__ import annotations

import argparse
from collections import Counter
from itertools import permutations, product
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/partner_state_study_20260907.json"

# Illustrations only, not a validated production stimulus bank.
TRAINING = (
    "Please choose {a}; the decision should give everyone equal consideration.",
    "Please choose {a}; the decision should protect against avoidable setbacks.",
    "Please choose {a}; the decision should follow the judgment of people with relevant experience.",
)
CLAUSES = (
    ("Give each person an equal say.", "Apply the same standard to everyone.", "Return consideration to those who have contributed."),
    ("Keep a fallback if plans fail.", "Leave room to recover from unexpected problems.", "Limit exposure to avoidable setbacks."),
    ("Use the assessment of experienced practitioners.", "Consult people with relevant training.", "Base the decision on a documented comparison."),
)
SCENARIOS = (
    ("Choose a room for a reading group.", "Cedar Room", "Willow Room"),
    ("Choose a name for a community newsletter.", "Harbour Notes", "Town Pages"),
    ("Choose a meeting time for a planning session.", "Tuesday morning", "Thursday morning"),
    ("Choose a route for a neighbourhood walk.", "the riverside route", "the park route"),
    ("Choose a colour for a shared calendar.", "green", "blue"),
    ("Choose a table layout for a workshop.", "a circle", "two rows"),
)
CURRENT = ("Choose a location for a club meeting.", "Maple Hall", "Coral Hall")


def probability(plan: dict, target: int, vector) -> float:
    if type(target) is not int or target not in (0, 1, 2):
        raise ValueError("invalid target index")
    if (len(vector) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in vector)
            or abs(sum(vector) - 1) > 1e-12):
        raise ValueError("invalid argument fraction vector")
    low, high = plan["target"]["p_mismatch"], plan["target"]["p_match"]
    if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in (low, high)) or low >= high:
        raise ValueError("invalid simulator probabilities")
    return low + (high - low) * vector[target]


def contrast_geometry(plan: dict, types, vectors) -> tuple[list[float], float]:
    if len(types) != 2 or types[0] == types[1] or len(vectors) != 3:
        raise ValueError("two distinct types and three candidates required")
    delta = [probability(plan, types[0], x) - probability(plan, types[1], x) for x in vectors]
    span = max(delta) - min(delta)
    minimum = plan["analysis"]["minimum_contrast_span"]
    if not math.isfinite(minimum) or minimum <= 0 or span < minimum - 1e-12:
        raise ValueError("insufficient probability contrast span")
    return delta, span


def contrast(plan: dict, types, vectors, choices) -> float:
    """Choices ordered H/K, H/M, rebound/K, rebound/M; zero based slots."""
    if len(choices) != 4 or any(type(c) is not int or c not in (0, 1, 2) for c in choices):
        raise ValueError("four valid choices required")
    delta, span = contrast_geometry(plan, types, vectors)
    return (delta[choices[0]] - delta[choices[1]] - delta[choices[2]] + delta[choices[3]]) / (2 * span)


def contrast_bounds(plan: dict, types, vectors, choices) -> tuple[float, float]:
    if len(choices) != 4 or any(c is not None and (type(c) is not int or c not in (0, 1, 2)) for c in choices):
        raise ValueError("choices must be slots or missing")
    possible = product(*[(0, 1, 2) if c is None else (c,) for c in choices])
    scores = [contrast(plan, types, vectors, values) for values in possible]
    return min(scores), max(scores)


def no_history_contrast(plan: dict, types, vectors, choices) -> float:
    """Two recipient queries; no fake duplicate rebound observations."""
    if len(choices) != 2 or any(type(c) is not int or c not in (0, 1, 2) for c in choices):
        raise ValueError("two valid choices required")
    delta, span = contrast_geometry(plan, types, vectors)
    return (delta[choices[0]] - delta[choices[1]]) / span


def parse_choice(raw: str) -> int | None:
    """Zero based selection, or missing. Never recover a digit from prose."""
    return int(raw.strip()) - 1 if isinstance(raw, str) and raw.strip() in ("1", "2", "3") else None


def parse_forecast(raw: str) -> tuple[float, float, float] | None:
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique_keys)
        if not isinstance(value, dict) or set(value) != {"p_a"}:
            return None
        ps = value["p_a"]
        if not isinstance(ps, dict) or set(ps) != {"1", "2", "3"}:
            return None
        numbers = tuple(ps[str(i)] for i in (1, 2, 3))
        if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in numbers):
            return None
        return tuple(float(v) for v in numbers)
    except (ValueError, TypeError):
        return None


def examples(plan: dict, random_response=False) -> list[dict]:
    bundles = []
    # One illustrative case per unordered type pair; no filtering by outcomes.
    for index, types in enumerate(((0, 1), (0, 2), (1, 2))):
        rng = random.Random(plan["seeds"]["examples"] + index)
        random_rng = random.Random(plan["seeds"]["examples"] + 1000 + index)
        aliases = plan["design"]["development_aliases"][index * 2:index * 2 + 2]
        events = []
        for cycle in range(plan["design"]["exposures_per_frame_per_participant"]):
            frames = list(range(3)); rng.shuffle(frames)
            for frame in frames:
                scenario = SCENARIOS[(cycle * 3 + frame + index) % len(SCENARIOS)]
                order = [0, 1]; rng.shuffle(order)
                for recipient in order:
                    p = probability(plan, types[recipient], [int(k == frame) for k in range(3)])
                    u = rng.random()
                    if random_response:
                        p, u = plan["target"]["p_random"], random_rng.random()
                    events.append({"participant": aliases[recipient], "decision": scenario[0],
                                   "option_a": scenario[1], "option_b": scenario[2],
                                   "message": TRAINING[frame].format(a=scenario[1]),
                                   "choice": "A" if u < p else "B", "analyst_frame": frame,
                                   "analyst_p_a": p, "analyst_uniform": u})
        bundles.append({"index": index, "aliases": aliases, "types": list(types), "events": events})
    return bundles


def history_text(bundle: dict, rebound=False, end_marker="End of records.") -> str:
    aliases = bundle["aliases"]
    exchange = dict(zip(aliases, reversed(aliases)))
    lines = ["Records of earlier interactions:"]
    for i, e in enumerate(bundle["events"], 1):
        recipient = exchange[e["participant"]] if rebound else e["participant"]
        lines += ["", f"Record {i}", f"Participant: {recipient}", f"Decision: {e['decision']}",
                  f"Option A: {e['option_a']}", f"Option B: {e['option_b']}",
                  f"Message: {e['message']}", f"Choice: Option {e['choice']}"]
    return "\n".join(lines) + "\n\n" + end_marker


def candidates(kind: str, option_a: str) -> list[str]:
    if kind == "familiar_pure":
        return [t.format(a=option_a) for t in TRAINING]
    if kind == "new_pure":
        return [f"Choose {option_a}. " + " ".join(c) for c in CLAUSES]
    if kind == "new_composite":
        groups = ((CLAUSES[0][0], CLAUSES[1][0], CLAUSES[0][1]),
                  (CLAUSES[1][1], CLAUSES[2][0], CLAUSES[1][2]),
                  (CLAUSES[2][1], CLAUSES[0][2], CLAUSES[2][2]))
        return [f"Choose {option_a}. " + " ".join(c) for c in groups]
    raise ValueError("unknown candidate kind")


def request(plan: dict, bundle: dict, recipient: str, kind: str, rebound=False, forecast=False,
            *, order=(0, 1, 2), no_history=False) -> dict:
    if recipient not in bundle["aliases"]:
        raise ValueError("unknown recipient")
    if len(order) != 3 or any(type(i) is not int for i in order) or sorted(order) != [0, 1, 2]:
        raise ValueError("candidate order must be a permutation")
    if no_history and rebound:
        raise ValueError("no history has no rebound variant")
    bank = candidates(kind, CURRENT[1])
    choices = [bank[i] for i in order]
    tail = plan["prompts"]["forecast_tail" if forecast else "choice_tail"]
    prefix = ("No earlier interaction records are available.\n\n" + plan["prompts"]["history_end"] if no_history
              else history_text(bundle, rebound, plan["prompts"]["history_end"]))
    user = prefix + "\n\n" + "\n".join([
        f"Current participant: {recipient}", f"Decision: {CURRENT[0]}",
        f"Option A: {CURRENT[1]}", f"Option B: {CURRENT[2]}", "", "Candidate messages:",
        "\n\n".join(f"{i}. {message}" for i, message in enumerate(choices, 1)), "", tail])
    return {"system": plan["prompts"]["system"], "user": user}


def audit(plan: dict) -> dict:
    if not __debug__:
        raise RuntimeError("Run without -O: this offline audit requires assertions")
    assert plan["status"] == "DESIGN_DRAFT_NOT_RUN_READY"
    assert plan["authorization"]["design_and_local_checks_only"]
    assert plan["authorization"]["old_gates_unchanged"]
    for key in ("paid_calls_allowed", "model_calls_allowed", "mechanistic_runs_allowed", "github_push_allowed"):
        assert plan["authorization"][key] is False
    assert plan["sample_plan"]["selected_confirmation_n"] is None
    assert plan["sample_plan"]["power_estimated"] is False
    assert plan["sample_plan"]["tiny_pilot_is_authorized"] is False
    assert plan["target"]["human_semantic_validation_complete"] is False
    assert plan["sample_plan"]["power_at_threshold_is_not_assumed_to_reach_80_percent"] is True
    assert set(plan["design"]["development_aliases"]).isdisjoint(plan["design"]["confirmation_aliases"])
    assert len(plan["analysis"]["primary_endpoints"]) == 2
    assert plan["analysis"]["two_sided_alpha_each"] * 2 == plan["analysis"]["familywise_alpha"]
    calls = sum(x["calls_per_bundle"] for x in plan["branches"])
    assert calls == plan["sample_plan"]["calls_per_bundle"] == 24
    for branch in plan["branches"]:
        assert branch["calls_per_bundle"] == branch["recipients"] * branch.get("history_variants", branch.get("candidate_sets"))
    assert all(n % 36 == 0 for n in plan["sample_plan"]["confirmation_grid"])
    assert plan["design"]["history_events_per_bundle"] == 2 * 3 * plan["design"]["exposures_per_frame_per_participant"]
    vectors = {
        "pure": [[int(k == f) for k in range(3)] for f in range(3)],
        "composite": [[v / plan["target"]["composite_denominator"] for v in x] for x in plan["target"]["composite_vectors"]],
    }
    cases = 0
    for types in permutations(range(3), 2):
        for bank in vectors.values():
            for order in permutations(range(3)):
                x = [bank[i] for i in order]
                opt = [max(range(3), key=lambda j: probability(plan, t, x[j])) for t in types]
                # A participant feature value table has exactly the same optimum
                # as a hidden type oracle here. This is a limitation, not a bug.
                qs = [[probability(plan, t, row) for row in vectors["pure"]] for t in types]
                feature_opt = [max(range(3), key=lambda j: sum(q[k] * x[j][k] for k in range(3))) for q in qs]
                assert feature_opt == opt
                assert abs(contrast(plan, types, x, [*opt, *reversed(opt)]) - 1) < 1e-12
                for a, b in product(range(3), repeat=2):
                    # Includes arbitrary fixed recipient biases.
                    assert abs(contrast(plan, types, x, [a, b, a, b])) < 1e-12
                lo, hi = contrast_bounds(plan, types, x, [None] * 4)
                assert abs(lo + 1) < 1e-12 and abs(hi - 1) < 1e-12
                cases += 1
    rendered = 0
    for bundle in examples(plan):
        counts = Counter((e["participant"], e["analyst_frame"]) for e in bundle["events"])
        assert len(counts) == 6 and set(counts.values()) == {4}
        assert len(bundle["events"]) == 24
        for kind in ("familiar_pure", "new_pure", "new_composite"):
            for rebound in (False, True):
                rs = [request(plan, bundle, recipient, kind, rebound) for recipient in bundle["aliases"]]
                assert rs[0]["system"] == rs[1]["system"]
                assert rs[0]["user"].split("Current participant:")[0] == rs[1]["user"].split("Current participant:")[0]
                for r in rs:
                    assert set(r) == {"system", "user"}
                    assert all(s not in r["user"] for s in ("analyst_", "hidden_type", "0.72", "0.38", "rebound"))
                    rendered += 1
    return {"status": "DESIGN_CONSISTENCY_CHECKS_PASS_NOT_A_SCIENTIFIC_GO", "analytic_cases": cases,
            "example_requests_checked": rendered, "example_histories": 3,
            "history_records_per_example": 24, "calls_per_future_bundle": calls,
            "tiny_pilot_planned_calls_not_authorized": calls * plan["sample_plan"]["tiny_pilot_bundles"],
            "confirmation_call_grid_not_authorized": {str(n): calls * n for n in plan["sample_plan"]["confirmation_grid"]},
            "participant_feature_reward_can_pass": True, "power_estimated": False,
            "model_calls": 0, "paid_calls": 0}


def example_markdown(plan: dict) -> str:
    lines = ["# Partner state study: three exact illustrative prompt bundles", "",
             "These are constructed examples, not model transcripts or a validated stimulus bank.",
             "No LLM has received them. No example was filtered for informative outcomes.",
             "Each code block contains the exact system or user text for a complete request.",
             "The first bundle also shows both rebound requests and separate transfer readouts.",
             "The other two give the two original history recipient queries.", "",
            "All examples use canonical candidate order for readability. Production must counterbalance slots.",
            "These three hand assigned alias/type cases are illustrations, not a production randomization or leakage test.", ""]
    for bundle in examples(plan):
        names = bundle["aliases"]
        mapping = ", ".join(f"{a}: {plan['target']['frames'][t]}" for a, t in zip(names, bundle["types"]))
        lines += [f"## Bundle {bundle['index'] + 1}", "", f"Analyst only initial types: {mapping}.", "",
                  "### Exact system prompt", "", "```text", plan["prompts"]["system"], "```", ""]
        conditions = [(False, a, "familiar_pure", False) for a in names]
        if bundle["index"] == 0:
            conditions += [(True, a, "familiar_pure", False) for a in names]
            conditions += [(False, names[0], "new_pure", False), (False, names[0], "new_composite", False),
                           (False, names[0], "new_composite", True)]
        for rebound, recipient, kind, forecast in conditions:
            label = "rebound" if rebound else "original"
            r = request(plan, bundle, recipient, kind, rebound, forecast)
            lines += [f"### Exact user prompt: {label}, {recipient}, {kind}, {'forecast' if forecast else 'choice'}",
                      "", "```text", r["user"], "```", ""]
        lines += ["### Analyst only candidate probabilities", "",
                  "These probabilities belong to the simulator, not to an LLM prediction. They are never sent in the request.", "",
                  "| Candidate bank | ID | Candidate 1 | Candidate 2 | Candidate 3 |",
                  "| --- | --- | ---: | ---: | ---: |"]
        for kind in ("familiar_pure", "new_pure", "new_composite"):
            vectors = ([[v / plan["target"]["composite_denominator"] for v in row] for row in plan["target"]["composite_vectors"]]
                       if kind == "new_composite" else [[int(i == j) for i in range(3)] for j in range(3)])
            for name, target in zip(names, bundle["types"]):
                ps = " | ".join(f"{probability(plan, target, row):.6f}" for row in vectors)
                lines.append(f"| {kind} | {name} | {ps} |")
        lines.append("")
        lines += ["### Analyst only outcome audit", "", "| Record | ID | Frame | P(A) | Uniform draw | Choice |",
                  "| ---: | --- | --- | ---: | ---: | --- |"]
        for i, e in enumerate(bundle["events"], 1):
            lines.append(f"| {i} | {e['participant']} | {plan['target']['frames'][e['analyst_frame']]} | {e['analyst_p_a']:.2f} | {e['analyst_uniform']:.8f} | {e['choice']} |")
        lines += ["", "Under rebound history the two type assignments exchange. Outcome and message text stay fixed.", ""]
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--examples", action="store_true")
    args = parser.parse_args(argv)
    plan = json.loads(args.plan.read_text())
    report = audit(plan)
    if args.examples:
        print(example_markdown(plan), end="")
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
