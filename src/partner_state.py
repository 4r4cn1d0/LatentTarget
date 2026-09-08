"""Offline partner study: balanced allocation, explicit prompt projection, ledger.

No provider or credentials. These generated stimuli still require human validation.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
from itertools import permutations
import json
import random

import numpy as np

from scripts.check_partner_state_design import (
    TRAINING, CLAUSES, probability, parse_choice, parse_forecast,
)

TYPE_PAIRS = tuple(permutations(range(3), 2))
ORDERS = tuple(permutations(range(3)))
BRANCHES = ("BIND", "NEAR", "TRANSFER", "FORECAST", "NO_HISTORY", "RANDOM_RESPONSE")
# Distinct neutral scenario families, neither conditions nor type enters selection.
SCENARIOS = {
    "development": (
        ("Choose a room for a reading group.", "Cedar Room", "Willow Room"),
        ("Choose a name for a community newsletter.", "Harbour Notes", "Town Pages"),
        ("Choose a meeting time for a planning session.", "Tuesday morning", "Thursday morning"),
    ),
    "confirmation": (
        ("Choose a label for a shared folder.", "Maple", "Coral"),
        ("Choose a cover for a local event booklet.", "the striped cover", "the dotted cover"),
        ("Choose a display order for two noticeboards.", "the north board first", "the south board first"),
    ),
}
WORDING = {
    "development": (TRAINING, CLAUSES),
    "confirmation": (
        ("Choose {a}; every person deserves an impartial hearing.",
         "Choose {a}; prevent a small problem from becoming a serious loss.",
         "Choose {a}; a careful assessment by qualified people should guide the decision."),
        (("Consider each person's interests on equal terms.", "Do not give one group special privileges.", "Treat contributions with reciprocal consideration."),
         ("Retain a way to reverse course if necessary.", "Reduce the consequences of an unexpected failure.", "Avoid exposing the group to unnecessary losses."),
         ("Seek advice from people who understand the subject.", "Let relevant qualifications inform the choice.", "Check the reasoning against a systematic evaluation.")),
    ),
}


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def rng_for(seed: int, *keys) -> random.Random:
    return random.Random(int(digest([seed, *keys]), 16))


def allocation(n: int, seed: int) -> list[dict]:
    if type(n) is not int or n <= 0 or n % 36:
        raise ValueError("N must be a positive multiple of 36")
    rows = []
    for block in range(n // 36):
        cells = [(t, o) for t in TYPE_PAIRS for o in ORDERS]
        rng_for(seed, "allocation", block).shuffle(cells)
        for types, order in cells:
            rows.append({"bundle_index": len(rows), "block": block,
                         "types": list(types), "candidate_order": list(order)})
    return rows


def make_bundle(plan: dict, row: dict, split="development", seed=0) -> dict:
    if split not in SCENARIOS or tuple(row["types"]) not in TYPE_PAIRS:
        raise ValueError("unknown split or type assignment")
    index = row["bundle_index"]
    aliases = rng_for(seed, split, index, "names").sample(plan["design"][f"{split}_aliases"], 2)
    schedule = rng_for(seed, split, index, "schedule")
    outcome_rng = rng_for(seed, split, index, "typed_outcomes")
    control_rng = rng_for(seed, split, index, "random_outcomes")
    content = rng_for(seed, split, index, "content")
    current = list(content.choice(SCENARIOS[split]))
    events, control = [], []
    for _ in range(plan["design"]["exposures_per_frame_per_participant"]):
        frames = schedule.sample(range(3), 3)
        for frame in frames:
            scenario = content.choice(SCENARIOS[split])
            for who in schedule.sample(range(2), 2):
                p = probability(plan, row["types"][who], np.eye(3)[frame].tolist())
                u = outcome_rng.random()
                event = {"participant": aliases[who], "decision": scenario[0], "option_a": scenario[1],
                         "option_b": scenario[2], "message": WORDING[split][0][frame].format(a=scenario[1]),
                         "choice": "A" if u < p else "B", "analyst_frame": frame,
                         "analyst_p_a": p, "analyst_uniform": u}
                events.append(event)
                random_u = control_rng.random()
                control.append(dict(event, analyst_p_a=plan["target"]["p_random"], analyst_uniform=random_u,
                                    choice="A" if random_u < plan["target"]["p_random"] else "B"))
    return dict(deepcopy(row), bundle_id=f"{split}-{index:05d}", split=split, aliases=aliases,
                events=events, random_events=control, current=current, seed=seed,
                stimulus_status="PROTOTYPE_NOT_HUMAN_VALIDATED")


def candidate_bank(plan: dict, bundle: dict, bank: str) -> tuple[list[str], list[list[float]]]:
    option_a = bundle["current"][1]
    training, clauses = WORDING[bundle["split"]]
    if bank == "familiar":
        texts, vectors = [t.format(a=option_a) for t in training], np.eye(3).tolist()
    else:
        # Same clause inventory in NEAR and TRANSFER, different grouping.
        if bank == "near":
            groups = clauses
            vectors = np.eye(3).tolist()
        elif bank == "composite":
            groups = ((clauses[0][0], clauses[1][0], clauses[0][1]),
                      (clauses[1][1], clauses[2][0], clauses[1][2]),
                      (clauses[2][1], clauses[0][2], clauses[2][2]))
            vectors = (np.array(plan["target"]["composite_vectors"]) / plan["target"]["composite_denominator"]).tolist()
        else:
            raise ValueError("unknown candidate bank")
        texts = [f"Choose {option_a}. " + " ".join(group) for group in groups]
    order = bundle["candidate_order"]
    if tuple(order) not in ORDERS:
        raise ValueError("invalid candidate permutation")
    return [texts[i] for i in order], [vectors[i] for i in order]


def request_specs() -> list[dict]:
    specs = []
    for branch in BRANCHES:
        if branch == "NO_HISTORY":
            cases = [(False, who, bank) for bank in ("familiar", "composite") for who in range(2)]
        else:
            bank = {"BIND": "familiar", "NEAR": "near", "TRANSFER": "composite", "FORECAST": "composite",
                    "RANDOM_RESPONSE": "familiar"}[branch]
            cases = [(rebound, who, bank) for rebound in (False, True) for who in range(2)]
        for cell, (rebound, who, bank) in enumerate(cases):
            specs.append(dict(branch=branch, cell=cell, rebound=rebound, recipient=who, bank=bank))
    return specs


SPECS = request_specs()


def visible_request(plan: dict, bundle: dict, spec: dict) -> dict:
    """Only explicit visible fields enter the request. Never serialize a bundle."""
    branch, rebound, who = spec["branch"], spec["rebound"], spec["recipient"]
    if spec not in SPECS:
        raise ValueError("request not in declared schedule")
    names = bundle["aliases"]
    if branch == "NO_HISTORY":
        lines = ["No earlier interaction records are available."]
    else:
        lines = ["Records of earlier interactions:"]
        events = bundle["random_events"] if branch == "RANDOM_RESPONSE" else bundle["events"]
        exchange = dict(zip(names, reversed(names)))
        for index, event in enumerate(events, 1):
            name = exchange[event["participant"]] if rebound else event["participant"]
            lines.extend(["", f"Record {index}", f"Participant: {name}", f"Decision: {event['decision']}",
                          f"Option A: {event['option_a']}", f"Option B: {event['option_b']}",
                          f"Message: {event['message']}", f"Choice: Option {event['choice']}"])
    lines += ["", plan["prompts"]["history_end"], "", f"Current participant: {names[who]}",
              f"Decision: {bundle['current'][0]}", f"Option A: {bundle['current'][1]}",
              f"Option B: {bundle['current'][2]}", "", "Candidate messages:", ""]
    texts, _ = candidate_bank(plan, bundle, spec["bank"])
    lines += ["\n\n".join(f"{i}. {message}" for i, message in enumerate(texts, 1)), "",
              plan["prompts"]["forecast_tail" if branch == "FORECAST" else "choice_tail"]]
    return {"system": plan["prompts"]["system"], "user": "\n".join(lines)}


def build_ledger(plan: dict, bundles: list[dict], execution_seed=0) -> list[dict]:
    if len({b["bundle_id"] for b in bundles}) != len(bundles):
        raise ValueError("duplicate bundle ID")
    ledger = []
    for bundle in bundles:
        for spec in SPECS:
            prompt = visible_request(plan, bundle, spec)
            ledger.append({"request_id": f"{bundle['bundle_id']}/{spec['branch']}/{spec['cell']}",
                           "bundle_id": bundle["bundle_id"], "spec": dict(spec),
                           "prompt": prompt, "prompt_sha256": digest(prompt)})
    rng_for(execution_seed, "request_order").shuffle(ledger)
    for index, item in enumerate(ledger):
        item["execution_index"] = index
    return ledger


def reconcile(ledger: list[dict], responses: list[dict]) -> list[dict]:
    """Missing requests survive; unknown/duplicate IDs and altered prompts fail."""
    expected = {r["request_id"]: r for r in ledger}
    if len(expected) != len(ledger):
        raise ValueError("duplicate planned request")
    found = {}
    for row in responses:
        rid = row["request_id"]
        if rid not in expected or rid in found:
            raise ValueError("unknown or duplicate response ID")
        if row["prompt_sha256"] != expected[rid]["prompt_sha256"]:
            raise ValueError("response prompt hash mismatch")
        if not isinstance(row.get("raw_response"), str):
            raise ValueError("raw response must be text")
        found[rid] = row
    result = []
    for item in ledger:
        response = found.get(item["request_id"])
        raw = response["raw_response"] if response else None
        parsed = parse_forecast(raw) if item["spec"]["branch"] == "FORECAST" else parse_choice(raw)
        result.append(dict(item, raw_response=raw, parsed=parsed,
                           response_status="missing" if response is None else "valid" if parsed is not None else "invalid"))
    return result


def integrity(plan: dict, bundles: list[dict], ledger: list[dict]) -> dict:
    by_id = {b["bundle_id"]: b for b in bundles}
    if len(by_id) != len(bundles):
        raise ValueError("duplicate bundle ID")
    counts = Counter((tuple(b["types"]), tuple(b["candidate_order"])) for b in bundles)
    if len(bundles) % 36 or len(counts) != 36 or len(set(counts.values())) != 1:
        raise ValueError("allocation is not balanced")
    for b in bundles:
        if tuple(b["types"]) not in TYPE_PAIRS or tuple(b["candidate_order"]) not in ORDERS or len(set(b["aliases"])) != 2:
            raise ValueError("invalid bundle assignment")
        expected_exposures = {(name, frame) for name in b["aliases"] for frame in range(3)}
        for field in ("events", "random_events"):
            exposures = Counter((e["participant"], e["analyst_frame"]) for e in b[field])
            if len(b[field]) != 24 or set(exposures) != expected_exposures or set(exposures.values()) != {4}:
                raise ValueError("wrong history exposure counts")
            for e in b[field]:
                who = b["aliases"].index(e["participant"])
                expected_p = (plan["target"]["p_random"] if field == "random_events" else
                              probability(plan, b["types"][who], np.eye(3)[e["analyst_frame"]].tolist()))
                if e["analyst_p_a"] != expected_p or not 0 <= e["analyst_uniform"] < 1:
                    raise ValueError("invalid probability or sampling draw")
                if e["choice"] != ("A" if e["analyst_uniform"] < expected_p else "B"):
                    raise ValueError("sampling audit failed")
        shared = ("participant", "decision", "option_a", "option_b", "message", "analyst_frame")
        if any(any(a[k] != c[k] for k in shared) for a,c in zip(b["events"], b["random_events"])):
            raise ValueError("random control changed nonresponse fields")
    if len(ledger) != 24 * len(bundles) or len({r["request_id"] for r in ledger}) != len(ledger):
        raise ValueError("missing or duplicate planned request")
    expected_ids = {f"{b['bundle_id']}/{s['branch']}/{s['cell']}" for b in bundles for s in SPECS}
    if {r["request_id"] for r in ledger} != expected_ids:
        raise ValueError("planned request set differs from declared schedule")
    for index, row in enumerate(ledger):
        spec = row["spec"]
        if row["bundle_id"] not in by_id or spec not in SPECS or row["request_id"] != f"{row['bundle_id']}/{spec['branch']}/{spec['cell']}":
            raise ValueError("request ID does not identify its declared cell")
        if row["execution_index"] != index:
            raise ValueError("execution order is not contiguous")
        if row["prompt"] != visible_request(plan, by_id[row["bundle_id"]], row["spec"]) or digest(row["prompt"]) != row["prompt_sha256"]:
            raise ValueError("prompt integrity failed")
    return {"bundles": len(bundles), "balanced_cells": len(counts), "planned_requests": len(ledger),
            "human_semantic_validation": False, "production_message_split_validated": False}
