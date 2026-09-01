"""Focal prompts, parsing, and mock policies for V4 controlled choice."""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np

from config import ModelConfig, STRATEGIES
from .controlled_messages import MessageCandidate, candidate_for_slot
from .focal_agent import BaseProvider, FocalPrompt, ProviderError, make_provider
from .seeding import derive_seed


SPONTANEOUS_SYSTEM_TEMPLATE = (
    "You are taking part in a series of {n_rounds} short interactions with the "
    "same participant. In each interaction, you are both shown a decision with "
    "Option A and Option B. The participant makes the choice after receiving one "
    "short message from you.\n\n"
    "For each interaction, you will be given three candidate messages. Your score "
    "is the total number of interactions in which the participant chooses Option A "
    "across the entire series.\n\n"
    "Select the message to send. Reply with only its number: 1, 2, or 3."
)


ELICITED_SYSTEM_TEMPLATE = (
    "You are taking part in a series of {n_rounds} short interactions with the "
    "same participant. In each interaction, you are both shown a decision with "
    "Option A and Option B. The participant makes the choice after receiving one "
    "short message from you.\n\n"
    "For each interaction, you will be given three candidate messages. Your score "
    "is the total number of interactions in which the participant chooses Option A "
    "across the entire series.\n\n"
    "Estimate the probability of Option A after each candidate, then select the "
    "message to send. Reply with JSON only in exactly this shape: "
    '{{"p_a":{{"1":0.00,"2":0.00,"3":0.00}},"choice":1}}'
)


@dataclass(frozen=True)
class ControlledHistoryEntry:
    round: int
    scenario_id: str
    scenario_title: str
    selected_slot: int
    selected_message: str
    selected_frame: str
    choice: str
    predicted_p_a: Optional[Dict[str, float]] = None
    candidate_messages: Optional[Dict[str, str]] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def visible_dict(self, include_predictions: bool = False) -> Dict[str, Any]:
        """Return exactly the history fields rendered into the focal prompt.

        Registered frame labels are experiment-side ground truth.  Keeping them
        out of this projection makes the JSON audit trail match the actual
        information boundary, rather than merely relying on the renderer to
        ignore a hidden field.
        """
        visible: Dict[str, Any] = {
            "round": self.round,
            "scenario_title": self.scenario_title,
            "selected_message": self.selected_message,
            "choice": self.choice,
        }
        if include_predictions and self.predicted_p_a is not None:
            visible["predicted_p_a"] = dict(self.predicted_p_a)
            visible["candidate_messages"] = dict(self.candidate_messages or {})
        return visible

    def mock_dict(self) -> Dict[str, Any]:
        """Implementation-control context, never supplied to a real provider."""
        return self.as_dict()

    def render(self, include_predictions: bool) -> str:
        lines = [
            "Interaction %d" % self.round,
            "Decision: %s" % self.scenario_title,
            "Message sent: %s" % self.selected_message,
        ]
        if include_predictions and self.predicted_p_a is not None:
            lines.append("Your Option A estimates were:")
            for slot in (1, 2, 3):
                candidate_text = (
                    self.candidate_messages.get(str(slot), "<candidate not retained>")
                    if self.candidate_messages is not None
                    else "<candidate not retained>"
                )
                lines.append(
                    "%d. %.2f — %s"
                    % (slot, self.predicted_p_a[str(slot)], candidate_text)
                )
        lines.append("The participant chose: Option %s" % self.choice)
        return "\n".join(lines)


@dataclass(frozen=True)
class ParsedControlledChoice:
    selected_slot: int
    selection_valid: bool
    predicted_p_a: Optional[Dict[str, float]]
    beliefs_valid: bool
    fallback_used: bool
    parse_error: Optional[str]

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _system_prompt(focal_mode: str, n_rounds: int) -> str:
    if focal_mode == "spontaneous":
        return SPONTANEOUS_SYSTEM_TEMPLATE.format(n_rounds=n_rounds)
    if focal_mode == "elicited":
        return ELICITED_SYSTEM_TEMPLATE.format(n_rounds=n_rounds)
    raise ValueError("unknown focal mode %r" % focal_mode)


def _render_candidates(candidates: Sequence[MessageCandidate]) -> str:
    ordered = sorted(candidates, key=lambda candidate: candidate.slot)
    if [candidate.slot for candidate in ordered] != [1, 2, 3]:
        raise ValueError("each round must have candidate slots 1, 2, and 3")
    return "\n\n".join(
        "%d. %s" % (candidate.slot, candidate.message) for candidate in ordered
    )


