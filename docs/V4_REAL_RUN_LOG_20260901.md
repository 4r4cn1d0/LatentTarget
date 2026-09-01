# V4 real-model checkpoint run log — 2026-09-01

Status: **completed, analyzed once, artifacts verified locally, pod and tied
volume terminated**.

Locked scientific decision:
`STOP_BEFORE_FREEFORM_OR_MECHANISTIC_SCALING`.

This is the detailed operational and scientific record for the first real-model
V4 controlled-choice checkpoint. It does not reinterpret the failed
confirmatory gate as a success.

## Run identity

- Run ID: `qwen38_27b_v4_checkpoint_20260902`
- Task version: `controlled-choice-v4.0`
- Model: `Qwen/Qwen3.8-27B`
- Immutable model revision:
  `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`
- Experiment checkout:
  `7d715a0b037ebada825e5141078e9b56ed3fa5ba`
- GPU: one NVIDIA A100-SXM4-80GB (81,920 MiB)
- Pod ID: `jn23b1x28qbksx`
- Provider location/type: RunPod secure cloud, US-MD-1
- Full behavioral process start: `2026-09-01T12:09:55+00:00`
- Full behavioral process finish: `2026-09-01T13:33:09+00:00`
- Full-run wall time: 1 hour, 23 minutes, 14 seconds
- Dashboard balance before deployment: `$52.82`
- Dashboard balance after retrieval and analysis: `$50.08`
- Dashboard balance at final termination: `$49.98`
- Final observed balance change: approximately `$2.84`
- Final pod state: terminated; the tied 100 GB volume was deleted
- Stopped 100 GB volume rate before termination: `$0.028/hour`

The balance difference includes pod setup, dependency installation, tests,
model download, two preflight attempts, the full run, analysis, and brief
stopped-volume retention before deletion. It is an observed dashboard delta,
not a separately itemized invoice.

## Frozen design executed

- Conditions: full history, no history, shuffled history, random target, and
  silent target swap.
- Episodes: 360 total.
- Rounds: 20 per episode.
- Generations: 7,200 total.
- Stable conditions: 60 episodes each.
- Swap condition: 120 episodes covering all six ordered target transitions.
- Swap: after round 10, without telling the focal model.
- Held-out candidate paraphrases: rounds 16–20.
- Target response probabilities: 0.72 for a registered-frame match, 0.38 for a
  mismatch, and 0.50 in the random-response condition.
- Generation: greedy, thinking disabled, bfloat16, at most 8 new tokens.
- Activation capture: disabled for the behavioral run.
- Human labeling: none, as requested.

The machine-readable source of truth is
[`behavioral_checkpoint_v4.json`](behavioral_checkpoint_v4.json). The runner
loaded scientific values from that file and rejected drift before model load.

## Chronological engineering log

1. Deployed one A100 SXM 80 GB pod with SSH access and a 100 GB `/workspace`
   volume. Verified the GPU identity, VRAM, driver, and workspace mount.
2. Checked out the then-current prepared artifact commit `db16494` and created a
   system-site-packages virtual environment with the pinned GPU stack.
3. The first PyTorch import failed because the newly pinned torch wheel could
   not find the template-provided `libcusparseLt.so.0`. Exposing the existing
   CUDA wheel library directories through `LD_LIBRARY_PATH` fixed this without
   changing scientific code.
4. Ran all 324 tests on the pod. They passed.
5. Ran the local V4 controls and exact no-weight dry run. The positive and
   negative controls passed, the blind message-bank gate passed, the plan had
   360 episodes and 7,200 generations, and the checkout matched the expected
   commit.
6. The first paid model preflight aborted with native `std::bad_alloc` before a
   generation. Python faulthandler localized this to `torchvision 0.23`, which
   the pod template had compiled for torch 2.8 and which Transformers imported
   through the multimodal processor.
7. Pinned the ABI-compatible wheels `torchvision==0.24.1` and
   `torchaudio==2.9.1` alongside `torch==2.9.1`. Committed and pushed this
   infrastructure-only fix as `7d715a0`.
8. Created a fresh detached worktree at `7d715a0` so the failed-preflight log
   was preserved rather than overwritten. Re-ran all 324 tests and the exact
   dry run from that clean worktree; both passed.
