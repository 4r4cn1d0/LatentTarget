# V7 adversarial review — outcome: REJECTED

Run 2026-09-02, five independent lenses (statistics, effect-size calibration,
scientific design, code fidelity, preregistration discipline) over
`docs/V7_DESIGN_PROPOSAL.md`, `src/controlled_v7_power.py`, its tests, and the
V4/V5/V6 record; each finding then put to three skeptics prompted to refute it.
42 agents; 33 completed; **9 failed on the operator's session limit**, including
the synthesis step, so there is no memo. The findings below are quoted from the
journal, not paraphrased. Author's assessment follows each.

## Findings that survived three skeptics (all critical)

### 1. V7's revision rule is satisfied by default-attraction alone

> The kept revision gates are pooled means over six transitions
> (adjusted_new_gain >= 0.05, adjusted_old_drop >= 0.05, sum >= 0.15, one exact
> test on the pooled bundle contrast). Under a model that acquires the new frame
> only when the new frame is its default and merely abandons the old frame
> otherwise, every kept gate still passes; the gates that would catch this
> (late_swap_new_minus_old, directional_transition_support,
> all_origin_types_support_revision) are demoted to 'reported only'. The
> primary therefore cannot falsify the very alternative explanation the
> proposal gives for V4.
>
> Evidence: V4's own pooled numbers (new-target gain 0.108, old-target drop
> 0.105, sum 0.213; 34/40 adapters into expertise, 0/40 into fairness) satisfy
> all of V7's kept effect gates, while the gate V4 actually failed (held-out
> new minus old, p = 0.498) is the one V7 drops.

**Author: correct.** V7's required rule would have passed on the V4 pattern
that V4 itself identified as *not* revision. The demoted gates are
construct-validity gates, not nuisance gates. This alone invalidates V7.

### 2. V7's required rule is satisfied by the regression-to-default pattern

Same defect from the science lens, with the sharper diagnosis that the dropped
gates are *origin*-based and V4 passes them; what V4 failed was
*destination*-sensitive. Prescribed fix: one required, destination-stratified
acquisition gate — bundle-mean adjusted new gain ≥ 0.05 over the transitions
whose destination is a non-default frame (at minimum the orthogonal pair
fairness ↔ risk, where regression to default predicts zero acquisition), with
its own exact within-bundle sign-flip test.

**Author: correct**, and the fix is the right shape for any successor.

### 3. The acquisition-asymmetry secondary is entailed by the no-gating null

> 'Toward-default acquisition > away-from-default acquisition' on the
> probability scale is predicted by any equal-sensitivity logit-choice model
> with a skewed prior (Δp ∝ p(1−p)), so observing it cannot support 'revision
> is gated by the prior, not by the evidence'.
>
> Evidence: V7's DGP contains no gating mechanism, yet at the V5-overall cell
> adj_new toward/away = 0.116/0.093 (learner_1), 0.141/0.125 (learner_2); flat
> for learner_3; reversed in the V4 cell.

**Author: correct.** The secondary had no estimand, no test, no alpha, and no
control against the null that predicts the same sign.

### 4. V7's legitimacy argument is unsound

> V7 removes exactly the gate whose failure terminated V6
> (no_history_frame_balance), was committed 21 minutes after V6's close, and its
> motivations were already known to, and rejected by, the V6 design.
> `V6_FINAL_PROTOCOL.md:252-255`: 'No outcome-triggered V7, sample extension,
> threshold relaxation ... is permitted.' V6 was designed after V5 with the
> balance gate as its chosen remedy; the V5 measurement 13.7/34.2/52.1 was
> known then.

**Author: correct on the protocol's text.** V6's authors had V5's measurement
and chose to require balance anyway, and wrote that no relaxation would follow.
V7 relaxed that gate after V6's outcome. Calling that "independently
motivated" was wrong. A PI may open a new milestone that explicitly overrides
V6's terminal clause; V7 was not declared as one.

## Findings whose refutation votes failed on the session limit — UNVERIFIED, not refuted

- "'Cancels by construction' and 'twin sharing prefix' overstate what the DID
  does; the prior enters as an effect modifier, not an additive term."
  (A separate, earlier phrasing of this *was* refuted by three skeptics; this
  one was not adjudicated.)
- "No Type I / null-size check exists for V7 cells." Moot in substance: 4,000
  null studies at the measured prior were run after the reviewers read the
  repo (`results/v7_design/feasibility/v7_null_size_measured_prior_large.json`).
- "V7's required rule is already satisfied by V4's observed values; the
  confirmatory run re-tests a p = 0.0001 result." One vote returned; the
  finding overlaps #1 and is treated as standing.

## Genuinely refuted (three skeptics each)

Power evaluated at uncalibrated alternatives (the realized effects were
already documented pre-result); 'cancels by construction' is false in the DGP;
`full_history_late_level` mislabelled as prior-cancelling (the proposal never
labelled it so, and the screen verdict names it as the absolute-level binding
gate); the every-cell rule is predetermined by calibration.

## Errors in the author's own artifacts, confirmed

| claim in repo | fact | fixed |
|---|---|---|
| diagnostic offsets 5000+ and null offsets 20000+ "disjoint from the screen" | screen used study indices 1–24,000; both overlap; only the 40000+ null run is disjoint | proposal corrected |
| "exactly one substitution" | the simplex validator also renormalizes and loosens the sum tolerance to 1e-9 (output still byte-identical under balanced shares; test proves it) | proposal corrected |
| `V7_MEASURED_NUISANCE_CELLS` | contains a hypothetical cell; V4 share rounded 0.922 → 0.923 | `kind` field added |
| screen `canonical_sha256` | hashed per-cell `wall_seconds`; not reproducible. File SHA-256 in WORK_LOG stands | `v7_screen_canonical_sha256` + test |
| "decay is primary" | code weights decay and acquisition identically | acknowledged; moot |
| `format_v7_screen` omits realized effects the proposal requires printed | true | acknowledged; moot |

## Disposition

`V7_STOPPED_INFEASIBLE_AND_REVIEW_REJECTED`. V7 failed its own pre-committed
feasibility rule (`docs/V7_DESIGN_PROPOSAL.md`, screen verdict) *and* would
have been invalid had it passed (findings 1–3), *and* was a rescue under V6's
terminal clause (finding 4). No protocol was frozen; nothing was spent.

What survives as reusable fact: the matched-twin estimand is powered and
Type-I-controlled at the model's measured prior. What any successor must add,
per this review: a destination-stratified acquisition gate; a secondary tested
against the no-gating prediction rather than against zero; an explicit
milestone declaration overriding V6's clause, with every rule change after
every observed outcome listed (V4 → V5 → V6 → V7); and disjoint, pinned study
offsets.
