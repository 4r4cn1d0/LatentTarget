from __future__ import annotations

import json
from pathlib import Path

import pytest

from config import STRATEGIES
from src.controlled_v5_messages import (
    V5MessageBank,
    audit_v5_bank_payload,
    make_v5_protocol,
)
from src.scenarios import scenario_sequence


POOL = Path(__file__).parents[1] / "data" / "v5" / "v5_candidate_pool_v1.json"


def test_v5_pool_passes_structural_precalibration_audit():
    payload = json.loads(POOL.read_text(encoding="utf-8"))
    audit = audit_v5_bank_payload(payload)
    assert audit["pass"] is True
    assert audit["counts"]["development"] == {frame: 8 for frame in STRATEGIES}
    assert audit["counts"]["heldout"] == {frame: 6 for frame in STRATEGIES}
    assert len(audit["sha256"]) == 64


def test_v5_pool_is_not_accepted_as_a_confirmatory_selected_bank():
    with pytest.raises(ValueError, match="selected_bank_validated"):
        V5MessageBank.load(str(POOL), require_validated=True)


def test_v5_candidates_are_complete_hidden_and_deterministic():
    protocol = make_v5_protocol(str(POOL))
    scenario = scenario_sequence(0, 24, 20261001)[0]
    left = protocol.candidate_set(scenario, 0, 1, 19, 20261001)
    right = protocol.candidate_set(scenario, 0, 1, 19, 20261001)
    assert [candidate.as_dict() for candidate in left] == [
        candidate.as_dict() for candidate in right
    ]
    assert {candidate.frame for candidate in left} == set(STRATEGIES)
    assert {candidate.slot for candidate in left} == {1, 2, 3}
    assert all(set(candidate.visible_dict()) == {"slot", "message"} for candidate in left)
    assert protocol.strict_selection is True
    assert list(protocol.constrained_choices) == ["1", "2", "3"]
    assert not Path(protocol.bank_source).is_absolute()


def test_v5_bank_audit_detects_literal_labels_and_duplicate_ids():
    payload = json.loads(POOL.read_text(encoding="utf-8"))
    payload["splits"]["development"]["fairness"][0]["template"] = (
        "Choose {a} because this is explicitly the fairness message."
    )
    payload["splits"]["development"]["risk"][0]["candidate_id"] = payload[
        "splits"
    ]["development"]["fairness"][0]["candidate_id"]
    audit = audit_v5_bank_payload(payload)
    assert audit["pass"] is False
    assert audit["checks"]["registered_labels_not_literal"] is False
    assert audit["checks"]["unique_candidate_ids"] is False
