"""Frozen text audit. Shallow policies see projected words and choices only.

This is a diagnostic bank, not human semantic validation or a production split.
"""
from collections import Counter
from copy import deepcopy
from functools import lru_cache
import json
import re

import numpy as np

from src.partner_state import candidate_bank, visible_request, build_ledger, integrity, digest, reconcile, TYPE_PAIRS, WORDING
from src.partner_pipeline import mock_responses
from src.partner_statistics import METRICS, bounds_from_choices, validity_from_choices, decision_batch
from src.stratified_intervals import repaired_decision, stratified_interval

SHALLOW = ("original_jaccard", "content_jaccard", "stem_jaccard", "character_trigram", "length_only")
REFERENCES = ("static_belief", "participant_feature_reward", "typed_history_oracle")
# Fixed before policy outputs. No category content words are removed.
FUNCTION_WORDS = frozenset("a an the and or but of to for from in on at by with without as so if while when before after across through into over under up down this that these those it its is are was were be been being have has had do does did not no any all each every both either neither one our us we you your they their them he she his her who whom which what how can could may might must shall should will would let using".split())


def body(text):
    if not text.startswith("Choose "):
        return text.strip()
    separator = ";" if ";" in text else ". "
    parts = text.split(separator, 1)
    if len(parts) != 2:
        raise ValueError("recommendation prefix has no declared separator")
    return parts[1].strip()


def stem(word):
    if word.endswith("ies") and len(word) > 5:
        return word[:-3]+"y"
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word)-len(suffix) >= 3:
            return word[:-len(suffix)]
    return word


@lru_cache(maxsize=8192)
def features(text, policy):
    if policy == "original_jaccard":
        return frozenset(re.findall(r"[a-z]+", text.lower()))-frozenset("a the of to for and choose please option decision should it this".split())
    stripped = body(text)
    if policy == "length_only":
        return len(stripped.split())
    if policy == "character_trigram":
        clean = " ".join(re.findall(r"[a-z]+", stripped.lower()))
        return frozenset(clean[i:i+3] for i in range(max(0,len(clean)-2)))
    words = frozenset(re.findall(r"[a-z]+", stripped.lower()))-FUNCTION_WORDS
    if policy == "stem_jaccard":
        return frozenset(map(stem,words))
    if policy == "content_jaccard":
        return words
    raise ValueError("unknown text feature")


@lru_cache(maxsize=32768)
def similarity(a, b, policy):
    x, y = features(a,policy), features(b,policy)
    if policy == "length_only":
        return 1/(1+abs(x-y))
    return len(x & y)/max(1,len(x | y))


def replace_wording(bundles, draft):
    changed = deepcopy(bundles)
    if draft is not None:
        for b in changed:
            for event in b["events"]+b["random_events"]:
                event["message"] = draft["training"][event["analyst_frame"]].format(a=event["option_a"])
    return changed


def audit_candidates(plan, bundle, bank, draft=None):
    texts, vectors = candidate_bank(plan,bundle,bank)
    if draft is None:
        return texts,vectors
    training, clauses = draft["training"], draft["clauses"]
    if bank == "familiar":
        new = [t.format(a=bundle["current"][1]) for t in training]
    else:
        groups = clauses if bank == "near" else ((clauses[0][0],clauses[1][0],clauses[0][1]),
                     (clauses[1][1],clauses[2][0],clauses[1][2]), (clauses[2][1],clauses[0][2],clauses[2][2]))
        new = [f"Choose {bundle['current'][1]}. "+" ".join(group) for group in groups]
    return [new[i] for i in bundle["candidate_order"]],vectors


def audit_prompt(plan,bundle,spec,draft=None):
    prompt = visible_request(plan,bundle,spec)
    if draft is None:
        return prompt
    old = "\n\n".join(f"{i}. {t}" for i,t in enumerate(candidate_bank(plan,bundle,spec["bank"])[0],1))
    new = "\n\n".join(f"{i}. {t}" for i,t in enumerate(audit_candidates(plan,bundle,spec["bank"],draft)[0],1))
    tail = plan["prompts"]["forecast_tail" if spec["branch"] == "FORECAST" else "choice_tail"]
    prefix, marker, suffix = prompt["user"].rpartition("Candidate messages:\n\n")
    if not marker or suffix != old+"\n\n"+tail:
        raise ValueError("original candidate block changed")
    return dict(prompt,user=prefix+marker+new+"\n\n"+tail)


