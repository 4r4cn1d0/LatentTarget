"""Grounded diagnostic stimuli and frozen development-fitted lexical controls.

Historical modules remain untouched. This stage makes no confirmation claim.
"""
from copy import deepcopy
import json

import numpy as np

from src.partner_state import (allocation,make_bundle,rng_for,visible_request,build_ledger,
                               candidate_bank,integrity,digest,reconcile,TYPE_PAIRS,SPECS)
from src.partner_pipeline import mock_responses
from src.partner_statistics import bounds_from_choices,validity_from_choices,METRICS
from src.stimulus_audit import shallow_scores,visible_history,SHALLOW,REFERENCES


def scenario_text(family):
    facts = [t for group in family["facts"] for t in group]
    # Scenario contains no frame labels. Keep grouping out of visible metadata.
    order = rng_for(20260908,family["id"],"fact_order").sample(facts,len(facts))
    return family["decision"]+"\nFacts about Plan A: "+" ".join(order)+"\nPlan B can start one day sooner. Its remaining features are unspecified. Both plans have the same total cost."


def texts_for(family,kind,order=(0,1,2)):
    clauses = family["facts"] if kind == "familiar" else family["paraphrases"]
    if kind in ("familiar","near"):
        groups = clauses
        vectors = np.eye(3)
    elif kind == "composite":
        groups = ((clauses[0][0],clauses[1][0],clauses[0][1]),
                  (clauses[1][1],clauses[2][0],clauses[1][2]),
                  (clauses[2][1],clauses[0][2],clauses[2][2]))
        vectors = np.array([[2,1,0],[0,2,1],[1,0,2]])/3
    else:
        raise ValueError("unknown bank")
    texts = ["Choose Plan A. "+" ".join(group) for group in groups]
    return [texts[i] for i in order],vectors[list(order)].tolist()


def make_grounded(plan,bank,n,seed,split):
    if split not in ("development","evaluation"):
        raise ValueError("unknown split")
    bundles = [make_bundle(plan,row,"confirmation",seed) for row in allocation(n,plan["seeds"]["allocation"])]
    for b in bundles:
        index = b["bundle_index"]
        current = rng_for(seed,index,"current_family").choice(bank[split])
        b["grounded_family"] = current["id"];b["audit_split"] = split
        b["current"] = [scenario_text(current),current["option_a"],current["option_b"]]
        for i,(event,control) in enumerate(zip(b["events"],b["random_events"])):
            family = rng_for(seed,index,i,"history_family").choice(bank["development"])
            frame = event["analyst_frame"]
            fields = dict(decision=scenario_text(family),option_a=family["option_a"],option_b=family["option_b"],
                          message=texts_for(family,"familiar")[0][frame],grounded_family=family["id"])
            event.update(fields);control.update(fields)
    return bundles


def grounded_candidates(bank,b,spec):
    family = next(f for f in bank[b["audit_split"]] if f["id"]==b["grounded_family"])
    return texts_for(family,spec["bank"],b["candidate_order"])


def grounded_prompt(plan,bank,b,spec):
    prompt = visible_request(plan,b,spec)
    old = "\n\n".join(f"{i}. {text}" for i,text in enumerate(candidate_bank(plan,b,spec["bank"])[0],1))
    new = "\n\n".join(f"{i}. {text}" for i,text in enumerate(grounded_candidates(bank,b,spec)[0],1))
    before,marker,after = prompt["user"].rpartition("Candidate messages:\n\n")
    tail = plan["prompts"]["forecast_tail" if spec["branch"]=="FORECAST" else "choice_tail"]
    if after != old+"\n\n"+tail or not marker:
        raise ValueError("candidate renderer mismatch")
    return dict(prompt,user=before+marker+new+"\n\n"+tail)


def grounded_ledger(plan,bank,bundles,seed):
    by_id = {b["bundle_id"]:b for b in bundles}
    ledger = build_ledger(plan,bundles,seed)
    for row in ledger:
        row["prompt"] = grounded_prompt(plan,bank,by_id[row["bundle_id"]],row["spec"])
        row["prompt_sha256"] = digest(row["prompt"])
    return ledger


def grounded_integrity(plan,bank,bundles,ledger):
    ids = {b["bundle_id"]:b for b in bundles}
    families = {f["id"]:f for split in ("development","evaluation") for f in bank[split]}
    if len(families)!=6 or len({f["id"] for f in bank["development"]} & {f["id"] for f in bank["evaluation"]}):
        raise ValueError("scenario families must be disjoint")
    for b in bundles:
        family = families[b["grounded_family"]]
        if b["current"] != [scenario_text(family),family["option_a"],family["option_b"]]:
            raise ValueError("grounded current facts changed")
        if family not in bank[b["audit_split"]]:
            raise ValueError("current split mismatch")
        for e in b["events"]+b["random_events"]:
            f = families[e["grounded_family"]]
            if f not in bank["development"] or e["decision"]!=scenario_text(f) or e["message"]!=texts_for(f,"familiar")[0][e["analyst_frame"]] or (e["option_a"],e["option_b"])!=(f["option_a"],f["option_b"]):
                raise ValueError("history facts, split or message mismatch")
    shadow = []
    for row in ledger:
        b = ids[row["bundle_id"]]
        if row["prompt"]!=grounded_prompt(plan,bank,b,row["spec"]) or row["prompt_sha256"]!=digest(row["prompt"]):
            raise ValueError("grounded prompt integrity failed")
        p = visible_request(plan,b,row["spec"])
        shadow.append(dict(row,prompt=p,prompt_sha256=digest(p)))
    return dict(integrity(plan,bundles,shadow),grounded_fact_validation="exact_source_projection",
                human_validation=False,diagnostic_only=True)


