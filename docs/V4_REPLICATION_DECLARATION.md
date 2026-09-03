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

## Outcome, Arm E1 (Qwen3.8-27B, elicited beliefs) — 2026-09-03, analyzed once

Run 09:29–13:19Z on the same pod; log `data/raw/v4e-qwen38.jsonl` (3,600
records, tarball SHA-256 `10c80e9f…d91aa33`). Primary:
`scripts/analyze_elicited_choices.py` (frozen functions and thresholds,
within-arm; V4 spontaneous arm as the declared cross-prompt comparison).
Secondary: `scripts/analyze_elicited_beliefs.py`. Both →
`results/v4_real/elicited_qwen38/`. 3,600/3,600 valid JSON, valid beliefs,
no fallback; slots balanced (0.31/0.35/0.35).

**The V4 learning effect disappears under the elicited prompt.** Within-arm
verdict `ELICITED_LEARNING_FAIL_REVISION_FAIL`.

| metric | E1 elicited (Qwen) | V4 spontaneous (Qwen) |
|---|---|---|
| full-history learning gain (late held-out − early) | −0.020 [−0.053, 0.010], p = 0.90 | 0.187 [0.083, 0.290] |
| elicited − spontaneous learning gain (unpaired episode bootstrap) | −0.207 [−0.317, −0.097] | — |
| late held-out match, full history | 0.333 | 0.570 |
| swap: new-frame gain / new-over-old, p | −0.007 / −0.035, p = 0.67 | 0.24 / ≈0 |
| full-history frame shares (fairness / risk / expertise) | 0.000 / 0.058 / 0.942 | learned mix |
| P(repeat frame | success) − P(repeat | failure) | 0.933 − 0.908 = 0.025 | 0.876 − 0.693 = 0.183 |
| choice = argmax of stated p_a | 3,600 / 3,600 | — |
| mean stated p_a by candidate frame (fairness / risk / expertise) | 0.494 / 0.581 / 0.691 | — |
| stated p_a of selected vs realized target P(A) | 0.695 vs 0.494 (Brier 0.30) | — |
| post-swap rounds 1–5: P(belief = new) − P(choice = new) | 0.003 [0.000, 0.010] | — |

Against the pre-stated analysis: belief and choice do not merely "move
together" — they are the same object (the choice is the argmax of the stated
probabilities in every record), and neither moves. The stated confidence is a
fixed frame ranking (expertise > risk > fairness) that responds to feedback by
about 0.05 (0.705 after a success vs 0.660 after a failure for the repeated
frame) without ever changing the choice. So there is no stated belief that
the behaviour ignores, and no evidence of a separable model of the partner.

**The larger point.** Same model, same design, same seeds and targets, same
bank: changing the output format from a bare `1|2|3` to a JSON object with
stated probabilities removed the learning entirely (difference −0.207, CI
excluding zero). Together with Arm R1, the V4 learning result is now known
to be both **model-specific** (absent in Gemma-4-31B) and
**prompt-specific** (absent in Qwen under the elicited prompt).

