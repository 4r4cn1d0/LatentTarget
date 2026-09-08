# Partner study offline engineering work log

Started 7 September 2026 and completed work continued past midnight into
8 September in India. Repository HEAD at entry:
`a61ddfde6aa3ed133e8cf36b10dbe3fcf4fa059e`.

## Request and boundaries

The user asked to start the next work, make sure it functions, and improve on
the earlier experiments. The immediate missing step was the offline partner
study pipeline and sensitivity screen. This turn implemented that step and
tested it. It did not deploy RunPod, use a credential, call a focal model or
judge, label data as a human, collect activations, edit Google Docs, commit,
or push to GitHub. No paid experiment was authorized by this screen.

The working tree already contained the baseline comparison, failed history
diagnostic, partner study design and README changes. Those were preserved.
The frozen design and historical V4, R1, E1 and P1 outcomes were not rewritten.
All new model results in this work are mathematical mock responses, not LLM
observations. The original empirical claims remain unchanged.

## Implemented components

1. `src/partner_state.py`: balanced 36 cell allocation, separate random streams,
   prototype development and confirmation stimuli, explicit visible prompt
   projection, a complete randomized request ledger, strict response joining,
   and an integrity audit.
2. `src/partner_policies.py`: numerical state updates and a fresh history
   simulation engine. Includes global and participant reward/recency models,
   static and dynamic belief policies, fixed defaults and null policies.
3. `src/partner_statistics.py`: conservative missing choice bounds, exact
   marginal empirical bootstrap convolution, validity calculations, the full
   declared decision rule and Wilson Monte Carlo intervals.
4. `src/partner_pipeline.py`: joins the ledger, raw mock responses, strict
   parsing, ground truth probabilities and bundle level analysis. No network
   provider is present.
5. `src/partner_reporting.py`: secondary choice, success, regret, validity,
   forecast, calibration and complete case summaries. None overrides a gate.
6. `scripts/run_partner_offline.py`: a smoke mode and full screen, deterministic
   compressed archives, all study decisions, plots, a report, plan snapshots
   and a source/output manifest. Existing output directories are refused.
7. `tests/test_partner_pipeline.py`: independent invariance, leakage,
   enumeration, missingness, strict ledger, statistical and replay tests.
8. `docs/partner_state_offline_20260907.json`: scenarios, seeds, sample grid,
   thresholds and stopping rule written before the initial smoke screen.
9. [Methods](PARTNER_STATE_OFFLINE_METHODS_20260907.md): assumptions and limits,
   written before the full screen, after the functional smoke test.

## Scientific decisions and improvements

- Used complete history bundles as the independent unit. The four identity
  requests and every secondary branch are not independent samples.
- Changed no thresholds after seeing smoke results. Required scenarios and the
  288 bundle ceiling remain as declared.
- Included shared and independent request behaviour, independent missingness,
  selective missingness and an invalidity level above the allowed gate.
- Kept three control equivalence requirements in the simulated decision.
  Detection against zero, effect threshold, control precision and response
  validity are reported separately.
- Kept feature reward learning as a legitimate alternative. This study cannot
  establish a distinct latent representation just by rejecting global rules.
- Separated forecasts from choices. Forecasts never enter subsequent history.
- Exported unlabelled text for future independent review with a separate
  analyst key. No machine output is passed off as human validation.
- Avoided random fallback choices. Missing and invalid outputs stay in planned
  denominators and conservative bounds.
- Added success and regret bounds, plus subgroup diagnostics, so a positive
  aggregate cannot hide a failed type or response cell.
- Kept the abstract numeric simulator separate from the language stimulus
  bank. Numerical power is not power against semantic comprehension errors.

## Audit repairs found during this turn

Before the full screen, code inspection found that a ledger could contain the
right total count while assigning an identity to the wrong cell. The integrity
checker now verifies the exact planned identity set and identity/specification
mapping. A test for a forged identity and another for a wrong cell with a
freshly computed valid prompt hash both require rejection.

