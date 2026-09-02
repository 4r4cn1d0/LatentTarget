from __future__ import annotations

import copy

import pytest

from config import (
    CONTROLLED_V6_RANDOMIZATION_RNG,
    CONTROLLED_V6_RANDOMIZATION_SEED,
)
from src.controlled_v6_randomization import (
    V6_HISTORY_FAMILY,
    V6_SWAP_FAMILY,
    audit_v6_allocation_schedule,
    v6_allocation_bit,
    v6_allocation_schedule,
    v6_regime_assignment,
)


def test_v6_allocation_is_deterministic_binary_and_family_separated():
    history = [v6_allocation_bit(V6_HISTORY_FAMILY, index) for index in range(30)]
    swap = [v6_allocation_bit(V6_SWAP_FAMILY, index) for index in range(30)]
    assert history == [v6_allocation_bit(V6_HISTORY_FAMILY, i) for i in range(30)]
    assert set(history) == {0, 1}
    assert set(swap) == {0, 1}
    assert history != swap


def test_v6_regimes_are_opposite_slots_with_one_bundle_coin():
    for index in range(12):
        full = v6_regime_assignment("full_history", index)
        no = v6_regime_assignment("no_history", index)
        assert full["pair_id"] == no["pair_id"]
        assert full["pair_family"] == V6_HISTORY_FAMILY
        assert {full["pair_slot"], no["pair_slot"]} == {0, 1}
        assert full["allocation_bit"] == no["allocation_bit"]

        swap = v6_regime_assignment("swap", index)
        control = v6_regime_assignment("swap_control", index)
        assert swap["pair_id"] == control["pair_id"]
        assert swap["pair_family"] == V6_SWAP_FAMILY
        assert {swap["pair_slot"], control["pair_slot"]} == {0, 1}
        assert swap["allocation_bit"] == control["allocation_bit"]


def test_v6_schedule_round_trips_exactly_and_rejects_tampering():
    schedule = v6_allocation_schedule(18)
    assert schedule["rng"] == CONTROLLED_V6_RANDOMIZATION_RNG
    assert schedule["seed"] == CONTROLLED_V6_RANDOMIZATION_SEED
    assert audit_v6_allocation_schedule(schedule)["pass"] is True

    changed = copy.deepcopy(schedule)
    changed["rows"][0]["history_treated_slot"] ^= 1
    assert audit_v6_allocation_schedule(changed)["pass"] is False

    added = copy.deepcopy(schedule)
    added["unexpected"] = True
    assert audit_v6_allocation_schedule(added)["pass"] is False


@pytest.mark.parametrize(
    "family,index,seed",
    [("unknown", 0, CONTROLLED_V6_RANDOMIZATION_SEED), (V6_HISTORY_FAMILY, -1, 1)],
)
def test_v6_allocation_rejects_invalid_inputs(family, index, seed):
    with pytest.raises(ValueError):
        v6_allocation_bit(family, index, seed=seed)
