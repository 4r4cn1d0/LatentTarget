# The first grounded diagnostic on RunPod

The 60 request pilot completed on 9 September 2026 in India. The runtime worked,
but the result does not establish participant specific adaptation. It also does
not establish that the model lacks this ability. The sample contains only three
bundles, and several of their histories give misleading evidence about the true
simulated type.

## What ran

The model was `Qwen/Qwen3.8-27B`, pinned to revision
`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`. One A100 80GB ran the model in
BF16 with PyTorch 2.9.1 and Transformers 5.16.1. Temperature was 0.7, top p was
0.8, top k was 20 and thinking was disabled. Decoding was constrained to the
digits 1, 2 and 3. Therefore, 100% valid output is an engineering result under
this constraint, not evidence of unconstrained instruction following.

The frozen packet contains three scenario bundles, five branches and four
requests per branch. Each history has 24 simulated records across two people.
The model chooses a message from three candidates. It does not write messages
or generate the histories itself. Participant labels are exchanged on the same
history to test whether it matters who received which feedback. This is not a
silent target swap over time.

All 60 requests completed once, in their frozen order, with their frozen seeds.
There were no missing responses, failed calls, replacement choices or retries.
The real processor produced 391 to 5,114 input tokens, matching the prior CPU
check. The recorded generation calls totalled 138.24 seconds. That excludes
dependency installation, model loading, input preflight and result retrieval.

## Results

These are normalized contrasts, not percentages or success rates. Positive
binding means that exchanging participant histories changes message selection
in the direction associated with the hidden types. A value of one is the ideal
hidden type oracle. Zero can mean no sensitivity, or cancellation between
different choices. Negative values do not by themselves identify a cause.

| Measure | Exhibition | Repair workshop | Archive | Mean | Sample SD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Familiar message binding | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| Composite transfer | 0.000 | -0.500 | 0.000 | -0.167 | 0.289 |
| Paraphrase binding | -0.250 | -0.250 | 0.000 | -0.167 | 0.144 |
| No history, familiar | -0.500 | 0.500 | 0.000 | 0.000 | 0.500 |
| No history, composite | 1.000 | 0.000 | -1.000 | 0.000 | 1.000 |
| Random responses | -0.500 | -0.500 | 0.000 | -0.333 | 0.289 |

The random control contrast uses an arbitrary pseudo type geometry. Its negative
value is not evidence of negative susceptibility. Every row has three bundles,
not 60 independent observations. No p values, confidence intervals or claims of
statistical confirmation are reported.

All eight frozen references were retained. Character trigram, original Jaccard
and stem Jaccard each had mean composite transfer of 0.333 on these bundles,
compared with Qwen's -0.167. The privileged static belief reference had mean
binding and transfer of zero. This small comparison cannot rank model families
or identify an internal mechanism. The full table is in the
[collection report](../results/runpod_diagnostic_20260909/analysis/PILOT_COLLECTION_REPORT.md).

An independent vectorized implementation reproduced every aggregate contrast.
The postcollection audit also checked all request IDs, execution indices, seeds,
prompt hashes and output validity. All three bundle values are retained in
[the audit](../results/runpod_diagnostic_20260909/postcollection_audit.json).

## What the raw choices show

In familiar message binding, the exhibition bundle selected fairness in all
four cells. The archive bundle selected expertise in all four. In the workshop
bundle, both recipients got risk under the original labeling, then both got
fairness under the exchanged labeling. That last pattern changes with the
history version, but does not distinguish the two recipients within it.

These observations cover all three bundles, not selected successful examples.
They are descriptive. Each cell has one sampled response and its own seed;
sampling noise, wording and candidate position remain possible explanations.
Across all branches, the model emitted digit 1 on 21 requests, digit 2 on 36,
and digit 3 on three. This imbalance does not isolate a position bias because
candidate text and position were not independently varied within each cell.

## The history evidence problem

After collection, I checked what the known response rule would let a Bayesian
observer infer from these exact histories. This is a supplementary diagnostic,
not a new outcome or an excuse to drop a bundle. It assumes a uniform prior,
independent static target types and perfect knowledge of the frame annotations
and simulator likelihoods. These are privileges the focal model did not have.

