# V7 design proposal — prior-cancelling revision test without the balance gate

Status: **PROPOSAL, pre-result.** Written and committed (`5c8a37c`) before the
exploratory feasibility screen reported. Nothing here is a registered
protocol yet. If the screen shows feasibility, the next step is a frozen
`docs/v7_protocol.json`, a commit, and a tag *before* the official fixed-seed
power run — the discipline V6 established and this proposal inherits.

## Why a V7 is legitimate

The V6 terminal rule forbids an *outcome-triggered rescue of V6*. V6 produced
no model outcome; its result was a design-feasibility limitation. V7 is
motivated by measurements that predate V6:

1. **V4 (real, 360 episodes, Qwen3.8-27B).** Stable target-specific selection
   was strong and survived every control. The silent-swap revision gate failed
   with held-out new−old ≈ 0 (p = 0.498). Post-hoc: a 92.2% expertise default
   in no-history rounds; swaps into expertise adapted 34/40, into fairness 0/40.
   Old-frame *decay* was nonetheless present in all six transitions, including
   the two away from expertise (0.15, 0.19) — the model leaves a stale frame; it
   fails to land on the right one against its default.
2. **V5 (real, target-free, $1.76).** No candidate bank can balance that
   default: the best fairness candidate reaches 33% selection, the median
   expertise candidate 63%. The selected bank measured 13.7 / 34.2 / 52.1.
   Balance is a property of the model, not of the instrument.
3. **V6's power model cannot represent the measured model.**
   `_clean_accepted_frame_shares` raises on 13.7/34.2/52.1. The balance gate
   was therefore never a threshold the real study could clear; it was an
   assumption the DGP could not even encode.

## What V7 changes — and what it does not

**Unchanged from V6** (the parts that are right):

- Controlled-choice action space: three unlabelled candidates, the model emits
  `1|2|3` under exact constrained decoding, no fallback (V5).
- The target uses the candidate's registered frame ID directly; no scorer or
  judge on the causal path (V4).
- **Matched stable-old counterfactual for every swap** (V6): each swap episode
  has a twin sharing prefix, bundle, and physical-slot randomization with the
  target left unchanged. Every revision estimand is `swap − twin`, so the
  default frame cancels *by construction*. This is V6's own estimand.
- Physical-slot bundle randomization, exact one-sided randomization tests at
  α = 0.025 each, the three learner profiles, N ∈ {12, 18, 24, 30}.
- The analyzer, `analyze_v6_bundle_study`, verbatim.

**Changed:**

| | V6 | V7 |
|---|---|---|
| no-history balance | **hard gate** in the complete rule and a prerequisite in the power rule | **reported only** |
| `all_target_types_supported` | hard gate | reported only — ceiling-doomed for the default frame (V4: expertise had no headroom) |
| `late_swap_new_minus_old ≥ 0` | hard gate | reported only — raw crossover is prior-confounded (V4); V5 had already demoted it |
| `directional_transition_support`, `all_origin_types_support_revision` | hard gates | replaced by **preregistered stratified reporting** by transition direction relative to the measured default |
| nuisance grid | 13 hypothetical *balanced* cells | 4 **measured** cells with provenance: V5 overall 13.7/34.2/52.1; V5 held-out 22.9/43.1/34.0; severe 5/15/80; V4 raw 1.2/6.5/92.2 |
| share validator | 0.25–0.42 band, gap ≤ 0.15 | any interior point of the simplex |

**Kept as required gates**, all prior-cancelling or integrity:
`design_integrity`, `all_selections_valid`, `zero_fallback`,
`no_history_learning_control`, `random_target_learning_control`,
`full_history_late_level`, `full_over_no_late`, stable DID ≥ 0.10,
revision DID ≥ 0.15, adjusted old-frame decay ≥ 0.05, adjusted new-frame
acquisition ≥ 0.05, and both exact tests at α = 0.025.

The V7 rule is a strict subset of the V6 rule (`test_v7_rule_is_a_strict_subset_of_v6_rule`).

## The hypothesis, stated before the data

**Primary (revision):** after a silent swap, the model's use of the *old* frame
falls relative to its matched stable twin by ≥ 0.05, and the swap-minus-twin
revision shift is ≥ 0.15 with the exact test at α = 0.025. Decay is primary
because it *is* the stale-model construct and V4 shows it is not
ceiling-limited.

**Secondary (acquisition asymmetry, preregistered):** new-frame acquisition is
larger for swaps *toward* the measured default than *away* from it. V4's
post-hoc table (34/40 vs 0/40) becomes a confirmatory prediction. If it holds,
the finding is *"revision is gated by the model's prior, not by the evidence"*
— a sticky-belief result with a mechanism, which is more interesting than
symmetric revision would have been.

