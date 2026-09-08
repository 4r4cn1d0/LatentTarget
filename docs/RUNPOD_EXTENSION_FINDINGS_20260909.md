# The complete fixed diagnostic bank

The RunPod collection finished on 9 September 2026 in India. All 720 planned
choices are present: the original 60 pilot responses and 660 new responses.
The larger dataset does not establish a latent model of the partner. Binding
is small, transfer is slightly negative, and simple text matching policies
score higher. This is a weak result under this particular setup, not proof
that the model cannot learn about another agent.

## What we actually ran

The model was `Qwen/Qwen3.8-27B`, revision
`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, on one A100 80GB. Settings were
unchanged from the pilot: BF16, temperature 0.7, top p 0.8, top k 20, maximum
16 output tokens, thinking disabled, and decoding constrained to digits 1, 2
and 3. The runtime used PyTorch 2.9.1 and Transformers 5.16.1. The actual
processor and loaded architecture are recorded in the runtime file.

Each of 36 fixed bundles contains 24 simulated history records involving two
participants. The model selects a message from three candidates. It sees the
history, the participant labels and the current decision. It does not receive
the hidden types, registered frame vectors or simulator probabilities.

There are five branches, each with 144 choices:

| Branch | What changes |
| --- | --- |
| Binding | Exchange participant labels on the same history and query each recipient |
| Transfer | Repeat the binding comparison with messages combining different frames |
| Paraphrase | Repeat it with paraphrased messages |
| No history | Remove history, retaining familiar and composite candidate queries |
| Random responses | Use histories with outcomes independent of the message frame |

Exchanging labels is not a silent target change over successive interactions.
These histories were supplied to the model, not produced by its own earlier
choices. No new target decision was sampled after the model chose a message.
The probabilities in the report are simulator expectations, not observed
success rates. Forecast requests in the parent ledger were not part of this
run. Those 144 unrequested forecasts are not failed responses.

The six ordered type pairs and six candidate orders each occur six times.
The current scenario families contain 13 repair workshop bundles, seven
community archive bundles and 16 exhibition space bundles. All were retained.
No family, history or seed was replaced after seeing an outcome.

## The result

Each number below is a normalized contrast. It is not a percentage. One is the
ideal hidden type oracle score; zero can reflect no sensitivity or cancellation
between different choices. The unit is a complete bundle, not an individual
choice. Every row contains all 36 bundles.

| Measure | Mean | Sample SD | Positive bundles | Zero bundles | Negative bundles |
| --- | ---: | ---: | ---: | ---: | ---: |
| Familiar binding | 0.076 | 0.353 | 9 | 20 | 7 |
| Composite transfer | -0.028 | 0.266 | 4 | 28 | 4 |
| Paraphrase binding | 0.007 | 0.296 | 9 | 20 | 7 |
| No history, familiar | 0.069 | 0.341 | 8 | 25 | 3 |
| No history, composite | -0.194 | 0.525 | 2 | 25 | 9 |
| Random responses | 0.014 | 0.401 | 13 | 15 | 8 |

Every median is zero. The random branch uses arbitrary pseudo types for its
contrast geometry. It does not measure actual susceptibility in a target whose
responses are independent of the message. The no history and full history
scores also have different constructions, so subtracting their means is not
automatically a valid causal estimate.

The decision to complete the bank came after the original pilot results were
known. This is therefore descriptive followup work, not an untouched
confirmation study. The reporting contract was saved before inspecting the
new choices. It specifies no confidence intervals, p values or retrospective
scientific gate passes. Sample SD describes variation across these bundles;
it is not uncertainty about a population effect.

### Every baseline remains in the comparison

| Policy | Binding | Transfer | Paraphrase |
| --- | ---: | ---: | ---: |
| Qwen3.8-27B | 0.076 | -0.028 | 0.007 |
| Original Jaccard text matching | 0.514 | 0.194 | 0.403 |
| Content Jaccard text matching | 0.500 | 0.250 | 0.375 |
| Stem Jaccard text matching | 0.472 | 0.306 | 0.153 |
| Character trigram matching | 0.583 | 0.417 | 0.347 |
| Length only | 0.125 | 0.111 | 0.028 |
| Static belief reference | 0.653 | 0.667 | 0.653 |
| Participant feature reward reference | 0.597 | 0.528 | 0.597 |
| Hidden type oracle | 1.000 | 1.000 | 1.000 |

These are comparisons on this fixed bank, not general rankings of LLMs and
algorithms. The final three references receive privileged annotations. The
belief reference also knows the simulator likelihoods, while the oracle knows
the hidden type. The text controls use parameters fixed on development data.
The [complete report](../results/runpod_extension_20260909/analysis/REPORT.md)
includes all six measures for every baseline and all 36 bundle scores.

## What the raw records show

The model selected digit 1 on 364 requests, digit 2 on 313 and digit 3 on 43.
This is an imbalance worth testing in a future controlled diagnostic. It does
not establish a position bias by itself: the same history was not rerun under
every permutation with matched sampling. Candidate wording and history differ
between bundles.

In familiar binding, 14 of 36 bundles selected the same candidate in all four
cells. This happened in 15 transfer bundles and 19 paraphrase bundles. These
counts describe the outputs; they do not identify self consistency, failure to
retrieve feedback or any other internal cause.

Exploratory inspection by family found mean familiar binding of zero in the
workshop and archive families, and 0.172 in the exhibition family. Mean
transfer was zero, zero and -0.062 respectively. These small, unequal subgroups
are retained as observations, not selected positive findings. No subgroup test
or model tuning followed this inspection.

## Noisy evidence and the remaining scientific problem

The full history audit found that 46 of 72 participant histories uniquely
favoured the true type, 16 tied while including it, and 10 favoured a wrong
type under a privileged Bayesian observer. Ground truth scoring can therefore
penalize an agent that reasonably follows noisy evidence. None of those
histories was excluded.

The supplementary analysis measures how much expected reward the chosen
message leaves behind relative to that observer's best available candidate.
Average regret was 0.1035 for familiar messages, 0.0673 for composite messages
and 0.1168 for paraphrases. This comparison assumes perfect knowledge of the
registered frames and response rule. It is not independent human validation
or a measurement of the model's internal beliefs.

The rule remains `P(A) = 0.38 + 0.34 * x[target]`, with `P(A) = 0.5` in the
random branch. Here `x` is the registered fraction of clauses in each frame.
For any belief vector `b`, the prediction `0.38 + 0.34 * dot(b, x)` equals
`dot(q, x)` for the reward vector `q = 0.38 + 0.34 * b`, because the clause
fractions sum to one. The assay cannot distinguish these two representations
from their predicted choices alone.

The rendered prompt and hash checks found no direct analyst metadata in the
model input. That verifies the implemented boundary, not the absence of every
semantic shortcut. The high text baseline scores are a reason to remain
cautious. The earlier machine judge disagreements remain unresolved, and
human validation has not been performed.

## Verification, spending and cleanup

All 660 extension responses were collected once. The original 60 were joined
by their frozen hashes and were not rerun. There were no missing responses,
failed generations, random fallback choices or automatic retries. Constrained
decoding explains output validity; it is not an unconstrained instruction
following result. Input lengths were 391 to 5,118 tokens, with no truncation.

An independent scalar implementation reproduced every bundle score and mean,
with maximum floating point difference `1.11e-16`. A separate audit verified
all claim records, execution indices, response hashes, completion records and
raw choices against the report. The frozen primary analyzer is unchanged.
A complete local replay produced byte identical summary, report and manifest
files, with no additional model calls.

The full repository suite passed 1,067 tests in 546.45 seconds. Twelve final
focused tests passed in 2.21 seconds after adding the supplementary audit.
These are engineering checks, not scientific evidence for partner modeling.

The extension archive was downloaded and verified before stopping the GPU:
1,345 payload files plus its manifest, including all 660 new responses. The
archive SHA256 is
`7f306512087019023bf6bd83fb1ff5a88241ca0e58906b81afcadc9291c3c46a`.
RunPod confirmed `EXITED` for the extension pod. The original pilot pod is also
stopped. The old calibration pod and its network volume were not modified.

The extension used approximately 32 minutes at $1.59 per hour, about $0.85
in GPU compute. Including the first pilot, the compute estimate is about
$1.20. These are elapsed time estimates, not a finalized provider invoice.
Stopped pod disks still incur storage charges until deletion. Permission to
remove the two temporary pods and disks has been requested; no permanent
deletion has been performed. The API controller was closed after stop
confirmation, releasing the in memory credential.

The failed resume, package verification fix, dependency warning and other
operational details remain in the [execution log](RUNPOD_EXTENSION_LOG_20260909.md).
They have not been omitted because the final run succeeded.

## What should happen next

Do not use this result to justify activation collection or steering. First
separate basic task access from the proposed representation question. A next
small diagnostic could compare the same evidence in prose and in a compact
outcome table, and cross candidate order within the same histories. That would
test whether feedback retrieval and response presentation are bottlenecks.
It would be a new, explicitly labeled elicitation diagnostic, not a repaired
version of these results. Its sample and decision rule should be fixed before
any new paid call.

Even a successful diagnostic would leave the belief versus reward equivalence
unresolved. The current honest conclusion is that the engineering worked, but
this run did not produce convincing evidence for the proposed latent partner
model. No additional experiment has been launched.

## Read or reproduce the evidence

- [Complete table and all 720 selected messages](../results/runpod_extension_20260909/analysis/REPORT.md)
- [Machine readable scores and candidate probabilities](../results/runpod_extension_20260909/analysis/summary.json)
- [The 660 exact new system and user prompts](../results/diagnostic_extension_package_20260909/package/extension_packet.json)
- [The original 60 prompts](../results/diagnostic_pilot_package_20260908/package/packet.json)
- [All new raw response records](../results/runpod_extension_20260909/retrieved/responses)
- [Backup verification receipt](../results/runpod_extension_20260909/backup_receipt.json)
- [Independent score check](../results/runpod_extension_20260909/independent_score_check.json)
- [Execution audit and bundle descriptives](../results/runpod_extension_20260909/postcollection_audit.json)
- [Reporting contract saved before new outcome inspection](../results/runpod_extension_20260909/analysis_contract.json)

Reproduce the primary analysis locally into a new directory. This makes no
model calls and refuses to overwrite an existing report:

```bash
.venv/bin/python scripts/analyze_diagnostic_extension.py \
  --source results/grounded_partner_readiness_20260908 \
  --package results/diagnostic_extension_package_20260909/package \
  --prior results/runpod_diagnostic_20260909/retrieved/responses \
  --new results/runpod_extension_20260909/retrieved/responses \
  --output results/runpod_extension_20260909_replay
```

The statistical analysis skill guided reporting of every condition, bundle
variation and the distinction between exploratory observations and confirmation.
The experimental design skill guided retention of the fixed allocation.
The Google Doc and remote GitHub branch have not been edited during this run.
