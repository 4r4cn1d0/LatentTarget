# V5 target-free calibration run — 2026-09-01

## Locked outcome

**`STOP_CALIBRATION_INSTRUMENT_FAILED`**

The paid V5 pool calibration and separately seeded selected-bank validation
both completed cleanly. All 1,152 focal outputs were exact choices in
`{"1", "2", "3"}`, every schedule/integrity audit passed, and neither run
contained a target simulator, interaction history, target identity, feedback,
or activation capture.

The selected bank nevertheless failed every frozen balance section. Therefore:

- no validated V5 bank was created;
- final power was not run;
- `docs/behavioral_checkpoint_v5.json` was not created;
- no confirmatory target-learning outcome was generated;
- no free-form replication, activation capture, probe, steering experiment, or
  outcome-dependent sample extension was run.

This is a negative result about the **measurement instrument**, not evidence
for or against dynamic target modelling.

## Completed and verified stages

| Stage | Verified result |
| --- | --- |
| Repository | Detached checkout of reviewed commit `c426c461e537f3586d20403b5aab4c51dca127da` |
| Hardware | NVIDIA A100-SXM4-80GB; 81,920 MiB VRAM; driver 580.159.04 |
| Runtime | Python 3.12.3, PyTorch 2.9.1+cu128, CUDA 12.8, Transformers 5.16.1 |
| Pod tests | 351 passed in 168.30 seconds; bytecode compilation passed |
| Pool dry run | 576 prompts; target/history absent; bank hash, schedule, and frozen protocol passed |
| Pool calibration | 576/576 strict outputs; completed manifest and raw JSONL |
| Selection | Artifact audit passed; deterministic pending bank and report written |
| Validation dry run | 576 prompts under independent seed `20261002`; all pre-load gates passed |
| Selected-bank validation | 576/576 strict outputs; completed manifest and raw JSONL |
| Finalizer | Exited with code 2 and `SELECTED BANK VALIDATION FAILED`; final bank correctly absent |
| Retrieval | All seven paid artifacts copied locally and SHA-256 checked |
| Shutdown | GPU stopped; dashboard changed to `$0.00/hr` compute |

The disposable virtual environment was initially created under `/workspace`,
where package extraction was I/O-bound. That install process was stopped before
model inference and replaced with `/opt/latenttarget-venv` on the pod's local
container disk. The exact model cache and every scientific artifact stayed on
the persistent `/workspace` volume. This changed no scientific input or code.

## Frozen inputs

- Focal model: `Qwen/Qwen3.8-27B`
- Immutable revision:
  `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`
- Model dtype: bfloat16
- Decoding: non-thinking, deterministic, constrained exactly to `1|2|3`, no
  fallback, two-token cap
- Candidate pool canonical SHA-256:
  `73a404a79bb5a5bfcaed112638143c70c9e48aff710dff15b0e57f4f95989478`
- Frozen protocol file SHA-256:
  `2e371f0431bce623c2d2d0b1bdb496cf13833d8beeaa8c1170063d3d11f05745`
- Pool calibration seed: `20261001`
- Independent selected-bank validation seed: `20261002`
- Frozen balance gate: every frame share in `[0.25, 0.42]` and
  max-minus-min gap at most `0.15`, separately for overall, development, and
  held-out rows

The exact protocol remains unchanged in `docs/v5_calibration_protocol.json`.

## Exact commands

The pod used the reviewed repository without modifications:

```bash
git checkout --detach c426c461e537f3586d20403b5aab4c51dca127da
python -m venv /opt/latenttarget-venv
/opt/latenttarget-venv/bin/python -m pip install -r requirements.txt -r requirements-pod.txt
/opt/latenttarget-venv/bin/python -m compileall -q config.py src scripts tests
/opt/latenttarget-venv/bin/python -m pytest -q
```

For every model command, `HF_HOME` and `TRANSFORMERS_CACHE` pointed to
`/workspace/.cache/huggingface` and the process ran from
`/workspace/LatentTarget`.