**Stable co-primary:** unchanged from V6 (full-minus-no-history DID ≥ 0.10).

## Feasibility screen

`src/controlled_v7_power.py::run_v7_feasibility_screen` — 4 cells × 3 learner
scenarios × 4 N, 500 studies each, fixed seed, labelled
`EXPLORATORY_FEASIBILITY_SCREEN_NOT_A_REGISTERED_POWER_RUN`. It reports, per
cell: V7-complete rate with Wilson bounds, joint co-primary rate, V6-complete
for reference, **every required gate's individual pass rate** (so the binding
gate is visible, not hidden inside a conjunction), and the reported-only gates.

Decision rule for proceeding, fixed now: V7 is worth freezing only if some
allowed N reaches a V7-complete Wilson lower bound ≥ 0.80 in **every** measured
cell except `qwen38_v4bank_no_history`, which is a different bank and is
reported as a worst case, not a selection cell. If no N does, V7 is not
feasible either and that is the result.

## If feasible: the paid path, in order

1. Freeze `docs/v7_protocol.json` (rule, cells, seeds, N), commit, tag.
2. Official fixed-seed power run (CPU, $0) → selects N or stops.
3. **Second model prior measurement** — `google/gemma-4-31B-it` @
   `842da3794eaa0b77d5f08bae87a17459d91ff475`, target-free, no-history, on the
   frozen V5 bank. A *measurement*, not a gate. ≈ $2. Its shares become a
   fifth nuisance cell; power is re-checked at that cell before spending more.
4. Confirmatory run on Qwen3.8-27B (already-measured prior), then replication
   on Gemma-4-31B. Estimated ≈ $3–5 each at 360 episodes on an A100 80 GB.
5. Only a passed, replicated revision gate licenses activation capture.

## What would kill V7

- The screen shows the stable or revision co-primary underpowered at every N
  under the measured prior — then the *estimand* is fine but the effect sizes
  frozen in V5 (0.20 / 0.25) are too small to detect at ≤ 30 bundles, and the
  honest options are a larger N grid (new protocol) or stopping.
- Gemma's prior is as skewed as Qwen's in the *same* direction — then the
  asymmetry hypothesis cannot be separated from a frame-attractiveness
  artefact across models, and the secondary claim weakens to "in these two
  models."

## Pre-result diagnostic (2026-09-02 17:30 IST, screen still running): realized effect size depends on the prior

V6's probability tilts are additive on the probability scale and were
calibrated so the complete feedback model centers the estimands on the
registered alternatives (stable DID 0.20, revision shift 0.25). Twenty V7
studies per cell (learner_2, N = 18, study offsets 5000+, disjoint from the
screen) show what the same tilts realize under each nuisance cell:

| cell | stable | revision | new gain | old drop |
|---|--:|--:|--:|--:|
| balanced (V6 assumption) | 0.220 | 0.235 | 0.123 | 0.113 |
| `qwen38_v5bank_overall` 13.7/34.2/52.1 | 0.195 | 0.243 | 0.122 | 0.122 |
| `qwen38_v5bank_heldout` 22.9/43.1/34.0 | 0.215 | 0.236 | 0.120 | 0.116 |
| `severe_default_80` 5/15/80 | 0.153 | 0.177 | 0.094 | 0.083 |
| `qwen38_v4bank_no_history` 1.2/6.5/92.2 | **0.109** | **0.111** | 0.058 | 0.052 |

Under the **measured** priors the registered alternative is realized, so the
screen's power there is power for ≈ 0.20 / 0.25. Under the severe cells the
tilt is compressed against the simplex boundary and the screen measures power
for a smaller effect — about half the registered one in the V4-raw cell. This
is inherited from V6's DGP, not introduced by V7, and ceiling compression is a
real property of a model with a 92% default: the same learning strength *is*
less visible there.

**Consequences, fixed now rather than after the screen:**

1. The decision rule above is **not changed**. `severe_default_80` remains a
   selection cell; `qwen38_v4bank_no_history` remains reported-only. If
   `severe_default_80` blocks every N, that is the result and the honest
   statement is "V7 is powered for the measured prior but not for a
   hypothetical 80% default at these effect sizes."
2. Any V7 protocol must register the alternative as the **DGP tilt**, and must
   report the **realized population effect per cell** beside every power
   number. `simulate_controlled_v7_power` already returns `mean_estimates` for
   this reason; the screen table must print them.
3. The official run, if any, uses study offsets disjoint from both this
   diagnostic (5000+) and the exploratory screen.
