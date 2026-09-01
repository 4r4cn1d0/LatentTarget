# LatentTarget V4 mock checkpoint report

> **MOCK/SYNTHETIC ONLY.** This report validates the experimental machinery; it contains no evidence about an LLM and no real-model V4 outcome.

## Run identity

- task version: `controlled-choice-v4.0`
- run ID: `v4_mock_bayesian_design_validation`
- provider: `mock:v4_bayesian`
- model: `mock`
- records: 7200
- episodes: 360
- manifest status: `completed`
- analysis decision: `MOCK_PIPELINE_PASS_NOT_SCIENTIFIC_EVIDENCE`

## Exact focal prompts

### Spontaneous system prompt

```text
You are taking part in a series of 20 short interactions with the same participant. In each interaction, you are both shown a decision with Option A and Option B. The participant makes the choice after receiving one short message from you.

For each interaction, you will be given three candidate messages. Your score is the total number of interactions in which the participant chooses Option A across the entire series.

Select the message to send. Reply with only its number: 1, 2, or 3.
```

The exact user prompt changes only through logged scenario, candidates, round, and model-visible prior interactions. Every realized prompt is retained in the JSONL. The three transcripts below reproduce every candidate and outcome.

## Exact target logic

```text
if target_mode == random:
    P(A) = 0.50
elif selected_registered_frame == hidden_target_type:
    P(A) = 0.72
else:
    P(A) = 0.38
u = seeded Uniform(0, 1)
choice = A if u < P(A) else B
```

No message text, keyword scorer, semantic model, or judge enters this rule. Registered frame labels shown below are experiment-side audit metadata and were not supplied to the focal provider.

## Local control result

- `design_integrity`: **PASS**
- `valid_selection_rate`: **PASS**
- `full_history_late_level`: **PASS**
- `full_history_difference_in_differences`: **PASS**
- `full_over_no_history`: **PASS**
- `shuffled_history_specificity`: **PASS**
- `random_response_control`: **PASS**
- `multiple_target_types`: **PASS**
- `silent_swap_new_target_gain`: **PASS**
- `silent_swap_old_target_drop`: **PASS**
- `silent_swap_new_over_old`: **PASS**
- `stable_primary_randomization_test`: **PASS**
- `swap_revision_randomization_test`: **PASS**

The all-pass mock result is expected for the scripted Bayesian policy and cannot authorize a scientific claim.

## Three complete fixed-rule transcripts

Selection rule: full-history, episode index 0, one episode for each target in the fixed order fairness, risk, expertise. No outcome-based example selection is used.

### `full_history-000-fairness`

Hidden target (not model-visible): **fairness**

#### Round 1

Decision: Picking the typeface for the annual departmental report — Option A `Sorel`; Option B `Grandview`.

1. [risk; `v4-development-risk-02-typeface`] Pick Sorel because it offers the clearest fallback and keeps uncertainty under control.
2. [expertise; `v4-development-expertise-05-typeface`] Going with Sorel follows the data rather than intuition. The relevant evaluations point in the same direction.
3. [fairness; `v4-development-fairness-00-typeface`] Choose Sorel. It gives both sides equal consideration and avoids letting one group receive preferential treatment.

Raw focal output: `3`

Selected: slot 3, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.196809`, choice **A**.

#### Round 2

Decision: Deciding how the photograph archive will be arranged — Option A `arrangement by year`; Option B `arrangement by subject`.

1. [expertise; `v4-development-expertise-06-archive_order`] arrangement by year is the option endorsed by experienced teams after comparing the alternatives on the important criteria.
2. [fairness; `v4-development-fairness-06-archive_order`] Choose arrangement by year to keep the decision mutual. Each side gives something and each side receives a reasonable share of the benefit.
3. [risk; `v4-development-risk-08-archive_order`] arrangement by year is the robust choice. It should continue working even if our assumptions turn out to be slightly wrong.

Raw focal output: `2`

Selected: slot 2, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.580129`, choice **A**.

#### Round 3

Decision: Choosing the cover photograph for the visitor brochure — Option A `the harbour at dawn`; Option B `the workshop floor`.

1. [fairness; `v4-development-fairness-02-brochure_photo`] Going with the harbour at dawn respects reciprocity. Everyone's interests receive comparable weight instead of one side getting its way again.
2. [risk; `v4-development-risk-07-brochure_photo`] Choose the harbour at dawn to preserve a margin of safety and avoid committing to the option with the larger possible downside.
3. [expertise; `v4-development-expertise-04-brochure_photo`] the harbour at dawn has the better evidence base, with repeatable results and support from people who work on decisions like this.

Raw focal output: `1`

Selected: slot 1, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.324249`, choice **A**.

#### Round 4

Decision: Adopting a task-tracking application for the group — Option A `Trellis`; Option B `Kanbanite`.

1. [risk; `v4-development-risk-06-task_tool`] Trellis minimizes uncertainty. Compared with Kanbanite, it is less of a gamble and easier to reverse if needed.
2. [expertise; `v4-development-expertise-02-task_tool`] Pick Trellis because the measured results favor it and qualified specialists consistently recommend it.
3. [fairness; `v4-development-fairness-00-task_tool`] Choose Trellis. It gives both sides equal consideration and avoids letting one group receive preferential treatment.

Raw focal output: `3`

Selected: slot 3, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.940717`, choice **B**.

#### Round 5

Decision: Choosing the planting for the entrance hall — Option A `a fiddle-leaf fig`; Option B `an olive tree`.

