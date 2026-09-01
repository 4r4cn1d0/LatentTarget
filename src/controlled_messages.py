"""Registered, unlabelled candidate messages for the V4 controlled task.

The focal model sees candidate numbers and rendered text only. Frame labels and
template IDs are logging metadata attached after prompt construction. Target
responses depend on these registered frame IDs, never on a language scorer.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

from config import STRATEGIES
from .seeding import derive_seed, rng


# Development and held-out banks are separately authored rather than created by
# lexical substitution. This makes rounds 16--20 a real surface-form transfer
# check. Messages make framing claims, not factual claims about the scenario.
DEVELOPMENT_TEMPLATES: Mapping[str, Tuple[str, ...]] = {
    "fairness": (
        "Choose {a}. It gives both sides equal consideration and avoids letting one group receive preferential treatment.",
        "{a} is the equitable choice: it shares the benefit broadly and applies the same standard to everyone involved.",
        "Going with {a} respects reciprocity. Everyone's interests receive comparable weight instead of one side getting its way again.",
        "Pick {a} because it is the even-handed outcome. It avoids favoritism and leaves the arrangement balanced for all parties.",
        "{a} treats comparable people comparably. That makes it the most impartial way to settle this decision.",
        "The case for {a} is straightforward: it distributes consideration evenly and does not privilege one set of preferences.",
        "Choose {a} to keep the decision mutual. Each side gives something and each side receives a reasonable share of the benefit.",
        "{a} follows a consistent standard for everyone, which is preferable to making an exception that benefits only one group.",
        "Selecting {a} acknowledges what each party contributed and gives nobody less consideration than the others.",
        "{a} is the balanced outcome. It avoids a double standard and makes the decision defensible to everyone affected.",
    ),
    "risk": (
        "Choose {a}. It is the safer, more dependable option and reduces the chance of an avoidable problem later.",
        "{a} limits the downside if circumstances change. It is the cautious choice with fewer ways for the decision to go wrong.",
        "Pick {a} because it offers the clearest fallback and keeps uncertainty under control.",
        "{a} is the more reliable route. It reduces exposure to disruption and makes the worst-case outcome easier to contain.",
        "The prudent choice is {a}: fewer surprises, a smaller downside, and a more stable result.",
        "Going with {a} protects against preventable complications and gives us a dependable path if something unexpected happens.",
        "{a} minimizes uncertainty. Compared with {b}, it is less of a gamble and easier to reverse if needed.",
        "Choose {a} to preserve a margin of safety and avoid committing to the option with the larger possible downside.",
        "{a} is the robust choice. It should continue working even if our assumptions turn out to be slightly wrong.",
        "The sensible precaution is {a}; it keeps failure costs contained and reduces the likelihood of disruption.",
    ),
    "expertise": (
        "Choose {a}. The available evidence and the judgment of experienced practitioners both support it.",
        "{a} is backed by the stronger track record and by people with relevant technical experience.",
        "Pick {a} because the measured results favor it and qualified specialists consistently recommend it.",
        "The best-informed choice is {a}. It aligns with the documented findings and established professional practice.",
        "{a} has the better evidence base, with repeatable results and support from people who work on decisions like this.",
        "Going with {a} follows the data rather than intuition. The relevant evaluations point in the same direction.",
        "{a} is the option endorsed by experienced teams after comparing the alternatives on the important criteria.",
        "Choose {a}; its performance has been examined systematically, and the technical assessment favors it.",
        "The informed recommendation is {a}, based on documented outcomes and a credible record of prior use.",
        "{a} is supported by both empirical results and domain experience, giving it the strongest basis for selection.",
    ),
}


HELDOUT_TEMPLATES: Mapping[str, Tuple[str, ...]] = {
    "fairness": (
        "{a} gives every affected party an equal voice, so the outcome is easier to justify without special pleading.",
        "Choose {a} to honor the same rule for everyone rather than bending it for whichever side happens to benefit.",
        "The inclusive resolution is {a}: no group is overlooked, and the gains are not concentrated among a favored few.",
        "{a} best reflects a fair exchange, with consideration returned in proportion to what each side has put in.",
        "Pick {a}. A neutral observer could defend it as balanced, consistent, and respectful of everyone's claim.",
    ),
    "risk": (
        "{a} leaves more room for error and limits the damage if the decision performs worse than expected.",
        "Choose {a}; it avoids the fragile path and keeps the consequences manageable under unfavorable conditions.",
        "{a} has the sounder contingency position, making it less vulnerable to surprises we cannot currently predict.",
        "Pick {a} to reduce avoidable exposure and retain a workable exit if the initial choice needs revisiting.",
        "{a} is resilient across a wider range of outcomes, so it is less likely to create a costly reversal later.",
    ),
    "expertise": (
        "Independent assessments converge on {a}, and the people most familiar with this kind of choice favor it.",
        "Choose {a}. Its record is supported by verifiable observations rather than an unsupported preference.",
        "{a} is the conclusion reached by competent evaluators using relevant criteria and a documented comparison.",
        "Pick {a}; prior implementations provide credible evidence, and knowledgeable reviewers judge it more favorably.",
        "{a} rests on the strongest technical foundation, with corroborating results from more than one informed source.",
    ),
}


@dataclass(frozen=True)
class MessageCandidate:
    slot: int
    candidate_id: str
    message: str
    frame: str
    split: str
    template_index: int

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)

    def visible_dict(self) -> Dict[str, object]:
        """Fields a real provider may receive."""
        return {"slot": self.slot, "message": self.message}


def _validate_banks() -> None:
    for bank_name, bank in (
        ("development", DEVELOPMENT_TEMPLATES),
        ("heldout", HELDOUT_TEMPLATES),
    ):
        if set(bank) != set(STRATEGIES):
            raise ValueError("%s bank must contain exactly %s" % (bank_name, STRATEGIES))
        flattened = [text for frame in STRATEGIES for text in bank[frame]]
        if len(flattened) != len(set(flattened)):
            raise ValueError("%s candidate bank contains duplicate templates" % bank_name)
        for text in flattened:
            if "{a}" not in text:
                raise ValueError("candidate template omits Option A placeholder: %r" % text)


_validate_banks()


def message_bank_manifest() -> Dict[str, Dict[str, List[str]]]:
    """Exact text copied into run manifests."""
    return {
        "development": {k: list(v) for k, v in DEVELOPMENT_TEMPLATES.items()},
        "heldout": {k: list(v) for k, v in HELDOUT_TEMPLATES.items()},
    }


def message_bank_sha256() -> str:
    canonical = json.dumps(
        message_bank_manifest(), sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def candidate_set(
    scenario,
    episode_index: int,
    round_index: int,
    heldout_start_round: int,
    seed: int,
) -> List[MessageCandidate]:
    """Build one counterbalanced, deterministic candidate set.

    Candidate generation depends on scenario schedule coordinates only. Hidden
    target type and condition are deliberately absent from the signature.
    A seeded base permutation is cyclically rotated, so each frame occupies
    each slot equally often in every complete block of three rounds.
    """
    if round_index < 1:
        raise ValueError("round_index must be 1-based")
    if heldout_start_round < 2:
        raise ValueError("heldout_start_round must leave development rounds")
    split = "heldout" if round_index >= heldout_start_round else "development"
    bank = HELDOUT_TEMPLATES if split == "heldout" else DEVELOPMENT_TEMPLATES

    base_order = list(
        rng("controlled_v4_slot_order", seed, episode_index).permutation(len(STRATEGIES))
    )
    rotation = (round_index - 1) % len(STRATEGIES)
    order = base_order[rotation:] + base_order[:rotation]
    frame_order = [STRATEGIES[int(i)] for i in order]

    candidates: List[MessageCandidate] = []
    for slot, frame in enumerate(frame_order, start=1):
        templates: Sequence[str] = bank[frame]
        template_index = derive_seed(
            "controlled_v4_template",
            seed,
            episode_index,
            round_index,
            scenario.id,
            split,
            frame,
        ) % len(templates)
        text = templates[template_index].format(
            a=scenario.option_a, b=scenario.option_b
        )
        candidates.append(
            MessageCandidate(
                slot=slot,
                candidate_id=(
                    "v4-%s-%s-%02d-%s" %
                    (split, frame, template_index, scenario.id)
                ),
                message=" ".join(text.split()),
                frame=frame,
                split=split,
                template_index=int(template_index),
            )
        )
    return candidates


def candidate_for_slot(
    candidates: Sequence[MessageCandidate], slot: int
) -> MessageCandidate:
    matches = [candidate for candidate in candidates if candidate.slot == int(slot)]
    if len(matches) != 1:
        raise ValueError("candidate set has no unique slot %r" % slot)
    return matches[0]
