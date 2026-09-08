# Calibration repair and paired stimulus audit work log

Local project date: 8 September 2026, Asia/Kolkata. The session started on
7 September in UTC. This log describes the bounded follow up authorized by
the user, not a new series of paid experiments.

## Scope and scientific record

The prior failed screen, its source files and all historical model results
are retained. There was no new model selection, API call, GPU deployment,
human labelling, activation work, Git commit or GitHub push in this stage.
No credential was needed or read.

The experimental design and statistical power skills guided the fixed
comparison and sensitivity grid. The statistical analysis skill guided
uncertainty reporting, nonzero coverage checks and limitations. These skills
do not certify scientific success or authorize spending.

Before fresh simulated studies or policy outputs, I wrote:

- `docs/PARTNER_REPAIR_PLAN_20260908.md`, the fixed human readable plan.
- `docs/partner_repair_20260908.json`, seeds, sizes and gate definitions.
- `docs/partner_wording_candidate_20260908.json`, exactly one wording draft.

The parent config and original design are checked by SHA256. Each runner
also saves its input hashes before running and checks them again at completion.
There are no edits to the old `partner_*.py` modules or old screen runner.

## Implementation

### One interval candidate

Added `src/stratified_intervals.py`. It uses within stratum sample variance
with divisor n minus one, combines the variance components with fixed
allocation weights, and uses the smallest stratum degrees of freedom in a
Student critical factor. The whole bundle remains the unit of analysis.
Missing output lower and upper bounds remain in every primary and control.
All original effect, confidence, equivalence and validity thresholds remain.

Added `scripts/repair_partner_calibration.py`. It generates fresh datasets
once, then analyzes each with both the old bootstrap and the candidate. The
14 scenarios include all 12 prior scenarios plus two declared null stress
checks. Separate known mean distributions check nonzero coverage and the
effect threshold. It archives every study's decisions, not only passes.

No SciPy or other dependency was installed. Student critical values are
computed by numerical integration and bisection. Tests compare them with
the NIST table and an independent composite Simpson calculation.

### One paired wording audit

Added `src/stimulus_audit.py` and `scripts/audit_partner_stimuli.py`.
The original confirmation bank and the draft use identical aliases, scenario
assignments, history order, frame exposure, target probabilities and random
draws. Only message text changes. Tests assert that isolation directly.

Five shallow policies use visible words and target choices, not analyst
labels. Three mathematical references retain their declared access to frame
annotations or hidden type. All eight policies and all three seeds were
specified before output inspection. The complete prompt ledgers remain
undispatched. Full raw synthetic responses, classifications implicit in the
registered frame vectors, target probabilities and bundle contrasts are saved.

The human review export contains complete candidate messages and neutral
scenarios, with blank human labels and a separate analyst key. Creating this
file is not human validation. The draft is not a production held out split.

### Verification tools

Added `scripts/verify_partner_repair.py` for read only hash checks, reconstruction
of all saved pass flags and rates, verdict reconstruction and deterministic
replay of the first batch of every calibration and coverage cell. It reports
prefix replay separately from a full simulation replay. It can also compare
every scientific artifact hash between two full stimulus runs.

## Tests and implementation failures

1. The first interval test run had 20 passes and one failure. Identical
   decimal 0.1 values produced a tiny floating point variance. Centering each
   sample on its first observation before the variance calculation fixed
   this, while leaving the specified sample variance formula unchanged.
2. After that fix, 137 focused tests passed, including the prior partner
   pipeline, design and verifier tests. The calibration smoke run completed.
3. The first stimulus test run had nine passes and five failures, all caused
   by one incorrect newline assumption in candidate block replacement. The
   original prompt has a blank line before its output instruction. Preserving
   that blank line fixed the implementation before the first stimulus run.
4. All 35 interval and stimulus tests then passed. The stimulus smoke run
   completed. Two additional verifier tests passed separately.
5. The full repository suite passed 993 tests in 687.88 seconds, with no
   failures. Two verifier tests added after collection passed separately and
   were included in a final 37 test focused run, which passed in 3.73 seconds.
   The current covered test set is therefore 995 distinct tests, not a single
   full 995 test run. No test failure was treated as a scientific finding.
6. The first verification export failed with `FileNotFoundError` because its
   output parent directory did not yet exist. The checks themselves had run,
   but no saved verification was claimed. I added creation of the requested
   parent directory, kept exclusive file creation, reran successfully, and
   included that final implementation in the focused test run.