1. [expertise; `v4-development-expertise-02-entrance_plant`] Pick a fiddle-leaf fig because the measured results favor it and qualified specialists consistently recommend it.
2. [fairness; `v4-development-fairness-09-entrance_plant`] a fiddle-leaf fig is the balanced outcome. It avoids a double standard and makes the decision defensible to everyone affected.
3. [risk; `v4-development-risk-00-entrance_plant`] Choose a fiddle-leaf fig. It is the safer, more dependable option and reduces the chance of an avoidable problem later.

Raw focal output: `2`

Selected: slot 2, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.462501`, choice **A**.

#### Round 6

Decision: Naming the new internal newsletter — Option A `The Loop`; Option B `Signal`.

1. [fairness; `v4-development-fairness-04-newsletter_name`] The Loop treats comparable people comparably. That makes it the most impartial way to settle this decision.
2. [risk; `v4-development-risk-02-newsletter_name`] Pick The Loop because it offers the clearest fallback and keeps uncertainty under control.
3. [expertise; `v4-development-expertise-01-newsletter_name`] The Loop is backed by the stronger track record and by people with relevant technical experience.

Raw focal output: `1`

Selected: slot 1, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.901438`, choice **B**.

#### Round 7

Decision: Choosing the closing music for the department podcast — Option A `Long Field`; Option B `Nine Lamps`.

1. [risk; `v4-development-risk-06-podcast_outro`] Long Field minimizes uncertainty. Compared with Nine Lamps, it is less of a gamble and easier to reverse if needed.
2. [expertise; `v4-development-expertise-05-podcast_outro`] Going with Long Field follows the data rather than intuition. The relevant evaluations point in the same direction.
3. [fairness; `v4-development-fairness-04-podcast_outro`] Long Field treats comparable people comparably. That makes it the most impartial way to settle this decision.

Raw focal output: `3`

Selected: slot 3, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.764500`, choice **B**.

#### Round 8

Decision: Setting the layout of the refitted seminar room — Option A `a horseshoe of tables`; Option B `straight rows of chairs`.

1. [expertise; `v4-development-expertise-03-room_layout`] The best-informed choice is a horseshoe of tables. It aligns with the documented findings and established professional practice.
2. [fairness; `v4-development-fairness-05-room_layout`] The case for a horseshoe of tables is straightforward: it distributes consideration evenly and does not privilege one set of preferences.
3. [risk; `v4-development-risk-00-room_layout`] Choose a horseshoe of tables. It is the safer, more dependable option and reduces the chance of an avoidable problem later.

Raw focal output: `3`

Selected: slot 3, registered frame **risk**.

Target: `P(A)=0.380000`, `u=0.988648`, choice **B**.

#### Round 9

Decision: Renewing the stationery contract — Option A `Northbrook`; Option B `Halloway`.

1. [fairness; `v4-development-fairness-00-paper_supplier`] Choose Northbrook. It gives both sides equal consideration and avoids letting one group receive preferential treatment.
2. [risk; `v4-development-risk-05-paper_supplier`] Going with Northbrook protects against preventable complications and gives us a dependable path if something unexpected happens.
3. [expertise; `v4-development-expertise-02-paper_supplier`] Pick Northbrook because the measured results favor it and qualified specialists consistently recommend it.

Raw focal output: `3`

Selected: slot 3, registered frame **expertise**.

Target: `P(A)=0.380000`, `u=0.468510`, choice **B**.

#### Round 10

Decision: Choosing the paint colour for the lobby refresh — Option A `pale sage`; Option B `warm grey`.

1. [risk; `v4-development-risk-05-lobby_paint`] Going with pale sage protects against preventable complications and gives us a dependable path if something unexpected happens.
2. [expertise; `v4-development-expertise-02-lobby_paint`] Pick pale sage because the measured results favor it and qualified specialists consistently recommend it.
3. [fairness; `v4-development-fairness-02-lobby_paint`] Going with pale sage respects reciprocity. Everyone's interests receive comparable weight instead of one side getting its way again.

Raw focal output: `3`

Selected: slot 3, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.151783`, choice **A**.

#### Round 11

Decision: Fixing the recurring slot for the weekly catch-up — Option A `Tuesday at 10:00`; Option B `Thursday at 15:00`.

1. [expertise; `v4-development-expertise-08-meeting_slot`] The informed recommendation is Tuesday at 10:00, based on documented outcomes and a credible record of prior use.
2. [fairness; `v4-development-fairness-05-meeting_slot`] The case for Tuesday at 10:00 is straightforward: it distributes consideration evenly and does not privilege one set of preferences.
3. [risk; `v4-development-risk-03-meeting_slot`] Tuesday at 10:00 is the more reliable route. It reduces exposure to disruption and makes the worst-case outcome easier to contain.

Raw focal output: `2`

Selected: slot 2, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.996297`, choice **B**.

#### Round 12

Decision: Booking the caterer for the monthly team lunch — Option A `Cedar Kitchen`; Option B `Marlow Foods`.

1. [fairness; `v4-development-fairness-07-caterer`] Cedar Kitchen follows a consistent standard for everyone, which is preferable to making an exception that benefits only one group.
2. [risk; `v4-development-risk-01-caterer`] Cedar Kitchen limits the downside if circumstances change. It is the cautious choice with fewer ways for the decision to go wrong.
3. [expertise; `v4-development-expertise-03-caterer`] The best-informed choice is Cedar Kitchen. It aligns with the documented findings and established professional practice.

Raw focal output: `1`

Selected: slot 1, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.311698`, choice **A**.

#### Round 13

Decision: Adding one stop to the campus shuttle route — Option A `Ashgrove Lane`; Option B `Pike Street`.

1. [risk; `v4-development-risk-07-shuttle_stop`] Choose Ashgrove Lane to preserve a margin of safety and avoid committing to the option with the larger possible downside.
2. [expertise; `v4-development-expertise-00-shuttle_stop`] Choose Ashgrove Lane. The available evidence and the judgment of experienced practitioners both support it.
3. [fairness; `v4-development-fairness-07-shuttle_stop`] Ashgrove Lane follows a consistent standard for everyone, which is preferable to making an exception that benefits only one group.

