# V4 controlled checkpoint runbook

Status: **executed successfully through the locked analysis and STOP rule**.
This remains the exact historical procedure. Results, costs, hashes, and
failures are recorded in
[`V4_REAL_RUN_LOG_20260901.md`](V4_REAL_RUN_LOG_20260901.md).

This runbook is intentionally mechanical. The scientific source of truth is
`docs/behavioral_checkpoint_v4.json`; the GPU runner reads that file and exits
before model loading if any checked setting has drifted.

## 1. Frozen run

| item | frozen value |
|---|---|
| model | `Qwen/Qwen3.8-27B` |
| immutable revision | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` |
| dtype | bfloat16 |
| decoding | greedy, thinking disabled, maximum 8 new tokens |
| target probabilities | match 0.72, mismatch 0.38, random 0.50 |
| conditions | full history, no history, shuffled history, random target, silent swap |
| horizon | 20 rounds; swap after 10; held-out messages in rounds 16–20 |
| sample | 20 scenario seeds, 360 episodes, 7,200 generations |
| activation capture | off |

The blind bank check in
`results/v4_design/message_bank_validation/summary.json` must have `pass=true`
and the same SHA-256 as the checkpoint. The runner verifies both automatically.

## 2. Local release gate

Run from a clean checkout:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python scripts/validate_controlled_v4.py
.venv/bin/python scripts/run_controlled_open_weight.py \
  --run-id qwen38_27b_v4_checkpoint_20260902 --dry-run
git status --short
git rev-parse HEAD
```

Required result: tests pass, local controls print `PASS`, dry run prints
`DRY RUN PASSED`, and the checkout has no uncommitted scientific changes. Save
the commit printed by `git rev-parse HEAD`; the final manifest records it.

## 3. Cost and safety envelope

An A100 80 GB is sufficient for the pinned 27B bfloat16 checkpoint. RunPod's
published September 2026 rates list roughly `$1.19/hour` for Community A100
PCIe and `$1.39/hour` for Secure A100 PCIe; capacity and the dashboard quote
remain authoritative:

- <https://www.runpod.io/pricing>
- <https://www.runpod.io/gpu-models/a100>

The V3 run needed 41 minutes for 312 longer free-form generations. V4 has much
shorter outputs but 7,200 increasingly long prompts, so the honest engineering
range before benchmarking is **6–20 GPU-hours**: approximately `$7–$28` at
those rates, plus cold-start/storage overhead. Use a **$35 hard budget**. If a
timing projection after the preflight exceeds that cap, terminate and report;
do not silently reduce the frozen sample.

Never place the RunPod API key in a command transcript, repository file,
manifest, shell history, or artifact. Use an environment variable or a
mode-0600 temporary credential file outside the repository, and remove it
after pod termination.

## 4. Pod setup

Use an 80 GB A100 pod with a persistent `/workspace` volume. Then:

```bash
cd /workspace
git clone https://github.com/4r4cn1d0/LatentTarget.git
cd LatentTarget
git status --short
git rev-parse HEAD
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-pod.txt
.venv/bin/python -m pytest -q
export HF_HOME=/workspace/huggingface
export TRANSFORMERS_CACHE=/workspace/huggingface
```

The commit must equal the clean local release commit. Do not run from a branch
with uncommitted edits.

## 5. One-generation paid preflight

```bash
.venv/bin/python scripts/preflight_open_weight.py \
  --model Qwen/Qwen3.8-27B \
  --revision 1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0 \
  --controlled-v4-spec docs/behavioral_checkpoint_v4.json \
  --dtype bfloat16 \
  --seed 20260902 \
  --out results/v4_real/preflight.json
```

Proceed only if all of these hold:

- model/revision and message-bank hash match the frozen spec;
- the actual first-round V4 prompt carries no structured context;
- the model returns a valid `1`, `2`, or `3`;
- activation capture is structurally valid for the loaded architecture;
- zero-vector steering reproduces the greedy output exactly.

This preflight is a format/loader check. Do not interpret its candidate choice
as a result.

## 6. Frozen behavioral execution

```bash
.venv/bin/python scripts/run_controlled_open_weight.py \
  --checkpoint-spec docs/behavioral_checkpoint_v4.json \
  --run-id qwen38_27b_v4_checkpoint_20260902 \
  --out-dir data/raw \
  --quiet
```

The command intentionally omits every scientific value; they are loaded from
the checkpoint. The runner validates all values and the manipulation gate
before the first generation. Progress output contains completion counters only,
not choices, rewards, or partial metrics.

If the process is interrupted after one or more complete episodes, use the
identical checkout and provider settings:

```bash
.venv/bin/python scripts/run_controlled_open_weight.py \
  --checkpoint-spec docs/behavioral_checkpoint_v4.json \
  --run-id qwen38_27b_v4_checkpoint_20260902 \
  --out-dir data/raw \
  --quiet --resume
```

Resume refuses config/provider drift, duplicate rounds, unknown episodes, and
partial episodes. Never delete or truncate a partial log to force continuation;
preserve it and use a new run ID if the fail-closed check rejects it.

## 7. Completion and one-shot analysis

Before looking at any outcome metric:

```bash
wc -l data/raw/qwen38_27b_v4_checkpoint_20260902.jsonl
.venv/bin/python - <<'PY'
import json
p = 'data/raw/qwen38_27b_v4_checkpoint_20260902.manifest.json'
d = json.load(open(p, encoding='utf-8'))
assert d['run_status'] == 'completed'
assert d['n_records'] == d['expected_n_records'] == 7200
assert d['n_episodes'] == d['expected_n_episodes'] == 360
print('manifest completion gate: PASS')
PY
sha256sum data/raw/qwen38_27b_v4_checkpoint_20260902.jsonl \
  data/raw/qwen38_27b_v4_checkpoint_20260902.manifest.json
```

Then run the frozen analysis exactly once:

```bash
.venv/bin/python scripts/analyze_controlled_v4.py \
  --log data/raw/qwen38_27b_v4_checkpoint_20260902.jsonl \
  --manifest data/raw/qwen38_27b_v4_checkpoint_20260902.manifest.json \
  --checkpoint-spec docs/behavioral_checkpoint_v4.json \
  --out-dir results/v4_real/checkpoint \
  --n-boot 5000 --n-perm 10000 --seed 20260902
```

Copy the raw log, manifest, preflight, tables, figures, stdout/stderr log,
package versions, GPU identity, pod timestamps, and checksums off the pod before
termination. Verify local hashes, terminate the pod, and confirm zero active
pods.

## 8. Decision boundary

The only scientific decisions are:

- `GO_FOR_FREEFORM_AND_MECHANISTIC_PILOTS` if every design, effect, and
  inference gate passes;
- `STOP_BEFORE_FREEFORM_OR_MECHANISTIC_SCALING` otherwise.

Elicited predictions, a visually attractive curve, one target type, or a
post-hoc alternative analysis cannot rescue a failed primary gate. A pass
supports feedback-conditioned target-specific candidate selection; it does not
yet prove an explicit latent representation.
