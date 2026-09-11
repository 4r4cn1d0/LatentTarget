<!-- generated-by: gsd-doc-writer -->
# Research status, 12 September 2026

The model kept recipients apart, but usually retained the older preference
when one recipient changed. This note adds the completed recipient binding
and selective updating results, then separates them from the chronology test's
local preparation. Read it with the [README](../README.md). The
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

## Chronology: prepared locally, with no model outcomes

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
No new LLM outcomes or GPU readiness result comes from these checks.

## Before any new real calls

The real calibration runner, raw token replay and resource gates remain to
be completed. They must bind the exact inputs and generation settings to
verifiable token traces and a fresh quote, feasible deadline, shutdown
watchdog and bounded authorization. The earlier studies' resource approvals
do not carry forward.

The proposed protocol allows one uninterrupted generation of at most 8,192
new tokens, with no inserted thinking close or constrained digit. The separate
calibration requires all 12 answers to finish naturally with a strict final
digit, and at least 5/6 informative cases to select their supported message.
Tied cases test format only. The 36 main queries remain unrun until real
calibration passes and the collection gates are cleared. A failed calibration
is retained without an automatic retry or protocol sweep. The larger token
allowance has not yet been validated on the model.

Saved closure records confirm both the recipient binding GPU and the selective
updating replacement GPU were stopped, with controllers closed and watchdogs
inactive. Those are historical closure checks, not a fresh account wide live
check. Storage was retained. This note makes no provider invoice claim.

## What a fresh clone contains

Before this documentation update, local `main` and the live remote `main` were
verified at `d132c8303572978d34ad151202a29bb726456705`. The `90176e2` reference
in the earlier snapshot is its preceding source baseline.

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

This documentation update checked saved summaries, source, test receipts,
closure records, local references and replay equality. It did not rerun the
full test suite, make model calls, or change frozen reports. GitHub and the
Google Doc were accessed to publish and verify the requested documentation.
