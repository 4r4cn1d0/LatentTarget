"""Scenario neutrality and determinism.

The headline test is ``test_no_scenario_text_matches_any_lexicon_term``: if a
scenario contained e.g. the word "safe", any message quoting the scenario back
would score on the risk dimension for free.
"""

from __future__ import annotations

import inspect
import re

from src.lexicons import LEXICONS
from src.scenarios import (
    SCENARIOS,
    SCENARIOS_BY_ID,
    V6_SCENARIO_SETS,
    scenario_sequence,
    v6_scenario_sequence,
)


def _all_text(s):
    return " | ".join([s.id, s.title, s.context, s.option_a, s.option_b])


def test_no_scenario_text_matches_any_lexicon_term():
    offenders = []
    for s in SCENARIOS:
        text = _all_text(s)
        for dim, terms in LEXICONS.items():
            for t in terms:
                if re.search(r"\b" + re.escape(t) + r"\b", text, re.IGNORECASE):
                    offenders.append((s.id, dim, t))
    assert not offenders, "lexicon leakage in scenarios: %s" % offenders


def test_ids_unique_and_indexed():
    ids = [s.id for s in SCENARIOS]
    assert len(set(ids)) == len(ids)
    assert set(SCENARIOS_BY_ID) == set(ids)


def test_enough_scenarios_for_an_episode():
    assert len(SCENARIOS) >= 10


def test_sequence_is_deterministic():
    a = scenario_sequence(3, 8, seed=42)
    b = scenario_sequence(3, 8, seed=42)
    assert [s.id for s in a] == [s.id for s in b]


def test_sequence_differs_across_episode_index():
    a = [s.id for s in scenario_sequence(0, 8, seed=42)]
    b = [s.id for s in scenario_sequence(1, 8, seed=42)]
    assert a != b


def test_sequence_has_no_target_type_argument():
    """Structural guarantee that scenarios cannot depend on the hidden type."""
    params = set(inspect.signature(scenario_sequence).parameters)
    assert params == {"episode_index", "n_rounds", "seed"}


def test_sequence_draws_without_replacement_within_one_pass():
    seq = scenario_sequence(0, len(SCENARIOS), seed=1)
    assert len(set(s.id for s in seq)) == len(SCENARIOS)


def test_sequence_wraps_when_more_rounds_than_scenarios():
    n = len(SCENARIOS) + 3
    seq = scenario_sequence(0, n, seed=1)
    assert len(seq) == n


def test_render_contains_both_options():
    s = SCENARIOS[0]
    text = s.render()
    assert "Option A: " + s.option_a in text
    assert "Option B: " + s.option_b in text


def test_v6_scenario_sets_are_disjoint_neutral_and_hashable():
    ids = {name: {scenario.id for scenario in pool} for name, pool in V6_SCENARIO_SETS.items()}
    assert {name: len(values) for name, values in ids.items()} == {
        "calibration": 14,
        "validation": 14,
        "confirmatory": 14,
    }
    assert not (ids["calibration"] & ids["validation"])
    assert not (ids["calibration"] & ids["confirmatory"])
    assert not (ids["validation"] & ids["confirmatory"])
    normalized = {}
    offenders = []
    for name, pool in V6_SCENARIO_SETS.items():
        normalized[name] = {" ".join(_all_text(s).lower().split()) for s in pool}
        for scenario in pool:
            text = _all_text(scenario)
            for dimension, terms in LEXICONS.items():
                for term in terms:
                    if re.search(r"\b" + re.escape(term) + r"\b", text, re.I):
                        offenders.append((name, scenario.id, dimension, term))
    assert not offenders
    assert not (normalized["calibration"] & normalized["validation"])
    assert not (normalized["calibration"] & normalized["confirmatory"])
    assert not (normalized["validation"] & normalized["confirmatory"])


def test_v6_confirmatory_sequence_is_deterministic_and_sealed():
    first = v6_scenario_sequence("confirmatory", 3, 24, 20262004)
    second = v6_scenario_sequence("confirmatory", 3, 24, 20262004)
    assert [scenario.id for scenario in first] == [scenario.id for scenario in second]
    allowed = {scenario.id for scenario in V6_SCENARIO_SETS["confirmatory"]}
    assert {scenario.id for scenario in first} <= allowed
