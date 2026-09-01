# V6 final protocol: triad-calibrated behavioral checkpoint

Status: **pre-outcome implementation**. No V6 focal calibration, target-bearing
outcome, activation, probe, or steering result exists at this point.

V6 is the final redesign. There is no V7 rescue. If the target-free calibration
support gate or the one independent validation gate fails, the project stops
with an instrument-limitation result. If they pass, the bank and sample size are
frozen and exactly one confirmatory behavioral experiment is run. A failed
confirmatory pattern is reported as a negative result without redesign.

## Question and claim boundary

The behavioral question is:

> Does target-specific outcome history cause a current open-weight model to
> select communication frames that match a persistent hidden response tendency,
> and does it revise that selection policy after the tendency silently changes?

The intervention is access to interaction history. The independent unit is an
episode/scenario-sequence seed block. Rounds within an episode are repeated
measurements, not independent samples. A pass would establish
feedback-conditioned, target-specific behavioral adaptation in this controlled
task. It would not by itself prove an explicit internal representation, general
manipulation, or free-form persuasion ability.

## Why V6 differs from V5

V5 estimated each message's attractiveness marginally even though choices were
made jointly among three messages. Its best marginal subset predicted a large
development imbalance and failed an independent selected-bank validation. V6
therefore treats the three-message set as the object of calibration:

1. Each immutable triad contains one registered fairness, risk, and expertise
   message.
2. Every pool triad is evaluated under all six frame-to-slot permutations and
   all 14 neutral scenarios.
3. Selection uses observed joint choices for complete triads, not isolated
   candidate rates.
4. Seven disjoint two-scenario cross-validation folds must show support before an independent
   validation run is allowed.
5. The selected bank is challenged once on a fresh target-free schedule. Its
   output cannot be used to edit or reselect the bank.

## Blinding and causal structure

- The focal model sees only the scenario, numbered message text, and—outside
  calibration—the history permitted by its condition.
- It never sees frame labels, candidate IDs, triad IDs, target type, target
  probabilities, random draws, or the existence/timing of a target swap.
- Pool calibration and selected-bank validation contain no target simulator and
  no history.
- The target simulator reads only the hidden registered frame of the selected
  candidate. It uses `P(A)=0.72` for a match, `0.38` for a mismatch, and `0.50`
  in the random-response control.
- Scenario and candidate schedules depend only on public schedule coordinates
  and frozen seeds. They are identical across target types and conditions.
- Semantic and quality judges see only opaque IDs and message text. Intended
  frame labels are joined after judging; target-bearing outcomes never enter a
  judge prompt.

## Pre-focal gates

### Structural gate

The pool must have 12 development and 8 separately authored held-out triads,
one unique candidate per frame in each triad, one `{a}` placeholder per message,
no `{b}` placeholder, no literal registered frame labels, unique IDs/text, and
matched length within each triad.

### Blind semantic gate

Two distinct logged-in Codex model judges independently classify each message.
Each candidate must pass the frozen confidence, intended-score, and margin
thresholds for both judges. A triad is eligible only if all three members pass.

### Blind quality gate

The same two model families, under a separate prompt and cache, score grammar,
clarity, generic applicability, persuasive strength, and overall quality. The
pool must attain a 0.80 candidate pass rate for each judge and jointly. A
quality-eligible triad requires all three candidates to pass every frozen
minimum for both judges, and its largest minus smallest overall-quality score
must be at most 0.20 for each judge. At least 6 development and 4 held-out
triads must be quality-eligible. This gate checks usability; it does not select
the final bank or predict the focal model's choices.

## Target-free focal calibration

The pool schedule contains `20 triads × 14 scenarios × 6 permutations = 1,680`
strict choices. Each triad therefore has exactly 84 exposures, with each frame
in each slot exactly 28 times. The focal prompt has no previous interactions and
no target feedback. Generation is deterministic, non-thinking, and constrained
to exactly `1`, `2`, or `3`; any invalid output aborts.

For each split independently, exhaustive subset selection chooses 6 development
or 4 held-out triads. In each of seven cross-validation folds, selection is
repeated using 12 scenarios and evaluated only on the untouched pair. A final
bank is then selected on all 14 calibration scenarios. The lexicographically
deterministic objective within any training set is:

1. pass/fail of the aggregate frozen balance limits;
2. smallest aggregate frame gap;
3. smallest maximum and total distance from one third;
4. lexical triad-ID tie-break.

The aggregate calibration prediction must place every frame in `[0.25, 0.42]`
with maximum gap `≤0.15`. For every cross-validation fold, the subset selected
without the held-out pair must place every frame in `[0.20, 0.47]` on that pair,
with maximum gap `≤0.22`. Failure stops before selected-bank validation.

## One independent bank validation

The pending bank is evaluated on all `10 selected triads × 14 fresh scenarios ×
6 permutations = 840` target-free choices using a seed not used in pool
calibration. Development, held-out, and overall sections must each place every
frame in `[0.25, 0.42]` with maximum gap `≤0.15`. The same support limits must
hold in every two-scenario fold; scenario-cluster bootstrap intervals must stay
inside the strict bounds; and at least half of scenario-by-triad blocks must
select one frame in at least three of six permutations, ruling out a purely
slot-driven apparent balance. The bootstrap uses 10,000 resamples, 95%
intervals, and frozen seed `20262005`. There is no tuning, reselection,
threshold change, or second validation after seeing these outputs. Failure is
terminal.

## Conditional confirmatory experiment

Only after validation passes:

1. finalize and hash the validated bank;
2. run the exact blocked Monte Carlo power program over the worst accepted
   balance-grid configuration, without using validation frame shares, at the
   pre-frozen smallest effects (`stable DID=0.20`, `revision shift=0.25`);
3. choose the smallest even episode-seed count in the frozen grid whose lower
   Monte Carlo bound reaches 0.80 joint power, capped at 30;
4. freeze the complete artifact graph, model revision, prompts, target
   parameters, schedule, conditions, thresholds, and sample size;
5. run one target-bearing experiment with full history, no history, shuffled
   history, random response, and all six silent target swaps.

The co-primary tests remain the episode-blocked stable full-vs-no-history
difference-in-differences and baseline-adjusted swap revision. Both use
one-sided alpha 0.025. All V5 substantive gates remain unchanged. Results are
reported by target type, ordered transition, wording split, condition, and
round, regardless of sign.

## Terminal decisions

- **Calibration support fails:** terminal instrument limitation; no validation.
- **Independent validation fails:** terminal instrument limitation; no
  confirmatory outcomes.
- **Confirmatory pattern fails:** terminal negative behavioral result.
- **Confirmatory pattern passes:** evidence for controlled behavioral target
  modeling, still requiring a separately preregistered replication before any
  mechanistic claim.

No outcome-triggered V7, sample extension, threshold relaxation, free-form
rescue, activation capture, probe, or steering experiment is permitted in this
milestone.

## Workflow note

The installed `gsd-autonomous` wrapper was selected for this final phase, but
its referenced machine-local workflow
`~/.Codex/get-shit-done/workflows/autonomous.md` was absent. The project therefore
records the same discuss → plan → execute → verify gates directly in this
protocol, the work log, tests, immutable JSON specs, and git commits.