9. Re-ran the preflight. It loaded the immutable checkpoint through
   `AutoModelForMultimodalLM` with `Qwen3VLProcessor`, produced a valid candidate
   number, confirmed an empty structured prompt context and the exact bank
   hash, captured 65 residual-stream states across 64 text blocks at width
   5,120, and reproduced the greedy output exactly under zero-vector steering.
10. Started the frozen behavioral runner in a detached process. Monitoring read
    only process state, GPU utilization, VRAM, and completed episode/record
    counts. No partial outcome metric was inspected.
11. The run exited cleanly after writing 7,200 records. The manifest completion
    gate asserted status `completed`, 360/360 episodes, and 7,200/7,200 rows.
12. Ran the preregistered analysis exactly once with 5,000 bootstrap resamples,
    10,000 sign-flip permutations, and seed `20260902`.
13. Copied the raw log, manifest, preflight, failed-preflight diagnostic,
    package inventory, GPU inventory, stdout logs, tables, and figures to the
    local repository. Local hashes and artifact counts passed.
14. Stopped the GPU. The dashboard showed compute as not running and only the
    stopped volume rate of `$0.028/hour`.
15. After the user confirmed irreversible deletion, terminated pod
    `jn23b1x28qbksx` and its tied 100 GB volume. The pod disappeared from the
    dashboard and the account returned to the no-pods deployment page. Balance
    at termination was `$49.98`; no pod or volume charge remains.

## Verified preflight

- Architecture: `Qwen3_5ForConditionalGeneration`
- Loader: `AutoModelForMultimodalLM`
- Processor: `Qwen3VLProcessor`
- Model revision: exact immutable revision above
- Candidate selection: valid
- Structured context visible to real provider: empty
- Message-bank SHA-256:
  `f352c0a17b8ff3c9fca7543399499e966f9a88a99c5620e051da0c9003d2c0f4`
- Hidden-state shape: `[1, 65, 5120]`
- Text blocks discovered: 64
- Zero-vector steering reproduced unsteered greedy text: yes
- Preflight decision: PASS

The preflight selection itself is a format check, not a scientific data point.

## Confirmatory result

Twelve of thirteen printed gates passed, but the required swap revision
randomization test failed. Therefore the overall result is a scientific STOP.

| Registered quantity | Result |
|---|---:|
| Valid numbered selections | 0.9847 |
| Full-history early match, rounds 1–5 | 0.3833 |
| Full-history held-out late match, rounds 16–20 | 0.5700 |
| Full-history learning gain | 0.1867, 95% bootstrap CI [0.0833, 0.2900] |
| No-history learning gain | approximately 0.0000 |
| Full/no-history difference-in-differences | 0.1867, 95% CI [0.0933, 0.2833], one-sided permutation p = 0.0001 |
| Full minus no-history held-out match | 0.2367, 95% CI [0.1366, 0.3400], p = 0.0001 |
| Full minus shuffled held-out match | 0.3367, 95% CI [0.2300, 0.4400], p = 0.0001 |
| Random-target learning gain | -0.0067 |
| Swap new-target gain | 0.1083, 95% CI [0.0583, 0.1617], p = 0.0001 |
| Swap old-target drop | 0.1050, 95% CI [0.0583, 0.1517] |
| Swap held-out new minus old | approximately 0.0000, 95% CI [-0.1250, 0.1233], p = 0.4983 |
| Episodes meeting the adaptation rule | 43/120 |
| Median rounds to adapt among adapters | 4 |

Stable target-specific learning is strong in this controlled action space:
history improved held-out matching, the effect disappeared with no history and
random responses, and shuffled histories were actively harmful. That is
evidence for feedback-conditioned, target-specific candidate selection.

The stronger target-revision claim did not pass. Although use of the new frame
rose and use of the old frame fell, the new frame did not exceed the old frame
in the held-out post-swap window. This is why probing, steering, and free-form
scaling remain unauthorized by the V4 gate.

## Exploratory diagnosis — cannot rescue the checkpoint

These diagnostics were computed after the locked STOP and are for designing a
new preregistered experiment only.

The model had a strong expertise-frame prior: in no-history rounds it selected
expertise 92.2% of the time, risk 6.5%, and fairness 1.2%. In full-history
held-out rounds it selected the matching frame 24% for fairness, 61% for risk,
and 86% for expertise. Relative to no-history held-out behavior, fairness and
risk improved substantially; expertise had almost no room to improve.

Swap behavior was correspondingly asymmetric:

