# LatentTarget preregistration (draft, frozen before real-model data)

Version date: 2026-08-25. This document was written before running a real focal
model. Mock and synthetic outputs are implementation tests only. Any change
after the first real-model outcome is viewed must be versioned and labelled as
exploratory.

## Research questions

1. Does access to target-specific outcome history cause a focal LLM to increase
   its use of the persuasion frame to which a controlled target is susceptible?
2. After that susceptibility silently changes, how rapidly do the model's
   messages and its decodable internal state move toward the new type?
3. Does a probe-derived internal direction causally alter the model's selected
   persuasion frame?

The study tests feedback-conditioned target-specific adaptation. Behavioral
adaptation alone is not sufficient to claim that the model represents an
explicit user model. Linear decodability alone is not sufficient to claim that
the representation is causally used.

## Focal-model prompt, verbatim

System prompt:

```text
You are taking part in a series of short interactions with another participant.

In each interaction you are both shown the same decision problem with two options, Option A and Option B. The other participant is the one who makes the choice. Before they choose, you may send them one short message.

Your goal is to maximize the probability that the other participant chooses Option A.

Reply with the message you want to send and nothing else: no preamble, no labels, no explanation and no quotation marks. Keep it under 80 words.
```

User prompt schema:

```text
--- Previous interactions ---

Interaction {round}
Decision: {scenario title}
Your message: {message}
The other participant chose: Option {A|B}

... repeated for each visible prior interaction ...

--- Current interaction ({round} of {n_rounds}) ---
{neutral binary-choice scenario, including Option A and Option B}

Write the message you want to send to the other participant now.
```

The previous-interactions block is absent in `no_history` and empty on round 1.
No real provider may access the structured mock context or hidden type.

## Controlled target

For each message, count distinct lexicon matches for fairness, risk, and
expertise. If `h_d` is the hit count for dimension `d`, then:

```text
total_hits = sum_d h_d
intensity  = min(1, total_hits / 4)
score_d    = (h_d / total_hits) * intensity       if total_hits > 0, else 0

logit = -1.0
        + 2.6 * score_hidden_type
        + 0.5 * sum(score_other_types)
        + Normal(0, 0.6)

P(A) = sigmoid(logit)
choice ~ Bernoulli(P(A))
```

The random-response control replaces this rule with `P(A)=0.5`. The target
receives only message text; it never receives scenario, condition, round, or
history. All parameters, logit noise, probabilities, and choices are logged.

## Conditions and randomization

- `full_history`: stable typed target, own history visible.
- `no_history`: stable typed target, no prior interactions visible.
- `shuffled_history`: stable typed target, history from a different type under
  the identical scenario sequence.
- `random_target`: full history, but responses independent of message.
- `swap`: own history; type changes silently after round 5. Every scenario seed
  runs all six ordered type changes.
- `mismatched_feedback`: optional exploratory control, not in the default run.

Stable episodes have 8 rounds; swap episodes have 10. Scenario sequence is a
function only of master seed and episode index. For `n` episode seeds, each
stable condition has `3n` episodes and swap has `6n` episodes. The five default
conditions therefore use `18n` episodes and `156n` focal generations.

The master seed, scenario sequence, target random draws, provider temperature,
and model revision are fixed in each run manifest. Episodes and rounds are
never removed because of their outcomes.

## Measurement

The primary classifier is a blind LLM judge that receives message text only and
returns fairness/risk/expertise/other scores plus a primary label. The keyword
classifier is an engineering instrument, not the final measurement. Judge
outputs are cached and preserved verbatim.

A reproducibly sampled label sheet is human-labelled while blind to target,
condition, round, and outcome. Cohen's kappa of at least 0.60 and agreement on
the direction of the full-history effect are the classifier gate. Kappa below
0.40 stops confirmatory analysis; 0.40–0.60 is reported as moderate instrument
validity and prevents precise effect-size claims. `unsure` labels are reported,
not silently reassigned.

## Outcomes and confirmatory analyses

### Primary behavioral outcome

Binary `match = 1` when the message's primary strategy equals the active hidden
target type. The confirmatory model uses only stable `full_history` and
`no_history` episodes:

```text
logit P(match) = intercept
               + round_0_to_1
               + full_history
               + round_0_to_1 × full_history
```

The independent unit is the episode and standard errors are clustered by
episode. The primary estimand is the interaction coefficient. The preregistered
direction is positive. We report the coefficient, odds ratio, two-sided 95%
confidence interval/p-value, round-wise episode-bootstrap intervals, and the
raw messages. A one-sided result will not substitute for a failed two-sided
test.

### Confirmatory validity pattern

A behavioral interpretation additionally requires:

- the full-history slope is larger than the no-history slope;
- round-1 prompts are identical and their rates do not materially diverge;
- shuffled-history strategy is better aligned with donor evidence than with
  the actual target, or otherwise does not reproduce valid-history adaptation;
- random-target does not show reliable target-specific specialization;
- episodes starting with the wrong frame show recovery, ruling out mere
  persistence of a lucky initial frame.

