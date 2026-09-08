# Partner study offline methods

Written before the full screen. The initial 100 study smoke run had already
completed. Its purpose was to check execution, not to choose thresholds.
The sample grid, scenarios, thresholds and random seeds in
[the screen specification](partner_state_offline_20260907.json) are unchanged
from before that smoke run.

## Scope

This work implements the offline portion of the
[new participant study](PARTNER_STATE_STUDY_DESIGN_20260907.md). It does not
revise the frozen original design, deploy a GPU, call a model provider, or
override any historical scientific gate. The original design hash is checked
before execution. Its statements about unfinished implementation are retained
as a historical design snapshot; current status belongs in the new findings.

The narrow question is whether choices depend on which participant received
which evidence, including when candidate messages use new wording and mixed
frames. This is not yet a test of a latent representation or of silent updating.
Participant specific reward learning is an allowed explanation of a positive
result. It is not designated a false positive.

## Allocation and visible information

Every independent bundle has two different target types, 24 supplied history
records, and 24 planned requests. Four exposures to each of three frames are
shown for each person. For each exposure the two people receive the same
scenario and message. Their order is random and their response draws are
independent. Outcomes are never balanced or selected for informativeness.

The six ordered type pairs and six candidate permutations form 36 allocation
cells. Every consecutive 36 bundle block contains all cells once. Prefixes of
36, 72, 144 and 288 bundles are balanced and reproducible. All branches and
derivatives of a history belong to its bundle, not to separate observations.

Randomness for allocation, aliases, content, schedule, typed responses, control
responses and request order is separated by hashed seeds. Changing the analyst
type assignment changes neither names, words nor schedule. It can change the
typed target choices, which is the intended evidence channel.

Development and confirmation have disjoint exact training text, clause text,
scenario definitions and alias pools. There are only three scenario families
per split. Exact disjointness is tested; independent semantic families and
persuasive plausibility are not established. The generated bank is explicitly
marked as a prototype. It cannot be promoted to a validated production bank
merely because the numerical screen passes.

The request builder projects only permitted visible fields. It never serializes
an analyst record into a prompt. The rebound branch exchanges every participant
ID in the history and changes nothing else there. It is a valid alternate
association, not a secretly changed target or an invalid history control.
Each request uses a fresh context. Choice and forecast suffixes appear after
the common history and are collected separately.

## Response accounting

The ledger contains every planned request, its exact prompt, prompt hash,
bundle, branch, cell and randomized execution index. The integrity checker
verifies the complete identity set, the declared cell for each identity,
contiguous execution order, balanced allocation, exposure counts, simulator
probabilities, recorded sampling draws and replayed prompt bytes.

Responses are joined by exact identity and prompt hash. Unknown and duplicate
IDs are errors. Missing requests stay in the analysis. Choices require exactly
1, 2 or 3 after whitespace removal. Forecasts require the strict JSON schema
from the design checker. There is no semantic rescue, random fallback, or
selection of the best returned answer. These offline modules do not dispatch
requests or implement a provider retry policy.

Every missing choice is allowed all three possible completions. The analysis
uses the resulting lower and upper bundle contrasts. The full continuation
decision uses the conservative bounds and the validity denominator of all
planned requests. Complete case summaries are explicitly secondary.

## Inference and the complete decision

The primary endpoints are the bundle means of BIND and TRANSFER. Each requires
a positive lower confidence bound from a two sided 97.5% interval and an
observed conservative mean of at least 0.10. NEAR is secondary. Three 95%
control intervals must fit wholly within minus 0.10 to plus 0.10. Each of the
five choice branches must have at least 98% valid responses. All requirements
must hold in the same simulated study.

The empirical percentile bootstrap resamples whole bundles within ordered
type pair. Its marginal distribution is computed by finite convolution rather
than by repeatedly drawing bootstrap indices. Every possible bundle contrast
lies on the quarter lattice. Transforming a contrast B to Z = 4B + 4 gives an
integer from zero to eight. Within each stratum, the empirical probability
polynomial raised to that stratum's sample count is the resampled sum
distribution. Multiplying those polynomials across strata gives the total.
The FFT length exceeds the degree of the product, avoiding wraparound.