def responses(plan,bank,bundles,ledger,policy,params,signs=None):
    if policy in REFERENCES:
        return mock_responses(plan,bundles,ledger,policy,params)
    if policy not in SHALLOW:
        raise ValueError("unknown policy")
    by_id = {b["bundle_id"]:b for b in bundles};rows = []
    for row in ledger:
        b,spec = by_id[row["bundle_id"]],row["spec"]
        scores = shallow_scores(visible_history(b,spec),grounded_candidates(bank,b,spec)[0],policy)
        sign = 1 if signs is None else signs[spec["bank"]]
        if sign not in (-1,1):
            raise ValueError("invalid frozen sign")
        scores = scores if sign==1 else 1-scores
        selected = int(np.flatnonzero(scores>=scores.max()-1e-12)[0])
        raw = json.dumps({"p_a":{str(i+1):float(p) for i,p in enumerate(scores)}}) if spec["branch"]=="FORECAST" else str(selected+1)
        rows.append({"request_id":row["request_id"],"prompt_sha256":row["prompt_sha256"],"raw_response":raw,
                     "source":"synthetic_reference_policy","policy":policy,"frozen_sign":sign})
    return rows


def descriptives(plan,bank,bundles,ledger,raw):
    grounded_integrity(plan,bank,bundles,ledger)
    joined = reconcile(ledger,raw);ids = {b["bundle_id"]:i for i,b in enumerate(bundles)}
    choices = np.full((1,len(bundles),6,4),-1,dtype=int)
    vectors = np.array([[texts_for(next(f for f in bank[b["audit_split"]] if f["id"]==b["grounded_family"]),k,b["candidate_order"])[1] for k in ("familiar","composite","near","familiar","composite","familiar")] for b in bundles])
    for r in joined:
        s=r["spec"]
        if s["branch"]=="FORECAST":continue
        j={"BIND":0,"TRANSFER":1,"NEAR":2,"RANDOM_RESPONSE":5}.get(s["branch"]);cell=s["cell"]
        if s["branch"]=="NO_HISTORY":j,cell=(3 if s["bank"]=="familiar" else 4),s["recipient"]
        if r["parsed"] is not None:choices[0,ids[r["bundle_id"]],j,cell]=r["parsed"]
    lo,hi=bounds_from_choices(np.array([b["types"] for b in bundles]),vectors,choices)
    return {"status":"DESCRIPTIVE_ONLY_NOT_CONFIRMATION","n":len(bundles),"metric_order":list(METRICS),
            "mean_lower":lo.mean(1)[0].tolist(),"mean_upper":hi.mean(1)[0].tolist(),
            "bundle_lower":lo[0].tolist(),"bundle_upper":hi[0].tolist(),
            "branch_validity":validity_from_choices(choices)[0].tolist(),
            "invalid_or_missing":sum(r["parsed"] is None for r in joined)}


def fit_signs(plan,bank,bundles,ledger,policy,params):
    if any(b["audit_split"]!="development" for b in bundles):
        raise ValueError("sign fitting is restricted to development")
    results = {}
    for sign in (1,-1):
        raw = responses(plan,bank,bundles,ledger,policy,params,{k:sign for k in ("familiar","near","composite")})
        results[sign] = descriptives(plan,bank,bundles,ledger,raw)
    chosen = {k:(1 if results[1]["mean_lower"][j]>=results[-1]["mean_lower"][j] else -1)
              for k,j in (("familiar",0),("composite",1),("near",2))}
    return {"signs":chosen,"development_results":{str(k):v for k,v in results.items()},
            "fitting_split":"development","evaluation_data_used":False}


def equivalence_audit(seed=202609088,n=10000):
    rng=np.random.default_rng(seed);belief=rng.dirichlet([1,1,1],n);x=rng.dirichlet([1,1,1],(n,3))
    via_belief=.38+.34*np.einsum("nt,nkt->nk",belief,x)
    q=.38+.34*belief
    via_values=np.einsum("nt,nkt->nk",q,x)
    return {"seed":seed,"cases":n,"max_probability_difference":float(abs(via_belief-via_values).max()),
            "choice_disagreements":int((via_belief.argmax(1)!=via_values.argmax(1)).sum()),
            "interpretation":"Additive belief predictions have an exactly equivalent value table. This is not proof of either internal implementation."}
