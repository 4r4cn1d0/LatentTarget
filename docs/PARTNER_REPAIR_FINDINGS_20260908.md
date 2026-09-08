# What the bounded repair actually changed

The statistical candidate passed the declared synthetic screen at 288
independent bundles. The wording draft removed several positive word overlap
shortcuts, but it is not free of lexical information. Neither outcome is a
new result about an LLM. The project is still not ready for a claim about
latent target representations or a paid confirmation run.

## Completed

One interval candidate and one wording draft were fixed before new outcomes.
The old implementation, old failed screen and all historical model results
remain intact. No API calls, GPU deployments or human labelling took place.

The completed work consists of:

- 280,000 fresh simulated datasets, each analyzed by both interval methods.
- 160,000 separate known mean datasets for coverage diagnostics.
- Three paired wording seeds, each with 288 bundles and two banks.
- 41,472 complete prompts, all undispatched.
- 331,776 raw synthetic policy responses, with every failure retained.
- A 54 item human review export with blank labels and a separate analyst key.
- Read only verification, reproducible runners, plots and a full results table.

Replays and smoke runs are engineering checks, not additional independent
scientific evidence. See the [full generated report](../results/partner_repair_report_20260908/REPORT.md)
for every scenario, coverage cell, policy and seed. The
[work log](PARTNER_REPAIR_WORK_LOG_20260908.md) records implementation problems
and their fixes.

## Verified

The full repository suite passed 993 tests. Two later verifier tests passed
separately and in the final 37 test focused run. All 440,000 saved datasets
passed decision and rate reconstruction; 8,800 datasets were regenerated as
deterministic first batch checks. This was not a full simulation replay.

The full text audit replay matched every one of its 124 scientific output
hashes. The older failed screen also verifies unchanged. Both plots were
rendered and visually inspected. See the
[verification artifacts](../results/partner_repair_verification_20260908/).

## What improved statistically

The previous method resampled the empirical distribution within target pair
strata. Its variance estimate is too small by a factor of 5/6 at 36 bundles
and 47/48 at 288 bundles, relative to the estimate using sample variance with
divisor n minus one. That relationship is exact for equal stratum sizes. It
does not, on its own, prove correct confidence coverage.

The candidate corrects that variance factor and uses a conservative Student
critical value. The simulator, sample ceiling, missing response bounds and
all scientific thresholds are unchanged. The
[fixed plan](PARTNER_REPAIR_PLAN_20260908.md) gives the exact formula and sources.

At N = 288, the four required alternatives cleared the 80% lower confidence
bound requirement for the complete decision, including controls and validity:

| Prespecified alternative | Complete pass rate | 95% Monte Carlo interval |
| --- | ---: | --- |
| Half belief policy, shared routing | 97.48% | 97.01% to 97.88% |
| Half belief policy, independent routing | 82.54% | 81.46% to 83.57% |
| Half belief policy, 1% random missing outputs | 92.48% | 91.72% to 93.18% |
| Half belief policy, selective missing outputs | 96.22% | 95.65% to 96.71% |

These are mathematical mixture policies, not estimated LLM capabilities.
Selective missingness means a 3% failure probability conditional on a fairness
dominant choice, not a guaranteed 1% overall failure rate.

The candidate's uniform null primary rejection rate was 4.12%, with a 95%
Monte Carlo interval of 3.60% to 4.71%. The other nontrivial null upper bounds
were 4.64% and 4.83%. All six null scenarios cleared the declared 5% upper
bound requirement. Complete continuation was zero in every tested null cell.
The intervals are pointwise, not simultaneous across the screen.

On those same fresh datasets, the original bootstrap did not clear the rule.
For example, its uniform null estimate was 5.04% with an upper bound of 5.68%.
This does not prove its underlying error rate exceeds 5% at N = 288, since
the interval includes 5%. It means the stipulated certification rule failed.

Only N = 288 cleared both sensitivity and null calibration for the candidate.
The saved status is `OFFLINE_SENSITIVITY_PASS`, not deployment approval.

