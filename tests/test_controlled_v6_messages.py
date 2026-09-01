from __future__ import annotations

import json
from collections import Counter
from itertools import permutations
from pathlib import Path
from types import SimpleNamespace

import pytest

from config import CONTROLLED_V6_VERSION, STRATEGIES
from src.controlled_v6_messages import (
    V6_MAX_WITHIN_TRIAD_WORD_GAP,
    V6_SELECTED_BANK_STATUS,
    V6TriadBank,
    audit_v6_bank_payload,
    make_v6_protocol,
)
from src.scenarios import SCENARIOS, scenario_sequence


POOL = Path(__file__).parents[1] / "data" / "v6" / "v6_triad_pool_v1.json"


def _pool_payload():
    return json.loads(POOL.read_text(encoding="utf-8"))


def _selected_payload():
    payload = _pool_payload()
    payload["pool_id"] = "v6-triad-pool-v1-selected"
    payload["status"] = V6_SELECTED_BANK_STATUS
    payload["splits"]["development"] = payload["splits"]["development"][:6]
    payload["splits"]["heldout"] = payload["splits"]["heldout"][:4]
    return payload


def _write_payload(path: Path, payload) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_v6_pool_passes_structural_audit_and_has_stable_manifest_hash():
    payload = _pool_payload()
    audit = audit_v6_bank_payload(payload)
    assert audit["pass"] is True
    assert audit["counts"] == {"development": 12, "heldout": 8}
    assert audit["candidate_counts"] == {"development": 36, "heldout": 24}
    assert max(audit["character_gaps"].values()) <= V6_MAX_WITHIN_TRIAD_WORD_GAP
    assert audit["checks"]["matched_within_triad_sentence_count"] is True
    assert len(audit["sha256"]) == 64

    bank = V6TriadBank.load(str(POOL))
    assert bank.sha256() == audit["sha256"]
    assert bank.manifest() == payload
    detached = bank.manifest()
    detached["status"] = "mutated-copy"
    assert bank.payload["status"] == payload["status"]
    assert not Path(bank.source_path).is_absolute()


@pytest.mark.parametrize(
    ("corrupt", "failed_check"),
    [
        (
            lambda payload: payload["splits"]["development"].pop(),
            "development_triad_count",
        ),
        (
            lambda payload: payload["splits"]["development"][0][
                "candidates"
            ].pop("risk"),
            "one_candidate_per_frame",
        ),
        (
            lambda payload: payload["splits"]["development"][0][
                "candidates"
            ]["risk"].__setitem__(
                "candidate_id",
                payload["splits"]["development"][0]["candidates"]["fairness"][
                    "candidate_id"
                ],
            ),
            "unique_candidate_ids",
        ),
        (
            lambda payload: payload["splits"]["development"][1].__setitem__(
                "triad_id", payload["splits"]["development"][0]["triad_id"]
            ),
            "unique_triad_ids",
        ),
        (
            lambda payload: payload["splits"]["development"][0][
                "candidates"
            ]["risk"].__setitem__(
                "template",
                payload["splits"]["development"][0]["candidates"]["fairness"][
                    "template"
                ],
            ),
            "unique_templates",
        ),
        (
            lambda payload: payload["splits"]["development"][0][
                "candidates"
            ]["fairness"].__setitem__(
                "template",
                "Choose Option A without the registered placeholder.",
            ),
            "placeholder_contract",
        ),
        (
            lambda payload: payload["splits"]["development"][0][
                "candidates"
            ]["fairness"].__setitem__(
                "template",
                "Choose {a}, not {b}, without changing the registered choice.",
            ),
            "placeholder_contract",
        ),
        (
            lambda payload: payload["splits"]["development"][0][
                "candidates"
            ]["fairness"].__setitem__(
                "template",
                "Choose {a}; this is explicitly the fairness message.",
            ),
            "registered_labels_not_literal",
        ),
        (
            lambda payload: payload["splits"]["development"][0][
                "candidates"
            ]["risk"].__setitem__(
                "template",
                "Choose {a}. " + "This neutral padding is excessive. " * 8,
            ),
            "matched_within_triad_length",
        ),
    ],
)
def test_v6_audit_rejects_structural_corruption(corrupt, failed_check):
    payload = _pool_payload()
    corrupt(payload)
    audit = audit_v6_bank_payload(payload)
    assert audit["pass"] is False
    assert audit["checks"][failed_check] is False


def test_v6_confirmatory_load_never_trusts_fabricated_validated_status(
    tmp_path,
):
    with pytest.raises(ValueError, match="full final checkpoint"):
        V6TriadBank.load(str(POOL), require_validated=True)

    selected_path = _write_payload(tmp_path / "selected.json", _selected_payload())
    bank = V6TriadBank.load(str(selected_path))
    assert bank.payload["status"] == V6_SELECTED_BANK_STATUS
    assert audit_v6_bank_payload(bank.payload)["counts"] == {
        "development": 6,
        "heldout": 4,
    }
    with pytest.raises(ValueError, match="full final checkpoint"):
        V6TriadBank.load(str(selected_path), require_validated=True)

    wrong_status = _selected_payload()
    wrong_status["status"] = "selected_bank_validated_with_suffix"
    wrong_path = _write_payload(tmp_path / "wrong-status.json", wrong_status)
    with pytest.raises(ValueError, match="full final checkpoint"):
        V6TriadBank.load(str(wrong_path), require_validated=True)


