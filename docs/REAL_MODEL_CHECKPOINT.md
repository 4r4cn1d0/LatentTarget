# Qwen3.8-27B real-model checkpoint

Status date: 2026-08-26 UTC. This document records the first paid real-model
run. It was written after viewing the checkpoint results and is therefore a
report, not a preregistration. The frozen pre-data decisions remain in
`docs/PREREGISTRATION.md`.

## Decision

**Conditional GO; full scaling remains blocked.**

The narrow behavioral gate passed directionally: messages with valid history
became more aligned with the hidden target than messages with no history, and
the transcripts contain ordinary risk/expertise framing rather than keyword
lists or broken formatting. The direction also remains under a disjoint
measurement lexicon.

This is not yet evidence strong enough for the paper's main claim. The shared
keyword analysis is circular, the disjoint interaction is uncertain, realized
success did not improve, the fairness frame was never detected, and the
preregistered independent-classifier/human-label gate is unfinished. No full
run is authorized by this checkpoint.

## What was executed

### Compute boundary

- RunPod Secure Cloud H100 80 GB HBM3, listed at $3.29/hour.
- Community A100 and community H100 allocation attempts returned no available
  instance and created no pod.
- Account balance before: 79.9992673608 credits.
- Account balance immediately before deletion: 78.8829114682 credits.
- Observed spend: **1.1163558926 credits (about $1.12)**.
- The pod was deleted successfully (`HTTP 204`) immediately after artifacts
  were copied, and the account returned an empty pod list.
- The RunPod credential was entered only into a hidden interactive shell,
  never written to the repository or a run manifest, then unset when the pod
  was deleted.

### Exact code revision

- Repository: `https://github.com/4r4cn1d0/LatentTarget`
- Revision executed on the pod:
  `c65700da5f03c68738865ba0729b2a4373f2d57e`
- Python: 3.12.3 on the pod.
- PyTorch: 2.9.1+cu128; CUDA available.
- Transformers: 5.16.1.

### Pod setup and verification

1. Cloned the public repository into `/workspace/LatentTarget` and verified the
   exact Git revision above.
2. Created a virtual environment with system site packages and installed
   `requirements.txt` plus `requirements-pod.txt`.
3. Ran the entire pod-side suite: **233 tests passed in 29.30 seconds**.
4. The first model download filled the pod's 30 GB root overlay because SSH did
   not inherit `HF_HOME`. The partial Hugging Face cache was moved to the 80 GB
   workspace volume, `/root/.cache/huggingface` was linked to that cache, disk
   space was rechecked, and the preflight was rerun with `HF_HOME` explicit.
   No experiment data had been generated at that point.

## Preflight result

Command:

```bash
python scripts/preflight_open_weight.py --model Qwen/Qwen3.8-27B
```

Result: **PASS**.

- Architecture: `Qwen3_5ForConditionalGeneration`.
- Official multimodal auto-model loader succeeded for text-only generation.
- 64 text blocks and 65 captured hidden-state positions.
- Activation tensor: `[1, 65, 5120]`, finite and correctly indexed.
- Greedy test generation: `Option A is worth considering.`
- A zero-vector intervention at hidden-state index 32 reproduced the exact
  unsteered output.
- Machine-readable report:
  `results/tables/preflight_qwen38_27b.json`.

This validates model loading, text generation, activation capture, layer
mapping, and the no-op steering control. It does not validate a behavioral or
mechanistic scientific effect.

## Behavioral gate

Command:

```bash
python scripts/run_open_weight.py \
  --model Qwen/Qwen3.8-27B \
  --conditions full_history no_history \
  --episodes 4 --rounds 8 --no-capture \
  --run-id qwen38_27b_gonogo_20260826 --quiet
```

Planned and completed:

- 4 episode seeds × 3 target types × 2 conditions = 24 episodes.
- 8 rounds per episode = **192/192 generations**.
- No activation capture.
- Qwen thinking disabled; temperature 0.7, top-p 0.8, top-k 20.
- Zero unparsed classifications.
- Mean message length 46.2 words; maximum 77; no message exceeded 80 words.
- Raw-log SHA-256:
  `fd161c00ec0dde3b0f330faf1e6596bd78f19b45916be9f3040168eb602c44d3`.
- Manifest SHA-256:
  `6a703ab01442621dc9bcde0f2311e8d4f8ae94d9ecd4ca02d61c9b3324592240`.

The raw JSONL is preserved at
`data/raw/qwen38_27b_gonogo_20260826.jsonl`. The complete manifest is beside it.

## Results

### Shared-lexicon engineering classifier

| condition | match rate | round slope | slope p | success rate |
|---|---:|---:|---:|---:|
| full history | 0.240 [0.104, 0.375] | +0.0268 | 0.048 | 0.333 |
| no history | 0.073 [0.021, 0.135] | -0.0069 | 0.727 | 0.344 |

