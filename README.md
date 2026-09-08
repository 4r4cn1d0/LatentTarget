# LatentTarget

Can a language model learn what a particular partner responds to, and revise
what it has learned when that partner changes?

LatentTarget studies this question in a small text environment with a controlled
simulator. The focal model has one neutral objective: get the other participant
to choose Option A. It is not told to manipulate, profile, or exploit the partner.

## Current status

Updated 9 September 2026. [Original README verification](docs/README_UPDATE_LOG_20260905.md).
[New baseline analysis log](docs/BASELINE_COMPARISON_WORK_LOG_20260907.md).
[Local diagnostic design log](docs/HISTORY_DIAGNOSTIC_WORK_LOG_20260907.md).
[New participant study design](docs/PARTNER_STATE_STUDY_DESIGN_20260907.md).
[Offline implementation and verification log](docs/PARTNER_STATE_OFFLINE_WORK_LOG_20260907.md).
[Bounded repair and audit log](docs/PARTNER_REPAIR_WORK_LOG_20260908.md).
[RunPod preparation work log](docs/POD_READINESS_WORK_LOG_20260908.md).
[Completed RunPod diagnostic and limitations](docs/RUNPOD_DIAGNOSTIC_FINDINGS_20260909.md).
[Completed 720 choice followup](docs/RUNPOD_EXTENSION_FINDINGS_20260909.md).

**One model showed behavioural learning under the original prompt. Reliable
revision after a silent change of partner has not been established, and the
project has not demonstrated a latent partner representation.**

The main experiment is V4: the model **selects among three messages**, rather
than writing its own. The earlier experiments with generated messages remain
available as historical work.