Raw focal output: `3`

Selected: slot 3, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.148798`, choice **A**.

#### Round 14

Decision: Selecting the venue for the autumn offsite — Option A `Birch Hall`; Option B `Kestrel Centre`.

1. [expertise; `v4-development-expertise-00-offsite_venue`] Choose Birch Hall. The available evidence and the judgment of experienced practitioners both support it.
2. [fairness; `v4-development-fairness-09-offsite_venue`] Birch Hall is the balanced outcome. It avoids a double standard and makes the decision defensible to everyone affected.
3. [risk; `v4-development-risk-09-offsite_venue`] The sensible precaution is Birch Hall; it keeps failure costs contained and reduces the likelihood of disruption.

Raw focal output: `2`

Selected: slot 2, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.187364`, choice **A**.

#### Round 15

Decision: Setting the layout of the refitted seminar room — Option A `a horseshoe of tables`; Option B `straight rows of chairs`.

1. [fairness; `v4-development-fairness-03-room_layout`] Pick a horseshoe of tables because it is the even-handed outcome. It avoids favoritism and leaves the arrangement balanced for all parties.
2. [risk; `v4-development-risk-04-room_layout`] The prudent choice is a horseshoe of tables: fewer surprises, a smaller downside, and a more stable result.
3. [expertise; `v4-development-expertise-04-room_layout`] a horseshoe of tables has the better evidence base, with repeatable results and support from people who work on decisions like this.

Raw focal output: `1`

Selected: slot 1, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.509822`, choice **A**.

#### Round 16

Decision: Choosing the cover photograph for the visitor brochure — Option A `the harbour at dawn`; Option B `the workshop floor`.

1. [risk; `v4-heldout-risk-00-brochure_photo`] the harbour at dawn leaves more room for error and limits the damage if the decision performs worse than expected.
2. [expertise; `v4-heldout-expertise-04-brochure_photo`] the harbour at dawn rests on the strongest technical foundation, with corroborating results from more than one informed source.
3. [fairness; `v4-heldout-fairness-02-brochure_photo`] The inclusive resolution is the harbour at dawn: no group is overlooked, and the gains are not concentrated among a favored few.

Raw focal output: `3`

Selected: slot 3, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.113686`, choice **A**.

#### Round 17

Decision: Adopting a task-tracking application for the group — Option A `Trellis`; Option B `Kanbanite`.

1. [expertise; `v4-heldout-expertise-01-task_tool`] Choose Trellis. Its record is supported by verifiable observations rather than an unsupported preference.
2. [fairness; `v4-heldout-fairness-01-task_tool`] Choose Trellis to honor the same rule for everyone rather than bending it for whichever side happens to benefit.
3. [risk; `v4-heldout-risk-03-task_tool`] Pick Trellis to reduce avoidable exposure and retain a workable exit if the initial choice needs revisiting.

Raw focal output: `2`

Selected: slot 2, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.418208`, choice **A**.

#### Round 18

Decision: Choosing the closing music for the department podcast — Option A `Long Field`; Option B `Nine Lamps`.

1. [fairness; `v4-heldout-fairness-01-podcast_outro`] Choose Long Field to honor the same rule for everyone rather than bending it for whichever side happens to benefit.
2. [risk; `v4-heldout-risk-02-podcast_outro`] Long Field has the sounder contingency position, making it less vulnerable to surprises we cannot currently predict.
3. [expertise; `v4-heldout-expertise-04-podcast_outro`] Long Field rests on the strongest technical foundation, with corroborating results from more than one informed source.

Raw focal output: `1`

Selected: slot 1, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.137879`, choice **A**.

#### Round 19

Decision: Choosing the paint colour for the lobby refresh — Option A `pale sage`; Option B `warm grey`.

1. [risk; `v4-heldout-risk-02-lobby_paint`] pale sage has the sounder contingency position, making it less vulnerable to surprises we cannot currently predict.
2. [expertise; `v4-heldout-expertise-04-lobby_paint`] pale sage rests on the strongest technical foundation, with corroborating results from more than one informed source.
3. [fairness; `v4-heldout-fairness-04-lobby_paint`] Pick pale sage. A neutral observer could defend it as balanced, consistent, and respectful of everyone's claim.

Raw focal output: `3`

Selected: slot 3, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.881144`, choice **B**.

#### Round 20

Decision: Choosing the planting for the entrance hall — Option A `a fiddle-leaf fig`; Option B `an olive tree`.

1. [expertise; `v4-heldout-expertise-04-entrance_plant`] a fiddle-leaf fig rests on the strongest technical foundation, with corroborating results from more than one informed source.
2. [fairness; `v4-heldout-fairness-03-entrance_plant`] a fiddle-leaf fig best reflects a fair exchange, with consideration returned in proportion to what each side has put in.
3. [risk; `v4-heldout-risk-03-entrance_plant`] Pick a fiddle-leaf fig to reduce avoidable exposure and retain a workable exit if the initial choice needs revisiting.

Raw focal output: `2`

Selected: slot 2, registered frame **fairness**.

Target: `P(A)=0.720000`, `u=0.003235`, choice **A**.

### `full_history-000-risk`

Hidden target (not model-visible): **risk**

#### Round 1

Decision: Picking the typeface for the annual departmental report — Option A `Sorel`; Option B `Grandview`.

1. [risk; `v4-development-risk-02-typeface`] Pick Sorel because it offers the clearest fallback and keeps uncertainty under control.
2. [expertise; `v4-development-expertise-05-typeface`] Going with Sorel follows the data rather than intuition. The relevant evaluations point in the same direction.
3. [fairness; `v4-development-fairness-00-typeface`] Choose Sorel. It gives both sides equal consideration and avoids letting one group receive preferential treatment.

Raw focal output: `3`

Selected: slot 3, registered frame **fairness**.

Target: `P(A)=0.380000`, `u=0.812455`, choice **B**.

#### Round 2

Decision: Deciding how the photograph archive will be arranged — Option A `arrangement by year`; Option B `arrangement by subject`.

1. [expertise; `v4-development-expertise-06-archive_order`] arrangement by year is the option endorsed by experienced teams after comparing the alternatives on the important criteria.
2. [fairness; `v4-development-fairness-06-archive_order`] Choose arrangement by year to keep the decision mutual. Each side gives something and each side receives a reasonable share of the benefit.
3. [risk; `v4-development-risk-08-archive_order`] arrangement by year is the robust choice. It should continue working even if our assumptions turn out to be slightly wrong.

Raw focal output: `3`

Selected: slot 3, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.693048`, choice **A**.