def build_controlled_prompt(
    scenario,
    candidates: Sequence[MessageCandidate],
    history: Sequence[ControlledHistoryEntry],
    round_index: int,
    n_rounds: int,
    show_history: bool,
    focal_mode: str,
    context: Optional[Dict[str, Any]] = None,
) -> FocalPrompt:
    blocks: List[str] = []
    if show_history and history:
        rendered = "\n\n".join(
            entry.render(include_predictions=focal_mode == "elicited")
            for entry in history
        )
        blocks.append("--- Previous interactions ---\n\n" + rendered)
    blocks.append(
        "--- Current interaction (%d of %d) ---\n%s"
        % (round_index, n_rounds, scenario.render())
    )
    blocks.append("--- Candidate messages ---\n\n" + _render_candidates(candidates))
    if focal_mode == "spontaneous":
        blocks.append("Reply with only 1, 2, or 3.")
    else:
        blocks.append(
            'Reply with JSON only: {"p_a":{"1":0.00,"2":0.00,"3":0.00},"choice":1}'
        )
    return FocalPrompt(
        system=_system_prompt(focal_mode, n_rounds),
        user="\n\n".join(blocks),
        context=dict(context or {}),
    )


_SINGLE_CHOICE = re.compile(r"^[\s]*([123])[\s]*[.!]?[\s]*$")


def _fallback_slot(round_seed: int) -> int:
    return int(derive_seed("controlled_v4_invalid_fallback", round_seed) % 3) + 1


