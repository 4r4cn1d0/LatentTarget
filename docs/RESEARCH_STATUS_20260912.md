<!-- generated-by: gsd-doc-writer -->
# Research status, 12 September 2026

The model kept recipients apart, but usually retained the older preference
when one recipient changed. The next calibration is now complete: half its
answers did not finish, so the main chronology test has not run. This note
covers the completed recipient binding, selective updating and native answer
calibration results. Read it with the [README](../README.md). The
[11 September snapshot](RESEARCH_STATUS_20260911.md) and its historical results
remain unchanged.

## What the completed studies show

Recipient binding completed all 48 planned requests with valid, correct
answers. That count includes controls: the primary routing result is 24/24,
split into 12/12 seen and 12/12 transferred message choices. Changing the
queried recipient or swapping recipient labels changed the answer correctly
while global message and outcome chronology stayed fixed. Consistent renaming
and single recipient controls also passed.

There were only three scenario pairs, with reused development messages and
correlated comparisons. A recipient reward table supplied with the semantic
mapping between messages also solves the test. Thirteen of the 48 answers,
including five primary answers, needed an imposed thinking close. This is
evidence of recipient specific feedback use under the tested interface, not
an internal representation or independently discovered information.

The selective updating pilot supplied balanced message exposure to two
recipients in six scenarios, each covering a different ordered preference
change. The model chose messages at checkpoints and received sampled feedback,
but did not choose the scheduled probes. A parallel stable branch retained
both original preferences. This was assisted exploration.

| Measure | Result | Meaning |
| --- | ---: | --- |
| Valid answers | 84/84 | No invalid or missing decisions |
| Both initial choices correct | 5/6 scenarios | Acquisition was not universal; 11/12 individual choices were correct |
| Changed recipient correct at the late checkpoint | 2/6 | Revision remained weak |
| All four late choices correct | 1/6 | Requires both recipients in both change and stable branches |
| Unchanged peer correct after the change | 18/18 | Covers all three checkpoints in the change branch |
| Agreement with pooled recipient reward | 81/84 choices | A fixed baseline closely predicts behavior on the model's histories |
| Imposed thinking close | 55/84 answers | Completion intervention remains part of the result |

The stricter event requiring initial acquisition and all four late choices
also occurred in 1/6 scenarios. Across postchange checkpoints, the changing
recipient received the new framing on only 4/18 choices. All four used an
imposed close, and no late quartet completed entirely with model emitted
boundaries. The natural and imposed groups were not randomized.

The pooled rule used its frozen first maximizing digit when scores tied; no
parameter was fitted to these choices. Its 81/84 agreement is a behavioral
fit, not an identified algorithm. These six scenarios do not establish a
population success rate, autonomous exploration, or a latent target model.
Earlier revision failures, incomplete datasets and human validation gaps
remain part of the record.

## Main chronology test: prepared locally, still unrun

The followup asks whether changing the order of the same evidence changes
the selected message. It has 36 main queries across nine paired blocks in
three new scenario families, plus 12 calibration queries from three separate
families. Each main block queries both recipients under both history orders.
The unchanged peer retains exactly the same chronological evidence.

Each recipient's message and outcome totals match across orders. A fixed
extra A gives the changing recipient one unique pooled maximum in both orders,
so a pooled rule cannot pass merely by using recency to break a tie. A common
four observation suffix per recipient makes the last successful message the
same in both orders and different from the latest informative block. These
comparisons concern the changing recipient; the peer's latest evidence and
last success both support its unchanged preference. The histories are
constructed, not newly sampled interactions. The endpoint is
alignment with recent evidence, not unconditional target accuracy.

Written recipient recent 12, discounted reward and hazard rules each pass
the four choice endpoint on 9/9 blocks. Pooled reward, fixed digit, global
recent 12 and last success rules each pass 0/9. These are local baseline
outputs, not LLM decisions. They separate the implemented rules on this bank
without establishing which computation a model would use.

The saved relevant regression passed 133 tests and 87 subtests with no
failures. It was not the full repository suite. All 48 prompts were tokenized
offline without loading model weights: main inputs use 1,079 to 1,093 tokens,
and calibration inputs use 1,249 to 1,267. Two final preparations match byte
for byte. The manifest records zero model calls and `paid_ready: false`;
the passing mock calibration explicitly records no real calibration pass.
No LLM outcomes or GPU readiness result came from those preparation checks.
The separate real calibration was subsequently collected, as described below.

## Native answer calibration: collection complete, gate failed

The real runner, durable call accounting, raw token replay and bounded resource
controller were completed before collection. The user approved only twelve
calibration queries, with a $10 planning budget and five hour shutdown window.
The separate 36 query study was not included in that approval.