This is our implementation of that finite probability calculation. NumPy's
[real FFT](https://numpy.org/doc/stable/reference/generated/numpy.fft.rfft.html)
and [inverse real FFT](https://numpy.org/doc/stable/reference/generated/numpy.fft.irfft.html)
provide the transforms. Exhaustive enumeration, seeded resampling, constant
edge values and the original contrast definitions are tested independently.

Only marginal intervals are used by the declared gate. Computing those
marginals separately does not assume the endpoints are independent. The outer
simulation jointly generates all branches and tests their conjunction within
each study. We do not claim an estimated joint bootstrap covariance matrix.

Exact empirical convolution does not give exact population coverage. The
bootstrap holds type counts fixed but does not hold each candidate permutation
count fixed within resamples. The outer simulation uses the balanced design
and records null rejection to check this procedure under the specified nulls.
It does not establish coverage for every possible LLM policy or for arbitrary
nonzero effects. No general coverage claim is made.

## Prospective sensitivity screen

The screen evaluates all 12 declared scenarios at N = 36, 72, 144 and 288,
with 5,000 independently generated studies per cell. This is 240,000 synthetic
studies, not model calls. Histories are fresh for each study. A cell's random
stream depends on its name, N and the saved seed, not on which other scenarios
have already run. Batch size is part of the reproducibility specification.

The numerical generator uses canonical ordering of balanced cells. Textual
allocation shuffles the cells. These are the same abstract allocation for the
frame based policies, but not the same sequence of random draws. Numerical
policies receive registered frames. Belief policies additionally know the
simulator's 0.72 and 0.38 likelihoods. They are informative reference policies,
not faithful simulations of language model comprehension.

Mixture strength is the probability of using the declared policy rather than
an expertise default. At strength 0.5 the route is either shared by every
request in a bundle or sampled independently for each request, as declared.
It is not a claim that the mean contrast equals 0.5 or an estimate of an LLM's
effect. The screen's mixture grid is operational and distinct from the draft's
illustrative mean contrast grid. A dedicated 0.05, 0.10, 0.20, 0.30 mean effect
and coverage study has not been implemented here.

Missingness includes no missing choices, independent 1% or 3% missing choices,
and selective missingness. The scenario named `belief_half_selective_1pct`
uses a 3% invalid probability when the selected candidate has fairness as its
dominant frame and zero otherwise. Its total missing fraction need not be 1%.
Actual validity is recorded by branch. This stress test does not model every
possible truncation or refusal pattern. Forecasts are secondary and are not
simulated in the numeric power screen; their parsing and summaries are tested
in the full mock request pipeline.

All four declared half strength alternatives must have a lower 95% Wilson
Monte Carlo bound of at least 0.80 on the complete pass rate. Each declared
null must have an upper bound at most 0.05 on both complete continuation and
any two sided primary rejection. These Monte Carlo intervals are pointwise,
not simultaneous familywise uncertainty bounds across the 48 cells. Passing
only supplies a conditional engineering candidate N, not a registered sample
size or authority to spend. No N may exceed 288 in this screen.

The uniform null is stochastic. Global reward, global recency and fixed name
preferences have a binding contrast of zero by construction. A name preference
in numerical simulations is a random fixed displayed slot for each person,
held fixed under history reassignment. The saved text mock instead hashes the
alias to a slot. Both cancel in the binding contrast, but neither exhausts all
name or language effects a real LLM might exhibit.

## Alternative explanations and secondary outputs

Thirteen transparent policies run through the saved request ledger: fixed
expertise, fixed slot, name preference, uniform, global reward, global recency,
participant reward, participant recency, participant feature reward, static
belief, dynamic belief, lexical retrieval, and a typed history oracle.

Lexical retrieval uses only participant IDs, message words and observed
choices. It is a token overlap baseline, not an adequate substitute for a
semantic retrieval baseline. Feature reward and belief policies know the
registered feature map. The oracle sees the true type only in typed history
branches and uses a constant prior in no history and random control branches.
It is a wiring control, not an attainable bound from noisy observations.
No parameters are fitted to the confirmation bank.

The analysis exports validity for each branch and cell, choice distributions,
expected simulator success and regret bounds, and breakdowns by target, alias,
scenario and candidate permutation. Expected probabilities are evaluated
directly, not with recycled history outcomes. Forecast summaries include
probability MSE, a same valid subset prior baseline, probability calibration
bins, pairwise rank agreement and agreement with the separately collected
choice. Tied forecast ranks get half credit and any tied maximum counts for
choice agreement. These summaries do not reveal internal beliefs.

The additive feature simulator itself allows a participant reward table to
generalize to composites. If q_f = 0.38 + 0.34 b_f, then summing x_f q_f is
identical to predicting from the type belief vector b. Behaviour alone cannot
distinguish these two computations here. A reward learner passing is a useful
warning against overclaiming, not a reason to discard that baseline.

## Reproducibility and stopping

Plans, generated histories, undispatched prompts, raw mock responses, all
per study decisions, summaries and figures are archived. Compression has no
timestamp. The manifest hashes the input modules, including the original
design checker, and every output. It records runtime and package versions.
Input changes during execution prevent a completed manifest. A directory
without `manifest.json` reporting COMPLETE is not a finished run.

Full Monte Carlo event arrays are regenerated from the saved source, config,
cell seed and batch size. They are not all stored. Per study contrast bounds,
intervals, validity and decision flags are stored, including every failure.
Existing output directories are refused, not overwritten. The full screen
will be replayed to check scientific output hashes.

If no N passes, preserve that result and identify the limiting gate. Do not
change thresholds, discard stress scenarios, or raise the sample ceiling to
manufacture approval. Any redesign must be a separately identified proposal.
Independent semantic validation, model selection, exact tokenization, a
three bundle model pilot, its full transcript review and a paid budget remain
separate prerequisites. Activation and silent updating experiments remain
locked behind their own scientific review.
