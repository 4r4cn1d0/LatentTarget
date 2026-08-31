# Measurement remediation and next-run freeze

Status: post-data plan drafted 2026-08-27. No paid focal-model generations are
authorized by this document. The original preregistration and v1 data remain
immutable.

Update 2026-09-01: the researcher explicitly requested completion of every
non-human stage and authorized paid execution while declining human labelling.
This does not retroactively satisfy Stage B. The project therefore proceeds
under an explicitly **machine-only, exploratory** track documented in
`TARGET_SCORER_V2_PROTOCOL.md`; no result from that track may be described as
human-validated or confirmatory.

Update 2026-08-30: the researcher separately authorized a bounded architecture
preflight and direct-elicitation baseline, documented in
`RUNPOD_CHECKPOINT_20260830.md`. That authorization did not waive the Stage B/C
gates or authorize the Stage D/E behavioral and mechanistic runs.

## Stage A — independent remeasurement (complete)

The saved 192 messages were classified by a blind, different-family judge.
The implementation is deterministic, schema-constrained, cached, resumable,
and preserves exact judge inputs/outputs plus privacy-sanitized process
metadata. Raw CLI process streams are omitted because they duplicate the
prompt and can expose local paths/session identifiers; their hashes and byte
counts are retained.

Historical execution command (this invokes the judge for messages absent from
its cache; it is recorded for provenance, not needed to inspect committed
results):

```bash
python scripts/run_codex_judge.py \
  --log data/raw/qwen38_27b_gonogo_20260826.jsonl \
  --out data/processed/qwen38_27b_gonogo_20260826.codex-judge.jsonl \
  --model gpt-5.6-luna --batch-size 24 --seed 20260826 \
  --cache data/processed/codex_judge_cache.jsonl \
  --artifact-dir results/qwen38_27b_gonogo/codex_judge/batches \
  --timeout 600
```

The independent behavioral tables and figures were then generated with:

```bash
python scripts/analyze_results.py \
  --log data/processed/qwen38_27b_gonogo_20260826.codex-judge.jsonl \
  --fig-dir results/qwen38_27b_gonogo/codex_judge/figures \
  --tab-dir results/qwen38_27b_gonogo/codex_judge/tables \
  --prefix codex_judge_ --n-boot 10000 --seed 20260826
```

Reproduce the artifact and classifier audit:

```bash
python scripts/audit_measurement.py \
  --source-log data/raw/qwen38_27b_gonogo_20260826.jsonl \
  --independent-log data/processed/qwen38_27b_gonogo_20260826.codex-judge.jsonl \
  --artifact-dir results/qwen38_27b_gonogo/codex_judge/batches \
  --out-dir results/qwen38_27b_gonogo/codex_judge/diagnostics
```

Expected headline output: 8 blind batches, 189 unique messages, no metadata
visible to the judge, 0.630 keyword/judge agreement, kappa 0.246, and 71/192
changed primary labels.

## Stage B — human measurement gate (blocked on human labels)

The blind sheet is:

`data/processed/qwen38_27b_gonogo_blind_labels.csv`

It contains the same 40 rows and byte-identical ordering as the original sheet
(SHA-256
`0c5600bce298f8e227f46ae80fa0253ddd9c61870d61d53276b6ac98628ca618`).
Only the concealed answer key was changed so it now references the independent
judge rather than the circular keyword classifier.

The researcher should:

1. Read `data/processed/LABELLING_INSTRUCTIONS.md`.
2. Fill only the `human_label` column with `fairness`, `risk`, `expertise`,
   `other`, or `unsure`.
3. Stay blind to target, condition, round, choice, and the answer-key file.
4. Save the CSV, then run (or ask the research engineer to run):

```bash
python scripts/score_labels.py \
  --sheet data/processed/qwen38_27b_gonogo_blind_labels.csv \
  --key data/processed/qwen38_27b_gonogo_blind_labels.key.json \
  --out results/qwen38_27b_gonogo/codex_judge/diagnostics/human_label_gate.json
```

The gate is fail-closed. It passes only if the sheet is complete, Cohen's kappa
is at least 0.60, and human labels show the same full-history-over-no-history
direction as the independent judge. More than 20% `unsure`, kappa below 0.40,
or a reversed direction stops scaling. Kappa 0.40–0.60 allows only exploratory
language and requires instrument revision.

## Stage C — semantic target-scorer calibration (machine-only track complete)

The original human-dependent Stage C remains blocked. Under the separately
authorized machine-only exploratory track, v2 was frozen, independently judged,
and failed its one-time held-out gate (macro-F1 0.778 but fairness recall 0.400).
It was retired without being used for focal-model outcomes.

The calibration process—not the final vocabulary—is frozen here:

1. Assemble 80 messages, blocked evenly across fairness, risk, expertise, and
   other. Use a mixture of existing focal-model messages and controlled minimal
   pairs/hard negatives.
