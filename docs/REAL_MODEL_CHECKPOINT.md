# Qwen3.8-27B real-model checkpoint

Status date: 2026-08-26 UTC; independent-measurement addendum 2026-08-27. This document records the first paid real-model
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

At the initial checkpoint, this was not evidence strong enough for the paper's
main claim: the shared keyword analysis was circular, the disjoint interaction
was uncertain, realized success did not improve, the keyword instruments did
not detect fairness, and both independent-classifier and human-label gates were
unfinished. The addendum below completes the independent-classifier step but
does not authorize a full run.

### Independent-measurement addendum (2026-08-27)

The independent-judge step is now complete. All 192 saved messages were judged
blindly by `gpt-5.6-luna`; no new focal output was generated. A structural
audit verified that each judge input contained only an opaque sample ID and the
message text. Eight batches classified 189 unique messages with zero schema or
parse failures.

Under this independent instrument, full-history match was 0.146 [0.063, 0.240]
versus 0.042 [0.010, 0.073] without history. The preregistered interaction was
+1.629 (odds ratio 5.10, two-sided `p=0.058`). This preserves the intended
direction and sharply reduces circularity (target/judge argmax agreement 0.541
rather than 1.00), but remains underpowered exploratory evidence.

The diagnosis changed: 5/32 full-history fairness messages were fairness-primary
under the independent judge versus 0/32 without history, while 0/32
full-history expertise messages were expertise-primary. All 13 independently
fairness-primary messages in the full dataset received zero fairness reward
from the v1 simulator. Of 36 old keyword expertise labels rejected by the
independent judge, 25 were triggered by `professional` and 10 by generic uses
of `experience`. The reward function therefore has a demonstrated construct
calibration problem.

The human gate remains incomplete (0/40 rows labelled), so scaling remains
blocked. Full evidence and remediation gates are in `docs/EVAL-REVIEW.md` and
`docs/MEASUREMENT_REMEDIATION.md`.

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
- generic “professional” language that the v1 keyword scorer treated as
  expertise but the independent judge mostly classified as other;
- some implicit fairness framing that the keyword scorer and reward missed;
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
2. The independent-judge step is complete; score the human sheet against that
   judge and retain the machine-readable gate result.
3. If the human gate passes, calibrate and freeze a separately versioned v2
   target scorer on human-labelled development/held-out messages. Do not alter
   v1 or tune against focal outcomes.
4. Request explicit researcher approval for a two-seed all-controls v2
   checkpoint. Do not jump directly to the full control/swap/activation run.
5. If either measurement gate fails, do not scale; treat the v1 result as an
   instrument-development pilot.

The full 1,248-generation experiment, target swaps, activation capture,
black-box self-report, probe training, and steering remain unrun.

## Final repository verification

After the reporting-only empty-plot fix, the full local suite passed:
**235 tests in 21.94 seconds**. Python bytecode compilation over `src`,
`scripts`, and `tests` passed; `git diff --check` passed; the raw JSONL parsed
completely as 192 records in 24 eight-round episodes; and a repository scan
found no RunPod credential pattern. The 14 emitted warnings are deprecations in
the locally installed Matplotlib/pyparsing stack, not project failures.

After the 2026-08-27 independent-measurement remediation, the expanded suite
passed **254 tests in 21.28 seconds**. Bytecode compilation and `git diff
--check` passed; 36 committed/generated JSON artifacts parsed; both source and
independently reclassified JSONL files parsed as exactly 192 records; the blind
artifact audit passed; deterministic report/audit hashes reproduced exactly;
and repository scans found no RunPod/OpenAI-style credential pattern. The same
14 third-party deprecation warnings remain.