## What remains wrong with confidence coverage

Passing the selected null screen is not enough to claim a generally calibrated
confidence interval. The extra diagnostics expose the difference:

| Known mean diagnostic | Candidate coverage | Nominal coverage | Important detail |
| --- | ---: | ---: | --- |
| Bernoulli mean 0.05, N = 36 | 83.52% | 97.5% | 16.48% of samples have zero estimated variance |
| Bernoulli mean 0.05, N = 72 | 87.36% | 97.5% | Worse than the old bootstrap's 97.06% |
| Bernoulli mean 0.10, N = 288 | 96.84% | 97.5% | Monte Carlo interval 96.32% to 97.29% |

The last result shows that this limitation is not confined to tiny samples.
Sparse, skewed distributions can defeat the approximation even when its
average variance estimate is reasonable. Zero variance was recorded explicitly,
not patched with a new fallback after the results arrived.

At true mean 0.10 and N = 288 in the Bernoulli diagnostic, detection against
zero was 100%, but only 49.96% met the observed 0.10 mean threshold. We must
not call those two quantities the same power calculation. That threshold is
also not a confidence claim that the true effect exceeds 0.10.

I have not replaced the historical analysis with this candidate or declared
the statistical problem universally solved.

## What changed in the wording

The new draft equalizes whitespace word lengths and avoids shared content
words between familiar messages and the new clauses. It retains the original
additive simulator vectors. Every bank comparison uses the same history
events, target choices and random draws.

The original positive word overlap shortcut replicated across all three audit
seeds. In the new draft:

- Content word and shallow stem policies had zero composite transfer.
- The length policy had zero binding and zero transfer.
- The original Jaccard policy's transfer was about minus 0.042, minus 0.042
  and plus 0.038, below the required positive effect.
- None of the five prespecified shallow policies passed the complete positive
  gate under either interval method on any of the three seeds.

That last sentence is true but insufficient. The character trigram policy
produced transfer of minus 0.181, minus 0.139 and minus 0.160. Its individual
97.5% intervals all excluded zero on the negative side. A rule that reverses
or learns such a mapping may recover useful lexical information. This is an
inference from the negative pattern, not a tested reversed policy. Adding a
reversal after seeing these results would be exploratory, so I did not use
one to certify the bank.

The wording therefore remains a diagnostic draft. Word length matching is
not tokenizer matching, semantic validity or immunity to lexical adversaries.

## The larger scientific limitation remains

Participant specific feature reward learning still produces strong transfer
on both banks. It passes the complete gate in two of the three seeds, with
identical results across wording banks. That is expected because this
mathematical reference receives registered frame annotations. It demonstrates
a viable simpler explanation, not an LLM's internal mechanism.

The messages also give criteria without establishing why the preferred option
meets those criteria. A message about equal treatment does not establish why
a folder called Maple is fairer than one called Coral. We still need independent
review of whether these stimuli are interpretable arguments at all.

The original research claims remain unchanged: one model showed behavioural
learning in the old setup; reliable silent revision and a latent target
representation have not been demonstrated.

## Next checkpoint

The bounded offline repair is complete. I do not recommend buying more GPU
time for this draft yet. The next decision should settle these items before
another experiment is run:

1. Review the [54 complete messages](../results/partner_repair_stimuli_20260908/human_review_items.json)
   independently. The labels are intentionally blank. If these are not valid
   arguments, reject the draft without treating the audit as a success.
2. Freeze a separate evaluation bank and a lexical check that allows either
   direction of prediction, with mappings fitted only on development data.
   Do not keep editing and testing the same confirmation examples.
3. Specify whether the next claim is participant specific reward learning or
   a belief about target type. The latter needs a test that separates those
   explanations, not simply more runs of the additive transfer task.
4. Present the exact prompt bank, analysis limitations, model choice and cost
   cap for approval before any new paid or mechanistic run.

This is a handoff recommendation, not an additional experiment or hidden
change to the fixed plan. No commit, push or Google Docs edit was performed
in this stage.
