"""Descriptive scoring of the three bundle diagnostic. No hypothesis testing."""
from collections import defaultdict

from src.diagnostic_pilot import validate_packet, digest

METRICS=("BIND","TRANSFER","NEAR","NO_HISTORY_familiar","NO_HISTORY_composite","RANDOM_RESPONSE")


def summarize(packet, analyst, responses):
    packet_sha=validate_packet(packet)
    if analyst["packet_sha256"]!=packet_sha:
        raise ValueError("analyst key belongs to another packet")
    expected={r["request_id"]:r for r in packet["requests"]}
    key={r["request_id"]:r for r in analyst["requests"]}
    if len(key)!=60 or set(key)!=set(expected):raise ValueError("analyst key is incomplete")
    found={}
    for r in responses:
        rid=r["request_id"]
        if rid not in expected or rid in found or r["prompt_sha256"]!=expected[rid]["prompt_sha256"]:
            raise ValueError("unknown, duplicate or altered response")
        if "record_sha256" in r and r["record_sha256"]!=digest({k:v for k,v in r.items() if k!="record_sha256"}):
            raise ValueError("response record changed")
        if r.get("raw_response") is not None and not isinstance(r["raw_response"],str):
            raise ValueError("raw response must be string or missing")
        found[rid]=r
    values=defaultdict(lambda:[0.,0.]);validity=defaultdict(list);details=[]
    for rid,r in expected.items():
        a=key[rid];s=r["spec"]
        if a["bundle_id"]!=r["bundle_id"] or a["spec"]!=s:raise ValueError("analyst identity differs")
        raw=found.get(rid,{}).get("raw_response")
        valid=raw in ("1","2","3")
        c=int(raw)-1 if valid else None
        t0,t1=a["types"]
        delta=[v[t0]-v[t1] for v in a["candidate_vectors"]];span=max(delta)-min(delta)
        if span<.5-1e-10:raise ValueError("degenerate diagnostic vectors")
        nohist=s["branch"]=="NO_HISTORY"
        sign=(1,-1)[s["recipient"]] if nohist else (1,-1,-1,1)[s["cell"]]
        coefficients=[sign*d/(span*(1 if nohist else 2)) for d in delta]
        metric="NO_HISTORY_"+s["bank"] if nohist else s["branch"]
        lo=hi=coefficients[c] if valid else None
        if not valid:lo,hi=min(coefficients),max(coefficients)
        values[(r["bundle_id"],metric)][0]+=lo;values[(r["bundle_id"],metric)][1]+=hi
        validity[s["branch"]].append(valid)
        details.append({"request_id":rid,"status":"valid" if valid else "missing" if rid not in found else "invalid",
                        "raw_response":raw,"selected_message":a["candidate_texts"][c] if valid else None,
                        "registered_vector":a["candidate_vectors"][c] if valid else None,
                        "simulator_expected_p_a":a["candidate_p_a"][c] if valid else None,
                        "observed_new_target_choice":None})
    bundle_ids=packet["provenance"]["selected_bundles"]
    bounds={bid:{m:values[(bid,m)] for m in METRICS} for bid in bundle_ids}
    return {"status":"DESCRIPTIVE_ONLY_NOT_CONFIRMATION","n_bundles":3,"planned_choices":60,
            "valid_choices":sum(sum(v) for v in validity.values()),"confidence_intervals":None,"p_values":None,
            "metric_order":list(METRICS),"mean_lower":[sum(bounds[b][m][0] for b in bundle_ids)/3 for m in METRICS],
            "mean_upper":[sum(bounds[b][m][1] for b in bundle_ids)/3 for m in METRICS],
            "bundle_bounds":bounds,"branch_validity":{k:sum(v)/len(v) for k,v in validity.items()},"requests":details}
