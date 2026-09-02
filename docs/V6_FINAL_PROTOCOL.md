# V6 final protocol: triad-calibrated behavioral checkpoint

Status: **`V6_POWER_CORRECTION_FROZEN`**. No V6 judge, focal calibration,
target-bearing outcome, activation, probe, steering, or paid GPU result exists.

V6 is the final redesign; there is no V7 rescue. An independent review rejected
the earlier IID-multinomial terminal proof because the registered power DGP has
heterogeneous, correlated round paths. That certificate is withdrawn. The
corrected path-based power screen is frozen here before it runs, and every
judge/model path remains unauthorized until power is resolved.

## Question and claim boundary

The behavioral question is:

> Does target-specific outcome history cause a current open-weight model to
> select communication frames that match a persistent hidden response tendency,
> and does it revise that selection policy after the tendency silently changes?

The intervention would have been randomized access to interaction history. The
independent unit is an episode/scenario-sequence seed bundle. Rounds within an episode are repeated
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

### Blind semantic gate (conditional and not authorized)

Two distinct model judges were intended to classify each message independently.
Each candidate must pass the frozen confidence, intended-score, and margin
thresholds for both judges. A triad is eligible only if all three members pass.
The two model IDs, deterministic shuffle seeds, batch size, prompt version,
prompt-template hash, and rubric hash are frozen in
`docs/v6_calibration_protocol.json`. The original draft used a tool-enabled
Codex CLI transport. Final review found that unsuitable for untrusted candidate
text, so it is not an authorized judge transport. No candidate was sent to it
and no judge result exists.

The seed and batch size are executable constraints, not labels in a summary.
The checkpoint regenerates exact shuffled membership/order, filenames, prompt
payloads, model, and batch indices, then reconciles every raw batch with its
repository-local JSONL cache. It recomputes the semantic gate from those raw
values and ignores a hand-edited `pass` field.

### Blind quality gate

The same two model families, under a separate prompt and cache, score grammar,
clarity, generic applicability, persuasive strength, and overall quality. The
pool must attain a 0.80 candidate pass rate for each judge and jointly. A
quality-eligible triad requires all three candidates to pass every frozen
minimum for both judges, and its largest minus smallest overall-quality score
must be at most 0.20 for each judge. At least 6 development and 4 held-out
triads must be quality-eligible. This gate checks usability; it does not select
the final bank or predict the focal model's choices.

Quality uses the same raw-file discipline under its independent prompt and
cache: exact batches are reconstructed and the complete quality evaluation is
recomputed before a checkpoint can pass.

## Target-free focal calibration

The pool schedule contains `20 triads × 14 scenarios × 6 permutations = 1,680`
strict choices. Each triad therefore has exactly 84 exposures, with each frame
in each slot exactly 28 times. The focal prompt has no previous interactions and
no target feedback. Generation is deterministic, non-thinking, and constrained
to exactly `1`, `2`, or `3`; any invalid output aborts.

The pool and independent-validation runners accept only their frozen
repository-relative destinations. Immediately before paid generation they
atomically create the one permitted launch receipt; manifests and downstream
checkpoints must reload that exact receipt.

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

## Prospective randomized design and corrected power gate

The last pre-outcome scientific review found that the earlier sign-flip tests
were not licensed by random assignment and that an apparent swap effect could
be produced by abandoning the old frame without acquiring the new frame. V6
was therefore corrected, before any focal-model outcome, to use prospective
matched-bundle randomization:

- One frozen coin per episode-seed bundle assigns physical branch slots to
  full-history versus no-history for all three stable targets.
- A second independent frozen coin assigns branch slots to silent-swap versus a
  stable-old counterfactual for all six ordered target transitions.
- The stable co-primary is the bundle mean of the full-minus-no-history change
  from rounds 1–6 to rounds 19–24.
- The revision co-primary is swap minus stable-old, with separately required
  adjusted new-frame acquisition of at least 0.05 and adjusted old-frame decay
  of at least 0.05. Their sum must be at least 0.15, and the late new-minus-old
  contrast must be non-negative.
- Both co-primaries use exact one-sided Fisher sign-flip tests over the
  prospectively randomized bundle labels at alpha 0.025 each.
- Generation and target-draw RNG streams are tied to bundle, physical slot,
  transition (when applicable), and round—not to assigned condition.
  No-history output bytes are generated once and reused across hidden target
  labels within the same physical slot.
- The real-data analyzer and every power replicate call the same frozen
  `analyze_v6_bundle_study` implementation.

The complete nuisance, sequential Beta-Bernoulli feedback, heterogeneity,
allocation, estimand, inference, control, null-size, and power assumptions are
serialized in `docs/v6_calibration_protocol.json` and bound by contract SHA-256
`e29dbbe8da2ecf6f7d891f5aee997052aff3d06dfc10e31db0d55ab757be2fd9`.
The registered sample-size grid is 12, 18, 24, and 30 independent bundles, with
a required 0.80 lower 95% Monte Carlo bound for both joint co-primary rejection
and the complete behavioral rule in every authoritative nuisance cell.

### Withdrawn IID calculation and frozen path-based correction

The prior calculation treated all `24N` no-history selections as IID draws from
fixed frame shares. Its arithmetic was correct for that reference model, but it
was not the registered DGP: V6 includes scenario, triad, candidate-slot,
physical-branch-slot, bundle, and serial effects. It therefore could not support
a terminal decision and has been removed from the execution path.

The correction uses the same heterogeneous no-history path constructor,
randomization assignments, RNG roots, and study offsets as the corresponding
complete power cells. It runs 10,000 model-free studies for the registered
`minimum_share_boundary_01` cell, all three learner profiles, and every allowed
N. For each replicate, complete-pattern success is a subset of balance-gate
success. Since Wilson lower bounds are monotone in success counts, any N whose
screened balance lower bound is below 0.80 cannot satisfy the every-cell
complete-power selection rule. Only that logical dominance permits the
remaining expensive trajectories to be skipped.

This correction is committed and tagged before its fixed-seed CPU-only screen
runs. Until the resulting artifact is independently replayed, V6 is unresolved
rather than terminal.

### Implemented but intentionally unexecuted pipeline

The repository contains a conditional downstream pipeline:
frozen candidate-pool identity; independently attested blind semantic and
quality judge contracts; target-free pool screening and selection; independent
bank validation; canonical one-launch receipts; exact-prefix paid-run resume;
model-free confirmatory finalization; immutable source/runtime closures;
raw-choice and target-draw replay; and summary-last idempotent analysis
publication. Final review identified remaining hardening work in the dormant
artifact and judge transports. Those paths are blocked and are not claimed
production-safe or experimentally validated.

## Terminal decisions

- **Observed V6 decision:** unresolved pending corrected path-based power; no
  judge, calibration, validation, or confirmatory execution.
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

The installed `gsd-autonomous` and `gsd-docs-update` wrappers were selected for
this final phase, but their referenced machine-local workflows under
`~/.Codex/get-shit-done/workflows/` were absent. The project therefore records
the same discuss → plan → execute → verify and code-verified documentation
gates directly in this protocol, the work log, tests, immutable JSON specs, and
git commits.
