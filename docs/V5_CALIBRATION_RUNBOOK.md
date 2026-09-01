# V5 calibration and freeze runbook

Status: **executed once on 2026-09-01; independent selected-bank validation
failed; confirmatory outcomes remain blocked**.

The historical commands below are retained to make the run reproducible, not
to authorize a rescue rerun. Pool calibration and selected-bank validation
both completed with 576/576 strict outputs and passed all integrity audits, but
the frozen balance gate failed overall, on development wording, and on
held-out wording. No final bank or behavioral checkpoint exists. Do not relax
thresholds, reselect on validation outcomes, or reuse the validation seed.
See `docs/V5_CALIBRATION_RUN_20260901.md` for exact results, costs, hashes, and
the V6 recommendation.

This runbook is deliberately fail-closed. Pool calibration and selected-bank
validation are engineering measurements of the focal model's baseline
preference. They contain no hidden target, no interaction history, no simulator
feedback, and no confirmatory behavioral outcome.

## Frozen inputs

- Calibration protocol: `docs/v5_calibration_protocol.json`
- Candidate pool: `data/v5/v5_candidate_pool_v1.json`
- Pool canonical SHA-256:
  `73a404a79bb5a5bfcaed112638143c70c9e48aff710dff15b0e57f4f95989478`
- Semantic gate: `results/v5_design/semantic_validation/summary.json`
- Focal model: `Qwen/Qwen3.8-27B`
- Immutable revision:
  `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`
- Decoding: bfloat16, non-thinking, temperature 0, exactly `1|2|3`, no
  fallback, no activation capture.

The official Hugging Face model API was rechecked on 2026-09-01 and returned
the same immutable revision and last-modified timestamp as V4. The newer
Qwen3.8 Flash-Next checkpoint is a 180B model; it is reserved for a possible
independent replication rather than silently changing the primary model and
compute class.

## 1. Local gate

```bash
.venv/bin/python -m compileall -q config.py src scripts tests
.venv/bin/python -m pytest -q
.venv/bin/python scripts/run_v5_calibration.py \
  --bank data/v5/v5_candidate_pool_v1.json \
  --mode pool_calibration \
  --run-id qwen38_27b_v5_pool_calibration_20260901 \
  --dry-run
```

Any failed test or failed protocol check stops the paid run.

## 2. Paid pool calibration

Use an 80 GB GPU with `requirements.txt` and `requirements-pod.txt`. Run:

```bash
.venv/bin/python scripts/run_v5_calibration.py \
  --bank data/v5/v5_candidate_pool_v1.json \
  --mode pool_calibration \
  --run-id qwen38_27b_v5_pool_calibration_20260901 \
  --out-dir data/calibration
```

Expected output: 576 strict choices. Do not inspect target-learning metrics;
there is no target or feedback. Retrieve both:

- `data/calibration/qwen38_27b_v5_pool_calibration_20260901.jsonl`
- `data/calibration/qwen38_27b_v5_pool_calibration_20260901.manifest.json`

## 3. Deterministic bank selection

```bash
.venv/bin/python scripts/select_v5_bank.py \
  --pool data/v5/v5_candidate_pool_v1.json \
  --calibration-log data/calibration/qwen38_27b_v5_pool_calibration_20260901.jsonl \
  --calibration-manifest data/calibration/qwen38_27b_v5_pool_calibration_20260901.manifest.json \
  --semantic-validation results/v5_design/semantic_validation/summary.json \
  --bank-out data/v5/v5_selected_bank_pending.json \
  --report-out results/v5_design/bank_selection/report.json
```

The selector first audits the calibration manifest, schedule, target/history
absence, strict outputs, candidate exposure, slot balance, frozen protocol, and
pool hash. It then exhaustively chooses six development and four held-out
templates per frame using the frozen objective. No confirmatory data exists at
this point.

## 4. Separately seeded selected-bank validation