The preregistered `round × full_history` logistic coefficient was +1.776
(`p=0.0318`, episode-clustered SE). This number is **not independently
interpretable**: the inline classifier and target reward used the same
lexicon, with target/classifier argmax agreement 1.0 whenever the target found
any lexical signal.

### Disjoint-lexicon sensitivity analysis

The messages were reclassified without generating any new model output. The
classifier used the odd lexicon half while the target had used the full
lexicon.

| condition | match rate | round slope | slope p | type-alignment p |
|---|---:|---:|---:|---:|
| full history | 0.177 [0.083, 0.292] | +0.0069 | 0.343 | 0.0060 |
| no history | 0.063 [0.010, 0.125] | -0.0079 | 0.787 | 0.8301 |

The primary interaction remained positive (+1.301) but was uncertain
(`p=0.222`). Thus the direction survives a less circular measurement, but the
small pilot does not estimate its size reliably. The full-history type-
alignment permutation result is encouraging because it compares the actual
target-to-episode assignment with shuffled assignments while leaving message
strategies fixed.

### Outcome and type asymmetry

- Realized target success was not better with history: 0.333 versus 0.344.
  With only 12 episodes per condition and noisy binary choices, this checkpoint
  cannot establish payoff improvement.
- Noise-free mean `P(A)` moved from 0.302 in round 1 to 0.370 in round 8 under
  full history, versus 0.271 to 0.305 under no history. This is descriptive and
  still inherits the target lexicon's construct assumptions.
- Both keyword instruments detected **zero fairness-primary messages in all 32
  full-history fairness rounds**. Full-history matching was carried by risk and
  expertise episodes. A human may disagree with some keyword labels; that is
  exactly why the blind label gate is mandatory.
- The evidence-only Bayesian observer reached 0.479–0.521 stable-target
  accuracy depending on the predeclared hazard. There were no swap episodes,
  so no observer/behavior swap trajectory exists for this checkpoint.

## Transcript and leakage audit

`PILOT_REPORT_REAL_QWEN38_27B.md` contains:

1. the exact focal system and user prompt schema;
2. the exact target equation and parameters;
3. a seeded random sample of 12 messages;
4. three complete fixed-rule full-history transcripts, one per target type;
5. every strategy classification, target score, `P(A)`, and choice in those
   transcripts; and
6. automated leakage diagnostics.

Manual reading found:

- no formatting failures or keyword dumping;
- convincing ordinary risk framing in some risk episodes;
- ordinary expertise framing, but some expertise episodes began in that frame
  before feedback and may reflect self-consistency;
- weak or absent explicit fairness framing;
- no target-type word in the current-round prompt block;
- identical scenario distributions across target types in both conditions;
- the target structurally received only message text, never scenario or type.

The five-episode seeded transcript sample is preserved at
`results/qwen38_27b_gonogo/transcripts/random_5_seed_20260826.txt`.

## Why this is not yet the claimed phenomenon

The checkpoint supports the narrower statement:

> Qwen3.8-27B's communication strategy is directionally conditioned on repeated
> target-specific binary feedback in this simulator.

It does not yet support:

- that the model has a latent, explicit model of the target rather than a
  model-free policy;
- that it updates after a silent target change;
- that the effect survives shuffled histories or random responses;
- that the framing labels are valid under an independent judge;
- that the behavior improves realized success; or
- any mechanistic claim about hidden activations.

Those are precisely the jobs of the held-out controls, swap condition,
independent classification, probing baselines, and causal steering tests.

## Required next checkpoint

No code needs to be written by the researcher. The only manual task is to fill
the `human_label` column for the 40 rows in
`data/processed/qwen38_27b_gonogo_blind_labels.csv`, using
`data/processed/LABELLING_INSTRUCTIONS.md`, without opening the answer key.

Then the engineering workflow is:

1. Score blind human agreement and require Cohen's kappa ≥0.60 plus agreement
   on the direction of the history effect. Kappa <0.40 stops confirmatory work;
   0.40–0.60 permits only approximate/exploratory interpretation.
2. Reclassify all 192 saved messages with a blind independent LLM judge. This
   requires no new focal episodes.
3. If both measurement gates agree, request explicit researcher approval for
   the full control/swap/activation run.
4. If the gate fails, do not scale. Diagnose the fairness construct and, at
   most, run the one predeclared easier-to-detect environment from
   `docs/POD_RUNBOOK.md`.

The full 1,248-generation experiment, target swaps, activation capture,
black-box self-report, probe training, and steering remain unrun.

## Final repository verification

After the reporting-only empty-plot fix, the full local suite passed:
**235 tests in 21.94 seconds**. Python bytecode compilation over `src`,
`scripts`, and `tests` passed; `git diff --check` passed; the raw JSONL parsed
completely as 192 records in 24 eight-round episodes; and a repository scan
found no RunPod credential pattern. The 14 emitted warnings are deprecations in
the locally installed Matplotlib/pyparsing stack, not project failures.
