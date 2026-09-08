# History diagnostic work log

## Scope

The user approved a local diagnostic design and synthetic checks after the
baseline comparison. This does not authorize paid inference or reopening the
stopped V5 to V8 designs. The existing uncommitted baseline analysis and README
changes were present at the start and are preserved.

The experimental design skill led to exact within pair matching and pair level
inference. The statistical power skill led to prospective sensitivity, explicit
Monte Carlo uncertainty, null tests and dependent pair sampling checks.
Matplotlib was used for the diagnostic plots. No new dependency was needed.

## Plan before computation

Created HISTORY_DIAGNOSTIC_PLAN_20260907.md and its JSON companion before
generating histories or inspecting power. The intervention preserves each
frame's own outcome stream and the last three events, changing only the global
interleaving. This gives exact invariance for ordinary chosen action reward
learning. Global recency rules are declared as counterexamples before testing.

The reference parameters and priors come from the completed V4 baseline fits.
They are planning inputs, not true internal parameters. No new LLM response is
used in stimulus selection. The local work has a finite bank and sample size
grid, with no outcome driven extensions.

## Implementation and tests before the screen

Implemented src/history_diagnostic.py and scripts/design_history_diagnostic.py.
The script can construct prompts and simulate mathematical policies but has no
dispatch path to an inference provider. Original source modules are reused
without modification. Prompt text and analyst labels are exported separately.

The first diagnostic test run passed all 17 tests in 0.69 seconds. The combined
diagnostic and baseline tests passed all 46 tests. Checks included equality of
Q states at six learning rates, static Bayes invariance, exact binomial tails,
null calibration under two within pair dependence patterns, text matching,
opaque requests, sham identity, deterministic construction and synthetic
recovery. Additional CLI and artifact refusal checks were then added before
running the production screen.

Both individual one sided null tests, as well as their joint rejection rule,
are included in the null calibration requirement. Agreement of the effect
direction across all five planning priors is recorded as a sensitivity result,
not an extra undeclared construction gate.

## Executed screen

Command:

```bash
.venv/bin/python scripts/design_history_diagnostic.py \
  --out-dir results/history_diagnostic_20260907
```

The screen ran from 13:22:57 to 13:23:23 UTC on 7 September 2026. It built
18,432 candidate histories, retained all 576 selected pairs and prepared 1,536
requests including identical prompt shams. None was dispatched. All matching
and request boundary checks passed. All pairs had the same positive reference
orientation under all five historical fitted priors.

Evaluated 17 policy candidates. The power grid contained 456 scenario cells,
5,000 simulated studies each, for 2,280,000 simulated studies. Closed set
recovery used a further 102,000 simulated datasets. These are cheap numerical
simulations, not millions of LLM calls or real observations.

The sensitivity gate failed at every declared N. At 576 pairs, nominal dynamic
beliefs with independent responses and no missing pairs passed both tests in
56.32% of simulated studies. Under the required half strength effect, 10%
unusable pairs and negative dependence bound, joint power was 8.46%, Wilson
95% interval [7.72%, 9.26%]. No sample size was selected.

The specificity challenge also failed. The five and eight event window rules,
which store recent outcomes but no partner type, produced a positive diagnostic
almost always at the maximum sample size. Discounted evidence rules also
produced the pattern. This is a counterexample to a partner representation
interpretation, not a Type I error under the narrower invariance null.

The original V4, baseline comparison, earlier protocols and paid run state were
not changed. No grid, effect assumption, alpha level or stopping criterion was
relaxed after these results.

## Verification

- Initial new tests: 17 passed in 0.69 seconds.
- Combined diagnostic and baseline suite: 46 passed in 6.74 seconds.
- After additional CLI checks: 49 passed in 7.18 seconds.
- Relevant regression suite: 108 passed in 32.78 seconds. This includes both
  new modules and the original target, bank, prompt, experiment, analysis,
  open weight runner and prompt variant tests. It is not the full repo suite.