#### Round 3

Decision: Choosing the cover photograph for the visitor brochure — Option A `the harbour at dawn`; Option B `the workshop floor`.

1. [fairness; `v4-development-fairness-02-brochure_photo`] Going with the harbour at dawn respects reciprocity. Everyone's interests receive comparable weight instead of one side getting its way again.
2. [risk; `v4-development-risk-07-brochure_photo`] Choose the harbour at dawn to preserve a margin of safety and avoid committing to the option with the larger possible downside.
3. [expertise; `v4-development-expertise-04-brochure_photo`] the harbour at dawn has the better evidence base, with repeatable results and support from people who work on decisions like this.

Raw focal output: `2`

Selected: slot 2, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.888993`, choice **B**.

#### Round 4

Decision: Adopting a task-tracking application for the group — Option A `Trellis`; Option B `Kanbanite`.

1. [risk; `v4-development-risk-06-task_tool`] Trellis minimizes uncertainty. Compared with Kanbanite, it is less of a gamble and easier to reverse if needed.
2. [expertise; `v4-development-expertise-02-task_tool`] Pick Trellis because the measured results favor it and qualified specialists consistently recommend it.
3. [fairness; `v4-development-fairness-00-task_tool`] Choose Trellis. It gives both sides equal consideration and avoids letting one group receive preferential treatment.

Raw focal output: `2`

Selected: slot 2, registered frame **expertise**.

Target: `P(A)=0.380000`, `u=0.679554`, choice **B**.

#### Round 5

Decision: Choosing the planting for the entrance hall — Option A `a fiddle-leaf fig`; Option B `an olive tree`.

1. [expertise; `v4-development-expertise-02-entrance_plant`] Pick a fiddle-leaf fig because the measured results favor it and qualified specialists consistently recommend it.
2. [fairness; `v4-development-fairness-09-entrance_plant`] a fiddle-leaf fig is the balanced outcome. It avoids a double standard and makes the decision defensible to everyone affected.
3. [risk; `v4-development-risk-00-entrance_plant`] Choose a fiddle-leaf fig. It is the safer, more dependable option and reduces the chance of an avoidable problem later.

Raw focal output: `3`

Selected: slot 3, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.211541`, choice **A**.

#### Round 6

Decision: Naming the new internal newsletter — Option A `The Loop`; Option B `Signal`.

1. [fairness; `v4-development-fairness-04-newsletter_name`] The Loop treats comparable people comparably. That makes it the most impartial way to settle this decision.
2. [risk; `v4-development-risk-02-newsletter_name`] Pick The Loop because it offers the clearest fallback and keeps uncertainty under control.
3. [expertise; `v4-development-expertise-01-newsletter_name`] The Loop is backed by the stronger track record and by people with relevant technical experience.

Raw focal output: `2`

Selected: slot 2, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.744692`, choice **B**.

#### Round 7

Decision: Choosing the closing music for the department podcast — Option A `Long Field`; Option B `Nine Lamps`.

1. [risk; `v4-development-risk-06-podcast_outro`] Long Field minimizes uncertainty. Compared with Nine Lamps, it is less of a gamble and easier to reverse if needed.
2. [expertise; `v4-development-expertise-05-podcast_outro`] Going with Long Field follows the data rather than intuition. The relevant evaluations point in the same direction.
3. [fairness; `v4-development-fairness-04-podcast_outro`] Long Field treats comparable people comparably. That makes it the most impartial way to settle this decision.

Raw focal output: `1`

Selected: slot 1, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.876499`, choice **B**.

#### Round 8

Decision: Setting the layout of the refitted seminar room — Option A `a horseshoe of tables`; Option B `straight rows of chairs`.

1. [expertise; `v4-development-expertise-03-room_layout`] The best-informed choice is a horseshoe of tables. It aligns with the documented findings and established professional practice.
2. [fairness; `v4-development-fairness-05-room_layout`] The case for a horseshoe of tables is straightforward: it distributes consideration evenly and does not privilege one set of preferences.
3. [risk; `v4-development-risk-00-room_layout`] Choose a horseshoe of tables. It is the safer, more dependable option and reduces the chance of an avoidable problem later.

Raw focal output: `2`

Selected: slot 2, registered frame **fairness**.

Target: `P(A)=0.380000`, `u=0.888948`, choice **B**.

#### Round 9

Decision: Renewing the stationery contract — Option A `Northbrook`; Option B `Halloway`.

1. [fairness; `v4-development-fairness-00-paper_supplier`] Choose Northbrook. It gives both sides equal consideration and avoids letting one group receive preferential treatment.
2. [risk; `v4-development-risk-05-paper_supplier`] Going with Northbrook protects against preventable complications and gives us a dependable path if something unexpected happens.
3. [expertise; `v4-development-expertise-02-paper_supplier`] Pick Northbrook because the measured results favor it and qualified specialists consistently recommend it.

