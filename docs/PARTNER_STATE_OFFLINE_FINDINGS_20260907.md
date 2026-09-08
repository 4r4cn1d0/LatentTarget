# What the offline partner study established

Screen started 7 September and finished 8 September 2026 in India. The artifact
date identifies the specification, not a new experimental version after midnight.

The pipeline runs, but its decision is **OFFLINE_SCREEN_NO_GO**. No new LLM
experiment ran. No GPU was deployed and no API money was spent. This is not
another failed LLM result. It is an audit of a proposed experiment before
asking a model to take it.

The [complete generated report](../results/partner_state_offline_20260907/REPORT.md)
contains all 48 simulation cells and all 13 mock policies. The
[methods](PARTNER_STATE_OFFLINE_METHODS_20260907.md) state the assumptions;
the [work log](PARTNER_STATE_OFFLINE_WORK_LOG_20260907.md) records implementation
and verification. Historical results and scientific stop conditions are unchanged.

## What now works

The offline system generated 288 balanced history bundles and all 6,912 planned
requests. None was dispatched. It ran 13 transparent policies through the full
prompt ledger, strict response parser and analysis, producing 89,856 synthetic
raw responses. It then ran 240,000 fresh simulated studies: 12 declared
scenarios, four sample sizes and 5,000 studies per cell.

It stores exact prompts, response identities and hashes, hidden probabilities,
sampling draws, raw mock responses, missing outputs, every study decision and
secondary diagnostics. No missing answer is replaced by a random choice.

The full repository test run passed 956 tests. Two newly added verifier tests
passed separately, and the final focused suite passed 116 tests. A second
complete execution reproduced all 85 scientific output hashes exactly. This
is a reproducibility check, not additional independent simulation evidence.

The tests confirm balanced allocation, isolation of hidden metadata, precise
participant ID reassignment and strict output handling. The bootstrap
calculation agrees with exhaustive enumeration and seeded resampling. This
checks the calculation, not its inferential coverage. The simulator and
measurement still implement an explicitly declared category task.

## 1. Sensitivity is promising at the largest planned sample

At 288 independent bundles, all four required alternative scenarios exceed
the registered sensitivity requirement: a lower 95% Monte Carlo confidence
bound above 80% for the complete decision.

| Synthetic scenario | Complete pass rate | 95% Monte Carlo interval |
| --- | ---: | --- |
| Half strength, shared routing | 98.12% | 97.70% to 98.46% |
| Half strength, independent routing | 84.68% | 83.66% to 85.65% |
| Half strength, 1% independent invalid choices | 94.02% | 93.33% to 94.64% |
| Half strength, fairness selective invalid choices | 96.60% | 96.06% to 97.07% |

Here half strength means choosing the evidence based reference policy with
probability one half and an expertise default otherwise. It does not mean a
0.5 contrast or describe a measured LLM. The mean BIND and TRANSFER contrasts
without invalid choices are roughly 0.30 and 0.32. Selective invalidity is 3%
conditional on choosing a fairness dominant candidate and zero otherwise;
its actual overall invalid rate at this mixture is about 0.5%, not 1%.

No smaller grid size meets all the required sensitivity conditions. At 144
bundles, independent routing has only a 22.70% complete pass rate even though
both primary tests pass in every simulated study. Control precision is the
limiting factor in that case, not a lack of signal.

These are conditional simulations. They do not estimate the probability that
a real LLM will understand the stimuli, use this strategy, or produce valid
answers. They do not justify selecting 288 bundles on their own.

## 2. Calibration does not clear the declared rule

The uniform choice null should not produce systematic participant matching.
The table counts rejection by either two sided primary test, before adding
the positive mean threshold and control requirements.

| Bundles | Null studies rejecting either primary | Rate | 95% Monte Carlo interval |
| ---: | ---: | ---: | --- |
| 36 | 418 / 5,000 | 8.36% | 7.62% to 9.16% |
| 72 | 302 / 5,000 | 6.04% | 5.41% to 6.73% |
| 144 | 272 / 5,000 | 5.44% | 4.84% to 6.10% |
| 288 | 222 / 5,000 | 4.44% | 3.90% to 5.0468% |

At 36 and 72 bundles, this is evidence of excessive rejection relative to the
intended 5% familywise level under the tested null. At 288, the estimate is
below 5%, but the upper confidence bound is just above it. The latter is
insufficient certification under our rule, not evidence that the true rate
at 288 exceeds 5%. Rounding that upper bound down to 5.0% would conceal why
the software returned no go.

There were zero complete continuations in all 16 null scenario/sample cells.
For any one 5,000 study cell, the upper 95% Wilson bound is about 0.0768%.
This means the full resource decision was conservative in these simulations.
It does not repair the smaller sample primary intervals. Fixed name, global
reward and global recency policies have zero binding contrast by construction.

