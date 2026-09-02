# V6 final milestone audit

Date: 2026-09-02  
Final status: **`STOP_V6_UNDERPOWERED_FINAL`**

## Outcome

V6 ended at its prospectively frozen, model-free power gate. No semantic or
quality judge was called; no focal-model calibration, target-bearing episode,
activation capture, probe, steering run, or paid GPU experiment occurred. The
result is a design-feasibility limitation, not evidence that an LLM does or
does not form a latent model of a target.

The final conditional objective was satisfied: redesign and audit the
measurement/experiment, run the preregistered power gate, proceed to one
confirmatory experiment only if that gate passes, and otherwise stop without a
V7 rescue. The gate failed, so stopping is the successful execution of the
decision rule—not a positive behavioral finding.

## Prospective integrity

- Corrected power/DGP code and the `NOT_RUN` protocol were committed as
  `c2da851f5445866a9ed4a8731808ac028e9c07d8`.
- The annotated tag `v6-power-correction-preregistered` was pushed before the
  corrected result artifact existed.
- The registered power constructor, randomization, thresholds, sample-size
  grid, nuisance cell, learner profiles, fixed seeds, study offsets, and
  short-circuit rule did not change after the result.
- The invalid earlier IID-multinomial certificate was removed from execution
  authority and is retained only as an explicitly labelled sensitivity
  calculation.

## Power decision

The official screen ran 10,000 model-free studies in each of 12 cells: all
three learner profiles crossed with `N = 12, 18, 24, 30` at the registered
`minimum_share_boundary_01` nuisance cell. It used the exact same
heterogeneous no-history path initializer, physical-slot assignment, RNG
roots, study offsets, and balance predicate as the corresponding complete
power cells.

| N | Blocking profile | Balance successes | 95% Wilson lower | Required |
|---:|---|---:|---:|---:|
| 12 | learner 3 | 4,184 / 10,000 | 0.4088 | 0.80 |
| 18 | learner 1 | 4,248 / 10,000 | 0.4151 | 0.80 |
| 24 | learner 2 | 4,289 / 10,000 | 0.4192 | 0.80 |
| 30 | learner 3 | 4,319 / 10,000 | 0.4222 | 0.80 |

The registered complete-pattern gate contains the same realized no-history
balance gate. Therefore, in every replicate, complete success is a subset of
balance success. A Wilson lower bound is monotone in the success count, so the
complete-gate lower bound cannot exceed the values above. The every-cell rule
is impossible for every allowed N, and the remaining 169-cell program cannot
authorize a sample size.

Artifact:

- path: `results/v6_design/power_prevalidation/v6_path_balance_dominance.json`
- file SHA-256:
  `23ca7e9155980dd8bf3e50b69e00353a5af8baf3cb535c2b3f28e6432b6d1d0b`
- certificate SHA-256:
  `79fd9eccf334789ed1249e39ee076d2f74f87f1c505273f07f75350f71187865`
- contract SHA-256:
  `e29dbbe8da2ecf6f7d891f5aee997052aff3d06dfc10e31db0d55ab757be2fd9`
- official command exit: `2`, as specified for terminal underpower

The full 120,000-study screen was deterministically replayed and reproduced
the artifact exactly. A separate scientific reviewer independently recomputed
the Wilson intervals and blocker selection and returned PASS with zero
Critical and zero Warning findings.

## Requirement and integration coverage

| Requirement | Final evidence |
|---|---|
| Controlled, hidden target types and silent swap | Implemented and tested in the conditional V6 runner; not executed after power failure |
| Full/no/shuffled/random/swap controls | Implemented, schedule-replayed, and mock-tested; no V6 model outcome |
| Target-free measurement | Structural, semantic, and quality contracts implemented; machine-judge transport never run |
| Current open-weight focal model | Qwen3.8-27B immutable revision frozen; never loaded for V6 |
| Outcome-independent sample-size decision | Corrected path screen prospectively tagged and run before any V6 model outcome |
| Exact randomization/inference | Physical-slot bundle randomization and shared analyzer/power estimator implemented and tested |
| Complete raw logging and recovery | Conditional JSONL, manifests, receipts, exact replay, locking, and crash paths implemented and tested |
| No cherry-picking or outcome-triggered redesign | No V6 target outcome exists; no V7 rescue; all terminal history retained |
| Paid-compute discipline | V6 API/GPU/model cost was $0 |

## Engineering closure

The final hardening pass made protocol authorization canonical and
status-bound, tied generation/target RNG streams to physical randomized slots,
reused exact no-history output bytes across hidden-label replications, rejected
duplicate/non-finite JSON, rooted critical reads/writes/locks through retained
descriptors, and tested crash-safe receipt/manifest/analysis publication.

The dormant Codex CLI judge transport is tool-enabled and is not represented as
safe for untrusted candidate text. This does not contaminate a result because
the canonical terminal protocol rejects semantic and quality dispatch before
runtime attestation, and tests assert that no transport is reached.

Release verification on the integrated tree:

- `745 passed in 682.99s` (`pytest -q`; zero failures);
- focused post-hardening bank/protocol tests: `22 passed`;
- Python `compileall`: pass;
- strict protocol JSON parse: pass;
- `git diff --check`: pass;
- independent scientific review: PASS, zero Critical, zero Warning.

## Deferred gaps

These are intentionally unexecuted, not unfinished evidence:

- independent semantic and quality judge outputs;
- focal target-free calibration and bank validation;
- the preregistered target-bearing confirmatory study;
- transcripts and behavioral metrics;
- activation collection, probing, and steering;
- human validation.

They may not be filled inside V6 because doing so after the terminal power
decision would violate the frozen design. Any future study would need a new,
independently motivated protocol rather than a rescue of this milestone.

## Final claim

V6 demonstrates that the proposed confirmatory design, as frozen, cannot meet
its own prospective complete-power criterion over the allowed sample-size grid.
It makes no empirical claim about latent target modelling. The repository is
archived as an auditable negative design result and a tested experimental
system, with downstream execution permanently blocked for V6.