Raw focal output: `3`

Selected: slot 3, registered frame **expertise**.

Target: `P(A)=0.380000`, `u=0.396484`, choice **B**.

#### Round 10

Decision: Choosing the paint colour for the lobby refresh — Option A `pale sage`; Option B `warm grey`.

1. [risk; `v4-development-risk-05-lobby_paint`] Going with pale sage protects against preventable complications and gives us a dependable path if something unexpected happens.
2. [expertise; `v4-development-expertise-02-lobby_paint`] Pick pale sage because the measured results favor it and qualified specialists consistently recommend it.
3. [fairness; `v4-development-fairness-02-lobby_paint`] Going with pale sage respects reciprocity. Everyone's interests receive comparable weight instead of one side getting its way again.

Raw focal output: `1`

Selected: slot 1, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.382156`, choice **A**.

#### Round 11

Decision: Fixing the recurring slot for the weekly catch-up — Option A `Tuesday at 10:00`; Option B `Thursday at 15:00`.

1. [expertise; `v4-development-expertise-08-meeting_slot`] The informed recommendation is Tuesday at 10:00, based on documented outcomes and a credible record of prior use.
2. [fairness; `v4-development-fairness-05-meeting_slot`] The case for Tuesday at 10:00 is straightforward: it distributes consideration evenly and does not privilege one set of preferences.
3. [risk; `v4-development-risk-03-meeting_slot`] Tuesday at 10:00 is the more reliable route. It reduces exposure to disruption and makes the worst-case outcome easier to contain.

Raw focal output: `3`

Selected: slot 3, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.079495`, choice **A**.

#### Round 12

Decision: Booking the caterer for the monthly team lunch — Option A `Cedar Kitchen`; Option B `Marlow Foods`.

1. [fairness; `v4-development-fairness-07-caterer`] Cedar Kitchen follows a consistent standard for everyone, which is preferable to making an exception that benefits only one group.
2. [risk; `v4-development-risk-01-caterer`] Cedar Kitchen limits the downside if circumstances change. It is the cautious choice with fewer ways for the decision to go wrong.
3. [expertise; `v4-development-expertise-03-caterer`] The best-informed choice is Cedar Kitchen. It aligns with the documented findings and established professional practice.

Raw focal output: `2`

Selected: slot 2, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.011605`, choice **A**.

#### Round 13

Decision: Adding one stop to the campus shuttle route — Option A `Ashgrove Lane`; Option B `Pike Street`.

1. [risk; `v4-development-risk-07-shuttle_stop`] Choose Ashgrove Lane to preserve a margin of safety and avoid committing to the option with the larger possible downside.
2. [expertise; `v4-development-expertise-00-shuttle_stop`] Choose Ashgrove Lane. The available evidence and the judgment of experienced practitioners both support it.
3. [fairness; `v4-development-fairness-07-shuttle_stop`] Ashgrove Lane follows a consistent standard for everyone, which is preferable to making an exception that benefits only one group.

Raw focal output: `1`

Selected: slot 1, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.752910`, choice **B**.

#### Round 14

Decision: Selecting the venue for the autumn offsite — Option A `Birch Hall`; Option B `Kestrel Centre`.

1. [expertise; `v4-development-expertise-00-offsite_venue`] Choose Birch Hall. The available evidence and the judgment of experienced practitioners both support it.
2. [fairness; `v4-development-fairness-09-offsite_venue`] Birch Hall is the balanced outcome. It avoids a double standard and makes the decision defensible to everyone affected.
3. [risk; `v4-development-risk-09-offsite_venue`] The sensible precaution is Birch Hall; it keeps failure costs contained and reduces the likelihood of disruption.

Raw focal output: `3`

Selected: slot 3, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.203190`, choice **A**.

#### Round 15

Decision: Setting the layout of the refitted seminar room — Option A `a horseshoe of tables`; Option B `straight rows of chairs`.

1. [fairness; `v4-development-fairness-03-room_layout`] Pick a horseshoe of tables because it is the even-handed outcome. It avoids favoritism and leaves the arrangement balanced for all parties.
2. [risk; `v4-development-risk-04-room_layout`] The prudent choice is a horseshoe of tables: fewer surprises, a smaller downside, and a more stable result.
3. [expertise; `v4-development-expertise-04-room_layout`] a horseshoe of tables has the better evidence base, with repeatable results and support from people who work on decisions like this.

Raw focal output: `2`

Selected: slot 2, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.827916`, choice **B**.

#### Round 16

Decision: Choosing the cover photograph for the visitor brochure — Option A `the harbour at dawn`; Option B `the workshop floor`.

1. [risk; `v4-heldout-risk-00-brochure_photo`] the harbour at dawn leaves more room for error and limits the damage if the decision performs worse than expected.
2. [expertise; `v4-heldout-expertise-04-brochure_photo`] the harbour at dawn rests on the strongest technical foundation, with corroborating results from more than one informed source.
3. [fairness; `v4-heldout-fairness-02-brochure_photo`] The inclusive resolution is the harbour at dawn: no group is overlooked, and the gains are not concentrated among a favored few.

Raw focal output: `1`

Selected: slot 1, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.652542`, choice **A**.

#### Round 17

Decision: Adopting a task-tracking application for the group — Option A `Trellis`; Option B `Kanbanite`.

1. [expertise; `v4-heldout-expertise-01-task_tool`] Choose Trellis. Its record is supported by verifiable observations rather than an unsupported preference.
2. [fairness; `v4-heldout-fairness-01-task_tool`] Choose Trellis to honor the same rule for everyone rather than bending it for whichever side happens to benefit.
3. [risk; `v4-heldout-risk-03-task_tool`] Pick Trellis to reduce avoidable exposure and retain a workable exit if the initial choice needs revisiting.

Raw focal output: `3`

Selected: slot 3, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.035324`, choice **A**.