The current screen separately requires acceptable primary test calibration.
That requirement was written before the smoke screen and was not removed
after it became the only final blocker at 288. No sample size is selected.

One plausible explanation for the small sample issue is the small number of
bundles in each bootstrap stratum. At N = 36 there are only six. Under an iid
within stratum model, the variance of the empirical bootstrap mean uses the
empirical variance with divisor n, rather than the unbiased divisor n minus
one. The expectation is smaller by the factor (n minus one)/n. This is a
candidate contributor to investigate, not a demonstrated complete explanation
or a justification for changing intervals after looking at the result.

The calibration rule also needs a separate statistical review: a method whose
true rejection probability is exactly the 5% boundary will seldom certify an
upper confidence bound below 5%. More Monte Carlo studies can narrow uncertainty
but cannot ensure that such a boundary criterion passes. Do not keep adding
seeds until the upper bound happens to fall on the desired side.

## 3. The complete gate is not a measure of modelling ability

The full static belief reference passes the primary endpoints in every
N = 288 simulation, but passes the complete decision only 71.12% of the time.
Its random response control is the bottleneck. The half strength shared policy
passes 98.12% of the time because its control statistic has less variation.

Both policies have control means near zero. Failure to put an entire confidence
interval inside the equivalence margin is not proof of leakage. A stronger
evidence using policy can therefore receive a lower full pass probability
than a weaker policy in this assay. That nonmonotonicity is a limitation of
interpreting the complete gate as a capability score. It is a precision and
resource decision, not a leaderboard.

The 3% independent invalidity stress condition has zero complete passes at
every N. At N = 288 its average response validity is about 97%, below the
required 98%. The gate correctly refuses to rescue a positive primary signal
using only valid answers.

## 4. A simple retrieval policy passes the proposed transfer test

On the saved 288 bundle bank, a participant specific word overlap policy has:

- BIND mean: **0.5955**.
- TRANSFER mean: **0.1944**.
- NEAR mean: **0.1042**.
- Complete mock decision: pass.

The policy compares sets of words in a candidate and the participant's earlier
messages, weights observed successes by Jaccard similarity, adds fixed
smoothing and chooses the largest score. It does not receive hidden types,
registered frame labels or simulator probabilities. It has no explicit type
belief. This is a direct implementation counterexample to a strong claim that
passing the new wording test requires such a belief.

This is one fixed bank result, not a power estimate for lexical retrieval.
The confirmation bank is therefore already exposed to this exploratory audit.
If a later bank is optimized against these results, it needs a genuinely new
evaluation split. Renaming a bank does not make it held out.

Participant reward, feature reward and recency policies also pass on this
bank. That is compatible with the narrower claim that behaviour uses evidence
associated with the right participant. It does not establish a latent target
representation or separate psychological modelling from associative learning.

Exact text disjointness is not the same as lexical independence. Familiar
fairness and new fairness text still share words such as person; expertise
text can share people. The audit does not isolate which particular overlap
caused the retrieval result, so individual words should not be declared the
proven mechanism.

## 5. Remaining stimulus problems are visible

A word count audit of canonical candidate sets found development NEAR lengths
of 22, 21 and 21 words versus TRANSFER lengths of 21, 21 and 22. In the
confirmation example, NEAR has 24, 27 and 26 words versus TRANSFER's 27, 27
and 23. Option text contributes the same prefix within a candidate set.
These are word counts, not model token counts. Three clauses per message
does not guarantee matched length or argument quality.

Some messages express a criterion without explaining why the preferred option
meets it. For example, expertise text asks that an assessment guide a neutral
choice but supplies no assessment. That may be acceptable for an explicitly
synthetic category learning assay; it is not realistic evidence of persuasion.
Independent semantic and plausibility validation remains unfinished.

## What I recommend next

Keep the existing experiment and results intact. The next engineering task is
one bounded calibration investigation, not another paid model run or a larger
sample ceiling. Diagnose the finite stratum bootstrap issue, choose a justified
correction before its validation run, and test it on fresh simulation seeds.
Retain the old result and report both. Do not silently relax the failed bound.

In parallel, make the stimulus claim explicit. If the intended claim is only
participant associated behavioural learning, simple retrieval passing is an
important baseline, not grounds for deleting the test. If the intended claim
is abstraction beyond lexical retrieval, the bank needs a separate lexical,
length and semantic audit and fresh held out stimuli. Even that cannot exclude
all participant feature reward learners under the additive simulator.

Only after that review should we select a current model, pin its exact revision
and prompt tokenization, quote a budget, and run the three bundle pilot. The
pilot must show every actual response and invalid output before scaling.
Human validation is still a separate requirement, not a task completed by
exporting review items. Causal activation and silent updating studies remain
unimplemented and require their own protocol and approval.

The important improvement is that the system now makes these limitations
testable before we spend money. It does not turn a synthetic success into
new evidence about the real model.
