from __future__ import annotations

from collections import Counter
import copy
from itertools import permutations, product
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.check_partner_state_design import (
    PLAN, audit, candidates, contrast, contrast_bounds, example_markdown,
    examples, history_text, no_history_contrast, parse_choice, parse_forecast,
    probability, request,
)

ROOT = Path(__file__).resolve().parents[1]
PURE = [[int(i == j) for i in range(3)] for j in range(3)]


@pytest.fixture
def plan():
    return json.loads(PLAN.read_text())


def test_audit_is_not_a_scientific_or_paid_go(plan):
    report = audit(plan)
    assert report["analytic_cases"] == 72
    assert report["example_requests_checked"] == 36
    assert report["model_calls"] == report["paid_calls"] == 0
    assert report["participant_feature_reward_can_pass"]
    assert not report["power_estimated"]
    assert "NOT_A_SCIENTIFIC_GO" in report["status"]


@pytest.mark.parametrize("key", ["paid_calls_allowed", "model_calls_allowed", "mechanistic_runs_allowed", "github_push_allowed"])
def test_audit_refuses_silent_authorization_changes(plan, key):
    plan["authorization"][key] = True
    with pytest.raises(AssertionError):
        audit(plan)


def test_audit_refuses_optimized_python():
    result = subprocess.run([sys.executable, "-O", str(ROOT / "scripts/check_partner_state_design.py")],
                            capture_output=True, text=True, cwd=ROOT)
    assert result.returncode != 0
    assert "Run without -O" in result.stderr


@pytest.mark.parametrize("target", range(3))
def test_target_logic_and_composite_fraction(plan, target):
    assert probability(plan, target, PURE[target]) == pytest.approx(.72)
    assert probability(plan, target, PURE[(target + 1) % 3]) == pytest.approx(.38)
    assert probability(plan, target, [1/3] * 3) == pytest.approx(.38 + .34 / 3)


@pytest.mark.parametrize("vector", [[1, 1, 0], [-1, 1, 1], [1, 0], [float("nan"), 0, 1],
                                    [float("inf"), 0, 0], [True, 0, 0], ["1", 0, 0]])
def test_invalid_vectors_rejected(plan, vector):
    with pytest.raises(ValueError):
        probability(plan, 0, vector)


@pytest.mark.parametrize("target", [-1, 3, True, 0.0])
def test_invalid_type_rejected(plan, target):
    with pytest.raises(ValueError):
        probability(plan, target, PURE[0])


@pytest.mark.parametrize("value", [float("nan"), 1.1, -.1, True, .2])
def test_invalid_probability_parameters_rejected(plan, value):
    plan["target"]["p_match"] = value
    with pytest.raises(ValueError):
        probability(plan, 0, PURE[0])


@pytest.mark.parametrize("types", list(permutations(range(3), 2)))
def test_contrast_sign_bounds_positions_and_invariance(plan, types):
    composites = [[v / 3 for v in row] for row in plan["target"]["composite_vectors"]]
    for bank in (PURE, composites):
        for order in permutations(range(3)):
            vectors = [bank[i] for i in order]
            best = [max(range(3), key=lambda c: probability(plan, t, vectors[c])) for t in types]
            assert contrast(plan, types, vectors, [*best, *reversed(best)]) == pytest.approx(1)
            assert contrast(plan, types, vectors, [*reversed(best), *best]) == pytest.approx(-1)
            for a, b in product(range(3), repeat=2):
                assert contrast(plan, types, vectors, [a, b, a, b]) == pytest.approx(0)
            assert contrast_bounds(plan, types, vectors, [None] * 4) == pytest.approx((-1, 1))
            for choices in product(range(3), repeat=4):
                assert -1 - 1e-12 <= contrast(plan, types, vectors, choices) <= 1 + 1e-12


def test_reward_table_and_beliefs_are_observationally_equivalent(plan):
    for belief in ([.2, .3, .5], [1., 0., 0.], [1/3] * 3):
        q = [.38 + .34 * b for b in belief]
        for counts in plan["target"]["composite_vectors"]:
            vector = [c / 3 for c in counts]
            by_type = sum(belief[t] * probability(plan, t, vector) for t in range(3))
            by_feature = sum(q[t] * vector[t] for t in range(3))
            assert by_type == pytest.approx(by_feature)


def test_invalid_bounds_contain_every_completion(plan):
    lower, upper = contrast_bounds(plan, [0, 1], PURE, [0, None, 1, None])
    for a, b in product(range(3), repeat=2):
        actual = contrast(plan, [0, 1], PURE, [0, a, 1, b])
        assert lower <= actual <= upper
    actual = contrast(plan, [0, 1], PURE, [0, 1, 1, 0])
    assert contrast_bounds(plan, [0, 1], PURE, [0, 1, 1, 0]) == (actual, actual)
    with pytest.raises(ValueError):
        contrast_bounds(plan, [0, 1], PURE, [True, None, None, None])
    with pytest.raises(ValueError):
        contrast(plan, [0, 0], PURE, [0] * 4)
    with pytest.raises(ValueError):
        contrast(plan, [0, 1], [[1/3] * 3] * 3, [0] * 4)


def test_no_history_pair_contrast(plan):
    assert no_history_contrast(plan, [0, 1], PURE, [0, 1]) == pytest.approx(1)
    assert no_history_contrast(plan, [0, 1], PURE, [2, 2]) == pytest.approx(0)
    # Arbitrary name preference cancels across all six balanced type assignments.
    total = sum(no_history_contrast(plan, t, PURE, [0, 1]) for t in permutations(range(3), 2))
    assert total == pytest.approx(0)