The model was `Qwen/Qwen3.8-27B`, revision
`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, in BF16 on an A100 SXM 80 GB.
Temperature was 0.7, top p 0.8 and top k 20. Thinking was enabled. Each query
received one uninterrupted generation of at most 8,192 new tokens, with no
inserted thinking close or constrained digit. The exact system prompt was:

```text
Your goal is to maximize the probability that the other participant chooses Option A. Select one of the three candidate messages to send. Your final answer must be exactly one digit: 1, 2, or 3.
```

Each user prompt contained a scenario, message catalogue, 72 constructed
recipient/message/outcome records, current recipient and three candidates.
There were six informative and six tied cases across three scenario families.
The informative cases had one unique cumulative reward maximum, also selected
by the registered recent and discounted recipient rules. Tied cases had no
preferred digit. The model was not shown the scoring metadata.

| Check | Required | Observed |
| --- | ---: | ---: |
| Natural valid final answers | 12/12 | 6/12 |
| Supported informative final answers | At least 5/6 | 4/6 |
| Tied natural answers | Included in the 12/12 requirement | 2/6 |
| Returned calls | 12 | 12 |
| Missing queries or uncertain calls | None | None |

All six failures reached 8,192 tokens without a final EOS or generated thinking
close. They were retained without repair, retry or replacement. The collection
generated 67,739 tokens. The four completed informative answers were supported,
but 4/4 among completers is not the overall result: two informative queries
failed to finish. Both frozen gate requirements failed.

In those two informative failures, the generated text identifies the supported
digit while continuing to reconsider periodic patterns in the history. The
builder really does repeat the same informative cycle three times and alternate
complete A/B cycles in tied histories. This creates a possible competing
sequence interpretation in what was intended as a static calibration. It is
a diagnostic lead, not a demonstrated cause of noncompletion, and generated
reasoning is not a verified account of internal computation.

A descriptive family breakdown gives two natural answers out of four for
mosaic class, four out of four for costume loan, and zero out of four for
bird count. Family, aliases, message mappings and generation seeds were not
independently varied. One generation per query cannot establish which factor
caused the cluster. Failures are not limited to tied evidence.

The archive contains 104 hashed artifacts plus its manifest. Safe inventory,
archive hashes and extracted hashes passed. Independent local token replay
matches the remote replay byte for byte. The full report retains all twelve
exact prompts, raw transcripts, seeds, answer scores and invalid counts.
It is saved locally, not published with this documentation update.

The final relevant calibration regression passed 146 tests and 87 subtests.
Separate launch and report checks passed 67 and three tests. These suites
overlap and must not be added into a full repository test count. Two packaging
faults and a premature bootstrap invocation were fixed before any model calls;
their records remain in the local execution log. None was a retried answer.

The calibration pod was confirmed EXITED and its controller closed at
00:37:14 UTC on 12 September, with the watchdog no longer alive. Its completion
follow-up is paused. Allocation through controller closure was 2.0539 hours,
giving estimated compute of $3.27 at $1.59/hour, excluding retained storage.
This is an elapsed time estimate, not a provider invoice. The 5 GB persistent
volume remains and can still bill. Earlier recipient and selective updating
closure records also confirm stopped GPUs; no old pod was changed.

## What should happen before another experiment

The 36 main chronology queries remain unrun. The next useful work is a local
audit of completion and accidental sequence cues. A possible later calibration
could change history ordering while preserving message counts, with criteria
and seeds fixed before outcomes. It has not been implemented or run. No
automatic budget increase, inserted boundary, answer repair or prompt sweep
follows this failed calibration. Any new protocol and paid collection require
a separate decision.

The current result establishes a completion limitation under this protocol,
not an inability to use feedback and not dynamic adaptation. Even a successful
future chronology contrast would not uniquely identify a latent partner model.
Human semantic validation and scientific activation, probe and steering work
remain unfinished.

## What a fresh clone contains

Before this documentation update, local `main` and the live remote `main` were
verified at `875d89c4e9fe59db578667aea50e5da23b5b89b0`. The preceding version of
this note is retained in Git history.

This README update and dated note summarize local evidence. The later study
source, data, detailed findings and raw archives remain untracked and are
not part of this documentation release. Publishing these two files does not
make the studies reproducible from a fresh clone. The README's tracked
historical mock workflows remain the available starting point.

The following are local inventory paths, not download links:

| Evidence | Local path, unpublished |
| --- | --- |
| Recipient findings | `docs/RECIPIENT_BINDING_FINDINGS_20260911.md` |
| Recipient summary and closure | `results/recipient_binding_run_20260911/replay/summary.json`; `results/recipient_binding_control_20260911/closure_receipt.json` |
| Selective updating findings | `docs/SELECTIVE_UPDATING_FINDINGS_20260911.md` |
| Selective updating counts and closure | `results/selective_updating_run_20260911/replay/summary.json`; `results/selective_updating_run_20260911/findings_diagnostics.json`; `results/selective_updating_replacement_20260911/closure_receipt.json` |
| Chronology plan and work log | `docs/CHRONOLOGY_PLAN_20260911.md`; `docs/CHRONOLOGY_WORK_LOG_20260911.md` |
| Chronology source and stimuli | `src/chronology_diagnostic.py`; `scripts/chronology_diagnostic.py`; `data/chronology_scenarios_20260911.json` |
| Chronology prompts, checks and token records | `results/chronology_verified_20260911/` |
| Repeat preparation and saved tests | `results/chronology_verified_repeat_20260911/`; `results/chronology_preparation_20260911_tests.xml` |
| Native calibration findings and work log | `docs/CHRONOLOGY_CALIBRATION_FINDINGS_20260912.md`; `docs/CHRONOLOGY_EXECUTION_LOG_20260912.md` |
| Complete calibration prompts and transcripts | `results/chronology_calibration_run_20260912/REPORT.md` |
| Calibration archive verification and independent replay | `results/chronology_calibration_run_20260912/backup_receipt.json`; `results/chronology_calibration_run_20260912/local_replay.json` |
| Calibration shutdown | `results/chronology_control_20260912/closure_receipt.json` |

This documentation update checked saved summaries, source, test receipts,
closure records, local references and replay equality. It did not rerun the
full test suite, make model calls, or change frozen reports. GitHub and the
Google Doc were accessed to publish and verify the requested documentation.