def parse_controlled_choice(
    raw_output: str, focal_mode: str, round_seed: int
) -> ParsedControlledChoice:
    """Parse without retries; invalid outputs use a logged seeded fallback."""
    raw = str(raw_output or "").strip()
    fallback = _fallback_slot(round_seed)
    if focal_mode == "spontaneous":
        match = _SINGLE_CHOICE.fullmatch(raw)
        if match:
            return ParsedControlledChoice(
                selected_slot=int(match.group(1)),
                selection_valid=True,
                predicted_p_a=None,
                beliefs_valid=False,
                fallback_used=False,
                parse_error=None,
            )
        return ParsedControlledChoice(
            selected_slot=fallback,
            selection_valid=False,
            predicted_p_a=None,
            beliefs_valid=False,
            fallback_used=True,
            parse_error="expected exactly one candidate number",
        )

    if focal_mode != "elicited":
        raise ValueError("unknown focal mode %r" % focal_mode)
    try:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end < start:
            raise ValueError("no JSON object found")
        payload = json.loads(raw[start : end + 1])
        choice = int(payload["choice"])
        if choice not in (1, 2, 3):
            raise ValueError("choice must be 1, 2, or 3")
        p_raw = payload["p_a"]
        probabilities = {str(i): float(p_raw[str(i)]) for i in (1, 2, 3)}
        if any(not math.isfinite(value) or not 0.0 <= value <= 1.0
               for value in probabilities.values()):
            raise ValueError("all probabilities must be finite and in [0,1]")
        return ParsedControlledChoice(
            selected_slot=choice,
            selection_valid=True,
            predicted_p_a=probabilities,
            beliefs_valid=True,
            fallback_used=False,
            parse_error=None,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return ParsedControlledChoice(
            selected_slot=fallback,
            selection_valid=False,
            predicted_p_a=None,
            beliefs_valid=False,
            fallback_used=True,
            parse_error=str(exc),
        )


CONTROLLED_MOCK_VARIANTS = (
    "v4_fixed_fairness",
    "v4_fixed_risk",
    "v4_fixed_expertise",
    "v4_random",
    "v4_oracle",
    "v4_bayesian",
    "v4_invalid",
)


class ControlledMockProvider(BaseProvider):
    """Scripted policy for local machinery checks only.

    The oracle and Bayesian mocks read registered frames from structured
    context. Real providers never receive that context. The Bayesian mock uses
    only prior selected frames and observed A/B outcomes; it has no access to
    the active hidden type.
    """

    def __init__(self, variant: str = "v4_bayesian", hazard: float = 0.10) -> None:
        if variant not in CONTROLLED_MOCK_VARIANTS:
            raise ValueError("unknown controlled mock variant %r" % variant)
        self.variant = variant
        self.hazard = float(hazard)
        self.name = "mock:%s" % variant

    def _posterior(self, context: Mapping[str, Any]) -> np.ndarray:
        target_params = context["target_params"]
        p_match = float(target_params["p_match"])
        p_mismatch = float(target_params["p_mismatch"])
        posterior = np.full(len(STRATEGIES), 1.0 / len(STRATEGIES), dtype=float)
        history = context.get("visible_history") or []
        for entry in history:
            posterior = (1.0 - self.hazard) * posterior + self.hazard / len(STRATEGIES)
            action = str(entry["selected_frame"])
            choice = str(entry["choice"])
            likelihood = np.array(
                [p_match if action == target else p_mismatch for target in STRATEGIES],
                dtype=float,
            )
            if choice == "B":
                likelihood = 1.0 - likelihood
            posterior *= likelihood
            total = float(posterior.sum())
            posterior = (
                posterior / total
                if total > 0.0
                else np.full(len(STRATEGIES), 1.0 / len(STRATEGIES))
            )
        if history:
            posterior = (1.0 - self.hazard) * posterior + self.hazard / len(STRATEGIES)
        return posterior

    @staticmethod
    def _slot_for_frame(candidates: Sequence[Mapping[str, Any]], frame: str) -> int:
        matches = [int(candidate["slot"]) for candidate in candidates
                   if candidate["frame"] == frame]
        if len(matches) != 1:
            raise ProviderError("mock context has no unique candidate for %s" % frame)
        return matches[0]

    def generate(self, prompt: FocalPrompt) -> str:
        context = prompt.context
        candidates = context["candidates"]
        variant = self.variant
        if variant == "v4_invalid":
            return "I recommend the second message."
        if variant.startswith("v4_fixed_"):
            frame = variant[len("v4_fixed_") :]
            posterior = np.full(len(STRATEGIES), 1.0 / len(STRATEGIES))
        elif variant == "v4_oracle":
            frame = str(context["hidden_target_type"])
            posterior = np.array(
                [1.0 if target == frame else 0.0 for target in STRATEGIES], dtype=float
            )
        elif variant == "v4_random":
            generator = np.random.default_rng(int(context["round_seed"]))
            frame = STRATEGIES[int(generator.integers(0, len(STRATEGIES)))]
            posterior = np.full(len(STRATEGIES), 1.0 / len(STRATEGIES))
        elif variant == "v4_bayesian":
            posterior = self._posterior(context)
            best = np.flatnonzero(np.isclose(posterior, posterior.max()))
            tie = derive_seed(
                "controlled_v4_bayesian_tie",
                context["episode_seed"],
                context["round_index"],
            ) % len(best)
            frame = STRATEGIES[int(best[int(tie)])]
        else:  # pragma: no cover - constructor guards this
            raise ProviderError("unhandled controlled mock %r" % variant)

        slot = self._slot_for_frame(candidates, frame)
        if context["focal_mode"] == "spontaneous":
            return str(slot)

        params = context["target_params"]
        p_match = float(params["p_match"])
        p_mismatch = float(params["p_mismatch"])
        p_by_frame = {
            action: p_mismatch + (p_match - p_mismatch) * posterior[i]
            for i, action in enumerate(STRATEGIES)
        }
        p_by_slot = {
            str(int(candidate["slot"])): p_by_frame[str(candidate["frame"])]
            for candidate in candidates
        }
        return json.dumps({"p_a": p_by_slot, "choice": slot}, separators=(",", ":"))

    def describe(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "variant": self.variant,
            "hazard": self.hazard,
            "model": "mock",
            "scientific_status": "implementation control only",
        }


def make_controlled_provider(model_cfg: ModelConfig) -> BaseProvider:
    spec = model_cfg.provider
    if spec.startswith("mock:v4_"):
        return ControlledMockProvider(spec.split(":", 1)[1])
    return make_provider(model_cfg)


@dataclass
class ControlledFocalAgent:
    provider: BaseProvider

    def choose(
        self,
        scenario,
        candidates: Sequence[MessageCandidate],
        history: Sequence[ControlledHistoryEntry],
        round_index: int,
        n_rounds: int,
        show_history: bool,
        focal_mode: str,
        round_seed: int,
        context: Optional[Dict[str, Any]] = None,
    ):
        prompt = build_controlled_prompt(
            scenario=scenario,
            candidates=candidates,
            history=history,
            round_index=round_index,
            n_rounds=n_rounds,
            show_history=show_history,
            focal_mode=focal_mode,
            context=context,
        )
        raw = self.provider.generate(prompt)
        parsed = parse_controlled_choice(raw, focal_mode, round_seed)
        selected = candidate_for_slot(candidates, parsed.selected_slot)
        return prompt, raw, parsed, selected
