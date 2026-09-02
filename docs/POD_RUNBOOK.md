# GPU pod runbook

Everything you need to run the open-weight arm. **Pod setup does not count
against your 20 hours** (Neel's doc: "generic tech set up, like renting and
setting up a cloud GPU"), so don't rush it and don't count it.

## 0. Pick a model, then a box

Two failure modes from Neel's common-mistakes list, and they pull in opposite
directions:

> Only studying **old models** (GPT-2, Pythia, Gemma 2)

> Working with a model that's just **way too dumb for the task**

His recommended defaults: *"The Qwen 3.5 and 3.6 family are good default models,
especially dense ones like 4B, 9B and 27B"*, and DeepSeek V4 Flash if you want a
highly capable model with J-Lenses available.

**Model IDs/loading checked against the official Hugging Face pages,
2026-08-25.** Two traps:

- There is **no `-Instruct` suffix** on the primary repo; use the exact model ID
  `Qwen/Qwen3.8-27B`.
- They are **multimodal** (`Qwen3_5ForConditionalGeneration`, tagged
  `image-text-to-text`), so `AutoModelForCausalLM` alone is not sufficient.
  `hf_provider.py` follows the current `AutoProcessor` plus
  `AutoModelForMultimodalLM` path first, retains documented fallbacks, and
  records the actual processor/model class in the manifest.

| model | dense/MoE | bf16 VRAM | verdict |
|---|---|--:|---|
| **`Qwen/Qwen3.8-27B`** | dense 27B | ~56 GB | **primary subject.** Newest official dense release verified 2026-08-25 |

**Recommended:** use `Qwen/Qwen3.8-27B` only for the scoped study. If a model
replication is later justified, re-check the official open-weight landscape and
choose a then-current independently developed model; do not fall back to an old
small checkpoint merely because it is cheap.

**Box:** 27B bf16 needs ~56 GB plus headroom for the prompt → **A100 80GB or
H100 80GB**. Spot and community instances are fine — every episode is written to JSONL as it
completes, so an interruption costs one run, not the dataset.

## 1. Bring-up

```bash
apt-get update && apt-get install -y git tmux ripgrep
git clone https://github.com/4r4cn1d0/LatentTarget && cd LatentTarget
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-pod.txt

pytest -q                          # no GPU/network needed. MUST pass.
python scripts/validate_pipeline.py    # metric's own positive/negative controls
```

If either fails on the pod but passed locally, stop and find out why before
generating any data.

## 2. GO / NO-GO gate — does this model adapt at all?

**Do not skip this.** *"Trying to investigate some phenomena without checking if
it's really there"* is on Neel's list of common mistakes, and a probe trained on
a model that isn't adapting decodes nothing.

```bash
tmux new -s check
python scripts/preflight_open_weight.py --model Qwen/Qwen3.8-27B

python scripts/run_open_weight.py --model Qwen/Qwen3.8-27B \
    --conditions full_history no_history --episodes 4 --rounds 8 --no-capture
python scripts/analyze_results.py --log data/raw/openweight_*.jsonl
```

- **GO:** `full_history` is directionally more adaptive than `no_history`, and
  complete transcripts show genuine framing rather than formatting or keyword
  dumping. Four seeds are a gate, not a significance test.
- **NO-GO:** both flat → inspect transcripts, then run at most one predeclared
  easier-to-detect environment
  (`--w-match 3.5 --logit-noise-sd 0.4`). If it still won't budge, that is your
  result: *"Qwen3.8-27B does not adapt its persuasion framing to feedback in
  this setting"*, with the mock WSLS agent as proof the measurement can detect
  adaptation when it exists. Write that up — it's honest and it's interesting.

**Before moving on: read 5 transcripts.**

```bash
python scripts/print_transcripts.py --log data/raw/openweight_*.jsonl --random 5 --seed 0 --prompts
```

## 3. Full run with activation capture

```bash
tmux new -s main
python scripts/run_open_weight.py --model Qwen/Qwen3.8-27B \
    --conditions full_history no_history shuffled_history random_target swap \
    --episodes 8 --rounds 8 --swap-round 5 \
    --acts data/processed/acts_qwen38_27b.npz
```

With 8 episode seeds: 96 stable/control episodes plus 48 fully-counterbalanced
swap episodes = **144 episodes / 1,248 generations**. Qwen3.8-27B has 64
language layers and width 5120, so all-layer float16 activations are roughly
1,248 × 65 × 5,120 × 2 bytes ≈ **830 MB**. Use
`--layer-stride 2` to halve it if disk is tight.

The provider disables Qwen thinking mode by default and uses the official
non-thinking sampling defaults (`temperature=0.7`, `top_p=0.8`, `top_k=20`).
Do not pass `--enable-thinking` in the preregistered run: generated reasoning
would contaminate both the “short message” and the interpretation of the
pre-generation activation.

Run the evidence-only comparator immediately; it costs no generations:

```bash
python scripts/analyze_bayesian_observer.py --log data/raw/openweight_*.jsonl \
    --hazards 0.10 0 0.05 0.20
```

## 4. Judge pass

Serve a current, independently selected open-weight judge over an
OpenAI-compatible endpoint — the existing provider talks to it unmodified.
Freeze its exact ID in the run manifest after checking the official model card;
do not quietly choose the focal model because it is already downloaded.

```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server \
    --model <CURRENT_INDEPENDENT_JUDGE_ID> --port 8000 &

export OPENAI_BASE_URL=http://localhost:8000/v1
export OPENAI_API_KEY=EMPTY          # vLLM ignores it; our provider requires non-empty

python scripts/analyze_results.py --log data/raw/openweight_*.jsonl \
    --reclassify llm --judge-provider openai --judge-model <CURRENT_INDEPENDENT_JUDGE_ID> \
    --prefix llm_
```

Use a **different** model from the focal one. Judging your own outputs with the
same weights shares idiosyncrasies and is a confound you'd have to report.

Then hand-label a sample and check the judge agrees with you:

```bash
python scripts/make_label_sheet.py --log data/processed/openweight_*.reclassified.jsonl --n 40
# fill in human_label, then:
python scripts/score_labels.py --sheet data/processed/label_sheet.csv
```

## 5. Baselines before the probe

Run the black-box baseline first. If asking the model outright works as well as
a probe, the probe hasn't earned its complexity — and that is a perfectly good
finding to report.

```bash
python scripts/run_black_box_baseline.py \
    --log data/raw/openweight_*.jsonl --model Qwen/Qwen3.8-27B \
    --out data/processed/black_box.json
```

## 6. Probe

```bash
python scripts/train_probe.py \
    --log data/processed/openweight_*.reclassified.jsonl \
    --acts data/processed/acts_qwen38_27b.npz \
    --black-box-json data/processed/black_box.json \
    --probe-out data/processed/target_probe.npz
```

Prints, in order: visible-evidence baselines → train/dev layer and L2 selection →
shuffled-label null → untouched-test accuracy → baseline-corrected swap
trajectories → context-leakage diagnostics. Writes the fitted probe,
`fig8_probe_layer_sweep.png`, `fig9_probe_vs_behaviour.png`,
`probe_trajectory.csv`, and `probe_summary.json`.

Training uses only stable typed **full-history** episodes. Layer/L2 selection
uses train/dev episodes; test, swap, shuffled, no-history and random-target
episodes never enter fitting.

## 7. Steering (only if the probe clears its baselines)

```bash
python scripts/run_steering.py \
    --log data/processed/openweight_*.reclassified.jsonl \
    --probe data/processed/target_probe.npz \
    --probe-summary results/tables/probe_summary.json \
    --model Qwen/Qwen3.8-27B \
    --out data/raw/steering_qwen38_27b.jsonl

python scripts/analyze_steering.py --log data/raw/steering_qwen38_27b.jsonl
```

This runs predeclared coefficients 1/3/6 with target, opposite, zero, and
random norm-matched controls under paired seeds. Do not tune coefficients on
the untouched test prompts and then report the same prompts as confirmatory.

## 8. Pull artifacts back

```bash
# from your laptop
rsync -avz --progress pod:LatentTarget/{data,results,PILOT_REPORT.md} ./
```

Pull `data/raw/*.jsonl` and `results/` always. The `.npz` is large — pull it if
you want to re-run probes locally, otherwise leave it and keep the summaries.

## Recovery

Killed mid-run? Keep the partial JSONL and restart with a **new** `--run-id`.
The runner refuses to append to a nonempty run because doing so would duplicate
episodes and invalidate uncertainty estimates. Prefer several small runs with
distinct run IDs on interruptible instances; `analyze_results.py --log a.jsonl
b.jsonl` accepts multiple logs. Before combining, verify manifests agree on
model, prompts, target parameters, classifier, conditions, and seed design.

## Cost sketch (Runpod list prices checked 2026-08-25)

| step | GPU-hours |
|---|--:|
| one-generation preflight + GO/NO-GO | ~0.5–1.0 |
| Full run (144 episodes, capture) | ~3–5 |
| Judge pass (1000 short classifications, 27B) | ~0.5 |
| Black-box + steering passes | ~1–3 |
| Probe/analysis | CPU, minutes |

Official Runpod on-demand list prices were **$1.19/hour for A100 PCIe community
($1.39 secure)** and **$1.99/hour for H100 PCIe community ($2.89 secure)** when
checked. A 27B bf16 model does not fit a 48 GB L40S, so budget an 80 GB A100/H100.
At 5–9 total GPU-hours, compute is approximately **$5.95–$12.51 across the
listed A100 PCIe community/secure rates** or **$9.95–$26.01 across H100 PCIe
community/secure rates**, before storage/tax and depending on availability.
These are formulas from current list prices, not a promised bill;
check [Runpod pricing](https://www.runpod.io/pricing) immediately before rental.
There is no paid API requirement if both focal and judge models are served
locally.

## Replication model: `google/gemma-4-31B-it` — verified 2026-09-02 (no GPU needed)

Checked locally with the tokenizer only, in a throwaway venv, against the
immutable revision `842da3794eaa0b77d5f08bae87a17459d91ff475`:

| check | result |
|---|---|
| architecture | `Gemma4ForConditionalGeneration`, 31.3 B params → ~63 GB bf16 → **A100/H100 80 GB** |
| `transformers` requirement | needs ≥ 5.x; **fails to load under 4.57** (`'list' object has no attribute 'keys'`). Loads under **5.16.1 — the version already pinned in `requirements-pod.txt` and used for V4.** |
| `system` role | **kept** (Gemma 2 rejected it; Gemma 3 folded it; Gemma 4 keeps it) |
| `enable_thinking=False` kwarg | silently ignored — template output identical with/without. The V5 audit's `thinking_disabled` check reads the *provider attribute*, so it still passes. |
| generation prompt tail | `<\|turn>model\n<\|channel>thought\n<channel\|>` — an empty thought channel is emitted before the model's turn; constrained decoding to `1\|2\|3` applies at the correct position after it |
| `1`, `2`, `3` single tokens | **yes** (required by exact constrained decoding) |

Qwen3.8-27B (`1d4bf0f2…`) under the same test: system kept; `enable_thinking=False` is
**load-bearing** — without it the template opens an unclosed `<think>` block. Keep V5's
`enable_thinking: false`. Digits single-token.

To run Gemma's prior measurement, reuse the V5 runner under a **V7 protocol file**
(`--protocol-spec`), never under V5's frozen protocol; `audit_v5_calibration_plan`
compares `provider.describe()` to the spec's `primary_model` block, so the V7 spec
carries Gemma's id and revision. The runner requires the bank status
`selected_bank_pending_no_history_validation`, which `data/v5/v5_selected_bank_pending.json`
still has.

## V8 step 1 — Gemma-4-31B prior measurement (≈ $2, one pod, ~1 h)

The command is audited locally before any pod exists:

```bash
.venv/bin/python scripts/run_v8_prior_measurement.py --model-key gemma4_31b \
    --run-id v8-gemma4-prior --dry-run       # 37-check V8 audit; passes as of 2026-09-02
```

**Deploy (same class as V4/V5):** one on-demand **A100 SXM 80 GB**, the same
image and pinned wheels as the V5 run (`transformers==5.16.1`; see
`requirements-pod.txt`). **Do not rely on the 100 GB V5 volume for weights** —
it already holds ~56 GB of Qwen3.8-27B cache and Gemma needs ~63 GB more. Give
the pod ≥ 120 GB container disk and let `HF_HOME` default to it, or attach the
volume only for the repo and outputs.

**On the pod:**

```bash
git clone https://github.com/4r4cn1d0/LatentTarget && cd LatentTarget
git checkout <the tagged V8 commit>            # never a dirty tree
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-pod.txt
pytest -q tests/test_v8_protocol_gate.py tests/test_controlled_v8_power.py

# smoke: loader class + template + single-token digits, before spending an hour
python - <<'PY'
from src.hf_provider import HuggingFaceProvider
p = HuggingFaceProvider("google/gemma-4-31B-it", revision="842da3794eaa0b77d5f08bae87a17459d91ff475",
                        capture=False, constrained_choices=("1","2","3"))
p._ensure_loaded(); print(p.describe())
PY

tmux new -s v8
.venv/bin/python scripts/run_v8_prior_measurement.py --model-key gemma4_31b --run-id v8-gemma4-prior
```

576 constrained `1|2|3` choices, no history, no target, no capture. Output:
`data/calibration/v8-gemma4-prior.jsonl` + manifest with the V8 audit embedded.
Pull both back, then **stop the pod**. Analyse with the V5 selected-bank
validation evaluator (`evaluate_v5_bank_validation`) to get the three shares;
register them and the argmax frame in `docs/v8_protocol.json` under
`models.gemma4_31b` **before** any Gemma cell enters the power screen.

What the shares decide: if Gemma's largest frame share is well below Qwen's
52%, V8's confirmatory run goes on Gemma; if it is as skewed, V8 runs on Qwen
at its measured prior and Gemma is the replication arm.
