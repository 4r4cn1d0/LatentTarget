# Behavioral checkpoint v3 — frozen before paid focal generations

Status: frozen 2026-09-01 under the explicitly authorized machine-only,
exploratory track. No v3 focal-model outcome had been generated when these
settings and thresholds were committed. Human validation remains 0/40 and is
not being claimed.

## Question and decision

This checkpoint asks whether `Qwen/Qwen3.8-27B` changes its messages in a way
that is specifically explained by the outcome history of one hidden target,
and whether it revises that behavior after a silent target change. It is not a
powered hypothesis test. Its only decision is whether the behavioral pattern
is coherent enough to justify a costlier activation/probe/steering run.

`GO_FOR_MECHANISTIC_EXPLORATION` does not mean “latent target model proven.”
`STOP_BEFORE_MECHANISTIC_EXPERIMENT` is a valid negative outcome and may not be
repaired by selecting episodes, changing seeds, or tuning the scorer against
the observed effect.

## Frozen execution

```text
focal model       Qwen/Qwen3.8-27B (official dense bfloat16 weights)
thinking          disabled
sampling          temperature 0.7, top-p 0.8, top-k 20
maximum tokens    200
master seed       20260901
episode seeds     2
stable rounds     8
swap rounds       10 (silent change after round 5)
conditions        full_history, no_history, shuffled_history,
                  random_target, swap
target scorer     semantic_nli_v3 at pinned revision
activations       not captured in this checkpoint
```

Expected design: 36 episodes and 312 generations. Each stable/control condition
has six episodes and 48 generations. Swap has 12 episodes and 120 generations,
covering all six ordered type changes twice.

Substantive command:

```bash
python scripts/run_open_weight.py \
  --model Qwen/Qwen3.8-27B \
  --conditions full_history no_history shuffled_history random_target swap \
  --episodes 2 --rounds 8 --swap-round 5 --seed 20260901 \
  --temperature 0.7 --top-p 0.8 --top-k 20 --max-tokens 200 \
  --target-scorer semantic_nli_v3 --no-capture \
  --run-id qwen38_27b_v3_checkpoint_20260901 \
  --experiment-id qwen38_v3_checkpoint
```

Every row, prompt, raw message, semantic target score, target noise draw,
probability, choice, and seed is retained. No episode is dropped.

## Independent measurement

The inline keyword label is only a debugging field. The decision uses a
separate blind `gpt-5.6-sol` pass over saved messages. Its serialized input may
contain only `sample_id` and `message`; no target, condition, round, scenario,
history, outcome, probability, or target score is visible. Exact batch inputs,
outputs, process hashes, and a copied-log immutability audit are retained.

## Frozen systems thresholds

For stable conditions, “early” means rounds 1–2 and “late” means rounds 5–8.
All rates below use the blind independent primary strategy.

1. **Valid-history advantage:** full-history overall match exceeds no-history
   by at least 0.05, and its late-minus-early gain exceeds no-history's gain by
   at least 0.05.
2. **Shuffled specificity:** from round 2 onward (when history evidence exists),
   full-history match exceeds real-target match under shuffled histories by at
   least 0.05, and shuffled messages match their donor target at least as often
   as their real target.
3. **Random-response control:** random-target late-minus-early gain is at most
   0.05, and full-history gain exceeds it by at least 0.05.
4. **Wrong-start recovery:** at least one full-history episode whose round-1
   strategy was wrong uses the matching strategy in round 3 or later.
5. **Silent revision:** after the swap, new-type match rises by at least 0.05,
   old-type match falls by at least 0.05, and post-swap new-type match exceeds
   post-swap old-type match.
6. **Not one-cell driven:** late full-history match exceeds late no-history
   match for at least two of the three target types.
7. **Integrity:** exact design counts, all six swap pairs, pinned scorer/model,
   no parse failures, type-invariant scenarios, type-invariant round-1 and
   no-history prompts, one safe system prompt, and blind judge artifacts all
   pass.

All seven gates must pass. There is no “near pass” and no post-hoc weighting.
Because there are only two episode seeds, passing is still exploratory and does
not establish statistical reliability.

The executable implementation is `scripts/evaluate_behavioral_checkpoint.py`.
Its negative decision exits normally so automation preserves a scientifically
valid null/failure rather than hiding it as a crashed run.

## Work after the decision

If STOP, finish the report with transcripts, controls, and the negative result;
do not buy activation experiments. If GO, use checkpoint variability only to
freeze the next sample size, rerun the architecture preflight, then collect
activations. A latent-target-model claim would additionally require:

- episode-held-out target decoding;
- a probe that beats both transcript-only and exact evidence-only Bayesian
  baselines by at least five percentage points;
- stable swap trajectories;
- target/opposite/random/zero causal steering controls.

Behavior alone supports only feedback-conditioned policy adaptation.