def audit_ledger(plan,bundles,seed,draft=None):
    ledger = build_ledger(plan,bundles,seed)
    by_id = bundles_by_id(bundles)
    for row in ledger:
        b = by_id[row["bundle_id"]]
        row["prompt"] = audit_prompt(plan,b,row["spec"],draft)
        row["prompt_sha256"] = digest(row["prompt"])
    return ledger


def bundles_by_id(bundles):
    return {b["bundle_id"]: b for b in bundles}


def audit_integrity(plan,bundles,ledger,draft=None):
    by_id = bundles_by_id(bundles)
    # Original validator still checks allocation, schedule, response draws,
    # branch identity and ordering, using its own original candidate renderer.
    shadow = []
    for row in ledger:
        b = by_id[row["bundle_id"]]
        if row["prompt"] != audit_prompt(plan,b,row["spec"],draft) or digest(row["prompt"]) != row["prompt_sha256"]:
            raise ValueError("audit prompt integrity failed")
        p = visible_request(plan,b,row["spec"])
        shadow.append(dict(row,prompt=p,prompt_sha256=digest(p)))
    result = integrity(plan,bundles,shadow)
    for b in bundles:
        training = WORDING[b["split"]][0] if draft is None else draft["training"]
        for event in b["events"]+b["random_events"]:
            if event["message"] != training[event["analyst_frame"]].format(a=event["option_a"]):
                raise ValueError("history wording differs from frozen bank")
    return dict(result, text_bank="original_confirmation" if draft is None else draft["id"])


def assert_wording_only_pair(original,changed):
    copy = deepcopy(changed)
    if len(original) != len(copy):
        raise ValueError("paired bundle count differs")
    for a,b in zip(original,copy):
        for field in ("events","random_events"):
            if len(a[field]) != len(b[field]):
                raise ValueError("paired history count differs")
            for x,y in zip(a[field],b[field]):
                y["message"] = x["message"]
    if original != copy:
        raise ValueError("paired bank changed more than message wording")


def visible_history(bundle,spec):
    if spec["branch"] == "NO_HISTORY":
        return []
    source = 1-spec["recipient"] if spec["rebound"] else spec["recipient"]
    who = bundle["aliases"][source]
    events = bundle["random_events" if spec["branch"] == "RANDOM_RESPONSE" else "events"]
    return [{"message": e["message"], "choice": e["choice"]} for e in events if e["participant"] == who]


def shallow_scores(history,texts,policy):
    if policy not in SHALLOW:
        raise ValueError("unknown shallow policy")
    scores = []
    for text in texts:
        total,success = 2.,1.
        for event in history:
            w = similarity(text,event["message"],policy)
            total += w; success += w*(event["choice"] == "A")
        scores.append(success/total)
    return np.array(scores)


def audit_responses(plan,bundles,ledger,policy,params,draft=None):
    if policy in REFERENCES:
        # These references use annotated vectors, not the original text.
        return mock_responses(plan,bundles,ledger,policy,params)
    if policy not in SHALLOW:
        raise ValueError("unknown audit policy")
    by_id = bundles_by_id(bundles)
    rows = []
    for item in ledger:
        b,spec = by_id[item["bundle_id"]],item["spec"]
        texts,_ = audit_candidates(plan,b,spec["bank"],draft)
        scores = shallow_scores(visible_history(b,spec),texts,policy)
        selected = int(np.flatnonzero(scores >= scores.max()-1e-12)[0])
        raw = json.dumps({"p_a": {str(i+1): float(p) for i,p in enumerate(scores)}}) if spec["branch"] == "FORECAST" else str(selected+1)
        rows.append({"request_id": item["request_id"], "prompt_sha256": item["prompt_sha256"],
                     "raw_response": raw, "source": "synthetic_reference_policy", "policy": policy})
    return rows


