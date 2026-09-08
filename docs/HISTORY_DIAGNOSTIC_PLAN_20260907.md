# A matched history diagnostic

Declared 7 September 2026, before generating this candidate bank or examining
its synthetic power. This is a bounded local feasibility study approved after
the baseline comparison. It does not reopen V5 to V8 or authorize model calls.

## The question and its limit

Does the order in which evidence from different message categories is
interleaved affect the next choice, after each category's own experience is
held exactly fixed?

Ordinary chosen action reward learning is invariant to this intervention. A
changing partner belief model need not be. But simple rules that discount old
evidence on a global clock need not be invariant either. A positive test could
reject a narrow reward learner. It could not, by itself, establish a latent
partner model. Explicitly test these counterexamples before recommending a run.

## History construction

Generate 576 independent history pairs, balanced by the category on which the
contrast is measured. Every history has 18 observations, six for each frame,
with three A outcomes and three B outcomes per frame. For each pair, generate
the three within frame outcome sequences once. Then generate 32 different
global interleavings. All preserve each within frame sequence exactly. Limit
consecutive prefix observations of one frame to three. The last three events
are identical across the pair and contain one observation of each frame.

Consequently the pair has exactly the same history length, frame frequencies,
reward totals, per frame reward order, most recent frame, most recent outcome,
and last three events. The per frame Q values agree for every learning rate,
not merely at a convenient fitted value. Counts, fixed preferences, repeating
the last frame, win stay rules and static Bayesian beliefs also agree. Static
beliefs depend on sufficient counts, not global interleaving.

For each pair choose the two interleavings with the highest and lowest
predicted probability of its designated focus frame under the dynamic belief
reference model. Selection sees only synthetic histories and fixed reference
models, never new LLM outputs. Keep all 576 pairs, even weak ones. Do not keep
generating a larger pool after seeing power.

Use the five V4 outer fold training priors as an equally weighted ensemble,
with their common selected reward and dynamic belief parameters. Verify those
parameters agree with the numerical plan before using them. This is informed
by the completed baseline analysis, not a fresh estimate or a claim that the
parameters are the LLM's mechanism. Save each prior's predictions too.

## Text rendering and information boundary

Within a pair, use the same 18 message and scenario event objects in a different
order. An event's identity is its frame and within frame occurrence. Message
wording and scenario are attached to that event, not to its global position.
Thus pairs have the same text multiset, and preserve message, scenario and
reward associations. Current scenario and all three candidate texts and slots
are identical within each pair. Balance current slot permutations and focus
frames in blocks of 18 pairs. Randomize both call order and which history is
shown first. Fresh contexts prevent one response affecting the other.

Use the existing V4 message bank and neutral scenarios; no new semantic labels
are claimed. These are **constructed history interventions**, not naturally
generated trajectories. Some may be unlikely under the focal policy. The
synthetic histories are possible under the noisy simulator, but selected for
model disagreement. That distribution shift must be disclosed.

Render the ordinary V4 system and user prompt at interaction 19 of 20 using
the exact existing prompt builder. The history was constructed by the analyst,
not actually produced by the LLM. No true target type or swap is sampled for
this diagnostic and no target outcome is generated after its test choice.
It tests processing of a supplied history, not successful online adaptation.
The provider facing export contains only a system and user string plus an
opaque request ID. Labels, scoring directions and reference predictions stay
in separate analyst metadata. Prepare prompts but provide no paid runner.

Add identical prompt sham pairs at one third the active pair count, balanced
across focus frames, for an eventual separate assessment of decoding stability.
They are technical repeats and never counted as extra independent active
pairs. No sham p value is a gate in the active effect's power calculation.

## Reference and challenge policies

Use fixed settings from the numerical plan. No refitting on the diagnostic.

- Ordinary reward learning, dynamic and static beliefs from the baseline code.
- Uniform, expertise, repetition, win stay and history frequency invariance
  checks. Exact invariant algorithms define the narrow null, not all algorithms
  that lack a partner model.
- Global decay Q: update the chosen Q value using alpha = 0.1, then move every
  Q value towards 0.5 after each global observation, at decay rates 0.02, 0.05,
  0.1 and 0.2. These are stress scenarios, not fitted estimates.
- Discounted evidence: discount every frame's success and exposure counts after
  each global observation, then add the current observation; estimate each
  success rate with a Beta(1,1) smoothing prior. Retention 0.8, 0.9 and 0.95.
- Recent event window: estimate per frame success rates with the same smoothing
  using only the last five or eight global observations.

