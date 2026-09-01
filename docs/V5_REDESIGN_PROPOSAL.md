# V5 behavioral redesign proposal

Status: **historical post-V4 proposal. The local implementation and blind
semantic gate are complete; see `V5_IMPLEMENTATION_PLAN.md` and
`v5_calibration_protocol.json`. No V5 behavioral outcome has been run.**

This proposal uses the V4 failure to improve identification. It cannot rescue or
replace the V4 decision. Any V5 real-model outcome requires a new frozen JSON,
new power calculation, clean outcome directory, and explicit launch checkpoint.

## What V4 established

V4 supplied credible evidence that Qwen3.8-27B used target-specific feedback in
the controlled candidate-selection task:

- full-history held-out matching exceeded no history and shuffled history;
- the full/no-history difference-in-differences was positive and significant;
- random target responses did not produce a learning curve;
- fairness and risk both improved relative to their no-history baselines.

V4 did not establish the stronger revision pattern. The new target frame rose
and the old frame fell after a swap, but the final new-minus-old contrast was
zero. The preregistered swap inference gate failed.

## Design problems exposed by V4

### 1. Large frame prior

Without history, the model selected expertise in 92.2% of rounds. This creates
floor and ceiling effects and makes ordered swaps radically asymmetric. The
experiment was balanced in candidate position but not in candidate
attractiveness to the focal model.

### 2. Final-level swap test ignored the baseline

The confirmatory swap statistic tested whether the new frame exceeded the old
frame in the final window. With a large pre-existing frame prior, that asks for
a complete crossover rather than measuring belief revision relative to the
starting state.

### 3. Free-form formatting leaked back into a discrete action

In 110 rounds the model began explaining the history instead of returning one
number. The seeded fallback preserved execution, but the invalid-output rate
was history-dependent and the 98% gate passed narrowly.

### 4. Aggregate swaps hid directional heterogeneity

Adaptation occurred in 85% of swaps into expertise, 22.5% into risk, and 0% into
fairness. A single aggregate can therefore mix qualitatively different
transition regimes.

## Proposed V5 question

> After controlling the focal model's baseline preference among communication
> frames, does target-specific feedback cause a baseline-adjusted shift from an
> old target frame toward a silently introduced new target frame?

This remains a behavioral question. A positive result would still not prove an
explicit internal target representation.

## Proposed changes

### A. Calibrated candidate bank

Create a new bank with equalized length, specificity, confidence, syntactic
form, and scenario grounding across fairness, risk, and expertise. Calibration
and evaluation must be split:

1. Author a calibration bank and a separately authored held-out evaluation
   bank.
2. Run no-history calibration prompts only.
3. Freeze an objective balance criterion before selecting the final bank, for
   example each frame receiving 25%–42% of no-history selections with no frame
   exceeding another by more than 15 percentage points.
4. Validate the registered frame semantics blindly with two independent judges.
5. Discard all calibration outcomes from the confirmatory dataset.

If no semantically clean bank meets the balance criterion, stop. Do not weaken
the criterion after seeing candidate-level results.

### B. Constrained candidate decoding

Use a first-token logits constraint or grammar that permits exactly the tokens
`1`, `2`, and `3`, followed by immediate termination. Record the pre-constraint
logits for engineering diagnostics if practical, but do not expose them to the
target. The primary run should have no fallback path.

### C. Keep the successful controls

Retain full history, no history, shuffled history, random responses, stable
targets, all six ordered swaps, common scenario schedules, hidden frame labels,
and held-out paraphrases. Keep the target response function at 0.72/0.38/0.50
unless a pre-data simulator study justifies a change.

### D. Give revision a clean temporal window

Use 24 rounds: 12 before the swap and 12 after it. Reserve rounds 19–24 for
held-out candidate wording. This provides six post-swap learning rounds before
the held-out final window while keeping the task small.

### E. New confirmatory contrasts

Proposed co-primary outcomes:

1. Stable target learning: the episode-paired full/no-history
   difference-in-differences on held-out target matching.
2. Baseline-adjusted revision:

   ```text
   revision_shift =
       (late_new_match - late_old_match)
       - (pre_new_match - pre_old_match)
   ```

The final late new-minus-old level remains an important secondary outcome, not
the sole definition of revision. Randomization should be blocked by ordered
transition, and the aggregate test should weight all six transitions equally.

Require directional support in at least four of six ordered transitions and at
least one successful transition away from each pre-swap target type. Report all
six transition estimates and intervals regardless of sign.

### F. Power and sample size

Do not power V5 directly from V4's observed p-value. Before focal calibration,
define the smallest effects of interest; after selected-bank validation supplies
the nuisance frame shares, simulate the exact blocked randomization analysis and
select the smallest seed count with at least 80% joint power for both co-primary
outcomes at the declared alpha allocation. Include Monte Carlo uncertainty.

The V4 run shows that thousands of short generations are inexpensive on one
A100, so statistical design—not GPU budget—should determine the sample. A
provisional planning ceiling is 30 scenario seeds, but this number has no
authority until the new power file is frozen.

Implementation note (frozen before focal calibration): the population
smallest-effect pair is stable DID `0.20` and revision shift `0.25`. This is the
smallest tested pair compatible with the existing `0.50` late-level gate under
a balanced one-third baseline and the complete-pattern power requirement. The
selected-bank validation may update nuisance frame shares and therefore sample
size, but it may not change this effect pair.

## Decision rule

V5 licenses a later free-form replication only if all of these are true:

- design-integrity and constrained-output gates pass;
- stable target learning passes its effect and inference gates;
- baseline-adjusted swap revision passes its effect and inference gates;
- at least four ordered transitions support revision, including movement away
  from every starting target type;
- no-history and random-response controls remain null within frozen bounds;
- held-out wording results agree with development wording;
- the result replicates on a second current open-weight model or a separately
  frozen seed bank.

Activation capture, probes, and steering remain out of scope until this new
behavioral gate is frozen, run, passed, and independently replicated.

## Before any paid V5 run

1. Implement and test constrained decoding.
2. Author and blindly validate the new calibration/evaluation banks.
3. Run no-history bank calibration only.
4. Freeze the bank-selection rule and selected bank.
5. Implement blocked transition summaries and corruption tests.
6. Run mock positive, random negative, invalid-output, and asymmetric-prior
   negative controls.
7. Run the exact Monte Carlo power analysis.
8. Freeze `behavioral_checkpoint_v5.json` and obtain launch approval.
