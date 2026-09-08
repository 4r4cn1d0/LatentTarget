# One bounded calibration repair and stimulus audit

Written before new simulated studies or policy outputs for this stage. This
follows the 7 September offline screen, whose no go verdict is retained.
The user authorized this local repair and audit, not a paid deployment.

## Fixed scope

Evaluate exactly one replacement interval procedure, alongside the original
procedure on identical fresh studies. Do not change the target simulator,
contrast definitions, mean threshold, confidence levels, equivalence margin,
response validity requirement, required alternatives or 288 bundle ceiling.
Do not add seeds or methods in response to an inconvenient outcome.

[The machine readable plan](partner_repair_20260908.json) specifies all seeds,
sizes, additional null checks, and descriptive coverage checks. Any code repair
must correct an implementation error against this specification, not tune it.
No result becomes authority to spend or capture activations.

## Candidate interval

For stratum h, let n_h be its number of bundles, w_h = n_h/N, and s_h squared
the sample variance with divisor n_h minus one. Compute:

```text
mean = sum_h w_h * mean_h
variance_of_mean = sum_h w_h**2 * s_h**2 / n_h
df = min_h(n_h - 1)
interval = mean +/- t_quantile(1 - alpha/2, df) * sqrt(variance_of_mean)
```

Use alpha 0.025 for each primary outcome and 0.05 for controls. Apply the same
procedure separately to lower and upper missing response bounds. Use the lower
bound analysis for primary continuation and both outer bounds for equivalence.
The whole bundle is still the independent unit. Intervals may be clipped to
the known support of minus one to one, without affecting coverage on that
support. Never remove an invalid request or use complete cases to rescue a gate.

The ordinary Student interval and its distributional qualifications are
described by [NIST](https://itl.nist.gov/div898/handbook/prc/section2/prc221.htm).
NIST also describes the [Welch Satterthwaite approximation](https://itl.nist.gov/div898/handbook/mpc/section5/mpc571.htm)
for combining estimated variance components. The minimum component degrees
of freedom used here is our deliberately conservative choice, not the Welch
Satterthwaite estimate or a NIST endorsed exact interval for this task. It is
no greater than that effective degrees of freedom formula for positive variance
components, and gives a wider critical factor for the same standard error.

This is not a distribution free confidence guarantee. Bundles have discrete,
bounded contrasts and fixed candidate allocations. Small, sparse distributions
may still be badly represented by a sample variance. A zero estimated variance
produces a point interval and is explicitly counted in coverage diagnostics,
not silently described as certainty about an arbitrary population. Null
calibration and nonzero coverage must be reported even when sensitivity passes.

The variance investigation will compare empirical variance of study means to
the average unbiased estimate and the conditional empirical bootstrap variance.
With equal stratum sizes m, the latter is exactly (m minus one)/m times the
unbiased estimate on each dataset. This checks the suspected contributor to
the old undercoverage without assuming it is the whole explanation.

Student critical values will be calculated by numerical integration and
bisection, tested against NIST's published t table and an independent composite
Simpson integration. No new runtime dependency is needed.

## Fresh calibration and sensitivity studies

All 12 original scenarios are retained. Add two null stress policies: a 90%
expertise default with 10% independently routed uniform choices, and a shared
bundle route selecting uniform choices half the time. Both have zero expected
binding. They test skewed defaults and within bundle dependence.

Run 5,000 studies in each of 14 scenarios at each of N = 36, 72, 144, 288.
This is 280,000 fresh datasets. Analyze both methods on each dataset. Report
paired decision differences, individual gates, complete continuation and null
rejection, using the same 95% Wilson Monte Carlo interval convention as before.

The original four intended alternatives must each have a lower Monte Carlo
bound at least 0.80 on complete continuation. Each of the six null scenarios
must have an upper bound at most 0.05 on both complete continuation and any
two sided primary rejection. These bounds are pointwise, not a simultaneous
confidence statement across all screen cells. If nothing clears, stop.

There is an important limitation in that rule: certifying an upper confidence
bound below a true rate exactly at 5% is inherently difficult. We retain the
rule rather than revising it after observing the first screen's borderline
result. Passing these particular nulls is conditional validation, not universal
calibration against every possible focal policy.

## Nonzero coverage and effect threshold diagnostics

Separately run 5,000 datasets per distribution, N and true mean in the fixed
grid 0.05, 0.10, 0.20 and 0.30. The distributions are Bernoulli on zero/one and
signed Bernoulli on minus one/one. Every bundle is independent, with the same
balanced stratum labels. This adds 160,000 datasets with exactly known means.

Report each method's interval coverage, zero variance frequency, mean and
standard deviation of study estimates, detection against zero and continuation
at the observed mean threshold. These are marginal metric diagnostics, not
full power for language comprehension. At a true mean of 0.10, continuation
at a 0.10 observed threshold should not be advertised as 80% power merely
because testing against zero has good sensitivity. Failures remain in the
report and constrain any claim of general interval coverage.

## One stimulus candidate, not a search loop

The new [wording draft](partner_wording_candidate_20260908.json) was authored
using only the previous audit. Every training body and every new clause has
eight whitespace words. New candidates still use three clauses and the same
registered composite vectors. The draft seeks to remove exact content word
overlap between training and new clauses without removing their intended
meaning. That intent is not semantic validation.

Compare original confirmation wording and the candidate draft on identical
allocation, aliases, neutral scenarios, frame schedules, target probabilities
and response draws. Only historical and candidate message wording changes.
Keep all choices and full prompt ledgers. Use three new fixed seeds at N = 288.
This is a paired text audit, not an independent real model replication.

Before outcomes, freeze these eight reference policies:

1. The original Jaccard word overlap implementation.
2. Content word Jaccard after removing the common recommendation prefix and
   a fixed function word list.
3. The same content policy with a fixed, shallow suffix normalization.
4. Character trigram Jaccard on the stripped body, retaining word order.
5. A length similarity policy with weight 1/(1 + absolute word count gap).
6. Static type belief with known frame annotations and simulator likelihoods.
7. Participant feature reward with known frame annotations.
8. The typed history oracle, restricted as in the original screen.

Shallow policies use visible words, the queried participant and observed
choices, never analyst frame labels or hidden type. The suffix transform is
not a semantic model and the character policy is not an exhaustive lexical
adversary. The mathematical references have explicit information advantages.

Export token overlap matrices, exact overlaps, character similarity, word and
character lengths, every policy's raw response, per bundle contrast bounds,
both interval analyses, complete gates, and paired original/candidate effects.
Also export unlabelled complete messages for independent review with a separate
analyst key. We do not label that review complete ourselves.

Do not reject or rewrite a candidate based on which individual examples happen
to yield good scores. A shallow policy passing limits interpretation. No shallow
policy passing does not prove a latent representation: semantic feature reward
learning remains a legitimate alternative under this additive simulator.

This draft is not a new production held out split. Future changes informed by
these audit results need a separate evaluation bank and human validation.

## Engineering acceptance and handoff

Tests must cover variance formulas, quantiles, direct confidence interval
calculation, deterministic replay, missing outputs, zero variance, malformed
inputs, paired text isolation and shallow policy ignorance of hidden fields.
Original sources and results stay unchanged so the previous verifier continues
to work. The new runner refuses existing output directories, freezes input
hashes and stores all study decisions, including failures.

The Matplotlib skill will guide comparison plots with clearly labelled
Monte Carlo intervals. The final report must separate completed engineering,
conditional statistical clearance, lexical limitations, human review and actual
paid run authorization. No stage here supplies an LLM result or a latent
representation claim.
