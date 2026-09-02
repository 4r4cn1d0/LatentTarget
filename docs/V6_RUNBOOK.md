# V6 final execution runbook (archived at power stop)

Status: **`STOP_V6_UNDERPOWERED_FINAL`**. Do not execute any judge or model
stage. The earlier IID terminal proof was invalid for the heterogeneous path
DGP and was withdrawn. The corrected CPU-only power screen in stage 5 was
prospectively anchored, executed, independently replayed, and failed its frozen
power rule. Nothing else in this runbook remains authorized.

V6 is the final instrument attempt. There is no V7, outcome-triggered redesign,
threshold relaxation, extra validation, sample extension, activation capture,
probe, steering, or free-form rescue in this milestone.

## Frozen identities

- focal model: `Qwen/Qwen3.8-27B`
- immutable focal revision:
  `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`
- semantic judges: `gpt-5.6-sol`, `gpt-5.6-luna`
- quality judges: `gpt-5.6-sol`, `gpt-5.6-luna`
- pool run ID: `v6_pool_screening_qwen38_27b_20260902`
- validation run ID: `v6_bank_validation_qwen38_27b_20260902`
- confirmatory run ID: `qwen38_27b_v6_confirmatory_20260902`
- protocol: `docs/v6_calibration_protocol.json`

Do not substitute a model alias, revision, seed, batch size, path, run ID,
scenario set, or threshold. The CLIs enforce these values and canonical paths,
and terminal power now blocks model execution altogether.

## 0. Local release audit

Run from the repository root:

```bash
git status --short
git rev-parse HEAD
git diff --check
python3 -m compileall -q src scripts tests
python3 -m json.tool docs/v6_calibration_protocol.json >/dev/null
python3 -m pytest -q
codex --version
```

The prospective power correction was committed as
`c2da851f5445866a9ed4a8731808ac028e9c07d8` and pushed under annotated tag
`v6-power-correction-preregistered` before its result existed. Final test and
review evidence is recorded in `docs/WORK_LOG.md` and
`docs/V6_PREJUDGE_CODE_REVIEW.md`.

## Corrected gate result

The prior IID values did not represent the frozen simulator because choices
share heterogeneous bundle/round/slot effects. The corrected screen ran those
actual paths with the registered fixed seeds. The blocking Wilson lower bounds
for N=12, 18, 24, and 30 were respectively 0.4088, 0.4151, 0.4192, and 0.4222,
all below the required 0.80. Sections 1–4 and 6–12 are retained below only to
document the counterfactual pipeline; **do not execute them**.

## 1. Blind target-free measurement gates (historical; prohibited)

These commands make 12 total schema-constrained Codex judge calls: three
batches for each of two models in each of two independent rubrics. The judges
receive opaque sample IDs and message text only.

```bash
python3 scripts/validate_v6_semantic_bank.py
python3 scripts/validate_v6_quality_bank.py
```

Canonical outputs:

- `results/v6_design/semantic_validation/summary.json`
- `results/v6_design/quality_validation/summary.json`
- raw batch triplets below each validation directory;
- exact JSONL caches under `data/processed/v6_semantic_validation/` and
  `data/processed/v6_quality_validation/`.

Both commands must exit zero and report `PASS`. A failure is a terminal V6
instrument limitation. Do not edit candidates, judges, rubrics, thresholds, or
cache files and do not run the focal model.

If interrupted, rerun the same command. A successful paid batch is recovered
from its audited journal/triplet and its whole-batch cache is published
atomically. A divergent partial artifact fails closed.

## 2. Model-free pool dry run on the GPU host (historical; prohibited)

The GPU host must check out the exact pushed pre-judge commit. Reuse the
persistent Hugging Face cache only after confirming the model revision.

```bash
git fetch origin
git checkout --detach <EXACT_PREJUDGE_COMMIT>
python3 -m pytest -q
python3 scripts/run_v6_calibration.py \
  --bank data/v6/v6_triad_pool_v1.json \
  --mode pool_screening \
  --run-id v6_pool_screening_qwen38_27b_20260902 \
  --dry-run
```

The dry run must report 1,680 prompts, no target, no history, and a passing
schedule/protocol audit. It creates no receipt and loads no model.

## 3. Official target-free pool screening (historical; prohibited)