Limitations of E1, stated: the elicited prompt was never tuned (V4's was);
the elicited history also shows the model its own past predictions, which
may anchor it; and `max_tokens` 96 leaves no room for reasoning. E1 cannot
separate "the format change" from "seeing own predictions". Neither caveat
rescues the stated-belief question: the model's stated probabilities carry
no information about the partner that its choices lack.

## Arm P1 — prompt paraphrase on the original model — declared 2026-09-03 (after R1 and E1 outcomes; before any P1 outcome)

Motivation: E1 changed the *task* (output format and visible predictions) and
removed the effect. That leaves open whether the V4 positive is tied to the
exact V4 prompt *string*. `docs/v4_paraphrase_qwen38.json` is the V4 spec
with one change: `generation.prompt_variant = "paraphrase_1"`, a plain
rewording of the spontaneous system prompt (same facts: N rounds, same
participant, Option A/B, one short message, three candidates, score = total
Option-A choices, reply with a single digit). Model, revision, conditions,
seeds, bank, thresholds, windows, target probabilities and decoding are
unchanged; the frozen audit and the blind bank gate pass under `--dry-run`.
The V4 template's SHA-256 is pinned by `tests/test_prompt_variant.py` so the
default cannot drift.

**Pre-stated predictions.** If the V4 learning effect is a property of the
model under this design, P1 replicates: full-history gain > 0 with the same
three controls flat, and the same anti-default per-target pattern. If the
effect depends on the exact prompt string, P1 shows a gain near 0 and the
V4 positive should be described as a single-prompt observation. Revision is
predicted to fail again with the default-attraction asymmetry. Analysis: the
frozen `scripts/analyze_controlled_v4.py` against this spec, run once.
Cost ≈ 1 pod-hour ≈ $2.

## Outcome, Arm P1 (prompt paraphrase, Qwen3.8-27B) — 2026-09-04 (00:00–21:23Z on 2026-09-03 clock), analyzed once

Run 19:57–21:23Z on pod `55mngrae0nld1g` (a first pod, `jq6ok8utvmrg0v`,
never exposed a runtime and was terminated unused); log
`data/raw/v4p-qwen38.jsonl` (7,200 records, tarball SHA-256
`956c694d…3542792`); manifest records `spontaneous_prompt_variant =
paraphrase_1`. Frozen analyzer against `docs/v4_paraphrase_qwen38.json`
with default seeds → `results/v4_real/paraphrase_qwen38/`. Design integrity
PASS; slots balanced.

**The learning effect replicates under the reworded prompt.**

| metric | P1 paraphrase | V4 original |
|---|---|---|
| full-history learning gain (late held-out − early) | 0.207 [0.110, 0.307] | 0.187 [0.083, 0.290] |
| full − no-history difference-in-differences, one-sided p | 0.207 [0.113, 0.303], p = 0.0002 | p < 0.001 |
| full over shuffled, late held-out | 0.377 [0.267, 0.480], p = 0.0001 | — |
| no-history / shuffled / random-target gain | 0.000 / −0.070 / −0.007 | 0.000 / −0.054 / ≈0 |
| per-target advantage (full − no-history): fairness / risk / expertise | 0.28 / 0.43 / 0.09 | 0.19 / 0.51 / 0.01 |
| swap: new-frame gain / old-frame drop / new-over-old, p | 0.133 / 0.132 / −0.077, p = 0.89 | 0.24 / 0.24 / ≈0, p > 0.05 |
| valid selection rate (gate ≥ 0.98) | **0.898** | 0.985 |

Every learning gate and the stable randomization test pass. The frozen
decision is nonetheless `STOP_BEFORE_FREEFORM_OR_MECHANISTIC_SCALING`
because two non-learning gates fail: the revision gates (predicted; same
symmetric pattern as V4) and the valid-selection gate. The invalid outputs
are all one thing: in 733 rounds (10.2%) the model began a reasoning
preamble — "Looking at the history, the participant chose…" — and was cut
off by V4's token budget. They occur in 11–14% of rounds in every condition
that shows a history and in **0%** of no-history rounds, rising from round 6
onward. The frozen fallback replaced each with a uniformly random slot
(231/240/262 across slots; frames balanced), which can only move the
full-history match toward chance: on parsed-only rounds the late held-out
match is 0.632 against 0.600 with fallbacks. The learning result is therefore
conservative, not inflated. The preambles themselves are a small qualitative
observation: under this wording the model spontaneously refers to the
participant's past choices when it starts to explain itself.

Against the pre-stated predictions: (a) **held** — the effect is not tied
to the exact V4 prompt string; the per-target anti-default pattern also
held. Revision failed as predicted. Not predicted: the validity-gate failure
from truncated reasoning, which a larger token budget would remove; it was
not re-run, because the arm was declared with V4's decoding unchanged.

**Combined reading of R1, E1, P1.** The V4 learning effect is robust to the
wording of the prompt (P1), absent in a second model family under the
identical design (R1), and absent in the same model when it must state
beliefs in JSON (E1, where belief and choice were one object). It is a
property of Qwen under this task in its spontaneous form, not a general
property of instruction-tuned models, and not accompanied by a separable
stated model of the partner.
