# Baseline comparison work log

## Scope and starting point

7 September 2026. The user approved the proposed comparison against simpler
explanations using existing data. No paid computation or new data collection
is in scope. No human labelling is performed. Existing raw logs will not be
published, and the Google Doc and frozen results will not be changed.

The worktree was clean at the start. The latest commit already included the
previous writeup changes. Source inspection confirmed that shuffled history
donors share episode_index with recipients, so this is the grouping unit.
All four raw logs and their manifests are available locally.

The statistical analysis skill guided the separation of exploratory results,
dependent observations, missing responses and fitting versus evaluation. The
Matplotlib skill guides diagnostic plots. GSD's docs update skill was read,
but its referenced workflow file is missing; documentation is checked directly
against code and executed commands instead.

## Before fitting

Created BASELINE_COMPARISON_PLAN_20260907.md and its numerical JSON companion
before fitting or inspecting new model comparison scores. Only source code,
one record's schema, file availability and registered parameters were checked
first. Historical results were already known. This is not a preregistration.

## Implementation and first tests

Implemented src/choice_baselines.py and scripts/compare_choice_baselines.py.
The prediction interface accepts only earlier frame and reward pairs. Nine
baseline families and two inner selected model sets share the declared lapse
floor. Every outer fold performs its own inner selection and training prior.
The original experiment runner, prompts, simulator and gates are untouched.

The first new test run passed all 27 tests in 3.08 seconds. This included
synthetic recovery for known reward learning and dynamic belief policies,
held out response mutation, hidden metadata mutation, history donors, missing
or duplicate rounds, analytic updates, fallback handling and repeatability.
The CLI help command also ran successfully. These are engineering tests, not
new evidence about the focal models.

The skill's full assumption utility imports SciPy and Seaborn, neither of which
is installed in the project environment. Rather than add dependencies for a
Gaussian test we do not need, the analysis implements its standard 1.5 IQR
outlier diagnostic in NumPy and checks dependence through the design. All
outliers remain included. No Gaussian or equal variance assumption is made.

## Executed comparison

Command:

```bash
.venv/bin/python scripts/compare_choice_baselines.py \
  --out-dir results/baseline_comparison_20260907
```

The run completed from 12:44:35 to 12:45:05 UTC on 7 September 2026. It read
25,200 existing records from 1,260 episodes across four runs. Each run passed
the original design audit and the new history reconstruction checks before
fitting. Twenty seed bundles per run were divided into five outer folds and
four inner folds. There were no API calls, GPU jobs or new focal generations.

Results are in results/baseline_comparison_20260907. There are 277,200 saved
probability rows: 25,200 original choices times nine baseline families and two
selected model sets. The report includes all families and controls. Tables
also include valid response sensitivity, individual rounds, stable types and
all six directed swap transitions. Every failed response remains recorded.

The original Qwen run favoured reward learning over the selected belief model
on outer test prediction loss, 0.4973 versus 0.5128. Gemma favoured static
beliefs over the selected simple set, 0.1750 versus 0.2017, but its individual
reward learning family was close at 0.1792 and simple family selection was
unstable. E1 and P1 showed small differences with intervals spanning zero.
These exploratory comparisons do not identify internal representations.

No numerical settings were changed after the real comparison. The exact plan
hashes are preserved in the result manifest. The full planned comparison is
reported, including the result favouring the belief set in Gemma.

## Verification completed

- Initial new suite: 27 passed in 3.08 seconds.
- New suite plus existing prompt and analysis tests: 41 passed in 19.20 seconds.
- Expanded new suite, including deterministic gzip and CLI refusal checks:
  29 passed in 3.13 seconds.
- Final relevant regression suite: 88 passed in 22.07 seconds. It included
  the new tests plus target, message bank, focal agent, experiment, analysis,
  open weight runner and prompt variant tests. The full repository suite was
  not run in this stage.
- All three new Python files compiled successfully. Git diff whitespace check
  passed.
- Both generated figures were visually inspected. Text, tick labels and
  uncertainty labels were legible, with no cropping or overlaps.
- A separate audit read the exported CSV probability rows without calling the
  baseline scorer. It recomputed log loss, checked normalization, unique keys,
  fold membership and the primary grouped contrasts for all four runs.
- All 41 recorded output hashes and all four recorded source hashes matched.
- All 50 local links checked across the README and new documentation resolved.
  New authored prose and code contain no em dashes. Model provenance contains
  configuration metadata, not credentials.

The independent audit recovered simple minus belief loss differences of
-0.015512 for V4, +0.026679 for R1, +0.000865 for E1 and -0.003020 for P1.

A second complete comparison was also run in a temporary directory with the
same plan. This was another CPU only replay of the same data, not another
experiment. Artifact equality is checked separately below.

Replay verification found 39 of 39 non PDF output files byte identical,
including all row probabilities, fold audits, tables, summaries, the report and
both PNG figures. PDF creation timestamps were excluded from the byte check.
The replay is at
`/var/folders/mk/33rfxgzn32318ntchzzgtm680000gn/T/tmp.MPhwQsfoux/replay`.

## Documentation and remaining limits

Added a plain language findings note and updated the local README, including
the previously stale next step about fitting these baselines. The Google Doc,
original result files, frozen specifications, and existing experiment code were
not edited. Human validation remains unfinished. No raw transcript release or
GitHub push was performed in this stage.

The next recommended work is a discriminating diagnostic design, using the
fitted rules to construct histories where predictions disagree and checking
synthetic recovery and power before a new focal run. This analysis does not
approve paid runs or reopen any stopped scientific gate.