```bash
python3 scripts/run_v6_calibration.py \
  --bank data/v6/v6_triad_pool_v1.json \
  --mode pool_screening \
  --run-id v6_pool_screening_qwen38_27b_20260902
```

Canonical outputs:

- `results/v6_design/launch_receipts/v6_pool_screening.json`
- `data/calibration/v6_pool_screening/v6_pool_screening_qwen38_27b_20260902.jsonl`
- matching manifest and per-sample artifact directory.

Every output must be exactly `1`, `2`, or `3`. An invalid output aborts with no
fallback. On interruption, rerun the identical command: it audits receipt,
manifest, sample artifacts, prompts, provider metadata, and the exact schedule
prefix before loading the model, then starts at the first missing coordinate.

Pull the complete canonical directories back to the local repository before
selection. Do not summarize from an unpulled pod copy.

## 4. Whole-triad selection support gate (historical; prohibited)

```bash
python3 scripts/select_v6_bank.py \
  --pool data/v6/v6_triad_pool_v1.json \
  --calibration-log data/calibration/v6_pool_screening/v6_pool_screening_qwen38_27b_20260902.jsonl \
  --calibration-manifest data/calibration/v6_pool_screening/v6_pool_screening_qwen38_27b_20260902.manifest.json \
  --semantic-validation results/v6_design/semantic_validation/summary.json \
  --quality-validation results/v6_design/quality_validation/summary.json \
  --bank-out data/v6/v6_selected_bank_pending.json \
  --report-out results/v6_design/selection_report.json
```

Exit code 2 is a terminal calibration-support failure. On pass, the exact
pending bank contains six development and four held-out triads. Exact reruns
are idempotent; conflicting pre-existing output fails closed.

## 5. Prospective power (completed terminal stage)

This step is CPU-only and cannot read selected-bank validation outcomes.

```bash
python3 scripts/power_controlled_v6.py --n-sim 10000
```

The command first runs the frozen 12-cell path-balance dominance screen (all
three learner profiles and all four N values at
`minimum_share_boundary_01`) with 10,000 studies per cell. It uses the same
path constructor and study offsets as the complete grid. If the registered
replicate-wise dominance rule blocks every N, it writes
`results/v6_design/power_prevalidation/v6_path_balance_dominance.json` and
exits 2. Otherwise it continues through the complete 169-cell program.

Observed result: exit code 2 and
`STOP_V6_UNDERPOWERED_BEFORE_VALIDATION`. The output file has SHA-256
`23ca7e9155980dd8bf3e50b69e00353a5af8baf3cb535c2b3f28e6432b6d1d0b`;
its canonical certificate SHA-256 is
`79fd9eccf334789ed1249e39ee076d2f74f87f1c505273f07f75350f71187865`.
The complete 169-cell branch was correctly skipped.

## 6. Freeze the pre-validation artifact graph (historical; prohibited)

```bash
python3 scripts/freeze_v6_validation_checkpoint.py \
  --source-pool data/v6/v6_triad_pool_v1.json \
  --semantic-validation results/v6_design/semantic_validation/summary.json \
  --quality-validation results/v6_design/quality_validation/summary.json \
  --prevalidation-power results/v6_design/power_prevalidation/v6_prevalidation_power.json \
  --pool-calibration-log data/calibration/v6_pool_screening/v6_pool_screening_qwen38_27b_20260902.jsonl \
  --pool-calibration-manifest data/calibration/v6_pool_screening/v6_pool_screening_qwen38_27b_20260902.manifest.json \
  --selection-report results/v6_design/selection_report.json \
  --pending-bank data/v6/v6_selected_bank_pending.json \
  --out results/v6_design/prevalidation_checkpoint.json
```

Commit and push the complete artifact graph before independent validation.
After this checkpoint, changing any Python file under `src/` or `scripts/`,
either requirements file, or `config.py` invalidates the run.

## 7. One independent selected-bank validation (historical; prohibited)

First run the dry audit on the exact checkpoint commit:

```bash
python3 scripts/run_v6_calibration.py \
  --bank data/v6/v6_selected_bank_pending.json \
  --mode selected_bank_validation \
  --run-id v6_bank_validation_qwen38_27b_20260902 \
  --pre-validation-checkpoint results/v6_design/prevalidation_checkpoint.json \
  --dry-run
```

Then make the one allowed validation run:

