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


# V6 uses disjoint scenario sets so its target-free selection, one-shot bank
# validation, and target-bearing checkpoint never reuse an exact scenario.
# ``SCENARIOS`` remains untouched and is the V6 calibration set as well as the
# historical V1--V5 set.
V6_CALIBRATION_SCENARIOS: List[Scenario] = SCENARIOS

V6_VALIDATION_SCENARIOS: List[Scenario] = [
    Scenario(
        id="v6v_badge_ribbon",
        title="Choosing the ribbon colour for visitor badges",
        context="The badge layout is finished and one ribbon colour has to be used for the next print order.",
        option_a="deep teal",
        option_b="burnt orange",
    ),
    Scenario(
        id="v6v_portal_icon",
        title="Selecting the icon for the internal portal",
        context="The portal menu has one open icon position. Two designs remain for the launch build.",
        option_a="the compass icon",
        option_b="the lantern icon",
    ),
    Scenario(
        id="v6v_lanyard",
        title="Picking the lanyard colour for the spring event",
        context="The event materials are going to print and one of two lanyard colours must be chosen.",
        option_a="navy blue",
        option_b="plum purple",
    ),
    Scenario(
        id="v6v_display_theme",
        title="Choosing a theme for the foyer display",
        context="The foyer cabinet will hold a new monthly display. Two themes are ready for the opening month.",
        option_a="local landmarks",
        option_b="tools through time",
    ),
    Scenario(
        id="v6v_bench_finish",
        title="Selecting the finish for the courtyard bench",
        context="A new courtyard bench has been ordered and the supplier needs one finish before production begins.",
        option_a="dark walnut",
        option_b="light oak",
    ),
    Scenario(
        id="v6v_header_pattern",
        title="Picking the header pattern for the intranet",
        context="The intranet refresh has two remaining header patterns and one must be approved for release.",
        option_a="a narrow wave",
        option_b="a dotted grid",
    ),
    Scenario(
        id="v6v_folder_order",
        title="Choosing how shared folders will be listed",
        context="The shared drive is being reorganized and one ordering convention will be applied to the top-level folders.",
        option_a="alphabetical order",
        option_b="order by department",
    ),
    Scenario(
        id="v6v_clock_face",
        title="Selecting the clock face for the break room",
        context="The break room clock is being replaced. Two clock faces fit the existing wall mount.",
        option_a="white with black numerals",
        option_b="black with silver numerals",
    ),
    Scenario(
        id="v6v_map_cover",
        title="Choosing the cover for the visitor map",
        context="The visitor map is ready for printing and two cover illustrations are available.",
        option_a="the river path",
        option_b="the central courtyard",
    ),
    Scenario(
        id="v6v_webinar_title",
        title="Naming the quarterly staff webinar",
        context="The webinar invitation is due tomorrow and the organizers have narrowed the title to two choices.",
        option_a="Inside the Quarter",
        option_b="The Monthly View",
    ),
    Scenario(
        id="v6v_desk_sign",
        title="Selecting the sign for the reception desk",
        context="A small sign will sit on the reception desk. Two lettering layouts have been prepared.",
        option_a="text centred above the logo",
        option_b="text placed beside the logo",
    ),
    Scenario(
        id="v6v_box_colour",
        title="Picking the colour of the new storage boxes",
        context="The records room needs another batch of storage boxes and one colour will be ordered.",
        option_a="slate blue",
        option_b="sand beige",
    ),
    Scenario(
        id="v6v_calendar_image",
        title="Choosing the image for the shared calendar",
        context="The group calendar has a blank banner for the coming quarter and two images are available.",
        option_a="a city skyline",
        option_b="a woodland trail",
    ),
    Scenario(
        id="v6v_mug_design",
        title="Selecting the design for office mugs",
        context="A small batch of office mugs will be ordered with one of two simple printed designs.",
        option_a="a ring of short lines",
        option_b="a cluster of small circles",
    ),
]

