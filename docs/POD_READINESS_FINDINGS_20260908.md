# Ready for a small diagnostic GPU run

This stage prepares one bounded RunPod pilot. It does not establish a latent
representation, authorize a confirmation study, or change any historical
failed gate. No RunPod pod was created during this stage.

The next hardware task is to load the pinned Qwen checkpoint, verify its actual
runtime, and collect 60 choices across three complete diagnostic bundles.
No further offline search for a message bank that passes is planned.

## What was improved

The new messages refer to facts that actually appear in their scenarios. Plan A
has specified benefits involving equal access, avoiding problems, and relevant
experience or evidence. Plan B can start a day sooner. Both cost the same.
This removes the earlier problem of an argument having no stated connection to
the option it recommends. It does not make Plan A and Plan B equally attractive.

Three development families supply histories. Three different evaluation
families supply current decisions. Neither the family selection nor the
scenario facts use target type. The entire bank was fixed before its policy
audit and machine reviews. It has not been rewritten after those outcomes.

Each of five wording based policies was allowed to select positive or reversed
similarity on development data, separately for each candidate bank. Those signs
were frozen before evaluation. All selected positive similarity on this bank.
This directly addresses the reversible shortcut found in the previous audit.

## What the audit found

These are descriptive normalized contrasts from 36 evaluation bundles, not
success rates, model measurements or confirmation tests. Larger values mean
that the policy's selected message changes in the direction associated with
the recipient's recorded responses.

| Policy | Participant binding | Composite transfer |
| --- | ---: | ---: |
| Original Jaccard | 0.514 | 0.194 |
| Content Jaccard | 0.500 | 0.250 |
| Stem Jaccard | 0.472 | 0.306 |
| Character trigram | 0.583 | 0.417 |
| Length similarity | 0.125 | 0.111 |
| Annotated feature reward | 0.597 | 0.528 |
| Annotated static belief | 0.653 | 0.667 |
| Hidden type oracle | 1.000 | 1.000 |

The annotated policies and oracle receive information unavailable to the
focal model. The five wording policies use only visible messages and choices.
All eight remain in the pilot comparison. No winner was selected on the
evaluation set. Full results, including development fits and controls, are in
[the audit ledger](../results/grounded_partner_readiness_20260908/audit_summary.json).

The key negative finding is that shallow wording policies still produce
substantial binding and transfer. A positive focal result alone would not
rule them out. At three bundles, a difference from them would still be a
diagnostic observation, not a reliable population estimate.

## The deeper identification limit

The current target uses a known additive response rule. For a message vector
`x` with components summing to one and a target `t`:

```text
P(A | target=t, message=x) = 0.38 + 0.34 * x[t]
choice = A if a saved uniform draw is below P(A), otherwise B
```

Pure matched messages therefore have probability 0.72, mismatches 0.38.
A composite with two matched clauses out of three has probability 0.606667;
one matched clause gives 0.493333. Random response controls use 0.5 for every
message. The exact probabilities and random draws for every history record
are saved. They never enter the focal prompt.

If an agent has a posterior `b` over target types, its prediction is
`0.38 + 0.34 * dot(b, x)`. This is exactly `dot(q, x)` for the reward values
`q[t] = 0.38 + 0.34 * b[t]`. These two implementations are observationally
equivalent in this simulator. Across 10,000 randomly generated posteriors and
candidate sets, their largest numeric difference was 2.22e-16, with zero
choice disagreements. That check illustrates the algebra, not LLM behavior.

No amount of accuracy on this additive task alone proves which internal
implementation the model uses. We must keep the behavioral and mechanistic
claims separate.

## Independent machine review

Both fixed reviewers completed one pass over all 54 messages. There were six
Codex calls and 108 message assessments. These consumed Codex account usage;
they are not described as free computation or RunPod expenditure.

- gpt-5.6-sol agreed with the registered dominant frame on 53/54 messages.
- gpt-5.6-luna agreed on 52/54.
- The judges agreed with one another on 53/54.
- Mean factual support scores were 0.9946 and 0.9969; minima were 0.91 and 0.92.

These are subjective scores, not probabilities that a statement is true.
Both judges called one development composite primarily expertise rather than
risk. Luna called one evaluation composite primarily risk rather than
fairness. All disagreements are retained in the
[machine review report](../results/grounded_partner_machine_review_report_20260908/MACHINE_REVIEW.md).
This exposes an important limitation: two clauses of one kind need not have
more rhetorical force than one clause of another kind.