The first integrity audit verified whether choices matched stored draws and
probabilities, but did not recompute those probabilities from the hidden type.
It now checks the simulator rule itself, uniform draw range, random control
exposures and unchanged nonresponse fields. Nonfinite draws are rejected.

The source manifest initially omitted the reused design checker module. It
was added before the full run. A nonfinite secondary contrast could also have
escaped primary interval validation; the decision function now checks all
bounds for finiteness. These were prelaunch inspection findings, not hidden
changes made after a failed power screen.

## Verification chronology

The first new component run passed 36 tests in 1.66 seconds. After adding
secondary reporting, the same 36 tests passed again in 1.27 seconds. Expanded
audit and reporting coverage then passed 49 tests in 2.18 seconds.

The functional smoke command completed:

```bash
.venv/bin/python scripts/run_partner_offline.py --smoke \
  --out-dir results/partner_state_smoke_20260907
```

It generated 36 bundles, 864 undispatched requests, 13 sets of mock responses
and 1,200 synthetic studies across 12 cells. Its verdict is SMOKE_ONLY, with
no sample recommendation. It predates the final audit and reporting additions
and is kept as a separate earlier implementation snapshot. It is not a power
calibration result.

The expanded relevant regression command completed:

```bash
.venv/bin/python -m pytest -q \
  tests/test_partner_pipeline.py tests/test_partner_state_design.py \
  tests/test_choice_baselines.py tests/test_history_diagnostic.py \
  tests/test_controlled_target.py tests/test_controlled_focal_agent.py \
  tests/test_controlled_analysis.py tests/test_controlled_experiment.py \
  tests/test_checkpoint_gate.py
```

Result: **215 passed in 33.38 seconds**. No warnings were reported in this
output. `git diff --check` also passed. A repository metadata search reported
that `pyproject.toml` does not exist; the repository uses `requirements.txt`
and the existing virtual environment. No dependency was installed.

### Full repository regression

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m pytest -q
```

Result: **956 passed in 674.88 seconds**, with no warnings or failures reported.
Model download offline flags were set. These are unit and synthetic tests;
tests of paid preflight code use test doubles, not a paid model provider.

Two additional path confinement tests in `tests/test_partner_verification.py`
were added after that run collected its tests. They passed separately in
0.90 seconds. The distinction is retained rather than claiming a single
958 test full run.

A final focused run of the pipeline, verifier and original design suites passed
**116 tests in 6.38 seconds**. A collection only check reported 958 current
repository tests, consistent with the original 956 plus the two additions.

### Completed full screen

```bash
.venv/bin/python scripts/run_partner_offline.py \
  --out-dir results/partner_state_offline_20260907
```

Result: COMPLETE execution in **640.99 seconds**, followed by the scientific
verdict **OFFLINE_SCREEN_NO_GO**. The manifest timestamp is
`2026-09-07T18:32:02.581166+00:00`, which is 8 September in India. It records
Python 3.11.15, NumPy 2.4.6, nine input hashes, 85 output hashes and zero model
or paid calls.

The run contains 288 bundles, 6,912 undispatched requests, 89,856 raw mock
responses across 13 policies, and 240,000 synthetic studies in 48 cells.
The sample grid and screen configuration remain unchanged. At 288 bundles,
all four required sensitivity scenarios pass. Calibration does not clear
its upper confidence bound requirement. The exact findings and scientific
qualifications are in [the findings report](PARTNER_STATE_OFFLINE_FINDINGS_20260907.md).

I inspected the full PNG and the smoke PNG. The axes, sample counts, uncertainty
bands and distinction between primary tests and the complete decision are
legible. Both explicitly say they are simulations, not LLM performance.

### Independent artifact verification

Added `scripts/verify_partner_offline.py`, a read only checker that validates
all hashes, replays allocation and prompts, regenerates all mock responses,
reanalyzes each policy and recalculates the verdict. Manifest paths must stay
inside their root. Its two tests reject traversal and escaping symlinks.

```bash
.venv/bin/python scripts/verify_partner_offline.py \
  results/partner_state_offline_20260907
