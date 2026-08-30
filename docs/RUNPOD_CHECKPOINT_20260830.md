# RunPod checkpoint — 2026-08-30

## Scope and decision boundary

The researcher explicitly authorized paid RunPod work on 2026-08-30. This was
a bounded engineering and baseline checkpoint, not the blocked v2 behavioral
experiment. It generated no new target outcomes and did not run shuffled
history, random responses, target swaps, a probe, or non-zero steering.

The tasks were frozen before the pod was created:

1. Reproduce the complete repository test suite on the GPU machine.
2. Run one bfloat16 generation with all-layer activation capture and the
   zero-vector steering control.
3. While the weights were cached, run the already-planned direct-elicitation
   baseline over the immutable 192-row v1 pilot.
4. Pull artifacts and terminate the pod in the same work session.

## Infrastructure and cost

| field | value |
|---|---|
| provider | RunPod Community Cloud |
| pod name | `latenttarget-preflight-20260830` |
| pod ID | `02it5s4m02adlo` |
| GPU | NVIDIA A100 80GB PCIe |
| advertised compute rate | `$1.19/hour` |
| image | `runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2404` |
| pod created | `2026-08-30T14:27:21Z` |
| termination confirmed | approximately `2026-08-30T15:05Z` |
| active pods after termination | `0` |
| estimated compute charge | at most about `$0.75` for roughly 38 minutes; the RunPod billing ledger is authoritative |

The cold Docker image pull and extraction consumed about 20 minutes. The public
model download took 6 minutes 48 seconds. No Hugging Face token was needed.
The RunPod API key was held only in mode-0600 temporary curl configuration
files outside the repository; those files were deleted after termination.

## Frozen software environment

| component | value |
|---|---|
| repository commit | `c3f7b285f7a01ccfac31b8dd6944ac1df18f07e5` |
| Python | `3.12.3` |
| PyTorch | `2.9.1+cu128` |
| Transformers | `5.16.1` |
| Accelerate | `1.14.0` |
| CUDA available | `True` |
| focal checkpoint | `Qwen/Qwen3.8-27B` |
| dtype | `bfloat16` |
| thinking mode | disabled |

The official Hugging Face repository was rechecked before rental. It remained
the current official dense 27B Qwen release, rather than an older convenience
checkpoint: <https://huggingface.co/Qwen/Qwen3.8-27B>.

## Commands and verification

Credentials, host, and transient port arguments are omitted. The substantive
commands were:

```bash
git clone --depth 1 https://github.com/4r4cn1d0/LatentTarget.git
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-pod.txt
.venv/bin/python -m pytest -q

.venv/bin/python scripts/preflight_open_weight.py \
  --model Qwen/Qwen3.8-27B \
  --out results/tables/runpod_preflight_20260830.json

.venv/bin/python scripts/run_black_box_baseline.py \
  --log data/raw/qwen38_27b_gonogo_20260826.jsonl \
  --model Qwen/Qwen3.8-27B \
  --out data/processed/qwen38_27b_gonogo_20260826.black_box.json \
  --conditions full_history no_history
```

Verified results:

- `254 passed in 60.65s` on the pod.
- Preflight status: `ok=true`, with no issues.
- Architecture: `Qwen3_5ForConditionalGeneration`, loaded through
  `AutoModelForMultimodalLM`.
- 64 text blocks, residual width 5120, activation shape `[1, 65, 5120]`.
- Generated text: `Option A is worth considering.`
- Zero-vector steering at hidden-state index 32 produced the identical text.
- The model download and load used the official bfloat16 checkpoint, not FP8.

Artifact hashes:

```text
89129176e1c22e5a1dbd6d7502e13a4e725dae64651843cc36da261d223c5e00  results/tables/runpod_preflight_20260830.json
72627e79ecec2ddb3ac5c83dc1b13da4a8b2bc5114d51cb16804f73e62fbf89f  data/processed/qwen38_27b_gonogo_20260826.black_box.json
f7edd3233c5f6fd645ee7ae28b3632411b2b64d57e6b4c7c398219db8eb288d5  data/processed/qwen38_27b_gonogo_20260826.black_box.json.manifest.json
```

## Direct-elicitation result

The black-box baseline asked the focal model, in a separate deterministic pass,
which frame the participant appeared to respond to. It covered all 192 frozen
prompts: 96 full-history and 96 no-history.

| condition | rows | accuracy | answer distribution |
|---|---:|---:|---|
| full history | 96 | 0.000 | 96 `unknown` |
| no history | 96 | 0.000 | 96 `unknown` |
| total | 192 | 0.000 | 192 `unknown` |

This is a black-box null, not evidence against all latent representations. It
does show that direct elicitation, as currently phrased, does not expose a
target estimate in the v1 histories. It also makes any later probe result more
interesting only if that probe clears the transcript/Bayesian controls.

### Auditability defect discovered

The original baseline script retained normalized labels but discarded raw model
strings. A fixed-rule audit reran three full-history round-8 prompts—one per
target type—and all three raw answers were exactly `unknown`. That supports the
parser diagnosis for those rows, but it cannot retroactively prove the other
189 raw strings.

The code was therefore changed after the pod run so future baselines atomically
checkpoint both normalized labels and exact raw answers. The old artifact is
preserved unchanged. The three-row diagnostic is in
`results/tables/qwen38_27b_black_box_raw_audit_20260830.json`.

## Scientific status after this run

What advanced:

- The newest selected open-weight model still loads under current libraries.
- Activation capture, layer mapping, and zero steering work on the exact current
  repository commit.
- The planned direct-elicitation baseline has an honest null result.

What did not advance:

- The blind human sheet remains incomplete.
- The v1 fairness/expertise reward-construct defects remain.
- No v2 scorer has been calibrated or frozen.
- No new behavioral controls or swap episodes were generated.
- No real probe or non-zero steering experiment was run.

The next paid behavioral run remains the two-seed, 312-generation v2 checkpoint,
and remains conditional on the human measurement and scorer-calibration gates.