The wording bank itself was not edited after any policy outputs. No extra
method, extra seed or post hoc reversed policy was added to get a pass.

## Interpretation warning noticed during execution

The draft removed positive transfer for the tested word overlap policies,
but the character trigram policy produced a negative transfer contrast.
This is potentially useful information in the wrong direction, not absence
of lexical information. An adversary might invert such a rule. That policy
was not added after seeing these results. The final report must not describe
the draft as free of lexical shortcuts merely because none of the five
prespecified shallow policies achieves the positive complete gate.

## Completed runs and final verification

All planned full runs are complete. Results are in
[the findings](PARTNER_REPAIR_FINDINGS_20260908.md) and
[the generated report](../results/partner_repair_report_20260908/REPORT.md).

| Run | Actual work | Outcome |
| --- | --- | --- |
| Calibration smoke | 1,400 calibration and 800 coverage datasets | Functional completion, not sample selection |
| Calibration smoke replay | Same 2,200 datasets | All 29 scientific artifact hashes match |
| Full calibration | 14 scenarios, four sizes, 5,000 datasets per cell | 280,000 fresh paired method analyses |
| Full coverage diagnostics | Two distributions, four means, four sizes, 5,000 per cell | 160,000 additional datasets |
| Stimulus smoke | 36 bundles, two banks, eight policies | Functional completion only |
| Full stimulus audit | 288 bundles per bank, three seeds, eight policies | 41,472 undispatched prompts and 331,776 raw synthetic responses |
| Full stimulus replay | Same complete audit | All 124 scientific artifact hashes match |

The full calibration and coverage execution took 801.26 seconds. The full
stimulus audit took 162.19 seconds and its replay 221.98 seconds while other
local work was running. Runtime differences are not scientific results.
Python was 3.11.15 and NumPy 2.4.6. No new runtime dependency was installed.

### Actual verification

- The full calibration verifier checked all 95 output files and 13 input
  hashes. It reconstructed decision flags, reported rates and verdicts from
  every one of the 440,000 saved datasets. It regenerated the first 100
  datasets of every calibration and coverage cell: 8,800 duplicate datasets.
  It did not regenerate all 440,000 datasets.
- The smoke verification regenerated all 2,200 smoke datasets, since each
  smoke cell contains one batch. The generic verifier conservatively reports
  `full_simulation_regenerated: false`; the separately compared complete smoke
  replay has matching scientific output hashes.
- The full stimulus replay matched 124 output files and 16 input hashes.
  All planned prompts, raw responses, analyses, inventories and review items
  are included in that comparison.
- The previous offline verifier still passes. Its 85 output files and nine
  input hashes are unchanged, all 13 original mocks regenerate and reanalyze,
  and its already completed full replay matches. Its no go verdict remains.
- Both new plots were rendered and visually inspected for clipping, readable
  labels, uncertainty labels and separation of synthetic results from LLM
  claims. The five generated report artifacts and three report input hashes
  also passed verification.
- An intentional rerun into the existing calibration smoke directory raised
  `FileExistsError`. A subsequent hash verification confirmed that all 29
  smoke artifacts remained unchanged. The expected refusal is not a broken
  experiment or a deleted result.
- `git diff --check` passed. Existing unrelated working tree changes were
  preserved. The local README is updated; no commit or push was performed.

Machine readable checks and JUnit test outputs are in
[`results/partner_repair_verification_20260908/`](../results/partner_repair_verification_20260908/).

### Final scientific boundary

The one candidate interval clears the fixed synthetic screen only at N = 288.
Its worst required sensitivity lower bound is 81.46%; all six null upper
bounds are below 5%. The old method still fails the same fresh screen.

Nevertheless, sparse Bernoulli coverage is poor at small N, and the mean
0.10 diagnostic at N = 288 covers only 96.84% against nominal 97.5%. The
character overlap reversal warning also persists across all three wording
seeds. No second interval, changed bank, added seed or reversed adversary was
run to replace those inconvenient findings.

The bounded work is finished, but paid confirmation is not approved. Human
semantic validation, a separate evaluation bank and a test that distinguishes
reward values from beliefs remain substantive requirements. No new model,
latent state or successful silent updating claim is supported by this stage.
