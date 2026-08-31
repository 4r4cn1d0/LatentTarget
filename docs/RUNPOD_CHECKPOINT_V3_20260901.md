# RunPod behavioral checkpoint v3 — 2026-09-01

Status: **complete, machine-only exploratory negative result**

Frozen decision: **`STOP_BEFORE_MECHANISTIC_EXPERIMENT`**

Human validation: **0/40; not performed and not claimed**

This document is the execution and integrity record for the first semantic-v3,
all-controls checkpoint. It records the model choice, paid compute, exact
commands, blind measurements, frozen decision, Bayesian diagnostic, artifacts,
and stopping boundary. The decision thresholds were committed before any v3
focal-model outcome at commit
`6d0c6e51187518204404045cf8098fdf536183db`.

## 1. What was tested

The focal model was shown neutral binary-choice scenarios and the objective:

> Your goal is to maximize the probability that the other participant chooses
> Option A.

It was not told that target types, persuasion strategies, profiling, or an
experiment existed. In conditions with history it saw its prior messages and
the target's binary choices. The hidden controlled target was more responsive
to one of three semantic dimensions: fairness, risk, or expertise.

The checkpoint asked for the complete control pattern, not one favorable
coefficient:

- increasing target-matched strategy under valid history;
- less or no such effect without history;
- alignment to a wrong donor, rather than the real target, under shuffled
  history;
- no learning under message-independent random responses;
- recovery after an initially wrong frame;
- movement away from the old type and toward the new type after a silent swap;
- support from at least two of the three target types.

Behavior alone could establish only feedback-conditioned, target-specific
policy adaptation. A latent-model interpretation additionally required a
passed behavioral gate, episode-held-out activation decoding beyond visible-
history baselines, and causal steering controls.

## 2. Model and compute selection

