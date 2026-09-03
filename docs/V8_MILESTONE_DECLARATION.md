# V8 milestone declaration

**Declared by the operator (PI) on 2026-09-02, in response to the question
"Declare V8 + measure Gemma?" — answered "Declare V8 + measure Gemma".**

This declaration **explicitly overrides the V6 terminal clause**
(`docs/V6_FINAL_PROTOCOL.md` lines 252–255: "No outcome-triggered V7, sample
extension, threshold relaxation ... is permitted in this milestone") for the
purpose of opening a new milestone. V6's clause bound V6's milestone. V7 was
run without such a declaration and was rejected on that ground among others
(`docs/V7_REVIEW.md`, finding 4); this document exists so that V8 cannot be.

## What V8 is

The V6/V7 controlled-choice design — three unlabelled candidates, `1|2|3`
under exact constrained decoding, target on the candidate's registered frame,
matched stable-old twin for every silent swap, exact bundle randomization
tests — with **one required gate added** and several absolute-level gates
dropped, per the V7 review's prescribed fixes. Rule, α, offsets, and dropped
gates are in `src/controlled_v8_power.py` and `docs/v8_protocol.json`.

## Rule-change ledger: every change, after which observed outcome

| from → to | observed outcome that preceded it | what changed |
|---|---|---|
| V3 → V4 | V3 free-form: learning pattern incomplete; keyword/judge circularity | controlled choice among registered candidates; target on frame ID; held-out paraphrase bank |
| V4 → V5 | V4 real: stable learning strong; revision failed; 92% expertise default | 24 rounds; constrained decoding; **balance gate** on a target-free calibrated bank; baseline-adjusted revision co-primary; raw crossover demoted |
| V5 → V6 | V5 real: bank could not be balanced (13.7/34.2/52.1) | whole-triad selection; **balance gate kept**; matched stable-old twin; decay + acquisition both required; every-cell prospective power rule |
| V6 → V7 | V6 power: balance gate infeasible at every N | **balance gate dropped**; absolute-level and origin/direction gates demoted; measured nuisance cells. *Undeclared; rejected.* |
| V7 → V8 | V7 screen: absolute `full_history_late_level` binds; V7 review: pooled rule passes on default-attraction; secondary entailed by null; undeclared | **destination-stratified acquisition gate REQUIRED** with its own exact test; α = 0.05/3 over three required tests; `full_history_late_level` and `all_target_types_supported` dropped as absolute; secondary tested against the DGP's own no-gating prediction; default frame registered from the prior measurement; offsets pinned 100k/200k/300k; **this declaration** |

## What is not changed

The instrument (frozen V5 bank, pool SHA-256 `73a404a9…`, semantic validation
`c28600f3…`), the generation settings, the twin-based estimands, the exact
tests, the three learner profiles, the null profiles, the N grid, the 0.20 /
0.25 DGP alternatives, and the requirement that every rule be frozen,
committed, and tagged before its official run.

## Sequence and kill-switch

1. Target-free prior measurement of `google/gemma-4-31B-it` on the frozen bank
   (≈ $2). A measurement, not a gate: it registers Gemma's default frame and
   adds a measured nuisance cell. Qwen's is already measured (expertise, 52.1%).
2. Exploratory V8 screen at the **measured** cells only; severe cells as
   sensitivity. **Pre-committed rule: V8-complete Wilson lower ≥ 0.80 at some
   N ∈ {12,18,24,30} in every measured cell, and every required test's null
   Wilson upper ≤ 0.05 in every null profile.** Fail → stop; write up V4.
3. Adversarial review of V8. Fail → stop.
4. Freeze `docs/v8_protocol.json` with the selected model and N; commit; tag;
   official fixed-seed power run at offsets 300000+.
5. One confirmatory run.

## Screen verdict (2026-09-02, 22:50 IST): FAIL under the pre-committed rule — V8 stopped

Exploratory screen at the two **measured** Qwen cells (`results/v8_design/screen/
v8_screen_qwen_measured.json`, file SHA-256 `0b5e4a808495ee07…`; 24 cells × 500 studies,
offsets 100000–111999). Rule: V8-complete Wilson lower ≥ 0.80 at some N in every
measured cell (and, as V6's inherited convention, every learner profile).

| N | min lower bound | blocking cell / profile | binding gate |
|--:|--:|---|---|
| 12 | 0.160 | overall / learner_1 | `stratified_exact_test` = 0.21 |
| 18 | 0.260 | overall / learner_1 | 0.31 |
| 24 | 0.433 | overall / learner_1 | 0.49 |
| 30 | 0.556 | overall / learner_1 | 0.60 |

**No N passes. V8 is stopped. The rule and the N grid are not changed.**

Null size at the measured prior (`v8_null_size_qwen_measured.json`, SHA-256
`738b3f59be1b405f…`; N = 18, 1,000 studies × 3 null profiles × 2 cells, offsets
200000–205999): stable test 0 rejections; revision 1.1–1.7%; stratified
0.9–1.7%; every Wilson upper ≤ 0.027 against the 0.05 rule; joint 0/6,000.
**Type I error is controlled.** The failure is power, not validity.

What the grid shows: at learner_2 and learner_3 the rule is met at N = 24–30
(lower bounds 0.72–0.92 in both cells). The binding profile is learner_1, whose
registered acquisition tilt is 0.013 — by V6's own DGP construction it barely
acquires the new frame, so a gate that *requires* destination-specific
acquisition is nearly unpowered against it at N ≤ 30. Both the gate (review
finding 1–2) and the profile (V6) were pre-registered. Extending N after this
outcome is forbidden.

Interpretation, stated once: **a revision test that cannot be passed by
default-attraction is underpowered at this model's measured prior against the
weakest registered learner at N ≤ 30.** That closes the V5 → V6 → V7 → V8 line
at the registered scale. Gemma's prior measurement cannot rescue V8, because
Qwen's measured cells remain in the rule; it is a standalone characterization
if run at all.

## Post-stop standalone measurement (declared 2026-09-03, before the spend)

After V8's stop, the operator chose to run the target-free prior measurement of
`google/gemma-4-31B-it` on the frozen V5 bank as a **standalone
characterization of the replication model**. It is not a V8 step, it feeds no
V8 decision, and it cannot rescue V8 (Qwen's measured cells remain in the rule
and fail). Its output is Gemma's three no-history frame shares and default
frame, registered by `scripts/register_v8_prior.py`. Pod: one A100-SXM4-80GB
on-demand at $1.39/hr, image `runpod/pytorch:1.2.0-rc.162-cu1281-torch291-
ubuntu2204`, deployed by the assistant via the RunPod API at the operator's
explicit instruction; expected cost ≈ $2.

## Standalone measurement result (2026-09-03): Gemma-4-31B shares the expertise default

`data/calibration/v8-gemma4-prior.jsonl` (576 records, file SHA-256 `0520697d999d23fc…`;
manifest alongside with the 37-check V8 audit embedded). Registered by
`scripts/register_v8_prior.py`; the committed registration is pinned to the raw
log by `test_gemma_registration_on_disk_matches_the_raw_log`.

| model, no history, frozen V5 bank | fairness | risk | expertise | default |
|---|--:|--:|--:|---|
| Gemma-4-31B-it, overall (576) | 0.240 | 0.122 | **0.639** | expertise |
| Gemma-4-31B-it, held-out (144) | 0.396 | 0.097 | 0.507 | expertise |
| Qwen3.8-27B, overall (576) | 0.137 | 0.342 | 0.521 | expertise |

A second model family, more skewed toward expertise than Qwen, with risk
nearly absent. The default frame is a property of the instrument-plus-task
across families, not a Qwen idiosyncrasy. This does not reopen V8.
