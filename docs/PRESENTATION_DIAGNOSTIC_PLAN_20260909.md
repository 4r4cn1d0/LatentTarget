# Final bounded presentation diagnostic

This plan follows the completed 720 choice diagnostic and the user's request
to continue until there is a conclusion. The earlier negative results stay
unchanged. The purpose is to narrow the explanation for weak performance,
not keep modifying the task until it produces a positive result.

## Questions and scope

1. Can the unchanged model return each requested digit reliably?
2. Can it retrieve an explicitly recorded outcome from the supplied history?
3. Does lossless compaction of that history change participant binding?
4. Does cycling candidate positions change which message it selects?

Use all 36 existing evaluation bundles. No new histories, outcome resampling,
type selection, scenario selection or model search. The model and generation
settings remain those of the completed diagnostic. These are familiar message
choices, not composite transfer or temporal target swaps.

## Fixed allocation: at most 972 new calls

- 36 direct output checks, with each of digits 1, 2 and 3 requested 12 times.
- 864 message choices: 36 bundles, four recipient/rebinding cells, two history
  renderings, and three cyclic candidate orders.
- 72 factual lookup checks: one existing record per bundle in both renderings.

The direct checks run first. If any answer is wrong, stop before the scientific
and lookup requests. Record and retrieve the failures, without retries or
replacement. The remaining 936 requests have a fixed shuffled order. A model
error or invalid output stops collection; missing cells stay missing.

The prose arm reproduces the existing visible evidence. The compact arm lists
each distinct historical scenario once, then each event with its record number,
participant, scenario reference, exact message and outcome. Expanding those
references must reconstruct every original visible event exactly. No totals,
frame labels, posterior beliefs, hidden types or strategy advice are added.
This changes layout and redundancy together. A difference cannot be attributed
to token count alone.

Every candidate occupies each numeric position once within a matched cell.
These are three cyclic rotations, not every possible permutation. The same
seed is used across formats and rotations within each cell. This reduces one
source of variation but does not eliminate sampling noise or make decoded
labels permutation invariant. Each request has only one sampled answer.

Lookup asks whether the outcome in one numbered record was A, B, or not
recorded. The answer is determined only by that visible event. A correct answer
demonstrates literal access to that record, not aggregation, strategy
classification or partner modeling. Direct checks are engineering controls
with different instructions, not examples given to the focal task.

## Analysis fixed before any new output

The main score is the original normalized familiar binding contrast, computed
within a bundle and rotation, then averaged over three rotations. Report both
format means, sample SDs, all 36 paired differences and all rotation scores.
Missing output cells receive conservative bounds; do not drop a bundle.
Report all digits, selected frames and candidate probabilities alongside raw
outputs. No new target outcomes are sampled.

Report direct check accuracy and paired lookup outcomes separately. For order
stability, report whether the same semantic candidate is selected in all three
rotations. Report numeric position distributions, not just semantic agreement.
Neither inconsistency nor position frequency alone isolates a deterministic
position bias under sampled decoding.

The fixed bank is already inspected and this design follows a negative result.
Use descriptive estimates, not a confirmatory gate pass, p value search or
claims of equivalence from a small difference. The statistical unit remains a
bundle. Retain the earlier reference policies and the exact belief/reward
equivalence as limitations; this run cannot prove a unique representation.

## Interpretation and stopping rule

After this one fixed run, write a project conclusion regardless of sign:

- Failed direct controls mean the output interface is not adequate for this
  protocol. Do not interpret uncollected focal performance.
- Poor lookup performance limits claims about the model using the supplied
  evidence. Better compact lookup would support presentation sensitivity.
- Good lookup but weak binding means literal reading alone is insufficient;
  it does not identify which later reasoning step failed.
- Better compact binding is a presentation effect in this setup, not proof
  of a latent partner model. Weak binding in both formats narrows this attempted
  explanation without proving the capability absent.
- No possible positive outcome resolves the additive belief/reward equivalence.

No automated model sweep, further prompt version, activation capture, probe or
steering experiment follows. Reusing these exact artifacts for a local audit
is allowed. Any genuine software fault is documented and historical data remain
immutable; a changed experiment is never silently substituted.

## Compute and data boundary

Try to resume only the backed up extension pod `i0szqs87ifg0id`, which holds
the public model cache. Never modify the old calibration pod or network volume.
If resume fails and stopped state is verified, at most one fresh A100 80GB may
be used, with the same packet and a live quote no greater than $2/hour.

Keep a 90 minute external watchdog and an 80 minute collection deadline. At the
earlier $1.59/hour quote, 90 minutes is $2.385 in additional compute. Including
the previous approximate $1.20, this leaves room under the existing $5 working
allocation. Recheck live prices. This is not a provider enforced billing cap;
storage still accrues on stopped pods. No deletion permission is inferred.
Retrieve and verify all outputs before stopping the scoped GPU. No API key is
written to source, a packet, the pod environment or logs.