2. Include implicit fairness phrasing and explicit fairness phrasing; genuine
   evidence/authority appeals; and expertise hard negatives containing words
   such as “professional” and generic senses of “experience.”
3. Randomize with seed `20260827` and label blind to the scorer. If feasible,
   use two independent labelers; resolve disagreements without viewing scorer
   outputs.
4. Before tuning, stratify 60 messages to development and seal 20 as a held-out
   test (five per human label). The held-out labels may not be used to edit
   rules.
5. Tune only on development construct agreement—not target choices, focal
   strategy match, or history-effect direction.
6. Proposed pilot gates, to freeze before labels are viewed: held-out macro-F1
   at least 0.75, no class F1 below 0.60, fairness recall at least 0.70, and no
   more than 15% expertise false positives on designated hard negatives.
7. Save the scorer as a new version and log its complete rules/configuration in
   every v2 manifest. Do not modify or relabel v1.

V3 was then selected only on the demoted v2 development data and committed
before a new held-out corpus was generated. On that independent 80-message
machine test it passed all gates: macro-F1 0.914, minimum class F1 0.864,
fairness recall 0.950, and 0/11 expertise false positives on adversarial other
messages. A blind second machine judge agreed with all 80 intended labels. See
`TARGET_SCORER_V2_PROTOCOL.md` and `TARGET_SCORER_V3_PROTOCOL.md` for the exact
provenance, failure, correction audit, and limitations.

This completes only the machine-only Stage C substitute. Stage B remains
unfinished and no result may be called human-validated or confirmatory.

## Stage D — tiny all-controls v3 checkpoint (complete: STOP)

The researcher explicitly authorized all remaining non-human work, including
paid execution, on 2026-09-01. This waived Stage B only as a prerequisite for
machine-only exploration; it did not make Stage B pass. The selected focal
checkpoint was the current official dense open-weight `Qwen/Qwen3.8-27B`, not
an older convenience model.

The architecture preflight and all 312 frozen generations completed on an
A100-SXM4 80 GB. The run contains exactly 36 episodes across `full_history`,
`no_history`, `shuffled_history`, `random_target`, and all six ordered silent
target swaps twice. The primary blind `gpt-5.6-sol` pass and a separate
`gpt-5.6-luna` sensitivity each classified all 312 messages with no metadata,
parse, or copied-log integrity failure.

The frozen executable decision was **`STOP_BEFORE_MECHANISTIC_EXPERIMENT`**:

- design integrity passed;
- blind independent measurement passed;
- random-response behavior passed its null gate;
- wrong-start recovery passed its minimal gate;
- valid-history advantage failed (overall 0.104 with and without history);
- shuffled-history specificity failed by the frozen threshold;
- silent-swap revision failed (new-type match did not rise and old-type match
  did not fall);
- only risk, not at least two target types, supported a positive late history
  difference.

The sensitivity judge was not a rescue: full-history match was 0.167 versus
0.188 without history. The two judges agreed on 0.814 of labels with Cohen's
kappa 0.624. An exact evidence-only Bayesian observer also found no useful
target-identification advantage under the generated messages: primary-hazard
final-target accuracy was 0.208 in full-history episodes (uniform baseline
0.333), and the swap trajectory-gap interval included zero.

A post-hoc simulator-capacity positive control selected one saved message per
dimension using target scores only, then chose messages to minimize expected
posterior entropy. It reached 0.738 stable-target accuracy after eight outcomes
and 0.567 active-target accuracy five rounds after a swap. The response
function is therefore learnable under an oracle exploration policy; the
focal-model result remains negative because its actual policy did not create
and use that evidence. This diagnostic does not enter or alter the frozen gate.

The complete execution record, costs, hashes, and artifact map are in
`RUNPOD_CHECKPOINT_V3_20260901.md`. The generated report is
`PILOT_REPORT_REAL_QWEN38_27B_V3_CHECKPOINT.md`. This failure is retained as a
negative result and was not repaired by selecting episodes, changing seeds, or
tuning the scorer against outcomes.

## Stage E — main run and mechanistic extension (not run; condition false)

The researcher authorized this work on 2026-09-01, but its scientific gate was
not waived. Stage D did not pass, so no main behavioral run, activation
dataset, probe, or steering experiment was executed. This is a completed
conditional skip, not an engineering or funding blocker. Running those
experiments now would produce mechanistic-looking numbers without an
established behavioral phenomenon to explain.

A future version would require a new pre-outcome protocol—not reuse of the
failed checkpoint—and should first strengthen the information content of the
feedback channel while preserving no-history, shuffled-history, random-target,
and silent-swap controls. Any redesigned system must be validated on new
construct data and must not be tuned to make this saved outcome positive.

Behavioral adaptation supports feedback-conditioned policy change. A latent
target-model claim requires stronger evidence: held-out decodability beyond
visible-history baselines plus causal intervention, or a behavioral design
where explicit belief updating and model-free reinforcement make different
predictions.
