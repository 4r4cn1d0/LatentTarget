# GPU-free adversarial audit

> **Historical pre-run audit.** The engineering risks below motivated the
> implementation, but the statements that no real model or GPU run exists are
> no longer current. See `RUNPOD_CHECKPOINT_V3_20260901.md` for the completed
> all-controls run and frozen negative decision.

Status date: 2026-08-25. This review superseded the earlier draft. It separated
resolved implementation defects from scientific limitations that code alone
could not remove. At that date, no real focal model had been run.

## Executive judgment

The package is ready for the **one-generation GPU preflight and four-seed
behavioral gate**, not for a full confirmatory run. The offline pipeline is
reproducible and well controlled. Its main unresolved issue is construct
validity: behavioral adaptation can establish feedback-conditioned strategy
learning, but it cannot by itself establish an explicit latent user model.
Probing and steering can narrow that interpretation only if they beat the
visible-evidence baselines and pass their controls.

## Resolved findings

### 1. First-crossing manufactured apparent probe leads — resolved

The original “rounds until first prediction of the new type” metric rewards
random three-class flicker and censors never-flipped episodes. It is now a
labelled secondary diagnostic only. The primary temporal statistic uses every
post-swap round and compares each channel's rise toward the new type after
subtracting its own pre-swap baseline. A regression test covers the adversarial
chance-probe case.

### 2. No evidence-only comparator — resolved

`src/bayesian_observer.py` computes a sequential posterior from exactly the
message/outcome history visible to the focal model. It integrates simulator
logit noise by Gauss-Hermite quadrature, assumes only the preregistered symmetric
change hazard, and never receives the true swap round. Probe dynamics are now
compared directly with this posterior as well as with behavior.

This does not make a probe a belief measure. If probe probability merely tracks
the Bayesian curve, the conservative conclusion is that it decodes evidence
available in the prompt.

### 3. Swap pair/scenario confound — resolved

Every episode seed now runs all six ordered target transitions. Initial target,
new target, and scenario sequence are therefore fully crossed rather than linked
through episode parity.

### 4. Optimistic layer selection — resolved

Probe fitting uses stable typed full-history episodes only. Episodes are split
50/25/25 into target-stratified train/dev/test sets. Layer and regularization
selection use train/dev data; final accuracy is evaluated once on untouched test
episodes. The full layer sweep remains available.

### 5. Mechanistic controls were plans, not executable experiments — resolved

The repository now contains resumable black-box self-report, probe persistence,
probe-derived target/opposite directions, norm-matched random and zero controls,
paired steering seeds, and episode-clustered steering analysis. The hooks and
analysis pass local tests, but execution remains GPU-blocked.

### 6. Current model loader mismatch — resolved locally, GPU verification open

The default moved to the current official dense `Qwen/Qwen3.8-27B`. The provider
tries the official `AutoProcessor`/multimodal auto-model path first, explicitly
disables default thinking output, and records the resolved classes. A one-call
preflight checks generation, activation dimensions, text-layer discovery, and
zero-vector steering equivalence before any larger run.

### 7. Duplicate run IDs could duplicate episodes — resolved

The experiment now refuses to append to a nonempty run log. Recovery requires a
new run ID; compatible runs may be combined only after manifest checks.

### 8. Probe serialization used pickle-compatible loading — resolved

Probe class labels now use a fixed Unicode dtype and loading uses
`allow_pickle=False`. This removes an unnecessary unsafe deserialization path.

## Open scientific risks

### A. Behavior does not identify a latent model

Win-stay/lose-shift can adapt without representing a target type. The behavioral
claim must remain “feedback-conditioned target-specific strategy adaptation.” A
latent-model claim requires converging evidence: held-out probe performance
above transcript and Bayesian baselines, sensible swap dynamics, and causal
steering with random/opposite/zero controls.

### B. The simulator is a lexical model organism

The target rewards distinct lexicon matches. This gives known ground truth but
does not establish adaptation to human persuasion. Keyword stuffing and simple
bandit learning remain plausible. Report message lengths and raw transcripts;
use the disjoint lexicon, independent judge, and human-label gates. An LLM-target
replication is a later extension, not part of the first confirmatory claim.

### C. Measurement circularity remains possible

The keyword classifier shares concepts—and in its default form words—with the
target scorer. It is suitable for debugging only. The real analysis requires a
blind independent judge, the disjoint-lexicon sensitivity analysis, and a
blind human sample with the preregistered agreement gate.

### D. Probe may decode prompt evidence

The residual state can encode the visible history without encoding a
decision-relevant belief. Required diagnostics are: same-test transcript
readout, the Bayesian observer, shuffled-history donor-vs-actual alignment,
no-history/random-target checks, and steering. Even a positive intervention
shows control of framing, not that the direction is unique or naturally used.

### E. Real model/tool compatibility is unverified

Unit tests mock the Transformers interface. They cannot prove the 55+ GB model
downloads, loads, exposes the expected hidden-state structure, or reproduces
greedy output under a zero intervention. The preflight is deliberately the first
paid-compute command and must pass before the behavioral gate.

### F. The initial sample is not powered for a subtle effect

Eight episode seeds are a variance-estimation run. The pre-data sensitivity
simulation found that roughly 28 seeds reached 80% power only for a large
nominal 25-point late-round increase under its assumptions. The final sample
size must be frozen from pilot variance without selecting on the observed effect
direction or significance.

### G. Random-target reinforcement rate is not marginally matched

The control fixes `P(A)=0.5`; typed conditions may have a somewhat different
overall success rate. This is transparent and configurable, but it can change
the frequency of reinforcing feedback. Treat a rate-matched random control as a
predeclared sensitivity if the pilot shows a substantial marginal difference.

## Offline evidence completed

- 233 tests pass.
- Python bytecode compilation passes for `src`, `scripts`, and `tests`.
- Positive/negative mock pipeline validation passes.
- A fresh 72-episode/624-round mock run produced all logs, tables, plots, and
  three complete transcripts.
- A 624-row synthetic activation fixture passed the complete train/dev/test
  probe pipeline and selected its planted signal layer.
- The Bayesian, black-box, steering-analysis, power, and command-line paths are
  covered by tests.

At the date of this audit, these facts established engineering readiness only;
there were zero real-model observations, paid API calls, or GPU experiments.

## Decision gate

Proceed only in this order:

1. one-generation Qwen preflight;
2. four-seed full-history/no-history behavioral run without activations;
3. inspect five random transcripts and the exact prompts/probabilities;
4. stop for researcher approval;
5. only then freeze the powered sample and run activation capture.

If valid history does not directionally beat no history, do not rescue the
headline with a probe. Report the behavioral null and retain the mock positive
control as evidence that the measurement pipeline was capable of detecting
adaptation.