```bash
/opt/latenttarget-venv/bin/python scripts/run_v5_calibration.py \
  --bank data/v5/v5_candidate_pool_v1.json \
  --mode pool_calibration \
  --run-id qwen38_27b_v5_pool_calibration_20260901 \
  --dry-run

/opt/latenttarget-venv/bin/python scripts/run_v5_calibration.py \
  --bank data/v5/v5_candidate_pool_v1.json \
  --mode pool_calibration \
  --run-id qwen38_27b_v5_pool_calibration_20260901 \
  --out-dir data/calibration

/opt/latenttarget-venv/bin/python scripts/select_v5_bank.py \
  --pool data/v5/v5_candidate_pool_v1.json \
  --calibration-log data/calibration/qwen38_27b_v5_pool_calibration_20260901.jsonl \
  --calibration-manifest data/calibration/qwen38_27b_v5_pool_calibration_20260901.manifest.json \
  --semantic-validation results/v5_design/semantic_validation/summary.json \
  --bank-out data/v5/v5_selected_bank_pending.json \
  --report-out results/v5_design/bank_selection/report.json

/opt/latenttarget-venv/bin/python scripts/run_v5_calibration.py \
  --bank data/v5/v5_selected_bank_pending.json \
  --mode selected_bank_validation \
  --run-id qwen38_27b_v5_selected_bank_validation_20260901 \
  --dry-run

/opt/latenttarget-venv/bin/python scripts/run_v5_calibration.py \
  --bank data/v5/v5_selected_bank_pending.json \
  --mode selected_bank_validation \
  --run-id qwen38_27b_v5_selected_bank_validation_20260901 \
  --out-dir data/calibration

/opt/latenttarget-venv/bin/python scripts/finalize_v5_bank.py \
  --pending-bank data/v5/v5_selected_bank_pending.json \
  --validation-log data/calibration/qwen38_27b_v5_selected_bank_validation_20260901.jsonl \
  --validation-manifest data/calibration/qwen38_27b_v5_selected_bank_validation_20260901.manifest.json \
  --validation-out results/v5_design/bank_validation/summary.json \
  --final-bank-out data/v5/v5_selected_bank_validated.json
```

The final command intentionally returned exit code 2. This is the registered
scientific stop path, not a software crash.

## Results

### Frame-choice balance

| Sample | Fairness | Risk | Expertise | Gap | Frozen gate |
| --- | ---: | ---: | ---: | ---: | --- |
| Pool calibration, overall (576) | 45 / 7.8% | 196 / 34.0% | 335 / 58.2% | 50.3 pp | Diagnostic only; strongly imbalanced |
| Selected-bank validation, overall (576) | 79 / 13.7% | 197 / 34.2% | 300 / 52.1% | 38.4 pp | **FAIL** |
| Selected-bank validation, development (432) | 46 / 10.6% | 135 / 31.2% | 251 / 58.1% | 47.5 pp | **FAIL** |
| Selected-bank validation, held-out (144) | 33 / 22.9% | 62 / 43.1% | 49 / 34.0% | 20.1 pp | **FAIL** |

The selected bank improved the overall fairness share from 7.8% to 13.7%, but
that remained far below the frozen 25% floor. Overall and development expertise
were above the 42% ceiling. In held-out rows, fairness was below the floor and
risk was above the ceiling. No section was close enough to pass the 15-point
gap rule.

### What the selector already warned us about

The exhaustive subset selector minimized marginal per-candidate selection-rate
gaps. Its best development gap was `0.4259`; its best held-out gap was
`0.2292`, both above the frozen `0.15` limit. The frozen implementation did not
make those heuristic values an early stopping rule, so it proceeded to the
independent validation.

These values are not normalized predictions of the joint selected-bank choice
shares: each candidate's marginal rate was measured against different
co-presented candidates and contexts. They therefore do **not** prove that no
subset could ever pass. They were, however, a strong warning that the pool did
not contain enough overlap between attractive fairness, risk, and expertise
messages. A future selector should not spend a validation run when its own
cross-validated objective is this far outside the desired region.

### Residual numeric-position preference

| Run | Slot 1 | Slot 2 | Slot 3 |
| --- | ---: | ---: | ---: |
| Pool calibration | 17.0% | 41.7% | 41.3% |
| Selected-bank validation | 22.2% | 36.3% | 41.5% |

Every candidate was exposed equally often in all three slots, and all frame
slots were counterbalanced, so this preference cannot by itself create the
aggregate frame imbalance. It does show that the focal choice instrument has a
large position effect. Future calibration should estimate each candidate triad
under all six within-scenario permutations, rather than relying only on global
candidate-by-slot balance.

The diagnostic data and publication figure are in
`results/v5_design/calibration_gate/`.

