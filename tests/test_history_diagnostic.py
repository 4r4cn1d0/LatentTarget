from __future__ import annotations

from collections import Counter
import copy
import json
import math
from pathlib import Path

import numpy as np
import pytest

from src.choice_baselines import HistoryFeatures
from src.history_diagnostic import (
    FRAMES, INVARIANT_POLICIES, allocation, binomial_tail_table, build_bank,
    decision, draw_pair_differences, matched_pair_checks, paired_tests,
    policy_probabilities, recency_values, reference_inputs, render_pair,
    request_schedule, simulate_design, synthetic_recovery, wilson,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def plan():
    return json.loads((ROOT / "docs/history_diagnostic_20260907.json").read_text())


@pytest.fixture
def small_plan(plan):
    return dict(plan, n_pairs=36, n_interleavings=8, n_grid=[18, 36], n_simulations=40,
                n_recovery_simulations=20, decay_q_rates=[.1], evidence_retention=[.9],
                recent_event_windows=[5])


@pytest.fixture
def priors():
    # Tests do not depend on the real logs or their fitted outputs.
    return np.tile(np.array([.08, .22, .70]), (5, 1))


@pytest.fixture
def bank(small_plan, priors):
    return build_bank(small_plan, priors)[0]


def test_allocation_balances_every_declared_prefix(plan):
    rows = allocation(plan["n_pairs"], plan["schedule_seed"])
    for n in plan["n_grid"]:
        cells = Counter((r["focus"], tuple(r["current_slot_frames"])) for r in rows[:n])
        assert len(cells) == 18
        assert set(cells.values()) == {n // 18}
    assert rows == allocation(plan["n_pairs"], plan["schedule_seed"])
    with pytest.raises(ValueError):
        allocation(20, 1)


def test_reference_parameters_are_verified(plan):
    families = {
        "reward_learning": {"params": {"alpha": .1, "beta": 8., "stickiness": 1., "prior_power": 1.}},
        "belief_dynamic": {"params": {"hazard": .05, "beta": 8., "stickiness": 1., "prior_power": 1.}},
    }
    folds = [{"fold": i, "families": copy.deepcopy(families), "training_prior": [.1, .2, .7]} for i in range(5)]
    assert reference_inputs(folds, plan).shape == (5, 3)
    folds[0]["families"]["reward_learning"]["params"]["alpha"] = .7
    with pytest.raises(ValueError, match="differs"):
        reference_inputs(folds, plan)


def test_bank_exactly_preserves_states_and_recent_events(bank, small_plan):
    for pair in bank:
        assert all(matched_pair_checks(pair["low"], pair["high"], small_plan).values())
        features = HistoryFeatures([pair["low"], pair["high"]])
        for alpha in (0., .03, .1, .3, .7, 1.):
            np.testing.assert_array_equal(features.reward_values(alpha)[0], features.reward_values(alpha)[1])
        np.testing.assert_allclose(features.posterior(0)[0], features.posterior(0)[1], atol=1e-15)
        np.testing.assert_array_equal(features.frequency[0], features.frequency[1])
        assert pair["reference_focus_gap"] > 0


def test_bank_reproducible_not_silently_resampled(bank, small_plan, priors):
    again, pools = build_bank(small_plan, priors)
    assert bank == again
    assert len({p["pair_id"] for p in bank}) == len(bank)
    assert all(len(p["histories"]) == small_plan["n_interleavings"] for p in pools)


def test_matching_detects_tampered_reward_and_suffix(bank, small_plan):
    pair = bank[0]
    high = copy.deepcopy(pair["high"])
    high[-1][1] = 1 - high[-1][1]
    checks = matched_pair_checks(pair["low"], high, small_plan)
    assert not checks["same_recent_events"]
    assert not checks["same_within_frame_streams"]


def test_policy_invariants_and_dynamic_sensitivity(bank, priors, small_plan):
    p = policy_probabilities(bank, priors, small_plan)
    for name in INVARIANT_POLICIES:
        np.testing.assert_allclose(p[name][:, 0], p[name][:, 1], atol=1e-12)
    assert not np.allclose(p["belief_dynamic"][:, 0], p["belief_dynamic"][:, 1])
    for tensor in p.values():
        assert tensor.shape == (len(bank), 2, 3)
        assert np.isfinite(tensor).all() and (tensor > 0).all()
        np.testing.assert_allclose(tensor.sum(2), 1)


def test_recency_rule_updates_on_global_clock():
    a = [(0, 1), (1, 0), (2, 1), (0, 0)]
    b = [(1, 0), (0, 1), (2, 1), (0, 0)]
    f = HistoryFeatures([a, b])
    np.testing.assert_array_equal(f.reward_values(.1)[0], f.reward_values(.1)[1])
    assert not np.allclose(recency_values(f, "decay_q", .1, .1)[0], recency_values(f, "decay_q", .1, .1)[1])
    np.testing.assert_allclose(recency_values(HistoryFeatures([[(0, 1)]]), "decay_q", .2, .1), [[.54, .5, .5]])
    np.testing.assert_allclose(recency_values(HistoryFeatures([[(0, 1), (1, 0)]]), "discounted_evidence", .5, .1), [[.6, 1/3, .5]])
    np.testing.assert_allclose(recency_values(HistoryFeatures([[(0, 1), (1, 0)]]), "recent_window", 1, .1), [[.5, 1/3, .5]])


def test_render_uses_identical_text_events_and_current_candidates(bank, small_plan):
    prompts, audit = render_pair(bank[0], small_plan)
    for arm in ("low", "high"):
        assert set(prompts[arm]) == {"system", "user"}
        assert "Current interaction (19 of 20)" in prompts[arm]["user"]
        for forbidden in ("hidden_target_type", "reference_focus_gap", "belief_hazard", "low history", "high history"):
            assert forbidden not in prompts[arm]["user"]
    assert prompts["low"]["system"] == prompts["high"]["system"]
    assert prompts["low"]["user"].split("--- Current interaction")[1] == prompts["high"]["user"].split("--- Current interaction")[1]
    events = audit["visible_events"]
    assert Counter(json.dumps(e, sort_keys=True) for e in events["low"]) == Counter(json.dumps(e, sort_keys=True) for e in events["high"])
    assert events["low"][-3:] == events["high"][-3:]


def test_schedule_has_opaque_requests_separate_key_and_identical_shams(bank, small_plan):
    prompts, key, samples = request_schedule(bank, small_plan)
    assert len(prompts) == len(key) == len(bank) * 8 // 3
    assert len({p["request_id"] for p in prompts}) == len(prompts)
    assert all(set(p) == {"request_id", "system", "user"} for p in prompts)
    assert len(samples) == 3
    lookup = {p["request_id"]: p for p in prompts}
    shams = {}
    for row in key:
        if row["kind"] == "sham":
            shams.setdefault(row["pair_id"], []).append(lookup[row["request_id"]])
    for pair in shams.values():
        assert pair[0]["system"] == pair[1]["system"] and pair[0]["user"] == pair[1]["user"]
    assert Counter(r["focus"] for r in key if r["kind"] == "sham") == dict.fromkeys(FRAMES, len(bank) * 2 // 9)


def test_exact_tail_against_direct_enumeration():
    table = binomial_tail_table(32)
    for n in range(33):
        for k in range(n + 1):
            expected = sum(math.comb(n, j) for j in range(k, n + 1)) / (2 ** n)
            assert np.isclose(table[n, k], expected, atol=1e-15, rtol=0)
    assert table[0, 0] == 1
    assert table[6, 6] == 1/64


def test_no_discordance_never_rejects_and_expertise_only_fails_joint():
    focuses = np.tile([0, 1, 2], 18)
    zeros = paired_tests(np.zeros(54), focuses, .025)
    assert zeros["pooled_p"][0] == 1 and not zeros["joint_reject"][0]
    d = (focuses == 2).astype(int)
    result = paired_tests(d, focuses, .025)
    assert result["pooled_reject"][0] and not result["joint_reject"][0]
    all_positive = paired_tests(np.ones(54), focuses, .025)
    assert all_positive["joint_reject"][0]
    for frame in FRAMES:
        assert all_positive["focus_" + frame + "_p"][0] == 2 ** -18


@pytest.mark.parametrize("coupling", ["independent", "negative_bound"])
def test_true_null_calibration_and_pair_margin_sampling(coupling):
    focuses = np.tile([0, 1, 2], 24)
    p = np.tile([.1, .2, .7], (72, 2, 1))
    d = draw_pair_differences(p, focuses, np.random.default_rng(922), 5000, coupling, 0)
    result = paired_tests(d, focuses, .025)
    assert result["joint_reject"].mean() < .04
    assert abs(d.mean()) < .01
    all_lost = draw_pair_differences(p, focuses, np.random.default_rng(922), 10, coupling, 1)
    assert not all_lost.any()


def test_probabilities_and_sample_grid_fail_closed(bank, small_plan, priors):
    with pytest.raises(ValueError):
        draw_pair_differences(np.ones((2, 2, 3)), np.array([0, 1]), np.random.default_rng(1), 10, "independent", 0)
    p = policy_probabilities(bank, priors, small_plan)
    with pytest.raises(ValueError, match="exceeds"):
        simulate_design(bank, p, dict(small_plan, n_grid=[100]))


def test_power_recovery_and_decision_reproduce(bank, small_plan, priors):
    p = policy_probabilities(bank, priors, small_plan)
    a = simulate_design(bank, p, small_plan)
    reloaded_order = {name: p[name] for name in sorted(p)}
    b = simulate_design(bank, reloaded_order, small_plan)
    assert a == b
    assert decision(a, small_plan)["recommend_paid_run"] is False
    assert decision([], small_plan)["selected_n_for_narrow_test"] is None
    recovery = synthetic_recovery(p, small_plan)
    assert recovery == synthetic_recovery(reloaded_order, small_plan)
    for n in small_plan["n_grid"]:
        for family in p:
            assert sum(r["hits"] for r in recovery if r["n_pairs"] == n and r["generating_policy"] == family) == small_plan["n_recovery_simulations"]


def test_closed_set_recovery_detects_known_very_different_policies(plan):
    p = np.tile([.01, .01, .98], (18, 2, 1))
    q = np.tile([.98, .01, .01], (18, 2, 1))
    recovery = synthetic_recovery({"a": p, "b": q}, dict(plan, n_grid=[18], n_recovery_simulations=100))
    for family in ("a", "b"):
        assert next(r["rate"] for r in recovery if r["generating_policy"] == family and r["selected_policy"] == family) == 1
    ties = synthetic_recovery({"a": p, "b": p}, dict(plan, n_grid=[18], n_recovery_simulations=100))
    assert all(r["rate"] == 1 for r in ties if r["selected_policy"] == "unresolved_tie")


def test_wilson_edge_cases():
    assert wilson(0, 5000)["ci_hi"] < .001
    assert wilson(5000, 5000)["ci_lo"] > .999
    with pytest.raises(ValueError):
        wilson(1, 0)


def test_plan_refuses_paid_and_under_simulated_runs(tmp_path, plan):
    from scripts.design_history_diagnostic import read_plan

    path = tmp_path / "plan.json"
    path.write_text(json.dumps(dict(plan, recommend_paid_run=True)))
    with pytest.raises(ValueError, match="cannot authorize"):
        read_plan(path)
    path.write_text(json.dumps(dict(plan, n_simulations=20)))
    with pytest.raises(ValueError, match="1000"):
        read_plan(path)


def test_gzip_prompt_export_reproducible(tmp_path):
    from scripts.design_history_diagnostic import save_gzip_jsonl

    rows = [{"request_id": "abc", "system": "System", "user": "User"}]
    a, b = tmp_path / "a.gz", tmp_path / "b.gz"
    save_gzip_jsonl(a, rows)
    save_gzip_jsonl(b, rows)
    assert a.read_bytes() == b.read_bytes()


def test_cli_refuses_existing_output(tmp_path, plan):
    from scripts.design_history_diagnostic import main, sha256

    families = {
        "reward_learning": {"params": {"alpha": .1, "beta": 8., "stickiness": 1., "prior_power": 1.}},
        "belief_dynamic": {"params": {"hazard": .05, "beta": 8., "stickiness": 1., "prior_power": 1.}},
    }
    fold = tmp_path / "folds.json"
    fold.write_text(json.dumps([{"fold": i, "families": families, "training_prior": [.1, .2, .7]} for i in range(5)]))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"outputs_sha256": {"V4/fold_audit.json": sha256(fold)}}))
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(dict(plan, source_fold_audit=str(fold), source_manifest=str(manifest))))
    with pytest.raises(FileExistsError):
        main(["--plan", str(path), "--out-dir", str(tmp_path)])