All Q, evidence and window policies use the same softmax scale, frame priors,
repetition term and lapse floor as the reference models. They never maintain a
probability over target types. If they reproduce the diagnostic effect, the
effect is not specific evidence for a partner representation.

## Planned endpoint and exact test

For active pair i, record d_i = 1[high history chooses focus] minus
1[low history chooses focus]. Use the exact one sided paired sign test on
discordant pairs: conditional on k nonzero differences, the number of positive
differences is Binomial(k, 0.5) under within pair exchangeability. No discordant
pairs gives p = 1. Ties are not successes. Use the exact binomial tail, with no
normal approximation or Monte Carlo p value.

Require both the pooled test and the test restricted to fairness and risk
focus pairs at alpha = 0.025 each. This conservative split controls the two
reported directional tests at 0.05. It prevents a pooled positive finding
arising only from the expertise focus pairs. The positive direction is fixed
from synthetic dynamic belief predictions before model responses.

Report all three focus frame means and tests descriptively without promoting
them to additional discoveries. The experimental unit is a unique history
pair. Two responses in a pair and sham repeats do not add independent units.
No repeated greedy call is treated as a new subject. The exact test assumes
independent pairs and within pair exchangeability under the narrow null.

An eventual model run would need exact constrained 1/2/3 selection, an approved
checkpoint and an explicit budget. Do not repair invalid responses by silently
changing the history, retrying until valid, or applying post hoc exclusions.
No real run will be launched in this stage.

## Synthetic recovery and prospective sensitivity

Evaluate N = 18, 36, 72, 144, 288 or 576 unique pairs. Use balanced prefixes of
the fixed bank. At most 1,536 calls would be needed including the sham pairs
at N = 576. This is a planning ceiling, not an authorized spend.

Run 5,000 independently seeded simulated studies per scenario and N using the
exact planned test. Estimate rejection rates with Wilson 95% Monte Carlo
intervals. The skill's simulation harness is used for a separate sanity check;
the production calculation may be vectorized for this larger scenario grid.

For dynamic beliefs, report the nominal contrast plus 50% and 25% of it, formed
by mixing dynamic predictions with the invariant reward learner. The nominal
effect comes from the fixed baseline fits and synthetic bank, not from new
LLM data. The shrunk effects are transparent sensitivity assumptions, not
estimates. Never present a single power value as guaranteed for a greedy LLM.

Simulate independent within pair sampling and the negative dependence bound
using opposite uniforms. The latter maximizes discordance variance for fixed
Bernoulli margins. Also simulate 0% and 10% randomly unusable whole pairs;
unusable pairs contribute zero, not imputed evidence. This is only a fragility
check under random loss. It does not justify ignoring condition dependent
format errors in a real run.

Run true invariant nulls and all recency challenge policies with the same
analysis. Challenge rejection is **not** a Type I error under the narrow
invariance null: these policies really are order sensitive. It is a
counterexample to interpreting rejection as proof of a partner model.

Record full categorical predictions as well as focus probabilities. At each N,
simulate 1,000 datasets from each fixed candidate policy and classify them by
their total predictive log likelihood under every candidate policy. Count ties
as unresolved. This is closed set synthetic recovery, not a mechanism decoder
and not an assertion that the candidate set contains the true LLM algorithm.

## Bounded decision rule

Report the smallest tested N with Wilson lower power at least 0.80 under both
required tests jointly, for the 50% contrast with 10% unusable pairs in both
coupling scenarios. Require invariant null Wilson upper bounds at most 0.05.
If none passes, record insufficient sensitivity within this planning ceiling.
Do not enlarge N or relax a gate in response.

Independently report whether any recency challenge has a rejection Wilson lower
above 0.05 at that N, or at the maximum N if none qualifies. If so, mark the
diagnostic NOT SPECIFIC TO PARTNER BELIEFS and do not recommend a paid run as a
test of a latent partner representation, even if nominal power is high.

Synthetic feasibility never overrides the original scientific stopping rules,
unfinished human validation, or the need for a reviewed real run protocol.
Stop after this one declared construction and report its limitations.

## Verification and outputs

Test invariant states at multiple learning rates, static Bayes invariance,
dynamic sensitivity, preserved recent events and text multisets, prompt metadata
separation, allocation balance, exact p values, null calibration, synthetic
recovery, reproducibility and refusal to overwrite. Keep an artifact manifest
with plan, input, source and output hashes. Save all candidate histories, model
predictions, tests, power tables, recovery matrices, sample prompts and a plain
language report. Existing baseline and original experiment results stay intact.