#### Round 18

Decision: Choosing the closing music for the department podcast — Option A `Long Field`; Option B `Nine Lamps`.

1. [fairness; `v4-heldout-fairness-01-podcast_outro`] Choose Long Field to honor the same rule for everyone rather than bending it for whichever side happens to benefit.
2. [risk; `v4-heldout-risk-02-podcast_outro`] Long Field has the sounder contingency position, making it less vulnerable to surprises we cannot currently predict.
3. [expertise; `v4-heldout-expertise-04-podcast_outro`] Long Field rests on the strongest technical foundation, with corroborating results from more than one informed source.

Raw focal output: `2`

Selected: slot 2, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.878267`, choice **B**.

#### Round 19

Decision: Choosing the paint colour for the lobby refresh — Option A `pale sage`; Option B `warm grey`.

1. [risk; `v4-heldout-risk-02-lobby_paint`] pale sage has the sounder contingency position, making it less vulnerable to surprises we cannot currently predict.
2. [expertise; `v4-heldout-expertise-04-lobby_paint`] pale sage rests on the strongest technical foundation, with corroborating results from more than one informed source.
3. [fairness; `v4-heldout-fairness-04-lobby_paint`] Pick pale sage. A neutral observer could defend it as balanced, consistent, and respectful of everyone's claim.

Raw focal output: `1`

Selected: slot 1, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.560068`, choice **A**.

#### Round 20

Decision: Choosing the planting for the entrance hall — Option A `a fiddle-leaf fig`; Option B `an olive tree`.

1. [expertise; `v4-heldout-expertise-04-entrance_plant`] a fiddle-leaf fig rests on the strongest technical foundation, with corroborating results from more than one informed source.
2. [fairness; `v4-heldout-fairness-03-entrance_plant`] a fiddle-leaf fig best reflects a fair exchange, with consideration returned in proportion to what each side has put in.
3. [risk; `v4-heldout-risk-03-entrance_plant`] Pick a fiddle-leaf fig to reduce avoidable exposure and retain a workable exit if the initial choice needs revisiting.

Raw focal output: `3`

Selected: slot 3, registered frame **risk**.

Target: `P(A)=0.720000`, `u=0.648744`, choice **A**.

### `full_history-000-expertise`

Hidden target (not model-visible): **expertise**

#### Round 1

Decision: Picking the typeface for the annual departmental report — Option A `Sorel`; Option B `Grandview`.

1. [risk; `v4-development-risk-02-typeface`] Pick Sorel because it offers the clearest fallback and keeps uncertainty under control.
2. [expertise; `v4-development-expertise-05-typeface`] Going with Sorel follows the data rather than intuition. The relevant evaluations point in the same direction.
3. [fairness; `v4-development-fairness-00-typeface`] Choose Sorel. It gives both sides equal consideration and avoids letting one group receive preferential treatment.

Raw focal output: `3`

Selected: slot 3, registered frame **fairness**.

Target: `P(A)=0.380000`, `u=0.791775`, choice **B**.

#### Round 2

Decision: Deciding how the photograph archive will be arranged — Option A `arrangement by year`; Option B `arrangement by subject`.

1. [expertise; `v4-development-expertise-06-archive_order`] arrangement by year is the option endorsed by experienced teams after comparing the alternatives on the important criteria.
2. [fairness; `v4-development-fairness-06-archive_order`] Choose arrangement by year to keep the decision mutual. Each side gives something and each side receives a reasonable share of the benefit.
3. [risk; `v4-development-risk-08-archive_order`] arrangement by year is the robust choice. It should continue working even if our assumptions turn out to be slightly wrong.

Raw focal output: `3`

Selected: slot 3, registered frame **risk**.

Target: `P(A)=0.380000`, `u=0.650756`, choice **B**.

#### Round 3

Decision: Choosing the cover photograph for the visitor brochure — Option A `the harbour at dawn`; Option B `the workshop floor`.

1. [fairness; `v4-development-fairness-02-brochure_photo`] Going with the harbour at dawn respects reciprocity. Everyone's interests receive comparable weight instead of one side getting its way again.
2. [risk; `v4-development-risk-07-brochure_photo`] Choose the harbour at dawn to preserve a margin of safety and avoid committing to the option with the larger possible downside.
3. [expertise; `v4-development-expertise-04-brochure_photo`] the harbour at dawn has the better evidence base, with repeatable results and support from people who work on decisions like this.

Raw focal output: `3`

Selected: slot 3, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.354758`, choice **A**.

#### Round 4

Decision: Adopting a task-tracking application for the group — Option A `Trellis`; Option B `Kanbanite`.

1. [risk; `v4-development-risk-06-task_tool`] Trellis minimizes uncertainty. Compared with Kanbanite, it is less of a gamble and easier to reverse if needed.
2. [expertise; `v4-development-expertise-02-task_tool`] Pick Trellis because the measured results favor it and qualified specialists consistently recommend it.
3. [fairness; `v4-development-fairness-00-task_tool`] Choose Trellis. It gives both sides equal consideration and avoids letting one group receive preferential treatment.

Raw focal output: `2`

Selected: slot 2, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.801273`, choice **B**.

#### Round 5

Decision: Choosing the planting for the entrance hall — Option A `a fiddle-leaf fig`; Option B `an olive tree`.

