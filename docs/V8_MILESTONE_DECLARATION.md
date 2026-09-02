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
