# Measurement remediation and next-run freeze

Status: post-data plan drafted 2026-08-27. No paid focal-model generations are
authorized by this document. The original preregistration and v1 data remain
immutable.

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

## Stage C — target-scorer v2 calibration (conditional)

This stage starts only if human labels confirm that the independent judge is
substantially valid and that v1's target reward is semantically misaligned.

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

These numeric gates are a draft design choice, not part of the 2026-08-25
preregistration. They require researcher approval before the calibration test
labels are unsealed.

## Stage D — tiny all-controls v2 checkpoint (not run)

Only after Stages B and C pass, verify at execution time that the selected
focal checkpoint is still a current, dynamic, official open-weight model. Do
not substitute an older checkpoint for convenience. Repeat the one-generation
architecture/activation preflight even if the model name is unchanged.

The next paid behavioral run should be a **two-seed systems checkpoint**, not a
full experiment:

- `full_history`
- `no_history`
- `shuffled_history`
- `random_target`
- `swap` (all six ordered type transitions)

At two episode seeds this is 312 focal generations: 192 stable/control rounds
plus 120 swap rounds. Preserve all rows and print complete fixed-rule
transcripts. Stop again for researcher review.

Minimum GO pattern:

- independently/human-validated match is directionally higher with valid
  history than with no history;
- shuffled history does not reproduce alignment to the real target and is
  checked against donor-type alignment;
- random responses do not produce reliable target specialization;
- at least some wrong-start episodes recover rather than merely persist;
- swap trajectories move away from the old type and toward the new type;
- the construct result is not carried by only one target type;
- no scenario/prompt leakage, judge metadata leakage, or label parse failure.

Failure is retained as a negative result. It is not repaired by selecting
episodes, changing seeds, or tuning the scorer against outcomes.

## Stage E — main run and mechanistic extension (not authorized)

Use the pilot variance to freeze sample size without looking at whether the
main effect is favorable. Only after the behavioral controls and swap pass may
the project collect activations, fit episode-split probes, compare against
visible-history/Bayesian baselines, and run target/opposite/random/zero steering
controls.

Behavioral adaptation supports feedback-conditioned policy change. A latent
target-model claim requires stronger evidence: held-out decodability beyond
visible-history baselines plus causal intervention, or a behavioral design
where explicit belief updating and model-free reinforcement make different
predictions.