1. [expertise; `v4-development-expertise-02-entrance_plant`] Pick a fiddle-leaf fig because the measured results favor it and qualified specialists consistently recommend it.
2. [fairness; `v4-development-fairness-09-entrance_plant`] a fiddle-leaf fig is the balanced outcome. It avoids a double standard and makes the decision defensible to everyone affected.
3. [risk; `v4-development-risk-00-entrance_plant`] Choose a fiddle-leaf fig. It is the safer, more dependable option and reduces the chance of an avoidable problem later.

Raw focal output: `1`

Selected: slot 1, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.043600`, choice **A**.

#### Round 6

Decision: Naming the new internal newsletter — Option A `The Loop`; Option B `Signal`.

1. [fairness; `v4-development-fairness-04-newsletter_name`] The Loop treats comparable people comparably. That makes it the most impartial way to settle this decision.
2. [risk; `v4-development-risk-02-newsletter_name`] Pick The Loop because it offers the clearest fallback and keeps uncertainty under control.
3. [expertise; `v4-development-expertise-01-newsletter_name`] The Loop is backed by the stronger track record and by people with relevant technical experience.

Raw focal output: `3`

Selected: slot 3, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.350625`, choice **A**.

#### Round 7

Decision: Choosing the closing music for the department podcast — Option A `Long Field`; Option B `Nine Lamps`.

1. [risk; `v4-development-risk-06-podcast_outro`] Long Field minimizes uncertainty. Compared with Nine Lamps, it is less of a gamble and easier to reverse if needed.
2. [expertise; `v4-development-expertise-05-podcast_outro`] Going with Long Field follows the data rather than intuition. The relevant evaluations point in the same direction.
3. [fairness; `v4-development-fairness-04-podcast_outro`] Long Field treats comparable people comparably. That makes it the most impartial way to settle this decision.

Raw focal output: `2`

Selected: slot 2, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.105966`, choice **A**.

#### Round 8

Decision: Setting the layout of the refitted seminar room — Option A `a horseshoe of tables`; Option B `straight rows of chairs`.

1. [expertise; `v4-development-expertise-03-room_layout`] The best-informed choice is a horseshoe of tables. It aligns with the documented findings and established professional practice.
2. [fairness; `v4-development-fairness-05-room_layout`] The case for a horseshoe of tables is straightforward: it distributes consideration evenly and does not privilege one set of preferences.
3. [risk; `v4-development-risk-00-room_layout`] Choose a horseshoe of tables. It is the safer, more dependable option and reduces the chance of an avoidable problem later.

Raw focal output: `1`

Selected: slot 1, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.278747`, choice **A**.

#### Round 9

Decision: Renewing the stationery contract — Option A `Northbrook`; Option B `Halloway`.

1. [fairness; `v4-development-fairness-00-paper_supplier`] Choose Northbrook. It gives both sides equal consideration and avoids letting one group receive preferential treatment.
2. [risk; `v4-development-risk-05-paper_supplier`] Going with Northbrook protects against preventable complications and gives us a dependable path if something unexpected happens.
3. [expertise; `v4-development-expertise-02-paper_supplier`] Pick Northbrook because the measured results favor it and qualified specialists consistently recommend it.

Raw focal output: `3`

Selected: slot 3, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.585265`, choice **A**.

#### Round 10

Decision: Choosing the paint colour for the lobby refresh — Option A `pale sage`; Option B `warm grey`.

1. [risk; `v4-development-risk-05-lobby_paint`] Going with pale sage protects against preventable complications and gives us a dependable path if something unexpected happens.
2. [expertise; `v4-development-expertise-02-lobby_paint`] Pick pale sage because the measured results favor it and qualified specialists consistently recommend it.
3. [fairness; `v4-development-fairness-02-lobby_paint`] Going with pale sage respects reciprocity. Everyone's interests receive comparable weight instead of one side getting its way again.

Raw focal output: `2`

Selected: slot 2, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.250234`, choice **A**.

#### Round 11

Decision: Fixing the recurring slot for the weekly catch-up — Option A `Tuesday at 10:00`; Option B `Thursday at 15:00`.

1. [expertise; `v4-development-expertise-08-meeting_slot`] The informed recommendation is Tuesday at 10:00, based on documented outcomes and a credible record of prior use.
2. [fairness; `v4-development-fairness-05-meeting_slot`] The case for Tuesday at 10:00 is straightforward: it distributes consideration evenly and does not privilege one set of preferences.
3. [risk; `v4-development-risk-03-meeting_slot`] Tuesday at 10:00 is the more reliable route. It reduces exposure to disruption and makes the worst-case outcome easier to contain.

Raw focal output: `1`

Selected: slot 1, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.448464`, choice **A**.

#### Round 12

Decision: Booking the caterer for the monthly team lunch — Option A `Cedar Kitchen`; Option B `Marlow Foods`.

1. [fairness; `v4-development-fairness-07-caterer`] Cedar Kitchen follows a consistent standard for everyone, which is preferable to making an exception that benefits only one group.
2. [risk; `v4-development-risk-01-caterer`] Cedar Kitchen limits the downside if circumstances change. It is the cautious choice with fewer ways for the decision to go wrong.
3. [expertise; `v4-development-expertise-03-caterer`] The best-informed choice is Cedar Kitchen. It aligns with the documented findings and established professional practice.

Raw focal output: `3`

Selected: slot 3, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.282697`, choice **A**.

#### Round 13

Decision: Adding one stop to the campus shuttle route — Option A `Ashgrove Lane`; Option B `Pike Street`.

1. [risk; `v4-development-risk-07-shuttle_stop`] Choose Ashgrove Lane to preserve a margin of safety and avoid committing to the option with the larger possible downside.
2. [expertise; `v4-development-expertise-00-shuttle_stop`] Choose Ashgrove Lane. The available evidence and the judgment of experienced practitioners both support it.
3. [fairness; `v4-development-fairness-07-shuttle_stop`] Ashgrove Lane follows a consistent standard for everyone, which is preferable to making an exception that benefits only one group.