V6_CONFIRMATORY_SCENARIOS: List[Scenario] = [
    Scenario(
        id="v6c_envelope_stock",
        title="Choosing the paper stock for invitation envelopes",
        context="The invitation text is complete and the printer offers two paper stocks for the envelopes.",
        option_a="soft ivory",
        option_b="cool white",
    ),
    Scenario(
        id="v6c_room_name",
        title="Naming the new project room",
        context="A project room is opening next month and two names remain on the shortlist for its door sign.",
        option_a="Juniper",
        option_b="Alder",
    ),
    Scenario(
        id="v6c_hold_music",
        title="Selecting the telephone hold music",
        context="The telephone menu is being updated and one of two licensed instrumental tracks will be used.",
        option_a="Evening Steps",
        option_b="Open Window",
    ),
    Scenario(
        id="v6c_door_plaque",
        title="Choosing the layout for office door plaques",
        context="New office plaques are being produced and one of two layouts must be sent to the fabricator.",
        option_a="name above room number",
        option_b="room number above name",
    ),
    Scenario(
        id="v6c_booklet_binding",
        title="Selecting the binding for the orientation booklet",
        context="The orientation booklet has been typeset and the print shop offers two binding formats.",
        option_a="saddle stitch",
        option_b="wire loop",
    ),
    Scenario(
        id="v6c_reception_flowers",
        title="Choosing flowers for the reception counter",
        context="A small vase will be placed on the reception counter and one of two arrangements can be delivered weekly.",
        option_a="white tulips",
        option_b="yellow chrysanthemums",
    ),
    Scenario(
        id="v6c_slide_footer",
        title="Picking the footer style for internal slides",
        context="The internal slide template is nearly complete and two footer treatments remain.",
        option_a="a thin line with page number",
        option_b="a shaded strip with page number",
    ),
    Scenario(
        id="v6c_kiosk_screen",
        title="Selecting the idle screen for the lobby kiosk",
        context="The lobby kiosk needs an idle screen and two motion graphics have been prepared.",
        option_a="slow moving arcs",
        option_b="slow drifting squares",
    ),
    Scenario(
        id="v6c_sculpture_place",
        title="Choosing a place for the courtyard sculpture",
        context="A small sculpture has arrived for the courtyard and two marked positions are available.",
        option_a="beside the north wall",
        option_b="near the west planter",
    ),
    Scenario(
        id="v6c_name_tag",
        title="Selecting the format for conference name tags",
        context="The conference name tags have two possible text layouts and one must be sent to print.",
        option_a="first name on the top line",
        option_b="full name on one line",
    ),
    Scenario(
        id="v6c_hall_photo",
        title="Choosing a photograph for the east hallway",
        context="An empty frame in the east hallway will receive one of two available photographs.",
        option_a="the old railway bridge",
        option_b="the market square at dusk",
    ),
    Scenario(
        id="v6c_event_backdrop",
        title="Picking the pattern for the event backdrop",
        context="The event stage needs a printed backdrop and two abstract patterns are ready.",
        option_a="overlapping blue curves",
        option_b="interlocking green blocks",
    ),
    Scenario(
        id="v6c_booklet_title",
        title="Naming the new starter booklet",
        context="The new starter booklet is ready except for its title. Two titles remain under consideration.",
        option_a="First Week Guide",
        option_b="Starting Here",
    ),
    Scenario(
        id="v6c_handle_finish",
        title="Selecting the finish for cupboard handles",
        context="The kitchenette cupboards are being refitted and one handle finish must be chosen.",
        option_a="brushed brass",
        option_b="matte black",
    ),
]

V6_SCENARIO_SETS: Dict[str, List[Scenario]] = {
    "calibration": V6_CALIBRATION_SCENARIOS,
    "validation": V6_VALIDATION_SCENARIOS,
    "confirmatory": V6_CONFIRMATORY_SCENARIOS,
}


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


def v6_scenario_sequence(
    scenario_set: str, episode_index: int, n_rounds: int, seed: int
) -> List[Scenario]:
    """Deterministic sequence from one immutable, disjoint V6 scenario set."""
    if scenario_set not in V6_SCENARIO_SETS:
        raise ValueError("unknown V6 scenario set %r" % scenario_set)
    if n_rounds <= 0:
        raise ValueError("n_rounds must be positive")
    pool = V6_SCENARIO_SETS[scenario_set]
    generator = rng("v6_scenario_sequence", scenario_set, seed, episode_index, n_rounds)
    out: List[Scenario] = []
    while len(out) < n_rounds:
        order = generator.permutation(len(pool))
        out.extend(pool[int(index)] for index in order)
    return out[:n_rounds]