The validation seed is `20261002`, distinct from pool calibration. On the same
GPU installation:

```bash
.venv/bin/python scripts/run_v5_calibration.py \
  --bank data/v5/v5_selected_bank_pending.json \
  --mode selected_bank_validation \
  --run-id qwen38_27b_v5_selected_bank_validation_20260901 \
  --out-dir data/calibration
```

Then finalize locally:

```bash
.venv/bin/python scripts/finalize_v5_bank.py \
  --pending-bank data/v5/v5_selected_bank_pending.json \
  --validation-log data/calibration/qwen38_27b_v5_selected_bank_validation_20260901.jsonl \
  --validation-manifest data/calibration/qwen38_27b_v5_selected_bank_validation_20260901.manifest.json \
  --validation-out results/v5_design/bank_validation/summary.json \
  --final-bank-out data/v5/v5_selected_bank_validated.json
```

The bank passes only when overall, development, and held-out choices each put
every frame in `[0.25, 0.42]` and every max-minus-min gap is at most `0.15`.
Failure stops V5; thresholds are not relaxed and the validation run is not
reused for another selection.

## 5. Final exact power

Use the observed no-history shares only as nuisance baseline calibration, never
as a behavioral effect estimate:

```bash
.venv/bin/python scripts/power_controlled_v5.py \
  --bank-validation results/v5_design/bank_validation/summary.json \
  --n-sim 5000 \
  --out-dir results/v5_design/power_final
```

Power simulates the exact 24-round, six-window, three-target, six-transition
blocked design. Final tests use the complete exact sign-flip distribution. The
sample must satisfy the 80% lower Monte Carlo bound for both co-primary power
and the complete behavioral pattern, and cannot exceed 30 scenario seeds.

## 6. Freeze—still without running confirmatory outcomes

The population smallest-effect pair is already frozen at stable DID `0.20` and
revision shift `0.25` in `docs/v5_calibration_protocol.json`; it cannot be
chosen after calibration. Run:

```bash
.venv/bin/python scripts/freeze_v5_checkpoint.py \
  --bank data/v5/v5_selected_bank_validated.json \
  --pool-calibration-manifest data/calibration/qwen38_27b_v5_pool_calibration_20260901.manifest.json \
  --pool-calibration-log data/calibration/qwen38_27b_v5_pool_calibration_20260901.jsonl \
  --selection-report results/v5_design/bank_selection/report.json \
  --bank-validation results/v5_design/bank_validation/summary.json \
  --bank-validation-manifest data/calibration/qwen38_27b_v5_selected_bank_validation_20260901.manifest.json \
  --bank-validation-log data/calibration/qwen38_27b_v5_selected_bank_validation_20260901.jsonl \
  --power results/v5_design/power_final/v5_power_sensitivity.json
```

Final selected-bank shares can change the required seed count but cannot change
the effect pair. The freezer verifies every referenced file hash—including both
raw paid JSONL logs—and cross-checks each log against its manifest and
downstream report. It refuses to overwrite an existing checkpoint.

Only after the resulting `docs/behavioral_checkpoint_v5.json` is reviewed may
the no-weight confirmatory dry run be invoked:

```bash
.venv/bin/python scripts/run_controlled_open_weight_v5.py \
  --run-id qwen38_27b_v5_checkpoint_YYYYMMDD \
  --dry-run
```

Removing `--dry-run` requires a separate launch decision. No activation capture
option exists in the V5 runner.

## Failure policy

- Invalid model output: abort; no fallback.
- Hash, model, revision, schedule, seed, or threshold drift: abort before model
  loading.
- Semantic, calibration, validation, or power gate failure: do not freeze.
- Confirmatory partial failure: preserve artifacts and resume only at a
  validated episode boundary with identical settings.
- Failed behavioral checkpoint: stop; do not rescue with free-form outputs,
  activations, probes, steering, or post-hoc sample extension.