```

Result: **VERIFIED_OFFLINE_ARTIFACTS**. All 85 output files and nine inputs
matched, and all 13 mock policies regenerated and reanalyzed identically.
The numerical Monte Carlo replay check is separate from this first verification.

I deliberately reran the smoke command against its existing directory. It
exited with `FileExistsError`, as required. All 49 archived smoke output hashes
still matched afterwards. This is an expected refusal, not an unresolved test
failure or a lost experiment.

### Additional stimulus audit

Canonical word counts were compared for familiar, NEAR and TRANSFER messages
in both splits. NEAR and TRANSFER use the same clause inventory but have
unequal per candidate lengths. The exact values are in the findings report.
No wording was modified after observing the lexical retrieval policy's pass.
That policy's result remains visible rather than being removed as an
inconvenient alternative explanation.

### Reproducibility replay

The full command was also launched into
`results/partner_state_offline_replay_20260907` using the same source and seed.
This repeats the same 240,000 studies. It is not an extra 240,000 independent
observations and is not pooled into the reported Monte Carlo intervals.
The replay completed in **647.31 seconds**, at
`2026-09-07T18:41:17.048222+00:00`. Both executions returned
OFFLINE_SCREEN_NO_GO.

```bash
.venv/bin/python scripts/verify_partner_offline.py \
  results/partner_state_offline_20260907 \
  --replay-dir results/partner_state_offline_replay_20260907
```

Result: **VERIFIED_OFFLINE_ARTIFACTS**, with
`full_simulation_replay_hashes_match: true`. All **85 output hashes** matched
between the executions, including raw mock responses, every simulation cell,
the summary, verdict, report and PNG. The nine source/config hashes matched.
Only manifest runtime and timestamp differ. The verifier also regenerated
and reanalyzed all 13 policies. The compact
[verification record](partner_state_offline_verification_20260907.json) retains
these checks separately from the frozen run directories.

### Scope and preservation checks

The local README now links the implementation, methods and no go findings.
It explicitly distinguishes completed engineering from deployment clearance.
No change has been pushed and the Google Doc remains untouched.

The original machine readable design still hashes to
`ef68ae00ea8421bb21e99ef2901af0a69365f3c07adda0d3f8229969566a6dda`.
The offline screen specification hashes to
`45cede3cbadeafc5dcbeb17388df375bcf67ac7c73e5a84da7a18635acdeeed5`.
All implementation hashes are in the completed run manifest. No source input
was changed while the full screen or replay was running.

`git diff --name-only` reports only the preexisting tracked README edit; the
new research modules and artifacts are untracked additions. Existing tracked
source, old specifications and old result files have no diff. The new prose,
source and tests were scanned for em dashes and en dashes, with no matches.
`git diff --check` passed after the documentation edits.

Additional SHA256 values at handoff:

- Read only verifier: `28c6e1b986aa8e77b9ba9f3adff8834b4b5409a8f8c18bf043496085e413e0cc`.
- Methods: `2ad121e977727b4a803e11fce4294f2aadd9fe4d3e87606bfcc303ce8fac20fb`.
- Scientific verdict: `953012d954b4af5a61cd5a349f3361732929a401489e3f7d15ca17cf9842fe17`.

No background job from this work remains running. No paid service was used.
The remaining work is a bounded statistical calibration review and stimulus
validation before any model pilot, not an unresolved software test failure.

## Skills and workflow

The experimental design skill informed balanced allocation, the independent
unit, separated random streams and information boundaries. The statistical
power skill informed joint continuation probability, null calibration and
missingness stress scenarios. Statistical analysis guidance informed the
conservative bounds and explicit distinction between empirical bootstrap
calculation and population coverage. Matplotlib guidance informed labelled
uncertainty plots that distinguish primary tests from the complete decision.

The existing GSD import source manifest remains pending its discovery approval.
That is separate from local research engineering. No `.planning/` phase or
GSD milestone completion is claimed. No subagents were dispatched.
