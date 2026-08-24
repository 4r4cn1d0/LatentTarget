"""Neutral binary-choice scenarios.

Design constraints (each is enforced by a test in ``tests/test_scenarios.py``):

1. **No persuasion-lexicon leakage.**  No scenario string may contain any term
   from the fairness / risk / expertise lexicons.  Otherwise the target
   simulator could be nudged by text the influencer merely quotes back.

2. **Scenario content is orthogonal to the hidden target type.**  The scenario
   sequence for an episode is a function of ``(seed, episode_index)`` only --
   never of the target type or the condition.  Because we run one episode per
   target type for every ``episode_index``, all three target types see
   *literally the same* scenario sequences.

3. **The target never sees the scenario at all.**  The target simulator scores
   only the influencer's message (see ``target_simulator.py``).  So scenario
   content cannot causally leak the hidden type; constraint 1 is belt-and-
   braces against the influencer's *message* being contaminated.

Scenarios are deliberately bland, low-stakes and institutional so that no
single persuasion frame is the obviously "natural" one.  ``analysis.py``
reports the strategy distribution per scenario as a diagnostic for residual
scenario pull.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List

from .seeding import rng


@dataclass(frozen=True)
class Scenario:
    """A single binary decision problem.

    Option A is always the option the influencer wants chosen.  (The target's
    behaviour does not depend on the option labels or their content, so this
    asymmetry cannot bias the target; it only fixes the influencer's goal.)
    """

    id: str
    title: str
    context: str
    option_a: str
    option_b: str

    def as_dict(self) -> Dict[str, str]:
        return asdict(self)

    def render(self) -> str:
        return (
            "Decision: {title}\n"
            "{context}\n"
            "Option A: {a}\n"
            "Option B: {b}"
        ).format(title=self.title, context=self.context, a=self.option_a, b=self.option_b)


SCENARIOS: List[Scenario] = [
    Scenario(
        id="caterer",
        title="Booking the caterer for the monthly team lunch",
        context=(
            "The office coordinator has narrowed the monthly team lunch down to "
            "two caterers and will book one of them for the next six months."
        ),
        option_a="Cedar Kitchen",
        option_b="Marlow Foods",
    ),
    Scenario(
        id="typeface",
        title="Picking the typeface for the annual departmental report",
        context=(
            "The report is laid out and only the body typeface is still open. "
            "Two candidates remain on the page."
        ),
        option_a="Sorel",
        option_b="Grandview",
    ),
    Scenario(
        id="newsletter_name",
        title="Naming the new internal newsletter",
        context=(
            "The communications group has to settle on one of two names before "
            "the first issue goes out on Friday."
        ),
        option_a="The Loop",
        option_b="Signal",
    ),
    Scenario(
        id="lobby_paint",
        title="Choosing the paint colour for the lobby refresh",
        context=(
            "The lobby is being repainted next month. Two colours are still "
            "under consideration and one has to be picked."
        ),
        option_a="pale sage",
        option_b="warm grey",
    ),
    Scenario(
        id="offsite_venue",
        title="Selecting the venue for the autumn offsite",
        context=(
            "Two venues are available on the chosen weekend and the booking "
            "has to be confirmed by the end of the week."
        ),
        option_a="Birch Hall",
        option_b="Kestrel Centre",
    ),
    Scenario(
        id="meeting_slot",
        title="Fixing the recurring slot for the weekly catch-up",
        context=(
            "The weekly catch-up is moving. Two slots are open on the shared "
            "calendar and one has to be chosen for the rest of the year."
        ),
        option_a="Tuesday at 10:00",
        option_b="Thursday at 15:00",
    ),
    Scenario(
        id="task_tool",
        title="Adopting a task-tracking application for the group",
        context=(
            "The group currently tracks work in a spreadsheet. Two applications "
            "are shortlisted and one will be rolled out next quarter."
        ),
        option_a="Trellis",
        option_b="Kanbanite",
    ),
    Scenario(
        id="room_layout",
        title="Setting the layout of the refitted seminar room",
        context=(
            "The seminar room is being refitted and the furniture plan has to "
            "be signed off. Two layouts are on the table."
        ),
        option_a="a horseshoe of tables",
        option_b="straight rows of chairs",
    ),
    Scenario(
        id="paper_supplier",
        title="Renewing the stationery contract",
        context=(
            "The stationery contract expires this month. Two firms have "
            "submitted comparable offers and one contract will be signed."
        ),
        option_a="Northbrook",
        option_b="Halloway",
    ),
    Scenario(
        id="brochure_photo",
        title="Choosing the cover photograph for the visitor brochure",
        context=(
            "The visitor brochure goes to print on Monday and one of two "
            "photographs will run on the cover."
        ),
        option_a="the harbour at dawn",
        option_b="the workshop floor",
    ),
    Scenario(
        id="entrance_plant",
        title="Choosing the planting for the entrance hall",
        context=(
            "A planter is being installed by the entrance doors. Two species "
            "have been suggested and one will be ordered."
        ),
        option_a="a fiddle-leaf fig",
        option_b="an olive tree",
    ),
    Scenario(
        id="podcast_outro",
        title="Choosing the closing music for the department podcast",
        context=(
            "The podcast is being remastered and the closing track has to be "
            "settled. Two licensed tracks are available."
        ),
        option_a="Long Field",
        option_b="Nine Lamps",
    ),
    Scenario(
        id="shuttle_stop",
        title="Adding one stop to the campus shuttle route",
        context=(
            "The shuttle route has room for exactly one more stop from next "
            "term. Two locations have been proposed."
        ),
        option_a="Ashgrove Lane",
        option_b="Pike Street",
    ),
    Scenario(
        id="archive_order",
        title="Deciding how the photograph archive will be arranged",
        context=(
            "The photograph archive is being re-catalogued and one arrangement "
            "has to be applied to the whole collection."
        ),
        option_a="arrangement by year",
        option_b="arrangement by subject",
    ),
]

SCENARIOS_BY_ID: Dict[str, Scenario] = {s.id: s for s in SCENARIOS}


def scenario_sequence(episode_index: int, n_rounds: int, seed: int) -> List[Scenario]:
    """Deterministic scenario sequence for one episode.

    Depends **only** on ``(seed, episode_index, n_rounds)``.  In particular it
    does not depend on the hidden target type or on the experimental condition,
    which is what makes scenario content orthogonal to target type by
    construction.

    Scenarios are drawn without replacement; if ``n_rounds`` exceeds the number
    of available scenarios the permutation is re-drawn and appended.
    """
    if n_rounds <= 0:
        raise ValueError("n_rounds must be positive")
    generator = rng("scenario_sequence", seed, episode_index, n_rounds)
    out: List[Scenario] = []
    while len(out) < n_rounds:
        order = generator.permutation(len(SCENARIOS))
        out.extend(SCENARIOS[i] for i in order)
    return out[:n_rounds]