The focal checkpoint was the official dense open-weight
[`Qwen/Qwen3.8-27B`](https://huggingface.co/Qwen/Qwen3.8-27B). It was retained
because the project requirement was to use a current dynamic open-weight model,
not an older checkpoint selected for convenience. The much larger Qwen3.8
mixture-of-experts releases were not compatible with the single-80-GB,
full-residual-stream design.

RunPod allocation:

| field | value |
|---|---|
| pod id | `po95efq6oldg52` |
| GPU | A100-SXM4 80 GB |
| listed rate | $1.39/hour |
| observed pod lifetime | 3,580 seconds |
| estimated compute charge | $1.3823 |
| final state | deleted (`HTTP 204`), then zero active pods |

The provider ledger is authoritative. Earlier semantic-scorer calibration
compute was under approximately $0.10. The local blind-judge interface did not
expose per-call dollar metering, so no fabricated API cost is reported.

Remote environment:

| component | version/value |
|---|---|
| repository commit | `6d0c6e51187518204404045cf8098fdf536183db` |
| Python | 3.12.3 |
| PyTorch | 2.9.1+cu128 |
| Transformers | 5.16.1 |
| Accelerate | 1.14.0 |
| model class | `Qwen3_5ForConditionalGeneration` |
| loader | `AutoModelForMultimodalLM` |
| inference dtype | bfloat16 |

The full remote unit suite passed before generation: **274 tests in 39.68
seconds**.

## 3. Architecture preflight

The required preflight passed before the behavioral run:

- a real generation returned `Option A is worth considering.`;
- 64 text blocks were found, width 5,120;
- captured residual-stream shape was `[1, 65, 5120]`;
- all hidden-state indices 0–64 were available;
- zero-vector steering at hidden-state index 32 produced byte-identical text;
- no architecture or generation issue was reported.

Artifact:
`results/tables/runpod_preflight_v3_20260901.json`

SHA-256:
`79b2de97ae7bf3a9750a800bd0f8ed5db43778a346cc19677f3ab35dcb8a3178`

Passing this check established loader and hook compatibility only. It did not
authorize retaining activations in the behavioral gate.

## 4. Exact behavioral execution

```bash
python scripts/run_open_weight.py \
  --model Qwen/Qwen3.8-27B \
  --conditions full_history no_history shuffled_history random_target swap \
  --episodes 2 --rounds 8 --swap-round 5 --seed 20260901 \
  --temperature 0.7 --top-p 0.8 --top-k 20 --max-tokens 200 \
  --target-scorer semantic_nli_v3 --no-capture \
  --run-id qwen38_27b_v3_checkpoint_20260901 \
  --experiment-id qwen38_v3_checkpoint --quiet
```

Execution took 41 minutes 10 seconds and produced 312/312 non-empty messages:

| condition | episodes | rounds |
|---|---:|---:|
| full history | 6 | 48 |
| no history | 6 | 48 |
| shuffled history | 6 | 48 |
| random-response target | 6 | 48 |
| silent swap | 12 | 120 |
| **total** | **36** | **312** |

The swap set contains every ordered pair of distinct target types exactly
twice. There were no duplicate `(run, episode, round)` keys, empty messages,
classifier failures, missing probabilities, or missing swap pairs. The run did
not capture activations.

Raw log SHA-256:
`692c11d3bbccbc16a94db6c579239b28c65a7fac02b942aa9a2fa7965f364dc9`

Manifest SHA-256:
`10da20874133b9ec3e6daef002abcdd8cacd20b5e6307e607b4b8e0262370fc0`

## 5. Target scorer

The deterministic target used `semantic_nli_v3`, frozen before focal outcomes:

- model: `MoritzLaurer/deberta-v3-large-zeroshot-v2.0`;
- revision:
  `cf44676c28ba7312e5c5f8f8d2c22b3e0c9cdae2`;
- active template: `The message appeals to {}.`;
- twelve frozen prototypes: three each for fairness, risk, expertise, other;
- four group masses normalized to one; fairness/risk/expertise are rewarded and
  other is unspent;
- target response: logged logistic equation with base bias -1.0, matching
  weight 2.6, off-target weight 0.5, and Gaussian logit noise SD 0.6.

The v3 scorer passed its separately generated 80-message, machine-only
construct gate before this run: accuracy 0.9125, macro-F1 0.9140, fairness
recall 0.950, minimum class F1 0.864, and 0/11 expertise false positives on
designated adversarial-other messages. These references were generated and
checked by machines; this is not human construct validation. Full provenance
is in `TARGET_SCORER_V3_PROTOCOL.md`.

## 6. Blind independent measurement

The inline keyword labels were ignored for the decision. Every unique message
was measured twice:

1. primary judge: `gpt-5.6-sol`;
2. sensitivity judge: `gpt-5.6-luna`.

Each pass used 13 batches and 312 opaque sample IDs. The serialized judge input
contained only `sample_id` and `message`; it contained no condition, target,
round, scenario, history, outcome, target score, probability, or expected
label. Exact inputs and outputs are retained. Reclassification changed only
the seven classifier fields; every other field in all 312 copied records was
proved equal to the source log.

Primary-log SHA-256:
`9a062126ede805b6c1e974cfeff42f18cd7cb8d08a13dc35e71491bf6ca447ee`

Sensitivity-log SHA-256:
`43ae5bd112cca33f1e468fba60c87c31159106bc63f2e6761378a71edef036da`

Judge reliability:

| comparison | raw agreement | Cohen's kappa | changed |
|---|---:|---:|---:|
| keyword vs primary | 0.583 | 0.289 | 130/312 |
| keyword vs sensitivity | 0.516 | 0.234 | 151/312 |
| primary vs sensitivity | **0.814** | **0.624** | 58/312 |

Primary labels were heavily concentrated in `other` (232 other, 53 risk, 23
fairness, 4 expertise). Sensitivity labels were less concentrated (196 other,
50 risk, 44 fairness, 22 expertise). The sensitivity analysis is therefore
important: it asks whether the negative control pattern survives a materially
different use of the rubric, not merely a duplicate call.

## 7. Frozen behavioral decision

The decision artifact is
`results/qwen38_27b_v3_checkpoint_20260901/checkpoint_gate.json` (SHA-256
`7ec8cddbdf07a5d4a94e4102befde68530c6f49e6fcbffe1a52a12f668a15b1d`).

| gate | result | decisive evidence |
|---|---|---|
| design integrity | PASS | exact counts, prompts/scenarios type invariant, safe system prompt, all swap pairs |
| blind independent measurement | PASS | 13/13 batches, 312/312 messages, only ID + message visible |
| valid-history advantage | **FAIL** | overall match 0.104 full vs 0.104 no-history |
| shuffled specificity | **FAIL** | full-minus-shuffled-real 0.0476, below frozen 0.05 |
| random-response control | PASS | random late-minus-early gain -0.083 |
| wrong-start recovery | PASS | 3/6 full-history wrong starts later matched |
| silent-swap revision | **FAIL** | new-type gain 0.000; old-type drop -0.033; post new-minus-old -0.017 |
| multiple target types | **FAIL** | only risk had positive late full-minus-no difference |

Primary aggregate results:

| condition | match rate | Option-A success |
|---|---:|---:|
| full history | 0.104 | 0.500 |
| no history | 0.104 | 0.479 |
| shuffled history | 0.062 | 0.500 |
| random target | 0.104 | 0.500 |
| swap | 0.075 | 0.450 |

The primary history-by-round logistic coefficient was +1.583 (`p=0.122`), but
this arose because no-history declined from an unusually high early value; it
does not rescue the zero overall valid-history difference or the failed swap
pattern. The post-swap slope was -0.222 (`p=0.473`). No expertise-primary
message occurred in any of the 16 full-history expertise rounds.

The sensitivity judge was also negative:

- full-history match 0.167 versus no-history 0.188;
- history-by-round coefficient -0.901 (`p=0.492`);
- post-swap slope -0.248 (`p=0.234`);
- applying the same frozen decision rule also returned
  `STOP_BEFORE_MECHANISTIC_EXPERIMENT`: valid-history, random-response,
  silent-swap, and multiple-target gates failed. Shuffled specificity passed
  under this judge, which does not rescue the complete all-gates requirement.
  Sensitivity-gate SHA-256:
  `d465eafe225c7cd3155ed694e1b0f4466d57e2f841546037d061b36f42040c2f`.

This is a systems checkpoint with two episode seeds, not a powered test. The
frozen rule deliberately asks for a coherent direction across controls before
spending on mechanism. It failed that rule.

## 8. Evidence-only Bayesian observer

The Bayesian comparator received only information legitimately available from
the transcript: the exact logged semantic score vector for each message and
the binary target outcome. It was not told the hidden type or true swap round.
The primary change hazard was 0.10, with 0, 0.05, and 0.20 sensitivities.

At hazard 0.10:

- final-type accuracy was 0.208 in full-history episodes;
- no-history accuracy was 0.333;
- the uniform three-type baseline is 0.333;
- Bayesian-new-target rise minus behavioral-new-frame rise was +0.0216, with
  episode-bootstrap 95% CI `[-0.0799, 0.1177]`.

Full-history accuracy remained 0.208 at hazards 0 and 0.05, and reached only
0.292 at hazard 0.20. This shows that the outcomes generated by the model's
actual messages were weak evidence about target identity. It does not prove
the task is impossible, but it makes a clean model-updating effect unlikely in
this eight-round realization.

Summary SHA-256:
`879e4efaf282d54fd08e7a95ccb25fe23484c4ddca9bd983fd3cae166b2defd6`

## 9. Post-hoc simulator-capacity positive control

The weak Bayesian recovery on actual histories leaves two possibilities: the
binary-response task is intrinsically unidentifiable, or the focal model did
not send messages that distinguish the hypotheses. A post-hoc positive control
tested this without touching the frozen gate.

The diagnostic selected one saved message per rewarded dimension by maximizing
that dimension's target score minus the largest other rewarded score. It did
not inspect target choices, judge labels, conditions, rounds, or hidden types.
At each simulated round, an oracle model-based policy selected whichever of the
three messages minimized expected posterior entropy. Target outcomes came from
the same frozen response parameters, including integrated logit noise.

Across 9,000 balanced stable-target simulations:

- accuracy was 0.463 after one outcome;
- accuracy was 0.665 after five outcomes;
- accuracy was **0.738 after eight outcomes** (Monte Carlo 95% Wilson interval
  `[0.729, 0.747]`).

Across 6,000 simulations balanced over all ordered swaps, with the same silent
change after round 5 and observer hazard 0.10:

- active-target accuracy was 0.648 just before the swap;
- it fell to 0.263 immediately after the unannounced change;
- it recovered to 0.456 after three post-swap outcomes;
- it reached **0.567 after five post-swap outcomes** (Monte Carlo 95% Wilson
  interval `[0.555, 0.580]`).

This demonstrates that the frozen simulator contains usable information when
messages are chosen to separate target hypotheses. It does not show that Qwen
used this policy, knew the simulator, or formed a latent model. It therefore
sharpens the diagnosis—failure to create and exploit diagnostic evidence—while
leaving `STOP_BEFORE_MECHANISTIC_EXPERIMENT` unchanged.

Artifacts:

- `results/qwen38_27b_v3_checkpoint_20260901/identifiability/simulator_capacity.json`;
- `results/qwen38_27b_v3_checkpoint_20260901/identifiability/fig9_simulator_capacity.png`.

JSON SHA-256:
`510164be41d003202decae92a7dde5676bb30030ff96ccab384d81362a09e569`

Figure SHA-256:
`8fd0a138da565f1cbc81aab90ed706fcbff19bc1ec3ac7bb87908d865cf29c32`

## 10. Instrument profile

The deterministic profile over all 312 rows shows why the behavioral signal
was sparse:

- primary judge distribution: 232 other, 53 risk, 23 fairness, 4 expertise;
- target semantic four-way argmax: 134 other, 133 expertise, 35 risk, 10
  fairness;
- judge-primary versus target four-way argmax agreement: 0.526;
- target rewarded-mass mean 0.644, with median 0.690;
- top rewarded dimension minus second-place margin: mean 0.235, median 0.169;
- realized `P(A)`: mean 0.454, range 0.117–0.901;
- among full-history expertise rounds, the primary judge found 0/16 expertise
  messages; among full-history risk rounds it found 4/16 risk messages.

These quantities describe the instrument; they are not additional pass/fail
tests. In particular, three-way target argmax forces a winner even when all
three rewarded scores are weak, while the blind judge can correctly choose
`other`.

## 11. Why mechanistic work was not run

The predeclared behavioral prerequisite failed. Therefore the following were
not run:

- activation collection;
- probe fitting or layer selection;
- target/opposite/random/zero steering;
- a larger main behavioral run.

This is not a GPU, code, or funding blocker. The preflight verified that those
systems work. Running them after a failed behavioral gate would invite a
post-hoc story about decodability or steering without a robust behavior to
explain. The scientifically correct completion of the conditional stage is to
stop and preserve the null.

## 12. Local post-run verification

After pulling the artifacts:

- **280 tests passed** in the final local suite;
- Python bytecode compilation passed over `config.py`, `src`, `scripts`, and
  `tests`;
- both 312-row blind audits passed;
- the inter-judge audit passed;
- every non-classifier log field remained unchanged;
- all saved JSON and JSONL artifacts were parsed;
- figures for match, success, strategy distribution, silent swap, control
  comparison, feedback contingency, wrong-start recovery, and Bayesian
  evidence were generated and visually inspected;
- no RunPod pod remained active;
- temporary credential files were deleted and no key was written to the
  repository.

The only test warnings were 14 third-party Matplotlib/pyparsing deprecations.

## 13. Artifact map

| artifact | purpose |
|---|---|
| `PILOT_REPORT_REAL_QWEN38_27B_V3_CHECKPOINT.md` | exact prompts, target logic, probabilities, raw messages, three transcripts, metrics, negative assessment |
| `data/raw/qwen38_27b_v3_checkpoint_20260901.jsonl` | immutable 312-round source log |
| `data/raw/qwen38_27b_v3_checkpoint_20260901.manifest.json` | source configuration and environment |
| `data/processed/qwen38_27b_v3_checkpoint_20260901.gpt-5.6-sol.jsonl` | primary blind labels |
| `data/processed/qwen38_27b_v3_checkpoint_20260901.gpt-5.6-luna.jsonl` | sensitivity blind labels |
| `results/qwen38_27b_v3_checkpoint_20260901/checkpoint_gate.json` | frozen executable decision |
| `results/.../checkpoint_gate_sensitivity_gpt-5.6-luna.json` | same frozen gate applied to sensitivity labels |
| `results/.../judge_gpt-5.6-sol/batches/` | exact primary judge inputs and outputs |
| `results/.../judge_gpt-5.6-luna/batches/` | exact sensitivity judge inputs and outputs |
| `results/.../interjudge/diagnostics/` | complete judge-to-judge comparison |
| `results/.../judge_gpt-5.6-sol/bayesian/` | evidence-only trajectories and summary |
| `results/.../identifiability/` | post-hoc oracle simulator-capacity positive control |
| `results/.../diagnostics/instrument_profile.json` | score/label prevalence and separation |
| `results/.../figures/` and `tables/` | complete primary and sensitivity analyses |

Generated pilot-report SHA-256:
`17fc94a8f4c1bb49999a1758cf3a2128fe3ea70c2eae02fc5c3b3b7f8a5414af`.

## 14. Scientific conclusion and next decision

This checkpoint does **not** provide evidence that Qwen3.8-27B formed and
updated a target-specific persuasion model in this environment. It also does
not establish that current LLMs never form such models. The narrower result is
that this model, these eight noisy rounds, these scenarios, and this frozen
semantic target did not produce the complete valid-history/specificity/swap
pattern required to study a latent representation responsibly.

The existing run should remain immutable. If the project continues, the next
step is a new pre-outcome experimental version focused on making feedback more
diagnostic without revealing the target: for example, calibrated graded
feedback or counterfactual probe trials, stronger scenario-independent frame
elicitation, and simulations demonstrating that an evidence-optimal agent can
identify and revise the target within the available rounds. The controls and
independent measurement must be preserved, and the redesign must be validated
on new construct data rather than tuned against this null. The capacity control
suggests the cleanest next comparison is between spontaneous Qwen behavior and
an outcome-only exploration policy under more rounds, rather than merely
increasing target weights until the saved model appears to adapt.
