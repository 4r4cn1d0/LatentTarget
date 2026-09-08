# Why I would not spend money on this diagnostic

7 September 2026. [Full report](../results/history_diagnostic_20260907/REPORT.md).
[Exact sample prompts](../results/history_diagnostic_20260907/SAMPLE_PROMPTS.md).
[Plan](HISTORY_DIAGNOSTIC_PLAN_20260907.md).
[Work log](HISTORY_DIAGNOSTIC_WORK_LOG_20260907.md).

## What we tried

The baseline comparison left a question open. The original Qwen behaviour was
slightly better predicted by ordinary reward learning than by a model that
tracked the partner's hidden type. Could a more targeted test separate them?

I built pairs of histories that contain the same experiences, arranged in a
different order. Each history has six fairness messages, six risk messages
and six expertise messages. Each category has three successes and three
failures. Its own sequence of outcomes is identical in both histories. The
last three events are identical too.

Only the way the categories are interleaved changes. The words, scenarios and
outcomes stay attached to the same events. The current decision and candidate
messages also stay the same.

An ordinary reward learner updates a category only when that category is
chosen. Because each category has the same experience in both histories, its
final reward estimates must be identical. This holds for every learning rate,
not just the one we fitted.

A belief model that allows the partner to change can care about the global
order. Evidence about a category can become less useful while other categories
are being tried. That gives us a possible difference in predicted choices.

## What actually ran

Everything ran locally. I constructed 18,432 candidate histories and retained
576 matched pairs. There are 1,536 prepared prompts, including duplicate prompt
controls, but none has been sent to an LLM.

The screen tested 17 mathematical policies across 2,280,000 simulated studies.
It also ran 102,000 synthetic datasets for model recovery. These are small
numerical simulations, not model generations or paid API calls.

The experiment asks whether the model chooses a designated category more often
after one history than after its matched counterpart. The direction is fixed
by the reference predictions before any possible real response. Both the
overall test and the test excluding expertise focus pairs must pass. This
prevents a result coming only from the default category.

## Problem one: the predicted difference is too small

The fitted dynamic belief model predicted an average difference of 6.7
percentage points between paired histories. For fairness focus pairs it was
only 3.7 points. Under its modal choices, the average fairness choice contrast
was zero, another reason not to assume its probability model transfers
directly to a greedy LLM.

Even at the maximum of 576 independent pairs, the nominal dynamic model passed
both planned tests in only 56.3% of simulations under independent sampling with
no lost pairs. The Monte Carlo interval was [54.9%, 57.7%].

We also required sensitivity to half the predicted effect rather than assuming
the historical fitted parameters would transfer perfectly. With 10% randomly
unusable pairs and the conservative dependence scenario, the joint detection
rate was 8.5%, with interval [7.7%, 9.3%]. The target was a lower confidence
bound of at least 80%. None of the six planned sample sizes passed.

This was not a borderline decision. I did not increase the sample ceiling or
weaken the test after seeing the result.

## Problem two: ordinary recent memory produces the same effect

This is the more important problem.

A rule can remember recent successes and failures without tracking a hidden
partner type. I tested rules that discount old observations and rules that use
only the last five or eight observations.

Those recent window rules passed the diagnostic almost every time at the
maximum sample size. A discounted evidence rule reached about 93% joint
rejection in the most favourable declared scenario. None of these rules
contains a belief over partner types.

This is not a statistical false positive for the question, "Does global order
matter?" Global order really does matter to those rules. It is a problem with
interpreting the answer. An order effect would not tell us that the model had
formed a partner representation. It could just reflect ordinary recency.

Our formal distinction is between independent category reward estimates and
joint beliefs over one hidden type. It is not an exhaustive definition of user
modelling. Behaviour alone cannot automatically tell us which internal
description is the right one.

## Why the recovery result does not rescue the test

When I simulated the exact dynamic belief policy and asked which of the 17
fixed policies best predicted all its choices, it was identified correctly in
82.5% of datasets at 576 pairs. The reward learner was identified in 68.9%.

Those figures assume that the true algorithm is one of the candidates, with
the supplied parameters and probability model. An actual LLM need not meet
those assumptions. Recovery also uses the full pattern of choice likelihoods,
not the narrower paired test. Its 82.5% cannot be substituted for the failed
prospective sensitivity result.

Some candidates were exactly indistinguishable here. With balanced counts,
static beliefs and history frequency produce the same predictions under their
shared choice settings. Their unresolved ties are a limitation of the design,
not an implementation error.

## Decision

Do not pay to run this diagnostic as evidence for a latent partner model.

The local system works, and the tests exposed a scientific weakness before we
spent money collecting another ambiguous result. That is useful, but it is
not a new positive result about an LLM. The original evidence still supports
behavioural adaptation in one setting, with simple reward learning as a
plausible account and no established latent representation.

This failure applies to this proposed diagnostic. It does not prove that LLMs
lack partner representations or that every future diagnostic would fail.

The next step I recommend is to bring the completed baseline comparison and
this negative design result into the main writeup. Keep the claim narrow and
the missing human validation explicit. Any new experiment should begin with
a separately reviewed question and evidence that its result would discriminate
between the explanations we now know can mimic each other.

No paid run, GitHub push, Google Doc edit, activation experiment or scientific
gate change was performed in this stage.
