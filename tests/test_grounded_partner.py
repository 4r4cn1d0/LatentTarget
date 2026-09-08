from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from src.grounded_partner import (make_grounded,grounded_ledger,grounded_integrity,
    grounded_prompt,grounded_candidates,texts_for,fit_signs,responses,descriptives,equivalence_audit)
from src.partner_state import SPECS
from src.stimulus_audit import SHALLOW

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def setup():
    plan=json.loads((ROOT/"docs/partner_state_study_20260907.json").read_text())
    bank=json.loads((ROOT/"docs/grounded_partner_bank_20260908.json").read_text())
    bs=make_grounded(plan,bank,36,777,"development")
    return plan,bank,bs,grounded_ledger(plan,bank,bs,777)


def test_complete_balanced_grounded_ledger(setup):
    plan,bank,bs,ledger=setup
    assert grounded_integrity(plan,bank,bs,ledger)["planned_requests"]==864
    assert bs==make_grounded(plan,bank,36,777,"development")
    assert ledger==grounded_ledger(plan,bank,bs,777)
    assert len({f["id"] for s in ("development","evaluation") for f in bank[s]})==6


def test_all_facts_and_paraphrases_have_declared_dimensions(setup):
    _,bank,_,_=setup
    for split in ("development","evaluation"):
        for f in bank[split]:
            assert [len(g) for g in f["facts"]]==[3,3,3]
            assert [len(g) for g in f["paraphrases"]]==[3,3,3]
            for kind in ("familiar","near","composite"):
                t,v=texts_for(f,kind)
                assert len(set(t))==3
                np.testing.assert_allclose(np.sum(v,axis=1),1)


def test_evaluation_not_used_in_history_or_sign_fit(setup):
    plan,bank,_,_=setup
    bs=make_grounded(plan,bank,36,778,"evaluation");ledger=grounded_ledger(plan,bank,bs,778)
    assert grounded_integrity(plan,bank,bs,ledger)["diagnostic_only"]
    dev={f["id"] for f in bank["development"]};ev={f["id"] for f in bank["evaluation"]}
    assert all(b["grounded_family"] in ev for b in bs)
    assert all(e["grounded_family"] in dev for b in bs for e in b["events"])
    with pytest.raises(ValueError):fit_signs(plan,bank,bs,ledger,"character_trigram",{})


def test_hidden_metadata_does_not_enter_grounded_prompts(setup):
    plan,bank,bs,_=setup;b=deepcopy(bs[0]);b["types"]=[99,99]
    for e in b["events"]+b["random_events"]:e.update(analyst_frame=99,analyst_p_a="SECRET",analyst_uniform="SECRET")
    for s in SPECS:assert grounded_prompt(plan,bank,b,s)==grounded_prompt(plan,bank,bs[0],s)


def test_text_probabilities_and_execution_tamper_rejected(setup):
    plan,bank,bs,ledger=setup
    for field,value in (("message","Altered"),("analyst_p_a",.99),("decision","Other facts")):
        changed=deepcopy(bs);changed[0]["events"][0][field]=value
        with pytest.raises(ValueError):grounded_integrity(plan,bank,changed,ledger)
    with pytest.raises(ValueError):grounded_integrity(plan,bank,bs,ledger[:-1])


def test_oracle_and_missing_responses_are_honest(setup):
    plan,bank,bs,ledger=setup
    raw=responses(plan,bank,bs,ledger,"typed_history_oracle",{})
    d=descriptives(plan,bank,bs,ledger,raw)
    np.testing.assert_allclose(d["mean_lower"],[1,1,1,0,0,0],atol=1e-12)
    assert d["invalid_or_missing"]==0
    missing=descriptives(plan,bank,bs,ledger,[])
    assert missing["mean_lower"]==[-1]*6 and missing["mean_upper"]==[1]*6


@pytest.mark.parametrize("policy",SHALLOW)
def test_frozen_sign_fit_reproducible_and_tie_rule(setup,policy):
    plan,bank,bs,ledger=setup
    fitted=fit_signs(plan,bank,bs,ledger,policy,{})
    assert fitted==fit_signs(plan,bank,bs,ledger,policy,{})
    for k,j in (("familiar",0),("composite",1),("near",2)):
        values=fitted["development_results"]
        assert fitted["signs"][k]==(1 if values["1"]["mean_lower"][j]>=values["-1"]["mean_lower"][j] else -1)


def test_belief_and_value_observational_equivalence():
    result=equivalence_audit()
    assert result["max_probability_difference"]<1e-12
    assert result["choice_disagreements"]==0