- The statistical power skill's original simulate_power harness was run as a
  separate invariant null sanity check: N = 72, 5,000 simulations, negative
  dependence, 10% loss, alpha = 0.025. It reported a joint rejection rate of
  about 0.4%, with a Wilson interval approximately [0.2%, 0.6%].
- All 17 initial output hashes and all source and input hashes matched.
- All new Python files compiled successfully.

Visual inspection found the power plot legend obscured part of the curves.
Only the legend position was changed. The recovery explanation was also
clarified: balanced counts make static beliefs and history frequency identical
under the shared choice settings, so their unresolved ties are expected. No
numerical analysis changed. The initial driver source hash and the updated
source hash are retained in the result manifest's presentation update record.

A final plan audit found that the per frame mean contrasts were exported, but
the planned descriptive per frame test rates were missing from power.csv.
Added those secondary columns without changing either primary test, the
simulation seeds, scenarios, or decision rule. The expanded table is checked
against every original column before publication. These added outputs do not
rescue or replace either failed gate.

The first secondary table replay failed its equality assertion at the scenario
name, before changing any result file. Diagnosis: saving policy predictions
with sorted JSON keys changed dictionary iteration order on reload, while the
Monte Carlo seed coordinates depended on that order. The original end to end
driver was deterministic, but a reload was not equivalent. Added an explicit
policy order matching the original construction order and a regression test
that reload ordering leaves both power and recovery unchanged. This preserves
the original seed assignment; it does not choose new seeds or change a model.

## Final verification and handoff

The corrected reload passed: every original column in all 456 power cells and
both scientific verdicts remained unchanged. The new descriptive per frame
columns are now present. The manifest records the source change and updated
artifact hashes separately from the original run.

The latest combined module tests passed all 49 tests in 7.85 seconds. A final
relevant regression run after the ordering fix passed all 108 tests in 31.76
seconds, using:

```bash
.venv/bin/python -m pytest -q \
  tests/test_history_diagnostic.py tests/test_choice_baselines.py \
  tests/test_controlled_target.py tests/test_controlled_messages.py \
  tests/test_controlled_focal_agent.py tests/test_controlled_experiment.py \
  tests/test_controlled_analysis.py tests/test_controlled_open_weight_runner.py \
  tests/test_prompt_variant.py
```

This was the relevant regression suite, not the full repository test suite.
Earlier intermediate runs are retained above instead of replaced by the most
recent result.

Further checks actually run:

- A fresh end to end replay matched all 15 non PDF outputs byte for byte,
  including both PNG figures, the candidate pool, prepared requests, power
  table and recovery table. PDF byte equality was not required because their
  creation metadata can vary.
- All 17 output hashes, nine source hashes, two input hashes and the frozen
  JSON plan hash matched the final manifest.
- A separate scalar implementation, without importing either analysis module,
  reconstructed all 3,456 selected history predictions for reward learning,
  static beliefs and dynamic beliefs. Every probability agreed within 1e-13.
- All 576 selected pairs were checked against their saved candidate pools.
  Selected indices were the declared minimum and maximum reference predictions.
  Each frame's outcome sequence, event counts and final three events matched.
- All 1,536 request records had only opaque request IDs and system/user text.
  Current decision blocks matched within each pair. All 192 sham pairs had
  identical prompts. Checked analyst metadata strings were absent from prompt
  text. This is a boundary check, not proof against every linguistic confound.
- Both plots were visually inspected. The revised power legend leaves the
  plotted curves visible. Sixty local Markdown link targets existed.
- Git whitespace checking passed. No em dashes were found in the new diagnostic
  source, authored notes or generated report. Exact historical prompt wording
  was preserved.

No new focal responses, paid calls, Google Doc edits, commits or GitHub pushes
were made. Existing baseline artifacts were preserved. The diagnostic stops at
the local feasibility screen: insufficient sensitivity and a demonstrated
recency explanation. Neither failed gate was relaxed. Recommended next work is
to incorporate these limitations and the baseline comparison into the main
writeup, not to launch a paid diagnostic or another unreviewed redesign.
