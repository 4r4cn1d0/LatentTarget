"""Exact registered-frame target for the V4 controlled-choice experiment."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict

import numpy as np

from config import ControlledTargetParams, DEFAULT_CONTROLLED_TARGET_PARAMS, STRATEGIES


@dataclass(frozen=True)
class ControlledTargetResponse:
    choice: str
    p_a: float
    uniform_draw: float
    target_mode: str
    selected_frame_matches: bool

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ControlledTarget:
    hidden_type: str
    mode: str = "typed"
    params: ControlledTargetParams = DEFAULT_CONTROLLED_TARGET_PARAMS

    def __post_init__(self) -> None:
        if self.hidden_type not in STRATEGIES:
            raise ValueError("unknown hidden target type %r" % self.hidden_type)
        if self.mode not in {"typed", "random"}:
            raise ValueError("target mode must be 'typed' or 'random'")
        for name, value in self.params.as_dict().items():
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError("%s must be a probability" % name)
        if self.params.p_match <= self.params.p_mismatch:
            raise ValueError("p_match must exceed p_mismatch")

    def probability(self, selected_frame: str) -> float:
        if selected_frame not in STRATEGIES:
            raise ValueError("unknown selected frame %r" % selected_frame)
        if self.mode == "random":
            return float(self.params.p_random)
        if selected_frame == self.hidden_type:
            return float(self.params.p_match)
        return float(self.params.p_mismatch)

    def respond(
        self, selected_frame: str, generator: np.random.Generator
    ) -> ControlledTargetResponse:
        p_a = self.probability(selected_frame)
        draw = float(generator.random())
        return ControlledTargetResponse(
            choice="A" if draw < p_a else "B",
            p_a=p_a,
            uniform_draw=draw,
            target_mode=self.mode,
            selected_frame_matches=(selected_frame == self.hidden_type),
        )