def audit_analysis(plan,bundles,ledger,responses,draft=None):
    audit_integrity(plan,bundles,ledger,draft)
    joined = reconcile(ledger,responses)
    ids = {b["bundle_id"]: i for i,b in enumerate(bundles)}
    choices = np.full((1,len(bundles),6,4),-1,dtype=int)
    types = np.array([b["types"] for b in bundles])
    strata = np.array([TYPE_PAIRS.index(tuple(t)) for t in types])
    vectors = np.array([[audit_candidates(plan,b,k,draft)[1] for k in
                         ("familiar","composite","near","familiar","composite","familiar")] for b in bundles])
    diagnostics = []
    for row in joined:
        spec = row["spec"]; index = ids[row["bundle_id"]]; b = bundles[index]
        source = 1-spec["recipient"] if spec["rebound"] else spec["recipient"]
        ps = .38+.34*np.array(audit_candidates(plan,b,spec["bank"],draft)[1])[:,b["types"][source]]
        if spec["branch"] == "RANDOM_RESPONSE":
            ps[:] = .5
        diagnostics.append({"request_id": row["request_id"], "response_status": row["response_status"],
                            "analyst_target_probabilities": ps.tolist(), "parsed": row["parsed"]})
        if spec["branch"] == "FORECAST":
            continue
        j = {"BIND":0,"TRANSFER":1,"NEAR":2,"RANDOM_RESPONSE":5}.get(spec["branch"])
        cell = spec["cell"]
        if spec["branch"] == "NO_HISTORY":
            j,cell = (3 if spec["bank"] == "familiar" else 4),spec["recipient"]
        if row["parsed"] is not None:
            choices[0,index,j,cell] = row["parsed"]
    lo,hi = bounds_from_choices(types,vectors,choices)
    valid = validity_from_choices(choices)
    methods = {"original_bootstrap": decision_batch(lo,hi,strata,valid),
               "minimum_df_t": repaired_decision(lo,hi,strata,valid)}
    return {"status": "SYNTHETIC_TEXT_AUDIT_NOT_LLM_RESULT", "independent_bundles": len(bundles),
            "planned_requests": len(ledger), "response_counts": dict(Counter(r["response_status"] for r in joined)),
            "metric_order": list(METRICS), "strata": strata.tolist(), "branch_validity": valid[0].tolist(),
            "bundle_contrast_lower": lo[0].tolist(), "bundle_contrast_upper": hi[0].tolist(),
            "decisions": {m: {k:v[0].tolist() for k,v in d.items()} for m,d in methods.items()},
            "diagnostics": diagnostics, "provider_calls": 0}


def paired_effects(original,candidate):
    if original["strata"] != candidate["strata"] or original["planned_requests"] != candidate["planned_requests"]:
        raise ValueError("unpaired analyses")
    lo = np.asarray(candidate["bundle_contrast_lower"])-original["bundle_contrast_upper"]
    hi = np.asarray(candidate["bundle_contrast_upper"])-original["bundle_contrast_lower"]
    strata = original["strata"]
    return {"direction": "candidate_minus_original", "descriptive_not_a_selection_test": True,
            "multiplicity_adjusted_across_policies": False, "mean_lower": lo.mean(0).tolist(),
            "mean_upper": hi.mean(0).tolist(),
            "outer_ci": [[float(stratified_interval(lo[:,j],strata,.025 if j<2 else .05)[0,0]),
                          float(stratified_interval(hi[:,j],strata,.025 if j<2 else .05)[0,1])] for j in range(6)]}


def text_inventory(plan,bundle,draft=None):
    canonical = dict(bundle,candidate_order=[0,1,2])
    training = audit_candidates(plan,canonical,"familiar",draft)[0]
    banks = {k:audit_candidates(plan,canonical,k,draft)[0] for k in ("familiar","near","composite")}
    lengths = {k:[{"words":len(body(t).split()),"characters":len(body(t)),"complete_text":t} for t in texts] for k,texts in banks.items()}
    matrices = {policy:{k:[[similarity(query,t,policy) for t in training] for query in texts] for k,texts in banks.items()} for policy in SHALLOW}
    overlaps = {k:[[sorted(features(query,"content_jaccard") & features(t,"content_jaccard")) for t in training] for query in texts] for k,texts in banks.items()}
    return {"canonical_slot_frame_order":["fairness","risk","expertise"],"lengths":lengths,
            "candidate_by_training_similarity":matrices,"exact_content_overlaps":overlaps,
            "word_counts_are_not_model_token_counts":True}