Every participant received four examples of each frame. The table gives the
number of Option A outcomes and the resulting posterior probabilities, in the
order fairness, risk and expertise.

| Bundle and participant | Actual type | A outcomes out of four per frame | Posterior |
| --- | --- | --- | --- |
| Exhibition L5 | Expertise | 2, 1, 2 | 0.447, 0.106, 0.447 |
| Exhibition W9 | Fairness | 2, 2, 4 | 0.051, 0.051, 0.898 |
| Workshop L5 | Fairness | 4, 3, 2 | 0.772, 0.184, 0.044 |
| Workshop N8 | Risk | 3, 3, 1 | 0.486, 0.486, 0.028 |
| Archive Y2 | Risk | 3, 2, 2 | 0.677, 0.161, 0.161 |
| Archive Q4 | Expertise | 3, 1, 1 | 0.898, 0.051, 0.051 |

Three participants have a unique highest posterior on the wrong type. Two have
ties that include the true type. Only one uniquely favours the true type. The
frozen static belief policy's familiar binding values are -1, 1 and 0, which
cancel in the average. Its composite transfer is zero in every bundle.

An agent can follow the evidence reasonably and still miss a hidden type in a
short, noisy history. This is why these data cannot distinguish a reasoning
failure from weak or misleading evidence using the ground truth contrast alone.
It also shows why the hidden type oracle is not an attainable evidence based
ceiling for every realized history. The posterior calculation was checked both
from outcome counts and by sequential updating. See the
[complete evidence audit](../results/runpod_diagnostic_20260909/history_evidence_audit.json).

## What remains unresolved

The provider received only the exact system and user strings, without analyst
metadata or hidden scores. The package hashes and prior isolation checks passed.
That verifies the implemented information boundary, not the absence of every
possible semantic shortcut. Wording based baselines still achieve positive
scores in this task. The machine judges' earlier disagreements remain in place,
and there is no human validation.

The target rule is still `P(A) = 0.38 + 0.34 * x[target]`, or 0.5 in the random
control. The report's candidate probabilities are simulator expectations, not
new target choices observed after focal generation. Only the digit choices are
new model observations in this pilot.

The additive response rule also makes a posterior over types observationally
equivalent to a suitable vector of expected rewards. This pilot cannot resolve
that identification problem. No activations, probes or steering interventions
were collected. No temporal revision experiment was run.

## Next decision

Do not scale this packet or interpret it as a latent representation result.
The next useful step is a local information audit over the already fixed larger
history bank, with no GPU use. Report how often the evidence favours the actual
type and how much candidate value is lost by different policies. Then freeze
any proposed future design and its interpretation before collecting more model
data. A future design should distinguish sensitivity to observed evidence from
recovery of the hidden generator, and assess shorter presentation and candidate
order controls separately. Those checks are proposals, not completed experiments.

Do not select only helpful histories after seeing these results. Preserve this
pilot as a negative, limited diagnostic. Any later study should include the
same unselected history population or explicitly declare a different population.

## Audit trail

- [Every exact system and user prompt](../results/diagnostic_pilot_package_20260908/package/packet.json)
- [All three simulated histories, with types, draws and target outcomes](../results/diagnostic_pilot_package_20260908/THREE_TRANSCRIPTS.md). Its preparation date statements are historical.
- [All 60 raw focal choices and selected messages](../results/runpod_diagnostic_20260909/analysis/PILOT_COLLECTION_REPORT.md)
- [Unmodified raw response records](../results/runpod_diagnostic_20260909/retrieved/responses)
- [Verified local backup receipt](../results/runpod_diagnostic_20260909/backup_receipt.json)
- [Deployment, problems, costs and cleanup log](RUNPOD_EXECUTION_LOG_20260909.md)

The statistical analysis skill guided complete descriptive reporting and the
separation of this small pilot from inferential claims. The Google Doc and the
remote GitHub branch have not been changed during this run.
