"""Connect the offline ledger, mathematical mock policies and full analysis."""
from __future__ import annotations

from collections import Counter
import json
import re

import numpy as np

from src.partner_state import BRANCHES, TYPE_PAIRS, candidate_bank, digest, reconcile, integrity
from src.partner_policies import POLICIES, state_values
from src.partner_statistics import METRICS, bounds_from_choices, validity_from_choices, decision_batch
from src.partner_reporting import choice_summaries, forecast_summaries, complete_case_sensitivity


def history_arrays(bundles, random_response=False):
    frames, recipients, outcomes = [], [], []
    for b in bundles:
        events = b["random_events" if random_response else "events"]
        frames.append([e["analyst_frame"] for e in events])
        recipients.append([b["aliases"].index(e["participant"]) for e in events])
        outcomes.append([e["choice"] == "A" for e in events])
    return tuple(np.asarray(x)[None, ...] for x in (frames, recipients, outcomes))


def lexical_values(bundle, spec, texts):
    if spec["branch"] == "NO_HISTORY":
        return np.full(3, .5)
    source = 1-spec["recipient"] if spec["rebound"] else spec["recipient"]
    who = bundle["aliases"][source]
    events = bundle["random_events" if spec["branch"] == "RANDOM_RESPONSE" else "events"]
    stop = set("a the of to for and choose please option decision should it this".split())
    tokenize = lambda t: set(re.findall(r"[a-z]+", t.lower())) - stop
    result = []
    for text in texts:
        query = tokenize(text)
        total, success = 2., 1.  # Beta(1,1) smoothing with similarity weights.
        for event in events:
            if event["participant"] != who:
                continue
            tokens = tokenize(event["message"])
            weight = len(query & tokens) / max(1, len(query | tokens))
            total += weight
            success += weight * (event["choice"] == "A")
        result.append(success / total)
    return np.array(result)


def mock_responses(plan, bundles, ledger, policy, params):
    if policy not in (*POLICIES, "lexical_retrieval", "typed_history_oracle"):
        raise ValueError("unknown mock policy")
    indices = {b["bundle_id"]: i for i, b in enumerate(bundles)}
    regular = policy in POLICIES
    if regular:
        q = state_values(*history_arrays(bundles), policy, params)[0]
        random_q = state_values(*history_arrays(bundles, True), policy, params)[0]
    rows = []
    for item in ledger:
        index = indices[item["bundle_id"]]
        b, spec = bundles[index], item["spec"]
        texts, vectors = candidate_bank(plan, b, spec["bank"])
        vectors = np.array(vectors)
        who = spec["recipient"]
        source = 1-who if spec["rebound"] else who
        if policy == "lexical_retrieval":
            scores = lexical_values(b, spec, texts)
        elif policy == "typed_history_oracle":
            scores = (np.full(3, .5) if spec["branch"] in ("NO_HISTORY", "RANDOM_RESPONSE")
                      else .38 + .34 * vectors[:, b["types"][source]])
        else:
            values = random_q[index, source] if spec["branch"] == "RANDOM_RESPONSE" else q[index, source]
            if spec["branch"] == "NO_HISTORY":
                values = np.full(3, .5)
            scores = values[vectors.argmax(1)] if policy == "participant_reward" else vectors @ values
        selected = int(np.flatnonzero(scores >= scores.max() - 1e-12)[0])
        if policy == "fixed_slot":
            selected = 0
        elif policy == "name_bias":
            selected = int(digest(b["aliases"][who]), 16) % 3
        elif policy == "uniform":
            selected = int(digest([b["seed"], item["request_id"], policy]), 16) % 3
        raw = json.dumps({"p_a": {str(j+1): float(p) for j, p in enumerate(scores)}}) if spec["branch"] == "FORECAST" else str(selected+1)
        rows.append({"request_id": item["request_id"], "prompt_sha256": item["prompt_sha256"],
                     "raw_response": raw, "source": "synthetic_reference_policy", "policy": policy})
    return rows


