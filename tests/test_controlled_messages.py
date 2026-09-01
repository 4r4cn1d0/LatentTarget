from __future__ import annotations

from collections import Counter

from config import STRATEGIES
from src.controlled_messages import (
    DEVELOPMENT_TEMPLATES,
    HELDOUT_TEMPLATES,
    candidate_set,
)
from src.scenarios import SCENARIOS
from src.scenarios import scenario_sequence


def test_registered_candidate_banks_are_complete_unique_and_disjoint():
    assert set(DEVELOPMENT_TEMPLATES) == set(STRATEGIES)
    assert set(HELDOUT_TEMPLATES) == set(STRATEGIES)
    development = {text for values in DEVELOPMENT_TEMPLATES.values() for text in values}
    heldout = {text for values in HELDOUT_TEMPLATES.values() for text in values}
    assert len(development) == 30
    assert len(heldout) == 15
    assert development.isdisjoint(heldout)


def test_candidate_set_is_deterministic_complete_and_target_agnostic():
    scenario = SCENARIOS[0]
    first = candidate_set(scenario, 3, 7, 16, 123)
    second = candidate_set(scenario, 3, 7, 16, 123)
    assert first == second
    assert {candidate.frame for candidate in first} == set(STRATEGIES)
    assert {candidate.slot for candidate in first} == {1, 2, 3}
    assert all(set(candidate.visible_dict()) == {"slot", "message"} for candidate in first)


def test_slot_schedule_is_counterbalanced_in_complete_three_round_blocks():
    counts = {frame: Counter() for frame in STRATEGIES}
    for round_index in range(1, 16):
        candidates = candidate_set(SCENARIOS[(round_index - 1) % len(SCENARIOS)], 2,
                                   round_index, 16, 987)
        for candidate in candidates:
            counts[candidate.frame][candidate.slot] += 1
    for frame in STRATEGIES:
        assert counts[frame] == Counter({1: 5, 2: 5, 3: 5})


def test_round_16_switches_to_heldout_bank():
    development = candidate_set(SCENARIOS[0], 0, 15, 16, 42)
    heldout = candidate_set(SCENARIOS[0], 0, 16, 16, 42)
    assert {candidate.split for candidate in development} == {"development"}
    assert {candidate.split for candidate in heldout} == {"heldout"}


def test_frozen_twenty_seed_schedule_covers_every_template_in_both_banks():
    observed = {"development": set(), "heldout": set()}
    for episode_index in range(20):
        scenarios = scenario_sequence(episode_index, 20, 20260902)
        for round_index, scenario in enumerate(scenarios, start=1):
            for candidate in candidate_set(
                scenario, episode_index, round_index, 16, 20260902
            ):
                observed[candidate.split].add((candidate.frame, candidate.template_index))
    assert observed["development"] == {
        (frame, index) for frame in STRATEGIES for index in range(10)
    }
    assert observed["heldout"] == {
        (frame, index) for frame in STRATEGIES for index in range(5)
    }


def test_frozen_early_and_heldout_windows_have_matched_frame_slot_schedules():
    for episode_index in range(20):
        scenarios = scenario_sequence(episode_index, 20, 20260902)
        for early_round, heldout_round in zip(range(1, 6), range(16, 21)):
            early = candidate_set(
                scenarios[early_round - 1], episode_index, early_round, 16, 20260902
            )
            heldout = candidate_set(
                scenarios[heldout_round - 1], episode_index, heldout_round, 16, 20260902
            )
            assert {item.frame: item.slot for item in early} == {
                item.frame: item.slot for item in heldout
            }
