from __future__ import annotations

from collections import Counter
from copy import deepcopy
from itertools import product
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.check_partner_state_design import contrast_bounds, no_history_contrast
from src.partner_state import allocation, make_bundle, build_ledger, visible_request, integrity, reconcile, SPECS, digest, WORDING, SCENARIOS, candidate_bank
from src.partner_statistics import bootstrap_distribution, percentile_interval, bounds_from_choices, decision_batch, validity_from_choices
from src.partner_policies import simulation_geometry, simulate_choices, state_values
from src.partner_pipeline import analyze, mock_responses, history_arrays, lexical_values
from scripts.run_partner_offline import one_cell, verdict

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def plan():
    return json.loads((ROOT / "docs/partner_state_study_20260907.json").read_text())


@pytest.fixture
def screen():
    return json.loads((ROOT / "docs/partner_state_offline_20260907.json").read_text())


@pytest.fixture
def setup(plan):
    bundles = [make_bundle(plan, r, seed=44) for r in allocation(36, 22)]
    return bundles, build_ledger(plan, bundles, 7)


def test_balanced_reproducible_nested_allocation():
    rows = allocation(288, 7)
    for n in (36, 72, 144, 288):
        assert rows[:n] == allocation(n, 7)
        cells = Counter((tuple(x["types"]), tuple(x["candidate_order"])) for x in rows[:n])
        assert len(cells) == 36 and set(cells.values()) == {n//36}
    with pytest.raises(ValueError):
        allocation(37, 7)


def test_complete_ledger(setup, plan):
    bundles, ledger = setup
    assert integrity(plan, bundles, ledger)["planned_requests"] == 864
    assert set(Counter(r["bundle_id"] for r in ledger).values()) == {24}
    assert ledger == build_ledger(plan, bundles, 7)
    assert ledger != build_ledger(plan, bundles, 8)
    assert sorted(r["request_id"] for r in ledger) == sorted(r["request_id"] for r in build_ledger(plan, bundles, 8))


def test_type_change_does_not_change_schedule_words_or_names(plan):
    row = allocation(36, 8)[0]
    a = make_bundle(plan, row, seed=23)
    row["types"] = list(reversed(row["types"]))
    b = make_bundle(plan, row, seed=23)
    assert a["aliases"] == b["aliases"] and a["current"] == b["current"]
    assert a["random_events"] == b["random_events"]
    for x, y in zip(a["events"], b["events"]):
        assert all(x[k] == y[k] for k in ("participant", "decision", "option_a", "option_b", "message", "analyst_frame", "analyst_uniform"))


def test_hidden_sentinels_do_not_enter_prompt(setup, plan):
    b = setup[0][0]
    changed = deepcopy(b)
    changed["types"] = [99, 99]
    changed["secret"] = "SECRET_SENTINEL"
    for e in changed["events"] + changed["random_events"]:
        e.update(analyst_frame=99, analyst_p_a="SECRET_SENTINEL", analyst_uniform="SECRET_SENTINEL")
    for spec in SPECS:
        assert visible_request(plan, b, spec) == visible_request(plan, changed, spec)


def test_reassignment_and_recipient_are_the_only_changes(setup, plan):
    b = setup[0][0]
    specs = [s for s in SPECS if s["branch"] == "BIND"]
    prompts = [visible_request(plan, b, s)["user"] for s in specs]
    assert prompts[0].split("Current participant:")[0] == prompts[1].split("Current participant:")[0]
    changes = [(x,y) for x,y in zip(prompts[0].splitlines(), prompts[2].splitlines()) if x != y]
    assert len(changes) == 24
    assert all(x.startswith("Participant: ") and y.startswith("Participant: ") for x,y in changes)
    forecast = visible_request(plan, b, next(s for s in SPECS if s["branch"] == "FORECAST" and s["cell"] == 0))
    choice = visible_request(plan, b, next(s for s in SPECS if s["branch"] == "TRANSFER" and s["cell"] == 0))
    assert forecast["user"].removesuffix(plan["prompts"]["forecast_tail"]) == choice["user"].removesuffix(plan["prompts"]["choice_tail"])


def test_no_history_never_reads_event_data(setup, plan):
    b = deepcopy(setup[0][0])
    spec = next(s for s in SPECS if s["branch"] == "NO_HISTORY")
    clean = visible_request(plan, b, spec)
    b["events"] = b["random_events"] = None
    assert clean == visible_request(plan, b, spec)


def test_ledger_missing_duplicate_unknown_and_tampered(setup):
    _, ledger = setup
    r = {"request_id": ledger[0]["request_id"], "prompt_sha256": ledger[0]["prompt_sha256"], "raw_response": "1"}
    joined = reconcile(ledger, [r])
    assert len(joined) == len(ledger)
    assert sum(x["response_status"] == "missing" for x in joined) == len(ledger)-1
    for bad in ([r, r], [dict(r, request_id="unknown")], [dict(r, prompt_sha256="wrong")]):
        with pytest.raises(ValueError):
            reconcile(ledger, bad)


def test_exact_bootstrap_matches_exhaustive_enumeration():
    values = np.array([-.5, .75, -.25, 1.])
    strata = np.array([0,0,1,1])
    support, p = bootstrap_distribution(values, strata)
    brute = Counter()
    for first in product((0,1), repeat=2):
        for second in product((2,3), repeat=2):
            brute[np.mean(values[list(first + second)])] += 1/16
    expected = np.array([brute[x] for x in support])
    np.testing.assert_allclose(p[0], expected, atol=1e-12)
    assert np.dot(support, p[0]) == pytest.approx(values.mean())


def test_bootstrap_matches_seeded_resampling():
    rng = np.random.default_rng(54)
    values = rng.integers(-4, 5, 36)/4
    strata = np.repeat(np.arange(6), 6)
    exact = percentile_interval(values, strata, .025)[0]
    sampled = np.zeros(100000)
    for s in range(6):
        sampled += rng.choice(values[strata == s], (100000, 6)).sum(1)/36
    approx = np.quantile(sampled, [.0125,.9875])
    np.testing.assert_allclose(exact, approx, atol=.015)


@pytest.mark.parametrize("value", [-1., -.25, 0., .5, 1.])
def test_bootstrap_constant_no_aliasing(value):
    np.testing.assert_allclose(percentile_interval(np.full((2, 36), value), np.repeat(range(6), 6)), [[value, value]]*2)


def test_bootstrap_rejects_invalid_data():
    for x in ([.17, 0], [np.nan, 0], [2., 0.]):
        with pytest.raises(ValueError):
            bootstrap_distribution(x, [0,0])


def test_batched_bounds_match_original_definition(plan):
    types, _, vectors, strata = simulation_geometry(36)
    choices = np.random.default_rng(5).integers(-1, 3, (2,36,6,4))
    lo, hi = bounds_from_choices(types, vectors, choices)
    for run in range(2):
        for b in range(36):
            for j in (0,1,2,5):
                c = [None if x < 0 else int(x) for x in choices[run,b,j]]
                expected = contrast_bounds(plan, types[b].tolist(), vectors[b,j].tolist(), c)
                assert (lo[run,b,j], hi[run,b,j]) == pytest.approx(expected)
            for j in (3,4):
                cs = [(0,1,2) if x < 0 else (int(x),) for x in choices[run,b,j,:2]]
                possible = [no_history_contrast(plan, types[b].tolist(), vectors[b,j].tolist(), c) for c in product(*cs)]
                assert (lo[run,b,j],hi[run,b,j]) == pytest.approx((min(possible),max(possible)))


def test_missing_data_cannot_pass(setup, plan):
    b, ledger = setup
    result = analyze(plan, b, ledger, [])
    assert result["response_counts"] == {"missing": 864}
    assert not result["decision"]["joint_pass"]
    assert result["decision"]["mean_lower"] == [-1]*6
    assert result["decision"]["mean_upper"] == [1]*6


@pytest.mark.parametrize("policy", ["fixed_slot", "expertise", "global_reward", "global_recency", "name_bias"])
def test_global_and_name_policies_have_zero_binding(setup, plan, screen, policy):
    b, ledger = setup
    rows = mock_responses(plan, b, ledger, policy, screen["policy_parameters"])
    result = analyze(plan, b, ledger, rows)
    np.testing.assert_allclose(result["decision"]["mean_lower"][:3], 0, atol=1e-12)
    assert not result["decision"]["joint_pass"]


def test_oracle_connects_entire_pipeline(setup, plan, screen):
    b, ledger = setup
    result = analyze(plan, b, ledger, mock_responses(plan,b,ledger,"typed_history_oracle",screen["policy_parameters"]))
    assert result["decision"]["joint_pass"]
    np.testing.assert_allclose(result["decision"]["mean_lower"], [1,1,1,0,0,0])
    assert result["response_counts"] == {"valid": 864}


@pytest.mark.parametrize("scenario_index", range(12))
def test_simulation_runs_and_respects_missingness(screen, scenario_index):
    scenario = screen["scenarios"][scenario_index]
    choices, types, vectors, strata = simulate_choices(4, 36, np.random.default_rng(2), scenario, screen["policy_parameters"])
    lower, upper = bounds_from_choices(types, vectors, choices)
    result = decision_batch(lower, upper, strata, validity_from_choices(choices))
    assert result["joint_pass"].shape == (4,)
    assert np.isfinite(result["mean_lower"]).all()
    if scenario["policy"] in ("global_reward", "global_recency", "name_bias"):
        np.testing.assert_allclose(lower[:,:,:3], 0, atol=1e-12)


def test_state_belief_matches_direct_likelihood(setup, screen):
    b, _ = setup
    f,r,y = history_arrays(b)
    q = state_values(f,r,y,"static_belief",screen["policy_parameters"])
    for index in (0,4,17):
        for who in (0,1):
            likelihood = np.ones(3)
            for frame, recipient, outcome in zip(f[0,index],r[0,index],y[0,index]):
                if who == recipient:
                    p = .38 + .34 * (np.arange(3) == frame)
                    likelihood *= p if outcome else 1-p
            posterior = likelihood/likelihood.sum()
            np.testing.assert_allclose(q[0,index,who], .38+.34*posterior, atol=1e-12)


@pytest.mark.parametrize("mutation", ["id", "spec", "order", "probability", "uniform", "random_field", "random_exposure"])
def test_integrity_rejects_semantic_tampering(setup, plan, mutation):
    bundles, ledger = deepcopy(setup)
    if mutation == "id":
        ledger[0]["request_id"] += "/forged"
    elif mutation == "spec":
        # Matching prompt hash does not excuse an ID assigned to the wrong cell.
        ledger[0]["spec"] = next(s for s in SPECS if s != ledger[0]["spec"])
        ledger[0]["prompt"] = visible_request(plan, next(b for b in bundles if b["bundle_id"] == ledger[0]["bundle_id"]), ledger[0]["spec"])
        ledger[0]["prompt_sha256"] = digest(ledger[0]["prompt"])
    elif mutation == "order":
        ledger[0]["execution_index"] = 4
    elif mutation == "probability":
        bundles[0]["events"][0]["analyst_p_a"] = .123
    elif mutation == "uniform":
        bundles[0]["events"][0]["analyst_uniform"] = float("nan")
    elif mutation == "random_field":
        bundles[0]["random_events"][0]["message"] = "Altered text"
    else:
        bundles[0]["random_events"].pop()
    with pytest.raises(ValueError):
        integrity(plan, bundles, ledger)


def test_lexical_reference_ignores_hidden_fields(setup, plan):
    b = deepcopy(setup[0][0])
    spec = next(s for s in SPECS if s["branch"] == "TRANSFER")
    texts, _ = candidate_bank(plan, b, "composite")
    before = lexical_values(b, spec, texts)
    b["types"] = [99,99]
    for event in b["events"]:
        event.update(analyst_frame=99, analyst_p_a=-2)
    np.testing.assert_array_equal(before, lexical_values(b, spec, texts))


def test_exact_wording_and_scenario_split_is_disjoint(plan):
    words = {split: set(training) | {c for group in clauses for c in group} for split,(training,clauses) in WORDING.items()}
    assert not words["development"] & words["confirmation"]
    assert not set(SCENARIOS["development"]) & set(SCENARIOS["confirmation"])
    assert not set(plan["design"]["development_aliases"]) & set(plan["design"]["confirmation_aliases"])


def test_decision_cannot_rescue_with_valid_cases_or_omit_controls():
    lower = np.zeros((3,36,6))
    lower[:,:,:2] = .5
    lower[1,:,5] = .25
    validity = np.ones((3,5)); validity[2,0] = .97
    decision = decision_batch(lower, lower.copy(), np.repeat(range(6),6), validity)
    assert decision["primary_pass"].all()
    assert decision["joint_pass"].tolist() == [True,False,False]
    bad = lower.copy(); bad[0,0,2] = np.nan
    with pytest.raises(ValueError):
        decision_batch(bad, bad, np.repeat(range(6),6), validity)


def test_secondary_summaries_keep_missing_denominators(setup, plan, screen):
    b, ledger = setup
    rows = mock_responses(plan, b, ledger, "typed_history_oracle", screen["policy_parameters"])
    good = analyze(plan,b,ledger,rows)
    assert good["forecast_summaries"]["mse"] == 0
    assert good["forecast_summaries"]["pairwise_rank_agreement"] == 1
    assert good["forecast_summaries"]["choice_in_forecast_argmax_fraction"] == 1
    assert good["choice_summaries"]["branch"]["RANDOM_RESPONSE"]["expected_success_bounds"] == [.5,.5]
    missing = analyze(plan,b,ledger,[])
    assert missing["forecast_summaries"]["mse"] is None
    assert missing["forecast_summaries"]["validity"] == 0
    assert missing["choice_summaries"]["branch"]["BIND"]["planned"] == 144
    assert missing["choice_summaries"]["branch"]["BIND"]["valid"] == 0
    np.testing.assert_allclose(missing["choice_summaries"]["branch"]["BIND"]["expected_success_bounds"], [.38,.72])
    assert missing["complete_case_sensitivity"]["BIND"]["complete_bundles"] == 0


def test_cell_replay_does_not_depend_on_other_scenario_execution(screen):
    scenario = screen["scenarios"][5]
    first = one_cell(screen,scenario,36,5)
    one_cell(screen,screen["scenarios"][0],36,5)
    assert first == one_cell(screen,scenario,36,5)


def test_sample_verdict_needs_all_scenarios_and_never_authorizes(screen):
    rows = [{"scenario": s["id"], "n": 36, "joint": {"mc_ci": [.9,.95] if s["role"] != "null" else [0,.01]},
             "any_two_sided": {"mc_ci": [0,.04]}} for s in screen["scenarios"]]
    selected = verdict(screen,rows,False)
    assert selected["conditional_candidate_n"] == 36 and not selected["paid_run_authorized"]
    assert verdict(screen,rows,True)["conditional_candidate_n"] is None
    assert verdict(screen,rows[:-1],False)["conditional_candidate_n"] is None
    rows[5]["joint"]["mc_ci"][0] = .79
    assert verdict(screen,rows,False)["conditional_candidate_n"] is None