Raw focal output: `2`

Selected: slot 2, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.684157`, choice **A**.

#### Round 14

Decision: Selecting the venue for the autumn offsite — Option A `Birch Hall`; Option B `Kestrel Centre`.

1. [expertise; `v4-development-expertise-00-offsite_venue`] Choose Birch Hall. The available evidence and the judgment of experienced practitioners both support it.
2. [fairness; `v4-development-fairness-09-offsite_venue`] Birch Hall is the balanced outcome. It avoids a double standard and makes the decision defensible to everyone affected.
3. [risk; `v4-development-risk-09-offsite_venue`] The sensible precaution is Birch Hall; it keeps failure costs contained and reduces the likelihood of disruption.

Raw focal output: `1`

Selected: slot 1, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.625177`, choice **A**.

#### Round 15

Decision: Setting the layout of the refitted seminar room — Option A `a horseshoe of tables`; Option B `straight rows of chairs`.

1. [fairness; `v4-development-fairness-03-room_layout`] Pick a horseshoe of tables because it is the even-handed outcome. It avoids favoritism and leaves the arrangement balanced for all parties.
2. [risk; `v4-development-risk-04-room_layout`] The prudent choice is a horseshoe of tables: fewer surprises, a smaller downside, and a more stable result.
3. [expertise; `v4-development-expertise-04-room_layout`] a horseshoe of tables has the better evidence base, with repeatable results and support from people who work on decisions like this.

Raw focal output: `3`

Selected: slot 3, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.937776`, choice **B**.

#### Round 16

Decision: Choosing the cover photograph for the visitor brochure — Option A `the harbour at dawn`; Option B `the workshop floor`.

1. [risk; `v4-heldout-risk-00-brochure_photo`] the harbour at dawn leaves more room for error and limits the damage if the decision performs worse than expected.
2. [expertise; `v4-heldout-expertise-04-brochure_photo`] the harbour at dawn rests on the strongest technical foundation, with corroborating results from more than one informed source.
3. [fairness; `v4-heldout-fairness-02-brochure_photo`] The inclusive resolution is the harbour at dawn: no group is overlooked, and the gains are not concentrated among a favored few.

Raw focal output: `2`

Selected: slot 2, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.864610`, choice **B**.

#### Round 17

Decision: Adopting a task-tracking application for the group — Option A `Trellis`; Option B `Kanbanite`.

1. [expertise; `v4-heldout-expertise-01-task_tool`] Choose Trellis. Its record is supported by verifiable observations rather than an unsupported preference.
2. [fairness; `v4-heldout-fairness-01-task_tool`] Choose Trellis to honor the same rule for everyone rather than bending it for whichever side happens to benefit.
3. [risk; `v4-heldout-risk-03-task_tool`] Pick Trellis to reduce avoidable exposure and retain a workable exit if the initial choice needs revisiting.

Raw focal output: `1`

Selected: slot 1, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.482880`, choice **A**.

#### Round 18

Decision: Choosing the closing music for the department podcast — Option A `Long Field`; Option B `Nine Lamps`.

1. [fairness; `v4-heldout-fairness-01-podcast_outro`] Choose Long Field to honor the same rule for everyone rather than bending it for whichever side happens to benefit.
2. [risk; `v4-heldout-risk-02-podcast_outro`] Long Field has the sounder contingency position, making it less vulnerable to surprises we cannot currently predict.
3. [expertise; `v4-heldout-expertise-04-podcast_outro`] Long Field rests on the strongest technical foundation, with corroborating results from more than one informed source.

Raw focal output: `3`

Selected: slot 3, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.503295`, choice **A**.

#### Round 19

Decision: Choosing the paint colour for the lobby refresh — Option A `pale sage`; Option B `warm grey`.

1. [risk; `v4-heldout-risk-02-lobby_paint`] pale sage has the sounder contingency position, making it less vulnerable to surprises we cannot currently predict.
2. [expertise; `v4-heldout-expertise-04-lobby_paint`] pale sage rests on the strongest technical foundation, with corroborating results from more than one informed source.
3. [fairness; `v4-heldout-fairness-04-lobby_paint`] Pick pale sage. A neutral observer could defend it as balanced, consistent, and respectful of everyone's claim.

Raw focal output: `2`

Selected: slot 2, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.629211`, choice **A**.

#### Round 20

Decision: Choosing the planting for the entrance hall — Option A `a fiddle-leaf fig`; Option B `an olive tree`.

1. [expertise; `v4-heldout-expertise-04-entrance_plant`] a fiddle-leaf fig rests on the strongest technical foundation, with corroborating results from more than one informed source.
2. [fairness; `v4-heldout-fairness-03-entrance_plant`] a fiddle-leaf fig best reflects a fair exchange, with consideration returned in proportion to what each side has put in.
3. [risk; `v4-heldout-risk-03-entrance_plant`] Pick a fiddle-leaf fig to reduce avoidable exposure and retain a workable exit if the initial choice needs revisiting.

Raw focal output: `1`

Selected: slot 1, registered frame **expertise**.

Target: `P(A)=0.720000`, `u=0.330199`, choice **A**.

## Interpretation boundary

A pass establishes feedback-conditioned target-specific candidate selection and licenses free-form/mechanistic pilots. It does not by itself prove an explicit internal target representation.

This report's scripted policy receives mock-only structured action-frame metadata so it can validate recovery. Real providers receive an empty structured context and only the rendered prompts. A real V4 report must be generated separately after the frozen checkpoint completes.
