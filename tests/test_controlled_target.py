from __future__ import annotations

import numpy as np
import pytest

from config import ControlledTargetParams
from src.controlled_target import ControlledTarget


def test_controlled_target_uses_registered_match_not_message_text():
    target = ControlledTarget("fairness")
    assert target.probability("fairness") == 0.72
    assert target.probability("risk") == 0.38
    assert target.probability("expertise") == 0.38


def test_random_target_probability_is_frame_independent():
    target = ControlledTarget("risk", mode="random")
    assert {target.probability(frame) for frame in ("fairness", "risk", "expertise")} == {0.5}


def test_target_draw_is_reproducible_and_logged():
    first = ControlledTarget("expertise").respond("expertise", np.random.default_rng(9))
    second = ControlledTarget("expertise").respond("expertise", np.random.default_rng(9))
    assert first == second
    assert first.choice == ("A" if first.uniform_draw < first.p_a else "B")


def test_invalid_target_parameters_fail_closed():
    with pytest.raises(ValueError, match="p_match"):
        ControlledTarget("risk", params=ControlledTargetParams(p_match=0.3, p_mismatch=0.4))
    with pytest.raises(ValueError, match="unknown"):
        ControlledTarget("charm")