| Ordered transition | New-frame gain | Old-frame drop | Late new minus old | Adapted episodes |
|---|---:|---:|---:|---:|
| expertise → fairness | 0.03 | 0.15 | -0.81 | 0/20 |
| expertise → risk | 0.15 | 0.19 | -0.60 | 2/20 |
| fairness → expertise | 0.18 | 0.05 | 0.77 | 17/20 |
| fairness → risk | 0.20 | 0.08 | 0.25 | 7/20 |
| risk → expertise | approximately 0.00 | 0.04 | 0.52 | 17/20 |
| risk → fairness | 0.09 | 0.12 | -0.13 | 0/20 |

Aggregated by destination, 34/40 swaps into expertise met the adaptation rule,
9/40 into risk did, and 0/40 into fairness did. This looks less like a symmetric
target-updating mechanism and more like history-dependent movement around a
large expertise default. It is still a useful result: it identifies a concrete
source of sticky target models that the next design must separate from true
revision.

There were 110 invalid raw outputs (1.53%). All were truncated attempts to
explain the participant history, such as `Looking at the history...`, rather
than a single candidate number. The frozen seeded fallback handled them, and
the 98% validity gate narrowly passed. Invalid rates were 0% for no history,
2.0% each for full and shuffled history, 1.25% for random target, and 1.96% for
swap. This history-dependent format failure is a limitation and should be
removed with constrained decoding in the next experiment.

## Numerical gate audit

The run-commit code evaluated `silent_swap_new_over_old` using a raw
floating-point `mean > 0.0`. The stored mean was
`7.401486830834377e-18`, numerical residue around zero, so that effect-size gate
printed PASS. The inferential gate still failed with p = 0.4983 and the overall
STOP was unaffected. After preserving the original run artifacts and commit,
the code was patched to require a positive effect beyond `1e-12`; a regression
test covers this case. The V4 preregistered analysis was not rerun or replaced.

## What the next behavioral design should change

1. Use grammar- or logits-constrained decoding so only `1`, `2`, or `3` can be
   emitted. Do not rely on a fallback for the primary outcome.
2. Calibrate candidate banks before the next real run so no-history frame
   selection is approximately balanced. Candidate semantics should remain
   independently validated, but surface attractiveness must not make one frame
   the default action.
3. Preregister a baseline-adjusted revision contrast:
   `(late_new - late_old) - (pre_new - pre_old)`. The current final-level test
   is confounded by large pre-swap frame priors. This alternative is post-hoc
   for V4 and cannot rescue it.
4. Make ordered transition the analysis stratum. Require evidence across
   several transition directions, especially away from the dominant baseline
   frame, rather than relying only on an aggregate over six asymmetric swaps.
5. Increase or rebalance post-swap evidence only after a power calculation for
   the revised co-primary. Do not merely add rounds until significance appears.
6. Replicate the redesigned behavioral result on another current open-weight
   model before activation capture. Only a passed, replicated behavioral gate
   should license probes or steering.

## Artifact integrity

- Raw JSONL SHA-256:
  `d7e3cdf26ba3d8c3c3c5ea48667aa69c79f44786c8a92e124db495158e639a33`
- Manifest SHA-256:
  `b92f6d02b33f7874141dccd0a3086c9802fa918a9ffe88c9512b4a7484f80b66`
- Local row count: 7,200
- Local manifest status: completed
- Local episode count: 360
- Figures: five PNG and five PDF files
- Tables: three CSV files
- Package and GPU inventories: retained
- Successful and failed preflight logs: retained
- RunPod key stored in repository or artifacts: no

Primary artifacts:

- [`PILOT_REPORT_V4_REAL.md`](../PILOT_REPORT_V4_REAL.md)
- [`v4_checkpoint_summary.json`](../results/v4_real/checkpoint/v4_checkpoint_summary.json)
- [`v4_stable_conditions.csv`](../results/v4_real/checkpoint/tables/v4_stable_conditions.csv)
- [`v4_swap_episodes.csv`](../results/v4_real/checkpoint/tables/v4_swap_episodes.csv)
- [`preflight.json`](../results/v4_real/preflight.json)
- [`analysis.stdout.log`](../results/v4_real/analysis.stdout.log)
- [`raw-checksums.sha256`](../results/v4_real/raw-checksums.sha256)

The raw JSONL is retained locally under `data/raw/` and intentionally ignored by
Git because it is 56 MB. Its manifest, checksums, processed outputs, and full
fixed-rule transcripts are versioned.
