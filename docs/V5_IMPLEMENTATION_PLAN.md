# V5 local implementation plan

Status: **local implementation and blind semantic gate complete; ready for paid
target-free focal calibration; no V5 behavioral outcome exists**.

This plan turns the post-V4 proposal into testable requirements. It is not a
confirmatory preregistration. The final V5 checkpoint cannot be frozen until a
separate no-history calibration and validation run selects a balanced message
bank.

## Scientific unit and design

- The independent behavioral unit is an episode. Repeated rounds are used to
  construct episode summaries and are not counted as independent replicates.
- Scenario-sequence seed is a blocking variable shared across target types and
  conditions. Confirmatory randomization tests must preserve this block.
- Stable conditions retain full history, no history, shuffled history, and
  random target responses.
- Swap episodes retain all six ordered target transitions with equal counts.
- Episodes contain 24 rounds. A silent target swap occurs after round 12 and
  separately authored held-out language begins at round 19.
- The simulator remains exactly `P(A)=0.72` for a registered-frame match,
  `P(A)=0.38` for a mismatch, and `P(A)=0.50` for random responses.

## Requirements

### V5-R1 — strict model action

The real provider must be constrained to emit exactly one of `1`, `2`, or `3`
and then stop. A V5 episode aborts on an invalid selection; there is no seeded
fallback in the primary outcome. V4 fallback behavior remains reproducible.

### V5-R2 — version isolation

V4 code paths and frozen artifacts must remain reproducible. V5 records and
manifests use `controlled-choice-v5.0`, include the exact bank hash, and declare
the strict selection policy.

### V5-R3 — pre-outcome candidate pool

Development and held-out pools are separately authored with matched sentence
structure, length, specificity, confidence, and scenario grounding. Every
candidate has an immutable ID and registered frame hidden from the focal model.
The target uses only this registered ID; no language judge lies on the causal
path.

### V5-R4 — blind semantic gate

Candidate text is exported without intended labels. Two independent machine
judges classify it before focal-model calibration. Only candidates passing the
frozen agreement, recall, and confidence criteria are eligible for selection.
The judges never see target types, target outcomes, or which frame would count
as matched.

### V5-R5 — separate calibration and validation

A no-history calibration run may estimate candidate attractiveness, but none of
its prompts or outputs enters the confirmatory dataset. A deterministic,
predeclared selector chooses the bank from semantically eligible candidates.
A second no-history validation run on the selected bank must satisfy both:

- each frame receives between 25% and 42% of choices; and
- the largest frame share minus the smallest is at most 15 percentage points.

Failure stops the pipeline before a confirmatory run. Criteria cannot be
weakened after seeing calibration or validation outcomes.

### V5-R6 — stable-target co-primary

The stable co-primary remains the paired full-history versus no-history
difference-in-differences from early rounds 1–6 to held-out rounds 19–24.

### V5-R7 — baseline-adjusted revision co-primary

For each swap episode:

```text
revision_shift =
    (late_new_match - late_old_match)
    - (pre_new_match - pre_old_match)
```

The pre window is rounds 7–12 and the held-out late window is rounds 19–24.
The unadjusted late new-minus-old level remains secondary.

### V5-R8 — blocked and directional inference

- Co-primary randomization tests preserve scenario-sequence blocks and allocate
  one-sided alpha 0.025 to each co-primary.
- All six ordered transition estimates and intervals are reported.
- At least four of six transition directions must exceed the frozen substantive
  support threshold.
- At least one supported transition must originate from each old target type.
- Full history must outperform no history for every target type; an aggregate
  dominated by one frame cannot pass.

### V5-R9 — negative controls

No-history and random-response learning gains must remain within frozen null
bounds. Shuffled history must not reproduce full-history learning. Corruption
tests must detect leaked frame metadata, altered schedules, fallback use,
transition imbalance, and checkpoint drift.

### V5-R10 — a priori simulation power

Power uses the exact blocked V5 tests, not a closed-form approximation. It
reports sensitivity over several smallest effects of interest, at least 5,000
Monte Carlo replicates for the final selection, and a 95% Monte Carlo interval.
The smallest seed count whose lower interval bound reaches 80% joint power is
selected, subject to the declared planning ceiling. V4's observed p-value is
not used as the effect size.

### V5-R11 — launch and claim boundary

The confirmatory checkpoint is frozen only after semantic validation, focal
calibration, selected-bank validation, power selection, and exact model-revision
verification pass. No activation capture, probing, steering, free-form rescue,
or outcome-dependent sample extension is permitted before a passed and
replicated behavioral checkpoint.

## Implementation sequence

1. Add a protocol abstraction whose default is byte-compatible V4 behavior.
2. Add strict Hugging Face choice-token constraints and unit tests.
3. Add the external V5 pool, structural audit, calibration schedule, selector,
   and validation gate.
4. Add V5 experiment runner and manifest contracts.
5. Add V5 stable, blocked revision, transition, and corruption analyses.
6. Add exact Monte Carlo power sensitivity and mock controls.
7. Run all local tests and produce a calibration-ready—not confirmatory-ready—
   status report.
8. Only then provision a short paid focal-model calibration run.

## Local completion gate

Local V5 preparation is complete only when all tests pass; V4 artifacts remain
reproducible; invalid V5 outputs abort; mock positive and negative controls
behave as expected; candidate-pool structure is valid; power code is
deterministic; documentation distinguishes provisional, calibration-ready, and
frozen states; and no paid or mechanistic outcome has been generated.

## 2026-09-01 implementation checkpoint

- The V4-default protocol abstraction, external V5 bank, strict decoding,
  calibration schedule, deterministic selector, independent validation gate,
  24-round runner, blocked analysis, exact sign-flip test, exact-test power
  simulation, artifact graph, and fail-closed freezer are implemented.
- Two distinct blind machine judges saw only opaque IDs and text. Both reached
  1.000 accuracy/recall on all 42 pool candidates, inter-judge kappa was 1.000,
  and every candidate-level confidence, intended-score, and margin gate passed.
- The 8-seed positive mock completed 144 episodes/3,456 records and passed all
  effect, inference, design, wording, transition, and control gates. Random,
  asymmetric-prior, invalid-output, fallback, schedule, hash, revision, and
  artifact-corruption tests fail as intended.
- A provisional 5,000-study power sensitivity was run with equal one-third
  placeholder frame shares. This is not final authority; power must be rerun
  from selected-bank validation shares. Before any focal calibration, the
  population smallest-effect pair was frozen at stable DID `0.20` and revision
  shift `0.25`; calibration may change the required seed count but not that
  pair.
- The exact paid calibration plan passes a no-weight dry run for 576
  target-free/no-history choices on pinned `Qwen/Qwen3.8-27B`. Confirmatory V5
  and all mechanistic work remain blocked.