```bash
python3 scripts/run_v6_calibration.py \
  --bank data/v6/v6_selected_bank_pending.json \
  --mode selected_bank_validation \
  --run-id v6_bank_validation_qwen38_27b_20260902 \
  --pre-validation-checkpoint results/v6_design/prevalidation_checkpoint.json
```

This makes 840 target-free, no-history choices. Pull its canonical receipt,
JSONL, manifest, and sample artifacts back before finalization.

## 8. Apply the terminal validation gate and freeze confirmation (historical; prohibited)

```bash
python3 scripts/finalize_v6_bank.py \
  --pending-bank data/v6/v6_selected_bank_pending.json \
  --pre-validation-checkpoint results/v6_design/prevalidation_checkpoint.json \
  --validation-log data/calibration/v6_bank_validation/v6_bank_validation_qwen38_27b_20260902.jsonl \
  --validation-manifest data/calibration/v6_bank_validation/v6_bank_validation_qwen38_27b_20260902.manifest.json \
  --validation-out results/v6_design/bank_validation.json \
  --final-bank-out data/v6/v6_selected_bank_validated.json \
  --final-checkpoint-out results/v6_design/final_checkpoint.json
```

Exit code 2 is the final instrument-limitation result. There is no reselection
or second validation. On pass, commit and push the validation artifacts,
validated bank, and final checkpoint before any target-bearing call.

## 9. Confirmatory dry run and preflight (historical; prohibited)

```bash
python3 scripts/run_controlled_open_weight_v6.py \
  --run-id qwen38_27b_v6_confirmatory_20260902 \
  --dry-run

python3 scripts/preflight_controlled_v6.py \
  --run-id qwen38_27b_v6_confirmatory_20260902
```

The paid preflight uses a sentinel scenario/message set/seed that is disjoint
from every official cell and produces no target outcome. It must write exactly
`results/v6_design/confirmatory_paid_preflight.json` and pass all non-overlap,
model, revision, and constrained-choice checks.

## 10. Single official confirmatory run (historical; prohibited)

```bash
python3 scripts/run_controlled_open_weight_v6.py \
  --run-id qwen38_27b_v6_confirmatory_20260902
```

The final checkpoint supplies the selected sample size and every runtime
parameter. Do not pass overrides. If interrupted, use the same command plus
`--resume`. Resume replays the complete existing prefix before model load. A
completed-but-unsealed run is replayed and sealed without constructing the
model; an already sealed run is verified idempotently.

Canonical outputs are under `data/raw/v6_confirmatory/`, with the one launch
receipt at `results/v6_design/launch_receipts/v6_confirmatory.json`.

## 11. Frozen analysis (historical; prohibited)

After pulling and hashing the complete sealed log/manifest:

```bash
python3 scripts/analyze_controlled_v6.py \
  --log data/raw/v6_confirmatory/qwen38_27b_v6_confirmatory_20260902.jsonl \
  --manifest data/raw/v6_confirmatory/qwen38_27b_v6_confirmatory_20260902.manifest.json \
  --checkpoint-spec results/v6_design/final_checkpoint.json \
  --out-dir results/v6_confirmatory \
  --n-boot 5000 \
  --n-perm 10000 \
  --seed 20262004
```

Analysis reconstructs every raw selection, visible history, target probability,
random draw, and choice. It writes a fresh staged table/figure set and publishes
`v6_checkpoint_summary.json` last. Exit zero means valid input, not necessarily
a positive scientific result; the summary's fixed decision gates determine the
result. Exit 2 means invalid provenance/input.

## 12. Final archival checklist

- Preserve all rows and transcripts; do not cherry-pick examples.
- Record model, revision, commit, pod type, wall time, balance before/after,
  exact commands, exit codes, interruptions, and artifact hashes.
- Commit and push raw JSONL, manifests, launch receipts, aggregate results,
  figures, and the final report unless repository size policy requires a
  checksum-backed release artifact for a large file.
- Stop the GPU pod after verified retrieval. Retain or delete its volume only
  after verifying the local and pushed copies.
- Report semantic/quality or validation failure as an instrument limitation;
  report confirmatory failure as a negative behavioral result; report a pass
  only within the bounded claim in `docs/V6_FINAL_PROTOCOL.md`.

Observed archival disposition: no new pod was deployed for V6, no paid V6 GPU was started,
no model/judge output was generated, and there are no experimental transcripts
or metrics to report. The only V6 result is the outcome-independent power
limitation; it is not evidence for or against latent target modelling.