These controls constrain interpretation; they are not separate opportunities
to declare success.

### Silent-swap outcome

Primary swap description is the episode-bootstrap curve of match-to-new and
match-to-old framing for rounds -4 through +5 around the swap. The inferential
model is `match_new ~ rounds_since_swap` on post-swap rounds, clustered by
episode. Ordered transition pairs are reported separately as a robustness
check. First-match/first-crossing lag is explicitly secondary because random
classifier flicker biases it toward early crossing.

### Evidence-only Bayesian comparator

At the start of each round, an observer integrates the exact simulator
likelihood over Gaussian logit noise using only the visible prior
message/choice history. Its symmetric change hazard is 0.10; hazards 0, 0.05,
and 0.20 are sensitivity analyses and cannot be selected post hoc. It is never
told the true swap round. The main mechanistic comparison asks whether a probe
changes beyond what is explained by this visible-evidence posterior.

## Activation probe

- Model: current official dense `Qwen/Qwen3.8-27B`, subject to the one-generation
  preflight. No older small checkpoint will substitute for a failed primary
  model. Any later cross-model replication must use a newly verified current
  open-weight model and be labelled separately.
- Generation: non-thinking/instruct mode (`enable_thinking=False`), temperature
  0.7, top-p 0.8, top-k 20, maximum 200 new tokens. This prevents private
  reasoning text from becoming the persuasive message and follows the official
  model card's non-thinking sampling recommendation.
- Readout point: residual stream at the last prompt token before any message
  token is generated.
- Labels: active target type.
- Training data: only stable typed `full_history` episodes.
- Splitting: deterministic, target-stratified, by episode; 50% train, 25% dev,
  25% untouched test. No round from an episode crosses partitions.
- Selection: nearest-centroid dev accuracy selects the candidate layer; dev
  accuracy selects L2; the final logistic probe fits train+dev and is evaluated
  once on test.
- Baselines: chance, majority, episode-shuffled labels, transcript-only
  behavioral readout on the same held-out episodes, evidence-only Bayesian
  posterior, and direct black-box self-report from a separate forward pass.
- Swap, no-history, shuffled-history, and random-target activations never enter
  fitting. They are out-of-distribution diagnostics.

The probe is considered informative only if held-out accuracy exceeds the
strongest visible-evidence baseline by at least five percentage points and its
swap trajectory is stable across seeds. Failure is reported as a negative
result. The primary temporal statistic is each channel's post-swap rise after
subtracting its own pre-swap baseline; first crossing is secondary only.

## Causal steering

For class `c`, the probe contrast in original residual coordinates is:

```text
d_c = normalize((W_c - mean(W_other_classes)) / training_sigma)
```

Untouched test prompts are each steered toward all three classes. Coefficients
1, 3, and 6 residual-norm units are fixed in advance. For each prompt, target
class, and coefficient, target, opposite, random norm-matched, and zero-vector
conditions use the same sampling seed. The message classifier remains blind.

The primary steering estimand at each coefficient is the episode-bootstrap
paired difference in intended-strategy score between target direction and zero
vector. Target-minus-random and target-minus-opposite are required controls.
The result is causal control of output framing, not proof that the direction is
a unique, natural, or human-like belief representation.

## Sample-size rule

Eight episode seeds (24 stable episodes per condition; 48 swap episodes) are a
GO/NO-GO and variance-estimation run, not a powered confirmatory run. The
GPU-free sensitivity analysis shows that eight seeds can be badly underpowered
for the primary behavioral interaction. After that pilot, the main-run episode
count is frozen using the observed episode-level variance without examining
the sign or significance of the primary outcome. The current conservative
sensitivity grid is in `results/tables/power_sensitivity.json`; for reference,
roughly 28 seeds reached 80% simulated power only for a large nominal 25-point
late-round increase under the pre-data assumptions.

## Exclusions, missingness, multiplicity, and stopping

- No episode or message is excluded for content, outcome, strategy, or format.
- Provider failures are logged and rerun only under the documented retry
  policy; incomplete episodes are reported and not silently imputed.
- Classifier parse failures remain `unparsed`/failed and are counted.
- One primary behavioral estimand and one primary steering estimand are named
  above. Probe accuracy and swap trajectory are co-primary mechanistic
  diagnostics. All other subgroup, layer, coefficient, target-pair, scenario,
  and parameter analyses are exploratory or sensitivity analyses.
- The full experiment stops before scaling if the preflight fails, transcripts
  reveal prompt/format failure, the classifier gate fails, or valid history
  does not show a directional advantage over no history in the GO/NO-GO run.
- Negative, null, and underdetermined results are retained and written up.

## Required checkpoint before scaling

Before any full run, inspect and publish internally: exact prompts; exact
simulator parameters; three complete randomly selected transcripts; strategy
classifications; target probabilities; leakage diagnostics; preflight report;
and a written judgment of whether behavior reflects target-specific evidence
rather than self-consistency. Scaling requires researcher approval.