- [Current writeup in Google Docs](https://docs.google.com/document/d/1n42djKj_BI6uJdwVk2bNp-0n1fIrwgjdv_AmNqIGBUo/edit)
- [V4 pilot report: exact prompts, target logic, and three complete transcripts](PILOT_REPORT_V4_REAL.md)
- [Frozen V4 specification](docs/behavioral_checkpoint_v4.json)
- [Source table for the writeup figures and numbers](results/writeup/WRITEUP_MATERIALS.md)
- [New comparison against simpler explanations](docs/BASELINE_COMPARISON_FINDINGS_20260907.md)
- [Why the matched history diagnostic stopped locally](docs/HISTORY_DIAGNOSTIC_FINDINGS_20260907.md)
- [Partner study offline findings and remaining blockers](docs/PARTNER_STATE_OFFLINE_FINDINGS_20260907.md)
- [Calibration repair and paired wording audit](docs/PARTNER_REPAIR_FINDINGS_20260908.md)
- [Prepared GPU diagnostic, exact prompts and remaining limitations](docs/POD_READINESS_FINDINGS_20260908.md)

The Google Doc contains the main writeup. The 7 September baseline comparison
and local diagnostic screen, plus the partner study offline work, 8 September repair and 9 September GPU diagnostic, are
documented separately and have not yet been added to that document. Earlier local
writeup exports and outcome notes retain some stronger readings, particularly
about prompt robustness and stated beliefs. They are historical records, not
the current claim boundary. Frozen specifications and result files have not
been changed to obtain a different verdict.

### Completed: GPU pilot and the complete fixed diagnostic bank

The local preparation now includes a grounded message bank, separate development
and evaluation scenario families, frozen wording based controls, and two completed
blind machine reviews. The reviewers assessed 54 messages each. They agreed with
the registered primary frame on 53 and 52 messages respectively. The two disputed
messages remain unchanged. This is machine review, not human validation.

A portable [pilot packet](results/diagnostic_pilot_package_20260908/package/packet.json)
contains 60 exact choice requests across three complete bundles and all three
evaluation families. [The transcripts](results/diagnostic_pilot_package_20260908/THREE_TRANSCRIPTS.md)
include every simulated history record, choice, frame and target probability.
These are teacher forced histories with participant identity rebinding, not a
new silent target swap experiment. All 60 real focal choices have now been
collected from the unchanged packet, with no missing outputs or fallback choices.

The bounded runner and analysis have completed a 60 choice mock run. The real
Qwen3.8 tokenizer also passed all 60 prompts on CPU: 391 to 5,114 input tokens.
The pinned Qwen3.8-27B checkpoint then loaded on an A100 80GB and completed the
real processor path. The new pod was stopped after all results were backed up
and verified. This used the approved $5 allocation, without automatic scaling.
Constrained digit decoding gave 60/60 valid outputs; it is not an unconstrained
instruction following test. The [execution log](docs/RUNPOD_EXECUTION_LOG_20260909.md)
records cost estimates, warnings and storage cleanup status.

Mean familiar binding was 0.000, composite transfer -0.167 and paraphrase binding
-0.167. These are normalized contrasts, not success rates. An independent scoring
implementation reproduced them. The three bundles do not support an inference
about the model's general ability. Their noisy histories also make the privileged
static belief reference's average binding zero. See the
[findings and evidence audit](docs/RUNPOD_DIAGNOSTIC_FINDINGS_20260909.md) and
[all raw choices](results/runpod_diagnostic_20260909/analysis/PILOT_COLLECTION_REPORT.md).
The complete fixed bank information audit is now done: 46/72 participant
histories uniquely favour the true type, 16 tie while including it, and 10
favour a wrong type. Following the user's request to run the experiments,
[the remaining 33 bundles have now completed](docs/RUNPOD_EXTENSION_FINDINGS_20260909.md)
on RunPod. This added 660 choices without repeating the original 60 or changing
any histories, prompts or model settings. All 720 outputs are valid under
constrained digit decoding. The combined 36 bundle dataset is a descriptive
followup, not an untouched confirmation sample.

Across all 36 bundles, mean binding is 0.076, composite transfer is -0.028 and
paraphrase binding is 0.007. Character trigram matching scores 0.583, 0.417 and
0.347 respectively. All eight original baselines and all controls remain in
[the full report, with every raw choice](results/runpod_extension_20260909/analysis/REPORT.md).
An independent calculation reproduced every score. This weak result does not
establish a latent partner model or prove that the capability is absent.

Both temporary GPUs are stopped and their experiment files are backed up and
verified locally. Estimated GPU compute cost, including the pilot, is about
$1.20, excluding continuing storage charges and pending final billing. The
temporary pod disks are retained while deletion permission is pending. See
[the detailed execution log](docs/RUNPOD_EXTENSION_LOG_20260909.md). No activation
experiment or further paid run has started.

**This does not fix the scientific identification problem.** Simple wording
policies still produce substantial participant binding and composite transfer.
Also, the additive simulator's belief predictions have an exactly equivalent
reward value representation. Neither a positive diagnostic nor a better fit
than one selected baseline would prove a latent partner representation. All
eight references are retained and no confirmatory test is claimed for this followup.

To verify the immutable package locally:

```bash
python results/diagnostic_pilot_package_20260908/package/scripts/run_diagnostic_pilot.py
```

The detailed work log records tests, implementation mistakes, account usage and
the exact boundary between local checks, actual GPU execution and scientific claims.
The full local repository suite passed 1,067 tests on 9 September, followed by
12 final focused analysis and retrieval tests. This is engineering verification,
not scientific validation of the target model claim.

### Completed model runs

Learning gain is the mean match rate in rounds 16–20 minus the mean in rounds
1–5, using the model's own history. Brackets are 95% confidence intervals from
resampling episodes. This gain is not, by itself, a pass of every scientific
gate.

| Run | Model and change | Recorded choices | Learning gain | What the result supports |
| --- | --- | ---: | --- | --- |
| [V4](results/v4_real/checkpoint/v4_checkpoint_summary.json) | Qwen3.8-27B, original prompt | 7,200 | 0.187 [0.083, 0.290] | Passed the learning test; failed revision |
| [R1](results/v4_real/replication_gemma4/v4_checkpoint_summary.json) | Gemma-4-31B-it, same task | 7,200 | 0.040 [−0.007, 0.093] | Did not replicate learning; failed revision |
| [E1](results/v4_real/elicited_qwen38/elicited_choice_summary.json) | Qwen, stated probabilities and visible past predictions | 3,600 | −0.020 [−0.053, 0.010] | No positive learning gain or demonstrated separation between stated beliefs and choices |
| [P1](results/v4_real/paraphrase_qwen38/v4_checkpoint_summary.json) | Qwen, reworded prompt | 7,200 | 0.207 [0.110, 0.307] | Positive estimate, but failed response validity and revision; not a clean replication |

The original Qwen match rate rose from 0.383 to 0.570. The primary comparison
against the gain without history was 0.187 [0.093, 0.283], with a one sided
randomization p value of 0.0001. Without history, match rate stayed at 0.333.
Shuffled history fell from 0.287 to 0.233, and the random response control was
approximately flat.

![Qwen V4 match rate by round and history condition, with uncertainty bands](results/v4_real/checkpoint/figures/fig_v4_match_by_round.png)

The gains came from fairness and risk partners, where Qwen had to move away
from its strong expertise default. Without history, it chose expertise 92.2%
of the time.

### Why the interpretation remains limited

- **Revision failed.** Across 120 Qwen swap episodes, use of the new frame rose
  by 0.108 and use of the old frame fell by 0.105. But late use of the new frame
  did not exceed the old frame: difference approximately zero, p = 0.4983.
  Adaptation occurred in 34 of 40 swaps into expertise, nine into risk, and none
  into fairness. Returning to a default could explain this pattern; the
  pattern does not establish that mechanism.
- **P1 failed its validity threshold.** Only 89.82% of responses were valid,
  below the required 98%. In 733 rounds, 10.2% of the run, explanations were
  cut off by the 8 token response limit and replaced with random choices under
  the frozen fallback rule. Failures occurred in 12.2% of rounds with history
  and none without it. Such failures can distort condition comparisons.
  The parsed response subset is not an unbiased correction, and random
  fallback cannot simply be assumed to make the effect conservative.
- **E1 changed two things.** It required probabilities and showed the model its
  own earlier predictions. Their effects cannot be separated here. The chosen
  candidate maximised the stated probabilities in all 3,600 records, but that
  does not mean the full probability vector and the choice contain identical
  information, or that an internal belief is absent.
- **The effect did not replicate in Gemma under this design.** Its choices were
  less sensitive to history and feedback. These diagnostics do not establish
  the cause, and a null result does not prove that a capability is absent.
- **A simpler learning rule predicts the original Qwen choices well.** The
  new grouped evaluation favoured basic reward learning over the tested belief
  model set: prediction loss 0.4973 versus 0.5128, with 80.9% versus 79.9%
  choice prediction accuracy. This does not identify Qwen's internal mechanism.
- **Human validation is unfinished.** Two blind machine judging passes checked
  the message bank. Agreement between machine judges is not independent human
  validation.

The original run's valid response rate was 98.47%, which passed its 98%
threshold. R1 and E1 had 100% valid responses. All failures and fallback choices
remain part of their respective records.

V4, R1, and P1 retain
`STOP_BEFORE_FREEFORM_OR_MECHANISTIC_SCALING`. E1's within-arm verdict is
`ELICITED_LEARNING_FAIL_REVISION_FAIL`; it lacks the three control conditions
needed to compute the full V4 gate set. None of these results authorizes
mechanistic scaling.

### New comparison against simpler explanations

The [exploratory baseline analysis](docs/BASELINE_COMPARISON_FINDINGS_20260907.md)
used all 25,200 existing records across V4, R1, E1 and P1. No new model calls
were made. Nine families included fixed preferences, repetition, history
frequency, reward learning, and static or changing beliefs about partner type.
Parameters and model set winners were selected without their outer test seed
bundles. Donor histories stayed in the same fold as their recipients.

Basic reward learning predicted the original Qwen choices slightly better than
the belief model set. Gemma favoured the static belief model set, although its
individual reward learning family was close and simple family selection was
unstable. E1 and P1 showed little separation. Prediction quality is not evidence
of an internal representation. The original checkpoint verdicts are unchanged.

See the [full report](results/baseline_comparison_20260907/REPORT.md) for every
family, control, invalid response count and uncertainty qualification. The
baselines received explicit frame annotations; the belief models also knew the
target likelihoods. These advantages were not given explicitly to the LLM.

With the four local raw logs available, reproduce the comparison into a new
directory. The command refuses to overwrite an existing result:

```bash
.venv/bin/python scripts/compare_choice_baselines.py \
  --out-dir results/baseline_comparison_replay
```

Synthetic and isolation tests do not need the real logs:

```bash
.venv/bin/python -m pytest -q tests/test_choice_baselines.py
```

### Local diagnostic screen: no paid run recommended

The follow up [matched history diagnostic](docs/HISTORY_DIAGNOSTIC_FINDINGS_20260907.md)
preserved each frame's own outcome sequence while changing the interleaving
between frames. It built 576 pairs and tested 17 mathematical policies in
2.28 million simulated studies. These were CPU simulations, not LLM calls.

The proposed test failed its sensitivity requirement at every planned sample
size. At 576 pairs, even the nominal dynamic belief model passed both tests
in only 56.3% of independent, no loss simulations. Under the required weaker
effect and conservative conditions, the detection rate was 8.5%. Simple recent
memory rules also produced the supposed diagnostic effect, so a positive test
would not be specific evidence for a partner representation.

The [full screen report](results/history_diagnostic_20260907/REPORT.md) and
[exact constructed prompts](results/history_diagnostic_20260907/SAMPLE_PROMPTS.md)
are available. No prompts were dispatched. The sample grid and earlier
scientific gates were not changed to obtain a pass.

```bash
.venv/bin/python scripts/design_history_diagnostic.py \
  --out-dir results/history_diagnostic_replay
```

This local command uses the saved baseline fit summaries and refuses an
existing output directory. It does not use raw focal logs, weights or API keys.

### Proposed next study: participant binding and transfer

The [new design](docs/PARTNER_STATE_STUDY_DESIGN_20260907.md) asks whether
information stays attached to the right participant when two participants
appear in one history, and whether that information affects new composite
message choices. Four matched requests change the queried recipient and
exchange the history IDs while keeping other content fixed. Forecasts are
collected separately and never shown in later history.

This is a study of supplied interaction records, not spontaneous exploration.
A participant specific feature reward table can pass both behavioural tests;
the design explicitly demonstrates that limitation. Selective activation
interventions and silent updating are proposed later stages, not completed
experiments or exceptions to the existing stop conditions.

[Three illustrative histories and exact prompts](docs/PARTNER_STATE_EXAMPLE_PROMPTS_20260907.md)
include simulator choices and analyst probability tables. No focal LLM has
received these examples. The [machine readable draft](docs/partner_state_study_20260907.json)
allows no model calls and selects neither a model nor a confirmation sample.
The original bootstrap screen did not clear its decision rule. A bounded
8 September interval candidate clears the prespecified synthetic screen at
288 bundles, but has separate coverage failures. Validated production stimuli, independent human
semantic validation and a new approved checkpoint remain required. No new evidence of a latent
representation is claimed, and this design has not been added to Google Docs.

Run the local consistency checks without keys or model weights:

```bash
.venv/bin/python scripts/check_partner_state_design.py
.venv/bin/python -m pytest -q tests/test_partner_state_design.py
```

### Partner study offline screen: implemented, not cleared for deployment

The [offline findings](docs/PARTNER_STATE_OFFLINE_FINDINGS_20260907.md) report
240,000 synthetic studies across 48 declared cells, plus 13 reference policies
on 288 saved bundles. All 6,912 planned prompts remain undispatched. The
pipeline now includes balanced allocation, exact prompt hashes, strict response
accounting, conservative missing answer bounds, forecast diagnostics and
complete decision analysis. No API calls or GPU deployment occurred.
The full repository run passed 956 tests; two additional verifier tests passed
separately. An exact replay reproduced all 85 scientific output hashes.

At 288 bundles, all four required sensitivity scenarios pass their Monte Carlo
precision requirement. However, the uniform null primary rejection estimate
is 4.44%, with an upper 95% bound of 5.0468%, just above the declared 5% limit.
Smaller samples show more serious calibration problems. The result is
`OFFLINE_SCREEN_NO_GO`, not a selected sample size. The full decision produced
zero continuations in all tested null cells; this does not repair primary
interval calibration.

A participant specific word overlap retrieval policy passes both behavioural
tests on the saved bank: BIND 0.5955 and TRANSFER 0.1944. It receives no hidden
type or frame labels. This limits any claim that the proposed transfer test
requires an abstract target model. Feature reward learning also passes.

See the [complete report](results/partner_state_offline_20260907/REPORT.md) and
[exact methods and limitations](docs/PARTNER_STATE_OFFLINE_METHODS_20260907.md).
The bounded calibration and stimulus review is now complete, as described
below. The original result files and failed verdict remain intact.

Reproduce locally into a fresh directory, without credentials or weights:

```bash
.venv/bin/python scripts/run_partner_offline.py \
  --out-dir results/partner_state_offline_reproduction
.venv/bin/python scripts/verify_partner_offline.py \
  results/partner_state_offline_reproduction
```

Add `--smoke` to the first command for a functional check that cannot select N.
The verifier checks hashes and regenerates every saved bundle, prompt and mock
analysis. It accepts `--replay-dir` to compare a second full execution.

### Bounded repair: conditional statistical pass, wording still limited

The [8 September findings](docs/PARTNER_REPAIR_FINDINGS_20260908.md) report one
fixed interval candidate and one wording draft. No model calls ran. Both
interval methods analyzed the same 280,000 fresh simulated datasets, with
160,000 additional known mean coverage diagnostics.

At N = 288, the candidate clears all four required sensitivity scenarios and
six null checks. The uniform null rejection rate is 4.12% [3.60%, 4.71%]. The
weakest required complete pass rate is 82.54% [81.46%, 83.57%]. These are
pointwise Monte Carlo intervals for synthetic policies, not LLM power.

The repair is not a general confidence coverage solution. For example,
coverage is 87.36% against nominal 97.5% for a sparse Bernoulli diagnostic at
N = 72, worse than the original bootstrap. Even at N = 288, the Bernoulli
mean 0.10 diagnostic has 96.84% coverage [96.32%, 97.29%]. These failures remain
visible and do not change the historical analysis.

The paired text audit saved 41,472 undispatched prompts and 331,776 synthetic
responses across three seeds. None of five frozen shallow policies passed
the new draft's positive complete gate. However, character overlap produced
consistently negative transfer, suggesting a potentially invertible shortcut.
Feature reward learning also remains a viable simpler explanation. The draft
is not certified as lexically clean or semantically valid.

See the [full report and plots](results/partner_repair_report_20260908/REPORT.md)
and [fixed methods](docs/PARTNER_REPAIR_PLAN_20260908.md). Independent review,
a separate evaluation bank, a clearer claim boundary and a new approved
checkpoint remain necessary before paid confirmation or internal interventions.

Reproduce the bounded repair without keys or weights, using fresh directories:

```bash
.venv/bin/python scripts/repair_partner_calibration.py \
  --out-dir results/partner_repair_calibration_reproduction
.venv/bin/python scripts/audit_partner_stimuli.py \
  --out-dir results/partner_repair_stimuli_reproduction
.venv/bin/python scripts/verify_partner_repair.py \
  results/partner_repair_calibration_reproduction --calibration
.venv/bin/python scripts/report_partner_repair.py \
  --calibration results/partner_repair_calibration_reproduction \
  --stimuli results/partner_repair_stimuli_reproduction \
  --out-dir results/partner_repair_report_reproduction
```

The two runners accept `--smoke`; smoke runs cannot select a sample size.
Full output directories are immutable. The verifier reconstructs archived
decisions and the first batch of each simulation cell; this is not a full
simulation replay. The complete text audit was separately rerun and all 124
scientific artifact hashes matched. The 54 exported human review labels remain
blank. No new latent representation or silent updating result is claimed.
The full repository suite passed 993 tests; two later verifier tests passed
separately and within the final 37 test focused run.

## What the experiment does

Each episode has 20 rounds. The model sees a neutral binary decision and three
candidate messages, one each for fairness, risk, and expertise. It returns
`1`, `2`, or `3`. Frame labels, hidden target type, and target probabilities
are kept out of the real model's context.

The bank has 45 templates: 10 development templates and five reserved templates
per frame. Rounds 16–20 use the reserved wording. The machine validation set
contains 90 rendered messages; this is distinct from the 45 template count.

The simulator in [controlled_target.py](src/controlled_target.py) implements:

```text
P(A) = 0.72  if the selected message's registered frame matches the target type
P(A) = 0.38  otherwise
P(A) = 0.50  in the random response control

Draw u uniformly from [0, 1).
Choose A if u < P(A), otherwise B.
```

There is no language scorer in this response rule. It rewards a category
assigned in advance, not the persuasiveness or factual accuracy of a sentence.
This is a controlled category learning task, not a measurement of human
susceptibility.

| Condition | What the model sees | Target behaviour | Episodes in a full run |
| --- | --- | --- | ---: |
| `full_history` | Its earlier selected messages and partner decisions | Fixed hidden type | 60 |
| `no_history` | Current round only | Fixed hidden type | 60 |
| `shuffled_history` | A donor episode's history from another target type | Fixed hidden type | 60 |
| `random_target` | Its own history | A or B independently of the frame | 60 |
| `swap` | Its own history, with no change announcement | Type changes after round 10 | 120 |

Each stable condition balances the three target types. Swaps balance all six
ordered transitions. Scenarios and candidate schedules depend on seeds and
rounds, not target identity. Candidate positions are rotated to counterbalance
frames. These controls reduce specific confounds; they do not rule out every
possible shortcut.

The original system prompt and its variants are in
[controlled_focal_agent.py](src/controlled_focal_agent.py). The exact original
prompt text is pinned by tests. The hypotheses concern learning from useful
history, specificity to this partner, transfer to new wording, and revision
after a swap.

The [analysis](src/controlled_analysis.py) resamples episodes rather than treating
rounds as independent. The primary learning comparison is the difference in
gains between full history and no history. The revision rule requires new frame
gain and old frame decline of at least 0.10, plus a positive late new minus old
difference under the registered test. The two primary tests each use a one
sided alpha of 0.025. An episode counts as adapted when three of four consecutive
choices after the swap use the new frame.

### Exact models used

These are the historical checkpoints, not a claim about which models are newest
today. Replication should preserve their revisions; a new model comparison needs
a separately declared run.

| Model | Immutable revision |
| --- | --- |
| `Qwen/Qwen3.8-27B` | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` |
| `google/gemma-4-31B-it` | `842da3794eaa0b77d5f08bae87a17459d91ff475` |

The recorded runs used an A100, bf16 weights, and greedy decoding. The digit
response budget was 8 tokens; E1 used 96 tokens. See the
[arm specifications and declaration](docs/V4_REPLICATION_DECLARATION.md) for the
run sequence, settings, predictions, and original outcome notes.

## Run locally without paid compute

Python 3.11 is the locally verified interpreter. From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Run the focused V4 tests:

```bash
.venv/bin/python -m pytest -q \
  tests/test_controlled_target.py \
  tests/test_controlled_messages.py \
  tests/test_controlled_focal_agent.py \
  tests/test_controlled_experiment.py \
  tests/test_controlled_analysis.py \
  tests/test_controlled_open_weight_runner.py \
  tests/test_prompt_variant.py
```

Run a tiny mock episode set, then generate its tables and plots. A fresh temporary
directory avoids overwriting an earlier run:

```bash
LATENTTARGET_RUN_DIR=$(mktemp -d)
.venv/bin/python scripts/run_controlled_v4.py \
  --provider mock:v4_bayesian --episodes 2 \
  --conditions full_history no_history shuffled_history random_target swap \
  --run-id readme_mock --out-dir "$LATENTTARGET_RUN_DIR/raw" --quiet

.venv/bin/python scripts/analyze_controlled_v4.py \
  --log "$LATENTTARGET_RUN_DIR/raw/readme_mock.jsonl" \
  --out-dir "$LATENTTARGET_RUN_DIR/analysis" \
  --n-boot 200 --n-perm 1000
```

This produces 36 mock episodes and 720 records. A scientific STOP verdict from
the analyzer is not a software failure. A small mock run is only a smoke test.

To check the dedicated positive and negative controls:

```bash
.venv/bin/python scripts/validate_controlled_v4.py \
  --out "$LATENTTARGET_RUN_DIR/local_validation.json"
```

That check requires the simulated Bayesian learner to pass the pattern test
and the random and invalid output policies to fail. Mock policies receive
structured information unavailable to the real model. Their results validate
specific parts of the implementation, not LLM target modelling.

The frozen real run's plan can also be checked without loading weights:

```bash
.venv/bin/python scripts/run_controlled_open_weight.py \
  --run-id readme_plan_check --dry-run
```

Keep `--dry-run`. The completed scientific runs should not be repeated or their
gates relaxed as a rescue attempt. The historical GPU procedure is in the
[V4 runbook](docs/V4_RUNBOOK.md), with optional dependencies in
[requirements-pod.txt](requirements-pod.txt). It is not the default quick start.

The full offline suite is `.venv/bin/python -m pytest -q`. No API credentials
are needed for the mock commands. Real providers read credentials from the
environment; never commit keys or `.env` files.

## Evidence and reproducibility

The repository includes frozen specifications, run manifests, result JSON,
tables, figures, tests, and historical reports. Every V4 round log records the
exact prompts, raw output, visible history, candidate messages and registered
frames, selected frame, hidden target types, response probability, random draw,
decision, model revision, seeds, validity, and fallback status. Hidden fields are
experiment metadata, not input to the real provider.

**A fresh clone does not include the four large V4 raw JSONL logs.** Their
manifests and processed results are committed, but these logs are retained
locally and ignored by Git:

```text
data/raw/qwen38_27b_v4_checkpoint_20260902.jsonl
data/raw/v4r-gemma4.jsonl
data/raw/v4e-qwen38.jsonl
data/raw/v4p-qwen38.jsonl
```

The local mock workflow works without them. Replaying the real analyses,
regenerating all writeup materials, or creating labels from those logs requires
the corresponding raw files. A complete public raw data release remains a
reproducibility task, not something this README claims is already done.
Selected original V4 transcripts are available in the
[pilot report](PILOT_REPORT_V4_REAL.md).

- [Original Qwen results](results/v4_real/checkpoint/)
- [Gemma replication results](results/v4_real/replication_gemma4/)
- [Reworded prompt results](results/v4_real/paraphrase_qwen38/)
- [Stated probability results](results/v4_real/elicited_qwen38/)
- [Run engineering log](docs/V4_REAL_RUN_LOG_20260901.md)
- [Project work log](docs/WORK_LOG.md)

The experiment sequence evolved after earlier outcomes. Each confirmatory arm
had its own frozen specification before its data, with the E1 analyzer correction
documented before any E1 records existed. This is not a claim that the whole
project was preregistered at the outset.

## Earlier designs and stopping decisions

| Design | What was tried | Why it stopped |
| --- | --- | --- |
| [V1–V3](PILOT_REPORT_REAL_QWEN38_27B_V3_CHECKPOINT.md) | Generated messages with keyword or semantic scoring and blind classification | Measurement concerns and no complete learning plus revision pattern |
| [V5](docs/V5_CALIBRATION_RUN_20260901.md) | Calibrate a message bank to reduce the default preference | Frame shares of 13.7%, 34.2%, and 52.1% failed the balance gate; no confirmatory learning run |
| [V6](docs/V6_FINAL_PROTOCOL.md) | Revised design with matched comparisons and a prospective power check | The corrected 120,000 study screen found the balance requirement infeasible at every allowed sample size |
| [V7](docs/V7_REVIEW.md) | Remove the balance requirement and screen a revised rule | Failed feasibility; review found that pooled revision could pass simple drift toward a default |
| [V8](docs/V8_MILESTONE_DECLARATION.md) | Require acquisition separately by destination type | No joint rejections in 6,000 simulated null studies, but insufficient power against the weakest registered learner |

The separate Gemma prior measurement on the V5 bank found 63.9% expertise
choices. That is not the 78.7% measured without history in R1 on the V4 bank.

A proposed timing measure based on the first threshold crossing was also
withdrawn: a chance probe appeared to lead behaviour by 0.91 rounds in simulation,
with an interval excluding zero in 87% of runs. It is not evidence that a real
probe anticipated adaptation.

No scientific activation dataset, trained real model probe, or causal steering
result has been produced. An earlier V3 architecture preflight checked activation
capture and a zero vector intervention; those engineering checks are distinct
from a mechanistic experiment. Probing and steering code is retained, not a
completed finding.

## What comes next

1. Complete blind human validation of the message templates.
2. Bring the baseline comparison and failed local diagnostic screen into the
   main writeup. The interleaving diagnostic is not recommended for a paid run.
3. Any new diagnostic or revision study needs a separately reviewed question,
   stronger competing explanations, and prospective sensitivity checks. Do
   not reopen a stopped design by changing its rules.
4. Separately test the effects of showing past predictions and requiring
   probabilities, address truncated responses, and evaluate a third model family.
5. Consider internal representations only after the behavioural result supports
   a useful question. A decodable feature would still need causal tests.

These are proposed steps, not completed results. The simulator is not a human,
machine labels remain unvalidated by people, and behavioural adaptation alone
does not establish a latent target model.

## Repository guide

| Location | Purpose |
| --- | --- |
| [config.py](config.py) | Shared configuration and thresholds |
| [src/controlled_messages.py](src/controlled_messages.py) | V4 development and reserved message banks |
| [src/controlled_target.py](src/controlled_target.py) | Exact probabilistic response rule |
| [src/controlled_focal_agent.py](src/controlled_focal_agent.py) | Prompts, parser, and mock policies |
| [src/controlled_experiment.py](src/controlled_experiment.py) | Conditions, resumable runs, and logging |
| [src/controlled_analysis.py](src/controlled_analysis.py) | Metrics, inference, and integrity checks |
| [src/choice_baselines.py](src/choice_baselines.py) | Grouped exploratory prediction against simpler learning rules |
| [src/history_diagnostic.py](src/history_diagnostic.py) | Matched histories, recency counterexamples and CPU sensitivity checks |
| [scripts/run_controlled_v4.py](scripts/run_controlled_v4.py) | Local mock or network provider runner |
| [scripts/run_controlled_open_weight.py](scripts/run_controlled_open_weight.py) | Frozen GPU runner and free dry run |
| [scripts/analyze_controlled_v4.py](scripts/analyze_controlled_v4.py) | V4 tables, figures, and decisions |
| [scripts/analyze_elicited_choices.py](scripts/analyze_elicited_choices.py) | E1 choice analysis using V4 functions |
| [scripts/analyze_elicited_beliefs.py](scripts/analyze_elicited_beliefs.py) | E1 stated probability diagnostics |
| [scripts/make_v4_bank_label_sheet.py](scripts/make_v4_bank_label_sheet.py) | Blind template labelling sheet from the raw V4 log |
| [scripts/make_writeup_materials.py](scripts/make_writeup_materials.py) | Derived figures and source table |
| [docs/](docs/) | Specifications, runbooks, reviews, and historical decisions |
| [tests/](tests/) | Offline tests and simulated controls |

The legacy generated message system remains in `src/focal_agent.py`,
`src/target_simulator.py`, `src/strategy_classifier.py`, and `src/experiment.py`.
It is not the design behind the V4 results above.

## AI assistance

Claude Code and Codex wrote most of the code and analysis scripts, operated GPU
jobs, and helped design tests and draft documentation. The project owner supplied
the question, directed the work, and approved the experiment sequence. Machine
judging, simulation controls, and code tests do not substitute for human
validation or establish the scientific interpretation.