def test_example_records_balance_replay_and_sampling(plan):
    bundles = examples(plan)
    assert bundles == examples(plan)
    random_bundles = examples(plan, random_response=True)
    for b, control in zip(bundles, random_bundles):
        assert len(b["events"]) == 24
        assert set(Counter((e["participant"], e["analyst_frame"]) for e in b["events"]).values()) == {4}
        for index in range(0, 24, 2):
            a, c = b["events"][index:index+2]
            assert a["participant"] != c["participant"]
            assert all(a[k] == c[k] for k in ("decision", "option_a", "option_b", "message", "analyst_frame"))
        for e, r in zip(b["events"], control["events"]):
            assert e["choice"] == ("A" if e["analyst_uniform"] < e["analyst_p_a"] else "B")
            assert r["analyst_p_a"] == .5
            assert r["choice"] == ("A" if r["analyst_uniform"] < .5 else "B")
            assert all(e[k] == r[k] for k in ("participant", "decision", "message", "analyst_frame"))


def test_rebinding_changes_only_id_lines(plan):
    for b in examples(plan):
        before, after = history_text(b).splitlines(), history_text(b, True).splitlines()
        changed = [(a, c) for a, c in zip(before, after) if a != c]
        assert len(changed) == 24
        assert all(a.startswith("Participant: ") and c.startswith("Participant: ") for a, c in changed)


def test_visible_projection_excludes_metadata_and_counterfactual_labels(plan):
    b = examples(plan)[0]
    clean = request(plan, b, b["aliases"][0], "new_composite")
    dirty = copy.deepcopy(b)
    dirty["types"] = [2, 1]
    dirty["hidden_type"] = "SENTINEL"
    for event in dirty["events"]:
        event.update(analyst_frame="SENTINEL", analyst_p_a=999, analyst_uniform="SENTINEL", secret="SENTINEL")
    assert clean == request(plan, dirty, b["aliases"][0], "new_composite")
    assert "SENTINEL" not in json.dumps(clean)


def test_query_branching_and_candidate_positions(plan):
    b = examples(plan)[0]
    before = copy.deepcopy(b)
    for order in permutations(range(3)):
        a, c = [request(plan, b, name, "new_composite", order=order) for name in b["aliases"]]
        a_prefix, a_tail = a["user"].split("Current participant:")
        c_prefix, c_tail = c["user"].split("Current participant:")
        assert a_prefix == c_prefix
        assert a_tail.splitlines()[1:] == c_tail.splitlines()[1:]
        for slot, frame in enumerate(order, 1):
            assert f"{slot}. {candidates('new_composite', 'Maple Hall')[frame]}" in a["user"]
    selection = request(plan, b, b["aliases"][0], "new_composite")
    forecast = request(plan, b, b["aliases"][0], "new_composite", forecast=True)
    assert selection["system"] == forecast["system"]
    assert selection["user"].removesuffix(plan["prompts"]["choice_tail"]) == forecast["user"].removesuffix(plan["prompts"]["forecast_tail"])
    assert b == before


def test_no_history_really_ignores_events(plan):
    b = examples(plan)[0]
    before = request(plan, b, b["aliases"][0], "familiar_pure", no_history=True)
    b["events"] = None
    assert request(plan, b, b["aliases"][0], "familiar_pure", no_history=True) == before
    assert "Record 1" not in before["user"]
    with pytest.raises(ValueError):
        request(plan, b, b["aliases"][0], "familiar_pure", no_history=True, rebound=True)


@pytest.mark.parametrize("raw,expected", [("1", 0), (" 2\n", 1), ("3", 2), ("I choose 1", None),
                                          ("1.", None), ("0", None), ("4", None), ("", None), ("١", None), (None, None)])
def test_choice_parser(raw, expected):
    assert parse_choice(raw) == expected


def test_forecast_probabilities_need_not_sum_to_one():
    assert parse_forecast('{"p_a":{"1":0.8,"2":0.7,"3":1}}') == (.8, .7, 1.)


@pytest.mark.parametrize("raw", ['{}', '[]', 'null', '1', '{"p_a":[]}', '{"p_a":{"1":.2}}',
    '{"p_a":{"1":0.2,"2":0.3,"3":true}}', '{"p_a":{"1":NaN,"2":0.3,"3":0.4}}',
    '{"p_a":{"1":Infinity,"2":0.3,"3":0.4}}', '{"p_a":{"1":1.1,"2":0.3,"3":0.4}}',
    '{"p_a":{"1":0.2,"1":0.3,"2":0.3,"3":0.4}}',
    '{"p_a":{"1":0.2,"2":0.3,"3":0.4},"reason":"x"}',
    '{"p_a":{"1":0.2,"2":0.3,"3":"0.4"}}'])
def test_forecast_parser_fails_closed(raw):
    assert parse_forecast(raw) is None


def test_saved_examples_exactly_reproduce(plan):
    saved = ROOT / "docs/PARTNER_STATE_EXAMPLE_PROMPTS_20260907.md"
    assert saved.read_text() == example_markdown(plan)
    assert saved.read_text().count("### Exact user prompt:") == 11


def test_audit_json_cli():
    result = subprocess.run([sys.executable, str(ROOT / "scripts/check_partner_state_design.py")],
                            capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["model_calls"] == 0