def analyze(plan, bundles, ledger, responses):
    integrity(plan, bundles, ledger)
    reconciled = reconcile(ledger, responses)
    ids = {b["bundle_id"]: i for i, b in enumerate(bundles)}
    choices = np.full((1, len(bundles), 6, 4), -1, dtype=int)
    vectors = []
    for b in bundles:
        banks = [candidate_bank(plan, b, kind)[1] for kind in ("familiar", "composite", "near", "familiar", "composite", "familiar")]
        vectors.append(banks)
    diagnostics = []
    choices_by_cell = {(r["bundle_id"], r["spec"]["cell"]): r["parsed"] for r in reconciled if r["spec"]["branch"] == "TRANSFER"}
    for row in reconciled:
        spec = row["spec"]
        bi = ids[row["bundle_id"]]; b = bundles[bi]
        branch, cell = spec["branch"], spec["cell"]
        if branch == "FORECAST":
            ps = .38 + .34 * np.array(candidate_bank(plan, b, "composite")[1])[:, b["types"][1-spec["recipient"] if spec["rebound"] else spec["recipient"]]]
            diagnostics.append({"branch": branch, "bundle_id": b["bundle_id"], "cell": cell,
                                "valid": row["parsed"] is not None, "response_status": row["response_status"],
                                "forecast": row["parsed"], "probabilities": ps.tolist(),
                                "prior_mse": float(np.mean((.38+.34/3-ps)**2)),
                                "choice_slot": choices_by_cell[(b["bundle_id"], cell)],
                                "forecast_mse": None if row["parsed"] is None else float(np.mean((row["parsed"] - ps)**2))})
            continue
        metric = {"BIND": 0, "TRANSFER": 1, "NEAR": 2, "RANDOM_RESPONSE": 5}.get(branch)
        if branch == "NO_HISTORY":
            metric, cell = (3 if spec["bank"] == "familiar" else 4), spec["recipient"]
        if row["parsed"] is not None:
            choices[0, bi, metric, cell] = row["parsed"]
        current_type = b["types"][1-spec["recipient"] if spec["rebound"] else spec["recipient"]]
        probabilities = .38 + .34 * np.array(vectors[bi][metric])[:, current_type]
        if branch == "RANDOM_RESPONSE":
            probabilities[:] = .5
        success = None if row["parsed"] is None else float(probabilities[row["parsed"]])
        diagnostics.append({"branch": branch, "bundle_id": b["bundle_id"], "cell": spec["cell"],
                            "recipient": b["aliases"][spec["recipient"]], "target_type": current_type,
                            "scenario": b["current"][0], "candidate_order": b["candidate_order"],
                            "candidate_slot": row["parsed"], "response_status": row["response_status"],
                            "expected_success": success, "expected_success_lower": float(probabilities.min()) if success is None else success,
                            "expected_success_upper": float(probabilities.max()) if success is None else success,
                            "regret_lower": 0. if success is None else float(probabilities.max()-success),
                            "regret_upper": float(np.ptp(probabilities)) if success is None else float(probabilities.max()-success)})
    types = np.array([b["types"] for b in bundles])
    strata = np.array([TYPE_PAIRS.index(tuple(t)) for t in types])
    lower, upper = bounds_from_choices(types, np.array(vectors), choices)
    valid = validity_from_choices(choices)
    decision = decision_batch(lower, upper, strata, valid)
    converted = {k: v[0].tolist() if hasattr(v[0], "tolist") else bool(v[0]) for k, v in decision.items()}
    return {"status": "ANALYSIS_COMPLETE_NOT_DEPLOYMENT_APPROVAL", "independent_bundles": len(bundles),
            "planned_requests": len(ledger), "response_counts": dict(Counter(r["response_status"] for r in reconciled)),
            "metric_order": list(METRICS), "branch_validity_order": ["BIND", "NEAR", "TRANSFER", "NO_HISTORY", "RANDOM_RESPONSE"],
            "branch_validity": valid[0].tolist(), "decision": converted,
            "bundle_contrast_lower": lower[0].tolist(), "bundle_contrast_upper": upper[0].tolist(),
            "diagnostics": diagnostics,
            "choice_summaries": choice_summaries(diagnostics),
            "forecast_summaries": forecast_summaries(diagnostics),
            "complete_case_sensitivity": complete_case_sensitivity(lower, upper, strata),
            "all_supplied_responses_marked_synthetic": bool(responses) and all(r.get("source") == "synthetic_reference_policy" for r in responses),
            "provider_calls_by_this_function": 0}
