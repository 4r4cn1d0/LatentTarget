# Evaluation review: first real-model behavioral gate

> **Historical checkpoint.** This review is preserved as the audit of the v1
> 192-round run. It is superseded for current project status by
> `RUNPOD_CHECKPOINT_V3_20260901.md`, whose frozen decision is
> `STOP_BEFORE_MECHANISTIC_EXPERIMENT` after the complete v3 controls.

Review date: 2026-08-27. Scope: the 192-round `Qwen/Qwen3.8-27B`
`full_history`/`no_history` checkpoint and its post-data independent
remeasurement. This is an evaluation audit, not a new preregistration.

## Verdict

**BLOCKED for a latent-target-model claim and blocked for paid scaling.**

There is exploratory evidence in the intended direction after replacing the
circular keyword measurement with a blind GPT-family judge. However, the pilot
is underpowered, the human measurement gate is incomplete, the target reward
function is not well aligned with the intended fairness/expertise constructs,
and the shuffled-history, random-response, and swap controls have not been run.

The appropriate current claim is:

> In this small pilot, target-specific history was associated with more
> target-aligned message framing under an independent text-only judge, but the
> evidence is not yet sufficient to distinguish dynamic target modelling from
> policy persistence or measurement artefacts.

## Coverage score

This 47/100 score is a project-specific readiness rubric, not a standardized
scientific score.

| Evaluation area | Score | Evidence |
|---|---:|---|
| Data integrity and reproducibility | 15/15 | 192/192 rows, 24 complete episodes, raw prompts/messages/probabilities/seeds retained |
| Judge blindness and auditability | 15/15 | 8/8 batches structurally audited; the judge saw only opaque ID + message |
| Independent measurement validity | 10/15 | all messages judged by a different model family; human agreement still absent |
| Target construct validity | 2/15 | known fairness false negatives and generic-expertise false positives in the reward scorer |
| Behavioral controls | 5/15 | no-history ran; shuffled-history and random-target did not |
| Dynamic updating evidence | 0/15 | no silent-swap episodes |
| Mechanistic/causal evidence | 0/10 | no activations, probe, or steering run |
| **Total** | **47/100** | **not claim-ready** |

## What now passes

### Independent judge execution

- Focal model: `Qwen/Qwen3.8-27B` (unchanged saved outputs).
- Measurement model: `gpt-5.6-luna` through the logged-in Codex CLI.
- Inputs: 189 unique messages from 192 rows, shuffled with seed `20260826`.
- Batches: 8; schema failures: 0; missing classifications: 0.
- Saved batch inputs expose only `sample_id` and `message` per sample.
- Condition, target type, round, scenario, feedback, and choice were never
  serialized into judge input.
- Prompt and output hashes, process return codes, exact input/output, and
  privacy-sanitized process metadata all pass the repository audit. Removed
  process streams retain hashes and byte counts.

### Independent behavioral result

| Quantity | Full history | No history |
|---|---:|---:|
| Independently judged match rate | 0.146 [0.063, 0.240] | 0.042 [0.010, 0.073] |
| Round slope | +0.0099 (`p=0.271`) | -0.0060 (`p=0.730`) |
| Type-alignment permutation `p` | 0.047 | 0.846 |
| Realized Option-A success | 0.333 | 0.344 |

The preregistered `round × full_history` interaction was +1.629
(odds ratio 5.10, two-sided `p=0.058`). Its direction is encouraging, but it is
not conventionally significant and the 24-episode pilot was explicitly not
powered for a precise effect estimate.

Classifier/target-scorer argmax agreement fell from 1.00 under the shared
keyword instrument to 0.541 under the independent judge. This materially
reduces the original circularity. It does not validate the target simulator's
constructs.

## Newly identified construct failures

The keyword classifier and independent judge agreed on 63.0% of rows, with
Cohen's kappa 0.246; 71/192 labels changed. This confirms that the engineering
keyword classifier cannot be the scientific outcome instrument.

- The independent judge found 13 fairness-primary messages that the keyword
  instrument missed. All 13 received **zero fairness reward** from the target
  simulator.
- In full-history fairness episodes, 5/32 messages were independently judged
  fairness-primary; no-history fairness episodes had 0/32. Thus the old
  “zero fairness behavior” diagnosis was partly a measurement false negative.
- The old keyword instrument called 36 messages expertise-primary. The
  independent judge called **none of those 36** expertise-primary.
- Of those 36 overcalls, 25 matched the generic word `professional`, 10
  matched `experience`, 3 matched `researchers`, and isolated rows matched
  `authoritative` or `track record` (messages can contribute multiple terms).
- In full-history expertise episodes, the independent judge found 0/32
  expertise-primary messages. Expertise is therefore the clearest current
  construct/behavior failure.
- Independently judged risk specialization was 9/32 under full history versus
  3/32 without history. Independently judged fairness specialization was 5/32
  versus 0/32. The aggregate directional result is carried by fairness and
  risk, not expertise.

## Open evaluation gaps

1. **Human measurement gate:** 0/40 blind rows are labelled. Until a human
   agrees substantially with the independent judge and confirms the direction,
   the LLM judge remains an unvalidated instrument.
2. **Reward construct calibration:** the focal model cannot learn that implicit
   fairness works when the simulator assigns it zero fairness reward, and it
   can receive expertise reward for generic professionalism. This makes the
   three hidden types unequal in semantic detectability.
3. **Target-specificity controls:** no shuffled-history or random-target run.
4. **Updating:** no silent target swap; therefore no evidence about stale or
   sticky user models.
5. **Latent representation:** behavior alone cannot distinguish an explicit
   target belief from model-free win-stay/lose-shift or persistence.
6. **Causal use:** no steering experiment.

## Remediation decision

- Preserve v1 prompts, lexicons, data, and analyses unchanged as an auditable
  pilot. Do not retrofit new labels into the original raw log.
- Complete the existing blind human sheet before any new paid run.
- If human labels confirm the independent judge's construct diagnosis, build
  and human-calibrate a separately versioned target scorer (`v2`). Never tune
  it against focal-model success or the sign of the history effect.
- Run a two-seed all-controls v2 checkpoint only after the scorer and judge
  gates pass and the researcher explicitly approves it.
- Do not collect activations or run probes/steering until the behavioral swap
  and negative controls behave sensibly.

The exact staged process and stop rules are in
[`MEASUREMENT_REMEDIATION.md`](MEASUREMENT_REMEDIATION.md).
