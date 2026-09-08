from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from src.partner_state import allocation,make_bundle,SPECS,visible_request,candidate_bank
from src.partner_pipeline import lexical_values,analyze
from src.stimulus_audit import (SHALLOW,body,features,similarity,replace_wording,audit_candidates,audit_prompt,
    audit_ledger,audit_integrity,assert_wording_only_pair,visible_history,shallow_scores,audit_responses,audit_analysis,paired_effects,text_inventory)
from scripts.audit_partner_stimuli import validate_draft

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def setup():
    plan = json.loads((ROOT/"docs/partner_state_study_20260907.json").read_text())
    draft = json.loads((ROOT/"docs/partner_wording_candidate_20260908.json").read_text())
    bundles = [make_bundle(plan,r,"confirmation",31) for r in allocation(36,3)]
    changed = replace_wording(bundles,draft)
    return plan,draft,bundles,changed


def test_draft_construction_before_outputs(setup):
    plan,draft,_,bs = setup
    validate_draft(draft)
    inv = text_inventory(plan,bs[0],draft)
    assert [x["words"] for x in inv["lengths"]["familiar"]] == [8,8,8]
    assert [x["words"] for x in inv["lengths"]["near"]] == [24,24,24]
    assert [x["words"] for x in inv["lengths"]["composite"]] == [24,24,24]
    bad = deepcopy(draft); bad["clauses"][0][0] += " Extra."
    with pytest.raises(ValueError):
        validate_draft(bad)


def test_paired_only_words_and_vectors_unchanged(setup):
    plan,draft,original,changed = setup
    assert_wording_only_pair(original,changed)
    for a,b in zip(original,changed):
        for kind in ("familiar","near","composite"):
            assert candidate_bank(plan,a,kind)[1] == audit_candidates(plan,b,kind,draft)[1]
    bad = deepcopy(changed); bad[0]["events"][0]["choice"] = "bad"
    with pytest.raises(ValueError):
        assert_wording_only_pair(original,bad)


def test_original_renderer_identical_new_prompt_complete(setup):
    plan,draft,bs,changed = setup
    for spec in SPECS:
        assert audit_prompt(plan,bs[0],spec) == visible_request(plan,bs[0],spec)
        p = audit_prompt(plan,changed[0],spec,draft)
        for text in audit_candidates(plan,changed[0],spec["bank"],draft)[0]:
            assert text in p["user"]
        assert p["system"] == plan["prompts"]["system"]


def test_hidden_metadata_ignored_by_prompt_and_shallow_policies(setup):
    plan,draft,_,bs = setup
    b = deepcopy(bs[0]); b["types"] = [99,99]; b["secret"] = "HIDDEN_SENTINEL"
    for e in b["events"]+b["random_events"]:
        e.update(analyst_frame=99,analyst_p_a="HIDDEN_SENTINEL",analyst_uniform=None)
    for spec in SPECS:
        assert audit_prompt(plan,bs[0],spec,draft) == audit_prompt(plan,b,spec,draft)
        assert visible_history(bs[0],spec) == visible_history(b,spec)
        for policy in SHALLOW:
            texts = audit_candidates(plan,b,spec["bank"],draft)[0]
            np.testing.assert_array_equal(shallow_scores(visible_history(bs[0],spec),texts,policy),shallow_scores(visible_history(b,spec),texts,policy))


def test_ledger_validated_replay_and_tampering(setup):
    plan,draft,_,bs = setup
    ledger = audit_ledger(plan,bs,7,draft)
    assert ledger == audit_ledger(plan,bs,7,draft)
    assert audit_integrity(plan,bs,ledger,draft)["planned_requests"] == 864
    bad = deepcopy(ledger); bad[0]["prompt"]["user"] += " altered"
    with pytest.raises(ValueError):
        audit_integrity(plan,bs,bad,draft)
    with pytest.raises(ValueError):
        audit_integrity(plan,bs,ledger[:-1],draft)


def test_original_jaccard_matches_existing_on_every_branch(setup):
    plan,_,bs,_ = setup
    for b in bs[:3]:
        for spec in SPECS:
            texts = candidate_bank(plan,b,spec["bank"])[0]
            np.testing.assert_allclose(shallow_scores(visible_history(b,spec),texts,"original_jaccard"),lexical_values(b,spec,texts),atol=1e-15)


@pytest.mark.parametrize("policy",SHALLOW)
def test_shallow_no_history_and_rebound(setup,policy):
    plan,draft,_,bs = setup
    texts = audit_candidates(plan,bs[0],"composite",draft)[0]
    no = next(s for s in SPECS if s["branch"] == "NO_HISTORY")
    b = deepcopy(bs[0]); b["events"] = b["random_events"] = None
    np.testing.assert_array_equal(shallow_scores(visible_history(b,no),texts,policy),[.5]*3)
    specs = [s for s in SPECS if s["branch"] == "BIND"]
    assert visible_history(bs[0],specs[0]) == visible_history(bs[0],specs[3])


def test_feature_behaviour_and_unknown_policy():
    assert body("Choose Option A; Useful words.") == "Useful words."
    assert body("Choose Option A. Useful words.") == "Useful words."
    assert features("Choose X; and the losses","content_jaccard") == {"losses"}
    assert features("Choose X; qualifications","stem_jaccard") == {"qualification"}
    assert similarity("ab cd","ab cd","character_trigram") == 1
    assert similarity("one two","one two three","length_only") == .5
    with pytest.raises(ValueError):
        shallow_scores([],[],"unknown")


def test_original_analysis_agrees_and_new_missing_guard(setup):
    plan,draft,bs,changed = setup
    ledger = audit_ledger(plan,bs,7)
    rows = audit_responses(plan,bs,ledger,"typed_history_oracle",{})
    result = audit_analysis(plan,bs,ledger,rows)
    old = analyze(plan,bs,ledger,rows)
    assert result["decisions"]["original_bootstrap"] == old["decision"]
    newledger = audit_ledger(plan,changed,7,draft)
    newrows = audit_responses(plan,changed,newledger,"typed_history_oracle",{},draft)
    new = audit_analysis(plan,changed,newledger,newrows,draft)
    assert new["decisions"] == result["decisions"]
    assert new["decisions"]["minimum_df_t"]["joint_pass"]
    assert paired_effects(result,new)["mean_lower"] == [0]*6
    missing = audit_analysis(plan,changed,newledger,[],draft)
    assert missing["response_counts"] == {"missing":864}
    for d in missing["decisions"].values():
        assert not d["joint_pass"] and d["mean_lower"] == [-1]*6 and d["mean_upper"] == [1]*6


def test_references_do_not_change_with_words(setup):
    plan,draft,bs,changed = setup
    from scripts.repair_partner_calibration import load_config
    _,cfg = load_config(ROOT/"docs/partner_repair_20260908.json")
    for policy in ("static_belief","participant_feature_reward"):
        a = audit_responses(plan,bs,audit_ledger(plan,bs,7),policy,cfg["policy_parameters"])
        b = audit_responses(plan,changed,audit_ledger(plan,changed,7,draft),policy,cfg["policy_parameters"],draft)
        assert [r["raw_response"] for r in a] == [r["raw_response"] for r in b]