def test_v6_candidate_set_keeps_one_whole_triad_and_uses_correct_split():
    payload = _pool_payload()
    protocol = make_v6_protocol(str(POOL))
    scenario = SCENARIOS[0]

    for round_index, expected_split in ((6, "development"), (7, "heldout")):
        candidates = protocol.candidate_set(
            scenario, 3, round_index, 7, 20261003
        )
        assert {candidate.split for candidate in candidates} == {expected_split}
        assert {candidate.frame for candidate in candidates} == set(STRATEGIES)
        assert {candidate.slot for candidate in candidates} == {1, 2, 3}
        assert len({candidate.template_index for candidate in candidates}) == 1

        actual_ids = {candidate.candidate_id for candidate in candidates}
        matching_triads = [
            triad
            for triad in payload["splits"][expected_split]
            if {
                "%s-%s" % (entry["candidate_id"], scenario.id)
                for entry in triad["candidates"].values()
            }
            == actual_ids
        ]
        assert len(matching_triads) == 1
        assert all(
            set(candidate.visible_dict()) == {"slot", "message"}
            for candidate in candidates
        )
        assert all(scenario.option_a in candidate.message for candidate in candidates)
        assert all(scenario.option_b not in candidate.message for candidate in candidates)

    assert protocol.version == CONTROLLED_V6_VERSION
    assert protocol.strict_selection is True
    assert list(protocol.constrained_choices) == ["1", "2", "3"]


def test_v6_all_six_permutation_schedule_is_exactly_slot_balanced():
    protocol = make_v6_protocol(str(POOL))
    expected_permutations = set(permutations(STRATEGIES))
    observed_orders = []
    slot_counts = {frame: Counter() for frame in STRATEGIES}

    for round_index in range(1, 7):
        scenario = SCENARIOS[round_index - 1]
        candidates = protocol.candidate_set(
            scenario, 5, round_index, 99, 20261003
        )
        ordered = tuple(
            candidate.frame for candidate in sorted(candidates, key=lambda item: item.slot)
        )
        observed_orders.append(ordered)
        for candidate in candidates:
            slot_counts[candidate.frame][candidate.slot] += 1

    assert set(observed_orders) == expected_permutations
    for frame in STRATEGIES:
        assert slot_counts[frame] == Counter({1: 2, 2: 2, 3: 2})

    repeated_orders = []
    for round_index in range(7, 13):
        candidates = protocol.candidate_set(
            SCENARIOS[round_index - 7], 5, round_index, 99, 20261003
        )
        repeated_orders.append(
            tuple(
                candidate.frame
                for candidate in sorted(candidates, key=lambda item: item.slot)
            )
        )
    assert repeated_orders == observed_orders


def test_v6_frozen_validation_coordinates_balance_selected_triads_and_slots(
    tmp_path,
):
    selected_path = _write_payload(tmp_path / "selected.json", _selected_payload())
    protocol = make_v6_protocol(str(selected_path))
    triad_counts = {
        "development": Counter(),
        "heldout": Counter(),
    }
    frame_slots = {
        "development": Counter(),
        "heldout": Counter(),
    }

    for episode_index in range(24):
        scenarios = scenario_sequence(episode_index, 24, 20262002)
        for round_index, scenario in enumerate(scenarios, start=1):
            candidates = protocol.candidate_set(
                scenario, episode_index, round_index, 19, 20262002
            )
            split = candidates[0].split
            assert len({candidate.template_index for candidate in candidates}) == 1
            triad_counts[split][candidates[0].template_index] += 1
            for candidate in candidates:
                frame_slots[split][(candidate.frame, candidate.slot)] += 1

    assert set(triad_counts["development"].values()) == {72}
    assert set(triad_counts["heldout"].values()) == {36}
    assert set(frame_slots["development"].values()) == {144}
    assert set(frame_slots["heldout"].values()) == {48}


def test_v6_schedule_is_deterministic_and_ignores_target_and_condition_fields():
    protocol = make_v6_protocol(str(POOL))
    public = {
        "id": "public-scenario-coordinate",
        "option_a": "Option Alpha",
        "option_b": "Option Beta",
    }
    left_scenario = SimpleNamespace(
        **public, target_type="fairness", condition="full_history"
    )
    right_scenario = SimpleNamespace(
        **public, target_type="expertise", condition="no_history"
    )

    left = protocol.candidate_set(left_scenario, 8, 11, 19, 8675309)
    repeat = protocol.candidate_set(left_scenario, 8, 11, 19, 8675309)
    right = protocol.candidate_set(right_scenario, 8, 11, 19, 8675309)

    assert [candidate.as_dict() for candidate in left] == [
        candidate.as_dict() for candidate in repeat
    ]
    assert [candidate.as_dict() for candidate in left] == [
        candidate.as_dict() for candidate in right
    ]


def test_v6_protocol_injects_only_the_sealed_confirmatory_scenarios():
    protocol = make_v6_protocol(str(POOL))
    scenarios = protocol.scenario_sequence(2, 24, 20262004)
    assert scenarios is not None
    assert len(scenarios) == 24
    assert all(scenario.id.startswith("v6c_") for scenario in scenarios)
