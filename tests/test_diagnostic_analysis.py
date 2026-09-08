from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from src.diagnostic_pilot import read
from src.diagnostic_analysis import summarize
from src.partner_statistics import bounds_from_choices

ROOT=Path(__file__).resolve().parents[1]/"results/diagnostic_pilot_package_20260908"


@pytest.fixture
def setup():
    return read(ROOT/"package/packet.json"),read(ROOT/"analyst_key.json"),read(ROOT/"baseline_responses.json")


def test_all_baselines_against_original_vectorized_calculation(setup):
    packet,key,baselines=setup
    ids=packet["provenance"]["selected_bundles"]
    ar={r["request_id"]:r for r in key["requests"]}
    specs={r["request_id"]:r["spec"] for r in packet["requests"]}
    for rows in baselines.values():
        choices=np.full((1,3,6,4),-1,dtype=int);vectors=np.zeros((3,6,3,3));types=np.zeros((3,2),dtype=int)
        for r in rows:
            a=ar[r["request_id"]];s=specs[r["request_id"]];i=ids.index(a["bundle_id"])
            j={"BIND":0,"TRANSFER":1,"NEAR":2,"RANDOM_RESPONSE":5}.get(s["branch"])
            if j is None:j=3 if s["bank"]=="familiar" else 4
            cell=s["recipient"] if s["branch"]=="NO_HISTORY" else s["cell"]
            choices[0,i,j,cell]=int(r["raw_response"])-1;vectors[i,j]=a["candidate_vectors"];types[i]=a["types"]
        lo,hi=bounds_from_choices(types,vectors,choices)
        result=summarize(packet,key,rows)
        np.testing.assert_allclose(result["mean_lower"],lo.mean(1)[0],atol=1e-12)
        np.testing.assert_allclose(result["mean_upper"],hi.mean(1)[0],atol=1e-12)
        assert result["p_values"] is None and result["valid_choices"]==60


def test_missing_or_invalid_not_dropped(setup):
    p,k,b=setup
    empty=summarize(p,k,[])
    assert empty["mean_lower"]==[-1]*6 and empty["mean_upper"]==[1]*6 and empty["valid_choices"]==0
    rows=deepcopy(next(iter(b.values())));rows[0]["raw_response"]="not a digit"
    assert summarize(p,k,rows)["valid_choices"]==59


@pytest.mark.parametrize("change",["duplicate","unknown","hash"])
def test_response_mismatch_rejected(setup,change):
    p,k,b=setup;rows=deepcopy(next(iter(b.values())))
    if change=="duplicate":rows.append(rows[0])
    elif change=="unknown":rows[0]["request_id"]="unknown"
    else:rows[0]["prompt_sha256"]="altered"
    with pytest.raises(ValueError):summarize(p,k,rows)
