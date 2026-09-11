<!-- generated-by: gsd-doc-writer -->
# Research status, 11 September 2026

Snapshot: 11 September 2026, 08:15 UTC. Read with the [README](../README.md).
Completed evidence ends with the closed acquisition, transfer and revision
dataset. The recipient binding diagnostic is running; this note reports its
design and preallocation checks only. Its outcomes were not inspected for
this documentation update.

## The question now

Can I separate learning which message gets A from learning something about
the particular recipient? The completed evidence supports using supplied
feedback and revising a message choice under a bounded answer protocol.
It leaves spontaneous exploration, reliable live revision and a latent partner
representation unresolved.

For example, an archive scanning history can favor one message theme, and
later feedback can favor another. The model often changes its choice and
transfers that preference to choir recording messages. A recent reward table
with text matching can do this too. Calling the result a beleif update would
therefore add an interpretation that the choices alone do not establish.

## What is published and what remains local

The source baseline checked for this snapshot is `4r4cn1d0/LatentTarget`,
branch `main`, commit `90176e2`. The README links to tracked historical
specifications, processed V4 results, the original baseline comparison and
runnable local mock tools. The four large V4 raw logs are excluded from Git;
the [README evidence section](../README.md#evidence-and-reproducibility) names
them and explains which replays require them.

The later diagnostic source, findings, raw outputs and report archives listed
below remain local and unpublished at this snapshot. Their paths are inventory
entries, not download links. This status note reports their results; publishing
it with the README does not publish those dependencies or make the later runs
fully reproducible from a fresh checkout. The frozen source and packets remain
unchanged, and this documentation update edits no experimental code.

Published starting points include the
[original baseline findings](BASELINE_COMPARISON_FINDINGS_20260907.md),
[720 choice diagnostic](RUNPOD_EXTENSION_FINDINGS_20260909.md), and
[additive simulator identification limit](IDENTIFIABILITY_CONCLUSION_20260909.md).
The Google Doc is a companion writeup with a separate edit history.

## Acquisition, transfer and revision: closed partial dataset

Collection occurred on 10 September UTC, with the final audit completed on
11 September in India. All 118 observed final answers were valid out of 132
planned requests. One additional request was interrupted at the fixed process
limit; thirteen never started. The archived status is
`INCOMPLETE_DO_NOT_RESUME`. Missing answers are not scored as observed failures.
The summary field `unattempted: 14` includes the interrupted request, so it
must not be read as fourteen requests that never started.

Each call receives a separately constructed history and selects a prepared
message. There are three scenario pairs: archive scanning to choir recording,
seed exchange to costume repair, and heritage walk to poster printing.
No new target response is sampled after a choice. These are checkpoints with
supplied observations, not continuous live adaptation trajectories.

The first eighteen observations give the old message five A outcomes out of
six, versus one out of six for each alternative. After nine changed observations,
the pooled counts still favor the old message, 5/9 versus 4/9. After twenty
seven changed observations, the new message leads, 8/15 versus 7/15.
This complication matters: late revision is also compatible with pooled reward
tracking. The observations use fixed quotas, not new Bernoulli draws.

Acquisition succeeded in 9/9 seen and 9/9 transfer requests, including 3/3
for each framing in each form. The acquisition gate passed. The six empty
history requests have no supported type and are not scored as failures.

| Form and added observations | New framing after change | Original framing under stable feedback | Same alternative under stable feedback |
| --- | --- | --- | --- |
| Seen, 9 | 8/16 observed; 2 missing | 6/6 observed; 3 missing | 0/12 control uses observed; 6 missing uses |
| Seen, 27 | 17/18; complete | 8/9; complete | 1/18 control uses; complete |
| Transfer, 9 | 7/13 observed; 5 missing | 9/9; complete | 0/18 control uses; complete |
| Transfer, 27 | 14/16 observed; 2 missing | 6/7 observed; 2 missing | 1/14 control uses observed; 4 missing uses |

Each form and checkpoint has eighteen directed changes and nine distinct
stable controls, each used twice. Acquisition responses are also shared.
The complete late seen difference is 17/18 minus 1/18, or 88.9 percentage
points. The stricter joint event requiring acquisition, stable retention and
revision occurs in 15/18 comparisons. The stable failure affects two comparisons.

For early seen, early transfer and late transfer, complete matched subsets
have differences of 5/10, 7/13 and 9/12. Their strict joint counts are 5/10,
7/13 and 8/12. These subsets do not replace the planned denominators.

| Form and checkpoint | Possible new framing count out of 18 | Possible matched difference | Possible strict joint count out of 18 |
| --- | --- | --- | --- |
| Seen, 9 | 8 to 10 | 27.8 to 55.6 percentage points | 5 to 10 |
| Seen, 27 | 17 | 88.9 percentage points | 15 |
| Transfer, 9 | 7 to 12 | 38.9 to 66.7 percentage points | 7 to 12 |
| Transfer, 27 | 14 to 16 | 61.1 to 83.3 percentage points | 8 to 14 |

These supplemental bounds enumerate possible missing choices while respecting
control reuse. They are separate bounds for each metric, not confidence
intervals or imputations. Time limited missingness need not be representative.

### The baseline and completion limits

| Observed requests | Model supported choices | Recent nine text baseline |
| --- | --- | --- |
| Seen acquisition | 9/9 | 9/9 |
| Transfer acquisition | 9/9 | 8/9 |
| Seen early change | 8/16 | 16/16 |
| Seen late change | 17/18 | 18/18 |
| Transfer early change | 7/13 | 11/13 |
| Transfer late change | 14/16 | 14/16 |

The text baseline receives public message strings and outcomes, without frame
labels. The late transfer tie is a tie in supported choices; model and baseline
agree on 12/16 individual choices. The baseline scores 16/18 over all planned
late transfer requests, so even two correct missing model answers would only
tie it. Literal exact message lookup scores 3/9 on transfer acquisition with
uniformly weighted ties, leaving semantic reward tracking as a stronger rival.

The frozen baseline code averages individually smoothed message reward rates;
the written formula smooths weighted counts. Both were preserved and audited.
They disagree on six full history transfer contexts and no recent nine
contexts. On observed early transfer, their full history scores are 3/13 and
0/13; on late transfer, 9/16 and 11/16. Both recent nine versions retain
11/13 early and 14/16 late. The discrepancy changes the full history comparison
and was found during collection before choices were inspected.

The model is `Qwen/Qwen3.8-27B`, revision
`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, with thinking enabled,
temperature 0.7, top p 0.8 and top k 20. Each request allows 512 initial tokens,
then up to 1024 continuation tokens. If thinking remains open, the collector
inserts exactly `\n</think>\n\n` and allows up to 64 answer tokens.
No answer digit is inserted. The calls are segmented and reseeded.

Only 20/118 answers ended naturally; 98 required the imposed close. All 63
observed changed history answers required it. This supports conditional
behavioral revision under this protocol, with no unmodified native completion
demonstrating reversal in this run.

The preselected transcript audit covered all 28 available members of thirty
selected texts, retaining the two missing cases without replacement. It also
read the interrupted request's saved prefix. Some early failures notice the
changed feedback but choose the pooled historical leader. Some successes still
contain counting or mapping mistakes. This was unblinded assistant inspection,
not human annotation or a faithful measurement of internal computation.
I take it as a specifiic clue about evidence use, with the choice counts doing
the main evidential work.

Before collection, 1,477 tests and 24 subtests passed. Afterward, token replay,
independent final answer recount, runtime checks and identical report replay
passed. All 1,022 manifest listed backup files verified. The final scoped
regression passed 97 tests and 24 subtests. The frozen records remain intact.

## Why the preceding diagnostics matter

The completed grounded live pilot had three 10 round episodes and silent swaps
after round 5. All 30 choices were valid, but only 8/30 messages matched the
current hidden type and 15/30 target decisions were A. Risk was selected 22/30
times, including every round of one episode. None of the ten fairness target
rounds received a fairness message. One apparent improvement occurred when
the target changed to the model's existing risk preference.

In the expertise to fairness episode, repeatedly selecting risk gives the same
0.38 probability of A under either type. Those actions cannot reveal that swap.
The first five observations in all three episodes also favored a wrong type
under a privileged static likelihood reference. I cannot infer a stale learned
preference from those histories. This is why the next diagnostics supplied
balanced observations explicitly.

The evidence use diagnostic completed 66 choices: 18/18 clear acquisition
checks and 9/9 neutral prefix controls passed. With conflicting prior evidence,
the stronger later message was selected in 14/18 cases. Reversing the blocks
changed the choice in 4/18 pairs; reversed choices followed stronger earlier
evidence in 12/18, latest evidence in 5/18, and neither in one. Every one of
the 45 long history answers required an imposed thinking close.

The matched format and budget diagnostic then completed 180 outcomes from
90 shared initial generations. On the same 27 histories where all registered
references agree, the comparison was:

| Format | Short policy matches | Longer policy matches | Longer answers needing imposed close |
| --- | --- | --- | --- |
| Original prose | 23/27 | 27/27 | 4/27 |
| Chronological ledger | 25/27 | 27/27 | 6/27 |

The longer policy repaired four prose failures and two ledger failures.
Ledger at the short budget had three gains and one loss relative to prose.
All 45 concurrent prose short choices and initial token sequences reproduced
the preceding diagnostic. The matched gains establish a contribution from
the completion policy on this bank. That is a useful clue about thee interface.

The longer policy adds up to 1024 native continuation tokens after the shared
512 token prefix, before the bounded final answer step. It changes close
timing and answer opportunity as well as generation length. The ledger also
changes repetition, length and salience while preserving observations.
The result does not isolate extra reasoning as a pure causal explanation.

The 18 reversed histories have competing references: pooled evidence favors
the stronger earlier block, while recent rules favor the latest block.
Longer prose chose the latest message in 4/18 and longer ledger in 6/18;
35/36 of these endpoints still required the imposed close. These counts are
reference agreements, not unconditional accuracy or a live adaptation curve.

### Earlier completed checks

| Check | Result retained | What it limits |
| --- | --- | --- |
| Grounded supplied history bank | 60 initial choices plus 660 remaining choices; all 720 valid across 36 bundles | Mean binding 0.076, composite transfer -0.028 and paraphrase binding 0.007; character trigram baseline 0.583, 0.417 and 0.347 |
| Presentation diagnostic | All 972 requests completed; all 36 direct output checks passed | Factual lookup 36/36 prose and 33/36 compact; binding 0.027778 and 0.009259, so compaction did not recover reliable binding |
| Predictive information diagnostic | All 620 constrained choices valid | Factual lookup 28/32; reference selection 48/96 now and 36/96 later; later choice with full evidence 41/96; full minus withheld contrast 0.114583 versus required 0.50 |
| Balanced inference check | Reasoning 24/24 correct versus 11/24 without it, with the same 1024 token cap | Validates short table questions; all 21 completed longer bridge outputs exhausted 256 tokens before a final answer |
| Earlier live reasoning pilot | Three valid rounds, then a fourth generation exhausted 4096 tokens | No fourth target decision, fallback or swap; older V4 wording remained a separate confound |
| Grounded completion comparison | Ordinary prompt 9/18 valid, uncertainty instruction 10/18 | Both passed all nine informative items; all 17 invalid outputs exhausted 1024 tokens; neither readiness gate passed |
| Bounded answer screen | 18/18 valid versus 6/18 with unchanged continuation | 36 paired outcomes from 44 calls; 13 of 18 shared prefixes needed an imposed close; an interface result on constructed histories |

Binding statistics in this table are normalized contrasts, not success
percentages. The later screens reused development material and do not form
independent confirmations. The answer selection packet retained 357 completed
outputs, one interrupted call and 26 never started requests; the balanced
check added 48 outputs. Those 405 saved outputs include unfinished answers.
They must not be called 405 valid final choices.

The original V4 comparison is a separate result. Across held out seed bundles,
the selected reward learner predicted original Qwen choices with loss 0.4973
and accuracy 80.9%, versus 0.5128 and 79.9% for the selected belief model.
Those are choice predictions, not Option A success rates. The baselines saw
frame annotations, and the belief references knew the simulator likelihoods.
This exploratory fit does not identify the model's internal algorithm.

In the additive simulator, a suitable expected reward vector and a belief
over target types produce exactly the same predictions. A recipient reward
representation could still be useful, but choice accuracy alone cannot
distinguish these descriptions. No scientific activation dataset, trained
real model probe or causal steering finding has been produced. Human semantic
validation remains unfinished; the earlier blind reviews were machine reviews.

## Recipient binding: running, with outcomes withheld

The frozen diagnostic has 48 requests: three scenario pairs, two forms
(seen and transfer), and eight requests per pair and form. It reuses the
eighteen reviewed messages from the transfer bank, so these are development
stimuli. Each recipient has twelve observations, with twenty four rows in
the combined history.

The eight requests comprise two recipient queries under the base assignment,
two after swapping only history recipient labels, two consistent renaming
controls, and two controls retaining only the queried recipient's rows.
Query and label swaps preserve global message and outcome chronology.
The filtered controls also shorten the history, which limits an interpretation
solely in terms of interference from the other recipient.

Can I make the answer depend on whose feedback it was? This construction
requires that distinction, while retaining global and recipient reward
baselines, text similarity rules and identity controls. A recipient semantic
reward table is expected to solve the task. Even perfect results would leave
that explanation available. No collection outcomes are used in this note.

Before allocation, the work log reports 1,675 tests and 86 subtests passing in
505.25 seconds. The saved JUnit has 1,675 testcase records, a total of 1,761
including subtests, zero failures, errors or skips, and suite time 504.837
seconds. The wall time in the log and JUnit suite time are distinct timings.
The full mock covered 48 responses and 144 physical calls; report replay,
independent recount, all 48 tokenizer checks and frozen baseline predictions
passed before collection. The run is still running as of 08:15 UTC in this
snapshot. Its design does not become a finding until the terminal data are
audited, including any missing answers.

## Local evidence inventory

Every path in this table is local and not published at the source baseline
above. These entries locate the evidence for a future release; they are not
claims that a GitHub reader can already retrieve it. Where a directory is
listed, `summary.json` is the structured result unless another file is named.

| Evidence | Local path, not published |
| --- | --- |
| Transfer and revision findings | `docs/TRANSFER_REVERSAL_FINDINGS_20260910.md` |
| Transfer transcript audit | `docs/TRANSFER_REVERSAL_QUALITATIVE_AUDIT_20260910.md` |
| Transfer report and summary | `results/transfer_reversal_run_20260910/report/` |
| Transfer independent recount | `results/transfer_reversal_run_20260910/independent_recount.json` |
| Transfer missing outcome bounds | `results/transfer_reversal_run_20260910/missing_outcome_bounds.json` |
| Both baseline formulas | `results/transfer_reversal_run_20260910/formula_audit_observed.json` |
| Matched format findings | `docs/FORMAT_BUDGET_FINDINGS_20260910.md` |
| Matched format report and summary | `results/format_budget_run_20260910/report/` |
| Paired format and budget counts | `results/format_budget_run_20260910/descriptive_readout.json` |
| Grounded live findings | `docs/GROUNDED_LIVE_PILOT_FINDINGS_20260909.md` |
| Grounded live report and summary | `results/grounded_live_run_20260909/report/` |
| Earlier information audit | `docs/ADAPTATION_ROOT_CAUSE_AUDIT_20260909.md` |
| Evidence use findings | `docs/EVIDENCE_USE_DIAGNOSTIC_FINDINGS_20260909.md` |
| Evidence use report and summary | `results/evidence_use_run_20260909/report/` |
| Presentation findings and summary | `docs/PRESENTATION_DIAGNOSTIC_FINDINGS_20260909.md`; `results/runpod_presentation_20260909/analysis/summary.json` |
| Predictive findings and summary | `docs/PREDICTIVE_INFORMATION_FINDINGS_20260909.md`; `results/predictive_information_run_20260909/analysis/summary.json` |
| Inference findings and summaries | `docs/ANSWER_SELECTION_FINDINGS_20260909.md`; `results/answer_selection_run_20260909/analysis/summary.json`; `results/row_selection_run_20260909/analysis/summary.json` |
| Earlier live failure | `docs/REASONED_PILOT_FINDINGS_20260909.md`; `results/reasoned_pilot_run_20260909/report/summary.json` |
| Completion comparison | `docs/COMPLETION_COMPARISON_FINDINGS_20260909.md`; `results/completion_run_20260909/report/summary.json` |
| Bounded answer screen | `docs/BOUNDED_ANSWER_FINDINGS_20260909.md`; `results/bounded_run_20260909/report/summary.json` |
| Recipient prospective plan | `docs/RECIPIENT_BINDING_PLAN_20260911.md` |
| Recipient preallocation regression | `results/recipient_binding_ready_20260911/full_regression.xml` |

The checks for this documentation update read existing findings and structured
reports, inspected the saved JUnit, checked source paths and publication
coverage, and reviewed the two document diffs. They did not rerun the full
test suite or collect new model outputs. The remaining publication gap is
real, and I would keep that caveat visibile beside the current claim.
