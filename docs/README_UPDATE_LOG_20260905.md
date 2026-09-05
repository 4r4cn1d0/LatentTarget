# README update and verification

Date: 5 September 2026.

## Scope

Updated the repository landing page to reflect the completed experiments and
the current interpretation in the Google Doc. Only `README.md` and this log
belong to this update. Existing edits to writeup exports, figure scripts, the
swap figure, and other local files were left untouched.

The GSD documentation skill was inspected. Its referenced workflow file was
missing locally, so source inspection and command verification were performed
directly. No additional documentation framework was introduced.

## What changed

- Replaced the accumulated status history with one current summary, a results
  table, and a compact history of the stopped designs.
- Corrected the claim that P1 was a clean replication or necessarily conservative.
  It failed the response validity threshold, and failures depend on condition.
- Removed the claim that argmax agreement makes beliefs and choices one object.
  E1 changes both output format and visible prediction history; it cannot isolate
  their contributions or establish the absence of an internal belief.
- Kept the failed revision test, default preference, unfinished human labels,
  simple alternative learning rules, and limitations close to the positive result.
- Distinguished 45 message templates from 90 rendered validation messages.
- Replaced the legacy 8/10 round instructions with the actual 20 round V4 design,
  including a silent swap after round 10 and reserved wording in rounds 16–20.
- Added a local workflow that needs neither a model download nor API credentials.
- Disclosed that the four large V4 raw JSONL logs are not tracked by Git. Result
  summaries and manifests are committed; a public raw data release is unfinished.
- Distinguished V3 architecture preflight checks from a scientific activation,
  probing, or steering experiment.
- Linked the current Google Doc and retained historical reports and specifications
  without modifying frozen scientific artifacts.

## Evidence inspected

Checked `config.py`, the V4 message bank, target, prompt and parser code, runner,
analysis functions, and command argument definitions. Compared README results
with the four saved analysis summaries and corresponding committed manifests.
Checked the model identifiers and immutable revisions against their frozen specs.
Inspected Git tracking rather than assuming locally present raw files ship in a
fresh clone.

The four full history learning gains agree with the stored summaries:

| Run | Records | Gain with 95% episode bootstrap interval | Valid responses |
| --- | ---: | --- | ---: |
| V4 | 7,200 | 0.187 [0.083, 0.290] | 98.47% |
| R1 | 7,200 | 0.040 [−0.007, 0.093] | 100% |
| E1 | 3,600 | −0.020 [−0.053, 0.010] | 100% |
| P1 | 7,200 | 0.207 [0.110, 0.307] | 89.82% |

## Checks actually run

Python: 3.11.15, using the existing local virtual environment.

1. The seven focused V4 test files listed in the README: **59 passed in 13.68
   seconds**. The full project test suite was not rerun for this documentation
   change.
2. Frozen open weight runner with `--run-id readme_plan_check --dry-run`: **PASS**.
   Verified 360 planned episodes, 7,200 planned generations, and the blind bank
   gate. No weights were loaded and no real model outcomes were generated.
3. Initial mock smoke run: the runner's defaults included the two elicited
   conditions, producing 54 episodes and 1,080 rows. This exposed a mismatch with
   the intended README example. The command was corrected to name the five V4
   conditions explicitly, rather than changing the code's defaults.
4. Corrected README mock command: **completed 36 episodes and 720 rows**, with a
   completed manifest in a fresh temporary directory.
5. Analysis of that mock log with 200 bootstrap draws and 1,000 permutations:
   **completed**, producing summary JSON, three CSV tables, and five plots in
   both PNG and PDF. Design integrity passed. The random response effect gate
   and both inference gates failed at this tiny sample, so the scientific
   verdict was STOP. This is not a positive scientific result.
6. Dedicated `validate_controlled_v4.py` with its default sample sizes and
   settings: **all five checks passed**. The Bayesian mock passed the pattern
   test but was not scientific evidence. Random and invalid output controls
   were rejected as intended.
7. README link checks resolved every local link to a file or directory included
   in the commit. Numeric checks matched the four reported learning intervals
   to their result JSON. Punctuation and credential pattern checks passed.
8. `git diff --check` passed before staging.

Mock and validation artifacts were written to fresh temporary directories, not
over the committed research outputs. The existing environment was reused; the
installation instructions were not tested in a newly provisioned environment.
No paid compute, real model generation, new labels, or scientific reruns were
performed. No API keys or raw experimental logs were added to the commit.
