# V4 replication and elicited-belief arms — declared 2026-09-03, before any outcome

Two paid runs of the **frozen V4 design** (`docs/behavioral_checkpoint_v4.json`:
20 rounds, silent swap after 10, held-out wording 16–20, target P(A) 0.72 match
/ 0.38 mismatch, same bank, same seeds, same thresholds). Neither changes a
threshold, a window, or a seed. Both are declared here first; the analysis is
the frozen V4 analyzer, run once per arm.

## Arm R1 — replication on a second model family

`docs/v4_replication_gemma4.json`: identical to V4 except `primary_model` =
`google/gemma-4-31B-it` @ `842da3794eaa0b77d5f08bae87a17459d91ff475`. All
five conditions, 360 episodes, 7,200 records.

**Pre-stated predictions.** (a) H1–H3 replicate: full-history learning gain
> 0 with the same three controls flat or below chance. (b) The revision gate
fails again and the swap pattern is default-attraction: adaptation *into*
expertise high, *into* fairness/risk low — Gemma's measured default is
expertise at 63.9%, so the prediction is the same asymmetry as Qwen's. (c) The
per-target pattern is anti-default: expertise targets show no learning
relative to no-history; fairness and risk do. If (a) fails, the learning
result is Qwen-specific. If (b) fails and revision passes, H4 was a Qwen
limitation, not a design one.

## Arm E1 — elicited belief on the original model

`docs/v4_elicited_qwen38.json`: same model and design, conditions
`elicited_full_history` and `elicited_swap` only (180 episodes, 3,600
records), `max_tokens` 96. In this mode the model must output
`{"p_a":{"1":…,"2":…,"3":…},"choice":k}` — a stated probability that each
candidate wins — and sees its own past predictions in the history. **This is a
different prompt**, so choice behaviour is compared to V4's spontaneous arm as
a secondary check, not pooled with it.

**Pre-stated analysis.** Primary: the frozen V4 learning and swap metrics on
the *choices* (does elicitation change behaviour?). Secondary, the point of
the arm: the model's *stated belief* (argmax of its p_a over the three frames)
versus its *choice*, by round and by rounds-since-swap — P(belief matches the
new target) against P(choice matches the new target), bootstrap CI over
episodes. **No first-crossing statistic** (see `docs/V7_REVIEW.md`).
Prediction: if a belief exists that the behaviour ignores, belief-matches-new
rises after the swap while choice-matches-new does not; if belief and choice
move together, the stated belief is a description of the policy, not a model
of the partner.

## Cost and gates

One A100-80GB pod, both arms sequentially, ≈ 4–5 pod-hours ≈ $7. Both arms
`--dry-run` clean against the frozen audit before deployment. Each arm's log
is pulled with hash verification and analyzed once with
`scripts/analyze_controlled_v4.py` against its own spec. Failure of any audit
stops that arm; the other still runs.

## Correction, 2026-09-03 (before Arm E1 started; Arm R1 in progress, no R1 outcome read)

"Analyzed once with `scripts/analyze_controlled_v4.py` against its own spec"
is not executable for Arm E1: the frozen evaluator refuses a log that lacks
the five V4 conditions, and E1 deliberately contains only the two elicited
ones. Arm R1 is unaffected (all five conditions). For E1 the primary choice
analysis is `scripts/analyze_elicited_choices.py`, which applies the frozen
evaluator's *own* functions and thresholds (`_stable_episode_summaries`,
`_swap_episode_summaries`, `_bootstrap_mean`, `_sign_flip_test`,
`CONTROLLED_GATE_THRESHOLDS`, one-sided α) within the arm, and lists the V4
gates that need control conditions as *not computable within E1*. The V4
spontaneous arm's `full_history`/`swap` episodes are the declared cross-prompt
comparison, reported with an unpaired episode bootstrap. The secondary
belief analysis is `scripts/analyze_elicited_beliefs.py`. Both scripts and
their tests were committed before any E1 record existed.

## Outcome, Arm R1 (Gemma-4-31B) — 2026-09-03, analyzed once

Run 08:39–09:29Z on pod `8okwbdycp0h4a8`; log `data/raw/v4r-gemma4.jsonl`
(7,200 records, tarball SHA-256 `ec415557…081a111`), frozen analyzer against
`docs/v4_replication_gemma4.json` with default seeds →
`results/v4_real/replication_gemma4/`. Design integrity PASS; 7,200/7,200
valid selections; no fallback; slot positions balanced (0.34/0.33/0.33).

**Does not replicate.** Decision `STOP_BEFORE_FREEFORM_OR_MECHANISTIC_SCALING`;
every effect gate except `random_response_control` fails.

| metric | Gemma-4-31B (R1) | Qwen3.8-27B (V4) |
|---|---|---|
| full-history learning gain (late held-out − early) | 0.040 [−0.007, 0.093] | 0.187 [0.083, 0.290] |
| full − no-history difference-in-differences, one-sided p | 0.040, p = 0.16 | p < 0.001 |
| no-history / shuffled / random-target gain | 0.000 / −0.017 / 0.010 | 0.000 / −0.054 / ≈0 |
| swap: new-frame gain / old-frame drop / new-over-old, p | 0.000 / 0.005 / −0.055, p = 0.76 | 0.24 / 0.24 / ≈0, p > 0.05 |
| full-history frame shares (expertise / fairness / risk) | 0.895 / 0.022 / 0.083 | — |
| same choice as shuffled-history on the identical triple | 0.905 | 0.637 |
| P(repeat frame | success) − P(repeat | failure) | 0.972 − 0.941 = 0.031 | 0.876 − 0.693 = 0.183 |

Prediction (a) **failed**: Gemma does not learn under the frozen design, so
the learning result is, on present evidence, Qwen-specific. Prediction (b)
half-held: revision fails, but not through the predicted feedback-driven
asymmetry — the "adapted" counts (36/40 into expertise, 1/40 into fairness)
are the pre-existing default, not adaptation (new-frame gain ≈ 0 in every
transition). Prediction (c) **failed**: per-target movement is *toward* the
default (expertise 1.00 vs 0.72 no-history; fairness 0.01 vs 0.16).

Reading: Gemma's no-history default is *weaker* than Qwen's on this bank
(0.787 vs 0.922 expertise), yet it is almost insensitive to feedback
(win-stay/lose-shift gap 0.03 vs 0.18) and to history content (choice equals
the shuffled-history choice 90.5% of the time). Default strength does not
explain the difference; feedback use does. This is a model-level property,
not a design artefact — the same bank, seeds, and analyzer produced learning
in Qwen the day before.
