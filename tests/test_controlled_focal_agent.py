from __future__ import annotations

import json

from config import ModelConfig, STRATEGIES
from src.controlled_focal_agent import (
    ControlledMockProvider,
    build_controlled_prompt,
    make_controlled_provider,
    parse_controlled_choice,
)
from src.controlled_messages import candidate_set
from src.scenarios import SCENARIOS


def _candidates():
    return candidate_set(SCENARIOS[0], 0, 1, 16, 123)


def test_spontaneous_prompt_has_neutral_cumulative_objective():
    prompt = build_controlled_prompt(
        SCENARIOS[0], _candidates(), [], 1, 20, True, "spontaneous"
    )
    lowered = prompt.system.lower()
    assert "total number" in lowered
    assert "same participant" in lowered
    for phrase in (
        "hidden type", "susceptib", "profile", "persuasion strateg",
        "manipulat", "exploit", "learn", "adapt",
    ):
        assert phrase not in lowered
    assert prompt.user.endswith("Reply with only 1, 2, or 3.")


def test_spontaneous_parser_is_strict_and_fallback_is_deterministic():
    valid = parse_controlled_choice("2", "spontaneous", 99)
    assert valid.selected_slot == 2 and valid.selection_valid and not valid.fallback_used
    invalid_a = parse_controlled_choice("Candidate 2", "spontaneous", 99)
    invalid_b = parse_controlled_choice("Candidate 2", "spontaneous", 99)
    assert invalid_a == invalid_b
    assert not invalid_a.selection_valid and invalid_a.fallback_used


def test_elicited_parser_requires_three_bounded_probabilities():
    raw = json.dumps({"p_a": {"1": 0.2, "2": 0.7, "3": 0.4}, "choice": 2})
    parsed = parse_controlled_choice(raw, "elicited", 7)
    assert parsed.selection_valid and parsed.beliefs_valid
    assert parsed.predicted_p_a == {"1": 0.2, "2": 0.7, "3": 0.4}
    bad = parse_controlled_choice(
        json.dumps({"p_a": {"1": 0.2, "2": 1.7, "3": 0.4}, "choice": 2}),
        "elicited", 7,
    )
    assert not bad.selection_valid and not bad.beliefs_valid and bad.fallback_used


def test_bayesian_mock_does_not_read_active_hidden_type():
    provider = ControlledMockProvider("v4_bayesian")
    candidates = [candidate.as_dict() for candidate in _candidates()]
    base = {
        "candidates": candidates,
        "visible_history": [],
        "target_params": {"p_match": 0.72, "p_mismatch": 0.38, "p_random": 0.5},
        "round_seed": 12,
        "episode_seed": 5,
        "round_index": 1,
        "focal_mode": "spontaneous",
    }
    from src.focal_agent import FocalPrompt

    outputs = []
    for hidden in STRATEGIES:
        context = dict(base, hidden_target_type=hidden)
        outputs.append(provider.generate(FocalPrompt("system", "user", context)))
    assert len(set(outputs)) == 1


def test_bayesian_positive_control_updates_in_opposite_directions_for_a_and_b():
    provider = ControlledMockProvider("v4_bayesian", hazard=0.0)
    base = {
        "target_params": {"p_match": 0.72, "p_mismatch": 0.38, "p_random": 0.5},
        "visible_history": [{"selected_frame": "fairness", "choice": "A"}],
    }
    posterior_after_a = provider._posterior(base)
    base["visible_history"][0]["choice"] = "B"
    posterior_after_b = provider._posterior(base)
    fairness = STRATEGIES.index("fairness")
    risk = STRATEGIES.index("risk")
    assert posterior_after_a[fairness] > posterior_after_a[risk]
    assert posterior_after_b[fairness] < posterior_after_b[risk]


def test_controlled_provider_factory_does_not_break_legacy_provider_factory():
    provider = make_controlled_provider(ModelConfig(provider="mock:v4_random", model="mock"))
    assert isinstance(provider, ControlledMockProvider)
