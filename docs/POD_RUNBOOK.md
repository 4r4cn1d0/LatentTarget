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