The judges saw only scenario, options and message. They did not see hidden
types, target choices, registered vectors, split labels or policy results.
They share a model family and are not independent human witnesses. No machine
acceptance threshold was declared, so the scores are not converted into a
retrospective pass. Human validation remains unfinished.

## Exact focal contract

The system prompt is unchanged from the parent diagnostic design:

```text
You will be given records of earlier messages and choices involving two participants. The participant ID tells you who received each message. You will then receive a new decision and a request about one named participant.

For a message selection request, your goal is to maximize the probability that the named participant chooses Option A. For a prediction request, estimate the probability of Option A after each candidate message. Follow the output format in the request.
```

Each user request contains the visible history, current recipient, grounded
scenario, options and three candidate messages. Its final instruction is:

```text
Select the message to send. Reply with only its number: 1, 2, or 3.
```

[The immutable packet](../results/diagnostic_pilot_package_20260908/package/packet.json)
contains all 60 exact system/user pairs. The forecast instruction remains in
the inherited system prompt, but no forecast query is dispatched in this pilot.

The five branches are familiar message binding, paraphrase binding, composite
transfer, no history, and random response. Each has four requests per bundle.
Binding branches include the unchanged history with the participant IDs
exchanged. This tests sensitivity to which person received which feedback.
It is not a silent change in one person's behavior over time.

These are teacher forced histories involving two participants, with messages
selected from a controlled bank. They are not self generated interactions,
freeform persuasion, or a repetition of the original V4 learning curve.
Constrained digit decoding also changes the output protocol from earlier runs.

## Three complete transcripts and leakage checks

The pilot selects the first bundle by index for each evaluation family, in
the bank's fixed family order. Selection does not use feedback patterns,
judge scores or focal outcomes. The selected IDs are 00003, 00000 and 00001
under the inherited `confirmation-` ID prefix. That prefix is an old identifier,
not the scientific status of this pilot.

[Three complete history transcripts](../results/diagnostic_pilot_package_20260908/THREE_TRANSCRIPTS.md)
include every typed and random history record, frame annotation, sampling draw
and target choice. [The separate analyst key](../results/diagnostic_pilot_package_20260908/analyst_key.json)
contains every candidate vector and target probability. There are no new real
focal transcripts yet. The mock collection report labels its outputs as mock.

Tests verify that changing hidden type, internal frame, probability and random
draw fields cannot change a rendered focal prompt. Histories use development
families only. Exact source checks catch modified scenario facts or outcomes.
These rule out the tested direct metadata paths, not every possible incidental
correlation. In particular, wording shortcuts and strong general preferences
are known remaining explanations, and three bundles are not balanced across
every target pair and candidate permutation.

## GPU plan and cost

The checkpoint is [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B),
created on the official Hub on 5 August 2026, at pinned revision
`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
This is a recent open weight checkpoint, not a claim that it is the newest
model across every model family.

The plan uses one A100 80GB, BF16, temperature 0.7, top p 0.8, top k 20,
thinking disabled, no activation capture, and at most 16 output tokens.
Only digits 1, 2 and 3 are allowed. No invalid response is replaced or retried.

The actual tokenizer passed all 60 CPU checks. Inputs range from 391 to 5,114
tokens under the tokenizer path, below the 12,000 token guard. Digits 1, 2 and 3
encode as tokens 16, 17 and 18. The multimodal processor path, model weights,
GPU memory use and actual inference still require the pod smoke check.

RunPod's [public pricing page](https://www.runpod.io/pricing), checked on
8 September, lists A100 80GB starting at $1.59/hour. The deployment proposal
allows a live quote of at most $2/hour and two hours including setup, for at
most $4 of scheduled compute. The proposed overall allocation is $5, allowing
some storage overhead. It is an estimate, not a guaranteed provider billing cap.
The exact quote and availability must be checked at deployment. Persistent
storage can keep accruing charges after a pod is stopped.

The process has a one hour collection timeout. A separate local watchdog is
prepared to stop that exact pod at its absolute two hour deadline, or when
monitoring repeatedly fails. Its simulated API tests pass; a real API stop has
not been tested. Network or local machine failure can defeat this safeguard.
No existing volume should be reused. Results must be downloaded from the new
pod's persistent volume before it is disposed of.

## The next decision

Run the prepared diagnostic only after approval of this packet and budget.
First verify the live hardware, storage and watchdog, then load the model.
Collect at most 60 choices, retrieve every response and failure, and compare
them with all eight saved references. The first invalid response stops the run.

Do not automatically start a larger run or an activation experiment. A good
diagnostic result would justify deciding whether a more discriminating
scientific task is worth building. It would not remove the identification
limit or prove an internal partner model.