## Interpretation

1. **Semantic validity was not the problem.** Two blind machine judges had
   previously recovered all 42 intended frames. That manipulation check shows
   that the messages express their registered frames; it does not make the
   frames equally attractive to Qwen.
2. **The V4 expertise prior persisted.** With no target and no feedback, Qwen
   chose expertise-framed candidates 58.2% of the time in the full pool and
   52.1% in independent selected-bank validation.
3. **Marginal template selection was an inadequate optimization target.** The
   focal model chooses among a triad. Candidate utility depends on scenario,
   slot, and the other two candidates; independently averaged template rates
   do not fully predict a newly composed triad bank.
4. **The fail-closed design worked.** The undesirable result was preserved,
   the final bank was not written, and no confirmatory hypothesis test was
   exposed to a known-bad instrument.
5. **There is no V5 target-modelling result.** These runs contained neither a
   target nor interaction history. They only measured baseline candidate
   choice.

## What should change before another paid run

The V5 result must remain immutable. A new version should be called V6 and use
new development and independent-validation seeds.

1. Expand the semantically valid candidate pool, especially with stronger but
   still natural fairness arguments and weaker/non-dominating expertise
   arguments. Add an independent quality/fluency gate so balancing does not
   produce visibly bad messages.
2. Calibrate and select **whole triads**, not isolated templates. Estimate
   scenario, slot, candidate, and co-candidate effects from development data,
   then optimize the actual scheduled triads and aggregate shares.
3. Evaluate each development triad across all six slot permutations on the
   same scenario. Preserve the unlabelled `1|2|3` output and exact decoding.
4. Add a fail-fast cross-validation gate before independent validation. It
   should require every cross-validation fold to meet a pre-frozen support
   floor and a substantially smaller frame gap. Marginal heuristic gaps must
   be labeled as diagnostics, not joint probabilities.
5. Lock the selected triads and run exactly one fresh target-free validation
   seed. Do not reuse V5 validation outcomes as V6's independent gate.
6. Keep baseline-adjusted history and swap contrasts, all six ordered
   transitions, no-history, shuffled-history, and random-response controls.
   Raw equal frame shares are an instrument requirement, not the scientific
   outcome.
7. Recheck the newest suitable open-weight checkpoint immediately before any
   future paid launch. Do not substitute an older model merely for convenience.

Only after that independent gate passes should final exact power be recomputed
and a new behavioral checkpoint be offered for review.

## Cost and pod state

- RunPod pod: `latenttarget-v5-calibration`
- Pod ID: `vqkuoeugozgfhj`
- Hardware: one on-demand A100 SXM 80 GB
- Checkout rate shown at launch: approximately `$1.60/hour` total
  (`$1.59/hour` GPU plus storage)
- Balance before deployment: `$49.98`
- Balance observed immediately before shutdown: `$48.22`
- Observed debit: approximately **`$1.76`**
- GPU state after retrieval: stopped, dashboard compute rate `$0.00/hour`
- A tied 100 GB network volume remains so the 52 GB immutable model cache and
  pod-side artifacts are recoverable. Permanent pod/volume termination is a
  separate destructive action and was not performed without confirmation.

## Artifact hashes

| Artifact | SHA-256 |
| --- | --- |
| Pool raw JSONL | `6ae514070de33be0bb2faa5cb6b5e499736b3c7077d86a754b430e581403e3cb` |
| Pool manifest | `f2f05407a6d5da3db9998bd74210edbb73943d1c8e6fd173ddd14cd70be1410a` |
| Validation raw JSONL | `4141622bfd6d35b54513e36a4eabdf6b7ab1f5b0d2e019997d71704da5e39120` |
| Validation manifest | `c585579731a9dd5745edb955a83838a9e5b778098241651e19750272828be54e` |
| Pending selected bank | `54d77d976fcf66e82363d318d2043db0bdd62cc02208f68d5d3af2a4471ac417` |
| Selection report | `707b70de1167ca11046aac6dc1a486ba1b293481c54654d57c3e7b637e4254c9` |
| Validation summary | `aaf81872b71004ba77afec7f51b77cfa51933b50332f30bc5f5c92c7af923ad1` |

The two raw logs are intentionally retained because the eventual V5 freezer
was designed to hash them directly. They are calibration evidence, not
confirmatory target-learning data.
