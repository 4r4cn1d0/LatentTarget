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
